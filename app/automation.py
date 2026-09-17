"""Bounded foreground workflow. Stock assumptions never become observed quantities."""
import time
from . import capture
from .inventory_recognition import compact,scroll_label_candidates
from .flow_vision import Vision
from .name_candidates import distance,material_candidate_allowed
from .storage_scroll import scroll_page
from .name_memory import NameReviewRequired,NameReviewCompleted

class SkipMaterial(RuntimeError):
    """No transfer was attempted; material may be completed manually."""

class ScreenTimeout(RuntimeError):pass

class Runner:
    def __init__(self,window,safety,session,journal,entries,script,log=lambda message:None,on_progress=lambda event:None,name_memory=None,on_name_review=None):
        self.window=window;self.safety=safety;self.session=session;self.vision=Vision(session)
        self.journal=journal;self.batch=journal.batch;self.entries=entries;self.script=script;self.log=log
        self.name_memory=name_memory;self.on_name_review=on_name_review;self.storage_mode=False
        self.on_progress=on_progress;self.current_item="";self.current_quantity=None
    def progress(self,step,item=None,quantity=None):
        if item is not None:self.current_item=item
        if quantity is not None:self.current_quantity=quantity
        self.on_progress({'step':step,'item':self.current_item,'quantity':self.current_quantity})
        self.log(step+(f' | {self.current_item} × {self.current_quantity}' if self.current_item else ''))
    def check(self):self.safety.check(self.window)
    def rest(self,seconds=.3):
        if self.safety.cancelled.wait(seconds):raise RuntimeError('工作已暫停')
        self.check()
    def screen(self):
        self.check();image=capture.capture(self.window)
        result=self.vision.observe_storage(image) if self.storage_mode else self.vision.observe(image)
        self.check();return result
    def click(self,point):self.safety.click(self.window,*point);self.rest()
    def key(self,key):self.safety.key(self.window,key);self.rest()
    def inventory_screen(self):
        self.check();image=capture.capture(self.window)
        result=self.vision.observe_inventory_controls(image);self.check();return result

    def wait(self,predicate,reason,seconds=12,reader=None):
        self.progress(f'等待畫面驗證（重試期限 {seconds} 秒）：{reason}')
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            s=(reader or self.screen)()
            try:
                if predicate(s):return s
            except NameReviewCompleted:
                end=time.monotonic()+seconds
                continue
            self.rest(.3)
        raise ScreenTimeout(reason+'；已暫停，沒有自動重試動作。')
    def scroll_storage(self,image,direction):
        return scroll_page(image,
            lambda x,y,n:self.safety.scroll(self.window,x,y,n),self.rest,
            lambda:capture.capture(self.window),direction,self.log)
    def storage_top(self,image):
        self.progress('捲動至保管箱清單頂端')
        for _ in range(100):
            image,moved=self.scroll_storage(image,1)
            if not moved:return
        raise RuntimeError('向上捲動超過安全上限，尚未確認清單頂端；請檢查畫面。')

    def item_title(self,screen,name):
        exact=screen.item_title(name)
        if exact is not None:return exact
        candidates=screen.tooltip_titles()
        self.log('名稱 OCR 重試：提示裁切、彩色 3 倍、灰階 2 倍、反相 3 倍、二值化 3 倍')
        retried=self.vision.tooltip_retry(screen.image)
        self.check()
        self.log('提示標題讀回：'+('、'.join(x.text for x in retried) or '沒有可辨識標題'))
        combined=candidates+retried
        conflict=any((name=='羊毛' and ('級' in x.text or '高' in x.text) and x.text.endswith('羊毛'))
                     or x.text==name+'+' or (name.endswith('+') and x.text==name[:-1])
                     or (x.text!=name and x.text in {m.name for m in self.batch.materials}) for x in combined)
        if conflict:return None
        recovered=[x for x in retried if x.text==compact(name)]
        if len(recovered)==1:return recovered[0]
        if self.name_memory is None:return None
        if len(candidates)!=1:candidates=list({x.text:x for x in combined}.values())
        if len(candidates)!=1:return None
        title=candidates[0]
        if self.name_memory.matches(title.text,name):
            self.log(f'使用玩家確認的名稱：{title.text} → {name}')
            return title
        if self.name_memory.allowed(title.text,compact(name)):
            review=NameReviewRequired(name,title.text)
            if self.on_name_review is None:raise review
            self.on_name_review(review,self.window)
            raise NameReviewCompleted()
        return None

    def verify_quantity(self,name,expected):
        # Retry only observations. Never retype, dismiss, or confirm during retries.
        attempt=0
        while attempt<3:
            s=self.screen()
            dialog=s.quantity_dialog()
            attempt+=1
            observed=self.vision.entered_quantity(s.image) if dialog else None
            self.log(f'數量欄核對 {attempt}/3：數量視窗={"通過" if dialog else "未確認"}；要求 {expected}；'
                     f'讀回 {observed if observed is not None else "無法辨識"}')
            if observed==expected:return observed
            if observed is not None:
                raise SkipMaterial(f'{name}：要求 {expected}，讀回 {observed}；數量不符，未按下領取。')
            if attempt<3:self.rest(.4)
        raise SkipMaterial(f'{name}：要求 {expected}，三次畫面核對仍不明；未按下領取。請查看除錯紀錄中的視窗與數字結果。')

    def withdrawal(self):
        self.storage_mode=True
        self.journal.ready()
        self.progress('檢查公用保管箱畫面')
        s=self.screen()
        if not s.storage():raise RuntimeError('請先開啟公用保管箱的「全部」頁面，關閉物品提示及數量視窗。')
        for item in self.batch.materials:
            if item.name in self.journal.data['withdrawn']:continue
            if item.name in self.journal.data.get('skipped',{}):continue
            try:s=self.withdraw_one(item,s)
            except (SkipMaterial,ScreenTimeout) as error:
                if self.journal.data['pending'] or item.name in self.journal.data['withdrawn']:raise
                self.check()  # F8/lost focus always stop, never become a skip.
                self.journal.skip(item.name,str(error))
                self.log(f'待手動補領：{item.name} × {item.quantity}；{error}')
                s=self.restore_storage()
        skipped=self.journal.data.get('skipped',{})
        if skipped:
            lines=[f'{m.name} × {m.quantity}：{skipped[m.name]}' for m in self.batch.materials if m.name in skipped]
            self.log('本批次待手動補領清單：\n'+'\n'.join(lines))
            self.safety.pause('自動領取已結束。請依「待手動補領」清單補齊，再確認已補領後進行交付。')
        else:self.safety.pause('素材領取批次結束。請自行移動到任務佈告欄，再按開始交付。')
        return self.safety.reason

    def restore_storage(self):
        # Allow closing animations/OCR misses to settle without sending Escape
        # again to the same overlay (which could close storage itself).
        dismissed=set()
        for attempt in range(6):
            s=self.screen()
            if s.storage():return s
            dialog=bool(s.quantity_dialog())
            tooltip=bool(s.tooltip_titles() or s.has('獲得方法'))
            kind='quantity' if dialog else 'tooltip' if tooltip else None
            self.log(f'返回保管箱核對 {attempt+1}/6：公用頁={bool(s.shared())}；'
                     f'背包標題={bool(s.has("背包",(670,80,820,180)))}；'
                     f'數量視窗={dialog}；物品提示={tooltip}')
            if kind and kind not in dismissed:
                self.key(0x1B)
                dismissed.add(kind)
            if attempt<5:self.rest(.5)
        raise RuntimeError('未回到公用保管箱；六次畫面核對仍未確認，手動補領清單已保留。請查看除錯紀錄中的畫面標記。')

    def wait_transfer_prompt(self,seconds=12):
        self.progress('等待物品提示的移至背包按鈕就緒')
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            self.check();image=capture.capture(self.window)
            ready=self.vision.transfer_prompt_ready(image);self.check()
            if ready:return
            self.rest(.15)
        raise ScreenTimeout('物品提示的移至背包按鈕尚未就緒；未送出 Space。')

    def withdraw_one(self,item,s):
        self.progress('搜尋素材',item.name,item.quantity)
        target=None;end_reached=False;rewound=False
        for page in range(150):
            # The preceding confirmed transfer already supplied a fresh screen.
            if page:s=self.screen()
            if not s.storage():raise RuntimeError('保管箱畫面已變更；停止搜尋。')
            self.progress(f'辨識保管箱第 {page+1} 次掃描')
            names=self.vision.storage_names(s.image)
            self.log('本頁首次多方法 OCR：反相、彩色、灰階、二值化、加高裁切')
            for label in self.vision.storage_names_retry(s.image):
                if not any(x.text==label.text and abs(x.point[0]-label.point[0])<30 and abs(x.point[1]-label.point[1])<30 for x in names):names.append(label)
            self.check()
            self.log('本頁辨識名稱：'+('、'.join(x.text for x in names) or '沒有可辨識名稱'))
            # Multiple OCR variants of one cell are not separate stacks, and a
            # shortened grade/plus reading must not defeat a conflicting reading.
            blocked=[x for x in names if (item.name=='羊毛' and x.text.endswith('羊毛') and ('級' in x.text or '高' in x.text))
                     or x.text==item.name+'+' or (item.name.endswith('+') and x.text==item.name[:-1])]
            names=[x for x in names if not any(abs(x.point[0]-bad.point[0])<30 and abs(x.point[1]-bad.point[1])<30 for bad in blocked)]
            found=[x for x in names if x.text==compact(item.name)]
            if not found:
                # This only selects a tooltip to inspect. Withdrawal still requires
                # an exact full material name in that tooltip.
                ranked=sorted([(1-distance(x.text,compact(item.name))/max(len(x.text),len(compact(item.name))),x)
                               for x in names if material_candidate_allowed(x.text,item.name) and x.text.count('+')==item.name.count('+')],key=lambda pair:-pair[0])
                # Compare different physical cells, not OCR spellings of one cell.
                # Keep the best-scoring spelling at each location. Two actual cells
                # with similarly good names remain ambiguous.
                cells=[]
                for score,label in ranked:
                    if not any(abs(label.point[0]-other.point[0])<30 and abs(label.point[1]-other.point[1])<30 for _,other in cells):
                        cells.append((score,label))
                if cells and cells[0][0]>=.66 and (len(cells)==1 or cells[0][0]-cells[1][0]>=.08):found=[cells[0][1]]
            # Observed truncated OCR is a tooltip candidate, never a material identity.
            if not found and item.name=='洋蔥':
                found=[x for x in names if x.text=='洋蒽']
            if not found and item.name=='箭花':
                found=[x for x in names if x.text=='花']
            if len(found)==1:target=found[0];break
            if len(found)>1:raise SkipMaterial(f'{item.name} 有多個堆疊；不讀庫存數量時不能安全選擇足量堆疊。')
            if not rewound:
                self.storage_top(s.image);rewound=True
                continue
            self.progress(f'未找到 {item.name}，繼續向下捲動（第 {page+1} 頁）')
            _,moved=self.scroll_storage(s.image,-1)
            if not moved:
                end_reached=True
                self.log('連續兩次向下捲動無位移；清單可能已到底，或遊戲未接受滾輪。')
                break
        if target is None:
            if end_reached:
                raise SkipMaterial(f'未找到 {item.name}，且重試後無法再向下捲動（已到底或滾輪未生效）；請核對清單。未領取。')
            raise SkipMaterial(f'搜尋 {item.name} 達到安全上限，尚未確認到底；未領取。')
        self.progress(f'選取「{target.text}」→ {item.name}，沿用本次清單辨識')
        self.click(target.point)
        self.wait_transfer_prompt()
        self.key(0x20)
        # The selected list cell supplies identity for this action only.
        # Verify the dialog and numeric field without re-reading the item title.
        s=self.wait(lambda s:s.quantity_dialog(),'未確認移至背包數量視窗')
        self.progress('清除預設數量並輸入領取量')
        self.click((960,788));self.rest(.5)  # Allow the quantity field to receive focus.
        self.safety.number(self.window,item.quantity)
        self.safety.scroll(self.window,80,90,0);self.rest(.5)
        self.progress('核對輸入的領取量')
        observed=self.verify_quantity(item.name,item.quantity)
        self.progress('送出領取，準備下一項')
        self.journal.begin('withdraw',item.name)
        # User-selected policy: a successfully dispatched claim counts as retrieved.
        # Persist immediately, before any cancellable animation wait or capture.
        self.safety.click(self.window,960,902)
        self.journal.confirm();self.progress('已領取')
        self.log(f'領取已送出：{item.name} × {item.quantity}；依設定視為已入背包。')
        self.rest()
        return self.wait(lambda s:s.storage(),'等待保管箱清單，以處理下一項')
    def expected_tracker(self,s,q):
        tail=q.quest.replace('：',':').split(':',1)[-1].strip()
        return s.tracker(tail) or s.tracker(q.material)
    def open_quests(self):
        self.key(0x49)
        s=self.wait(lambda s:s.find('道具',(700,850,1230,950)) is not None,'等待背包道具分類',reader=self.inventory_screen)
        self.click(s.find('道具',(700,850,1230,950)).point)
        s=self.inventory_screen()
        if s.selected_tab('任務'):return s
        tab=s.find('任務',(700,95,1260,175))
        if tab is None:
            self.progress('橫向拖曳篩選列至末端，尋找任務')
            self.safety.drag(self.window,(1185,135),(775,135));self.rest(.2)
            s=self.inventory_screen()
            # Some game builds do not accept dragging. Use the known E shortcut,
            # but read only the small header/footer between keys, not the whole screen.
            for step in range(7):
                if s.selected_tab('任務'):return s
                tab=s.find('任務',(700,95,1260,175))
                if tab is not None:break
                if step==0:self.log('拖曳後任務尚未顯示；改用 E 快速切換並局部驗證。')
                if not s.find('道具',(700,850,1230,950)):raise RuntimeError('背包畫面已變更；停止切換。')
                self.safety.key(self.window,0x45);self.rest(.12);s=self.inventory_screen()
            if s.selected_tab('任務'):return s
            tab=s.find('任務',(700,95,1260,175))
            if tab is None:raise RuntimeError('拖曳及快速切換後仍未找到任務篩選；請手動切至任務後重試。')
        self.click(tab.point)
        return self.wait(lambda s:s.selected_tab('任務'),'未確認任務篩選已選取',reader=self.inventory_screen)
    def find_scroll(self,q):
        self.open_quests();self.safety.scroll(self.window,1000,520,35);self.rest(.4)
        seen=set()
        for page in range(20):
            s=self.inventory_screen()
            if not s.selected_tab('任務'):raise RuntimeError('任務清單畫面已變更；停止搜尋。')
            located=scroll_label_candidates(s.image,q.quest,self.entries,self.session)
            if not located:located=scroll_label_candidates(s.image,q.quest,self.entries,self.session,scale=4)
            self.check()
            self.log(f'卷軸搜尋第 {page+1} 頁：'+(' | '.join(raw for _,raw in located) or '未辨識到目標名稱後半段'))
            if len(located)>1:raise RuntimeError('同頁有多個卷軸候選，請整理背包後重試。')
            if located:
                (x1,y1,x2,y2),raw=located[0]
                self.log(f'卷軸名稱：{raw} → {q.quest}；沿用清單格位，不重讀提示名稱。')
                return ((x1+x2)/2,y1-45)
            signature=s.image.crop((700,170,1230,780)).resize((106,122)).tobytes()
            if signature in seen:break
            seen.add(signature);self.safety.scroll(self.window,1000,520,-3);self.rest(.4)
        raise RuntimeError(f'未找到卷軸 {q.quest}，不推算堆疊數量、不啟用其他任務。')
    def quests(self,no_active_confirmed=False):
        self.journal.ready()
        if self.journal.data['active'] is None and not no_active_confirmed:raise RuntimeError('請先確認沒有尚未完成的佈告欄任務。')
        while self.journal.data['completed']<len(self.batch.completions):
            index=self.journal.data['completed'];q=self.batch.completions[index]
            self.progress(f'交付 {index+1}/{len(self.batch.completions)}，第 {q.ordinal}/{sum(x.quest==q.quest for x in self.batch.completions)} 次',q.quest,1)
            if self.journal.data['active'] is None:
                initial=self.screen()
                if initial.report():raise RuntimeError('畫面已有可回報任務，請先完成或恢复追蹤後核對；不啟用第二個。')
                if not initial.world():raise RuntimeError('請站在佈告欄旁，關閉背包與對話後再開始。')
                point=self.find_scroll(q);self.click(point)
                s=self.wait(lambda s:s.find('使用',(600,650,1250,950)) is not None,'等待卷軸使用按鈕')
                self.journal.begin('activate',{'index':index,'identity':None})
                self.click(s.find('使用',(600,650,1250,950)).point)
                s=self.wait(lambda s:self.expected_tracker(s,q) is not None and s.report() is not None,'啟用後任務身份或回報狀態未確認',20)
                self.journal.data['pending']['value']['identity']=self.expected_tracker(s,q).text
                self.journal.confirm()
            else:s=self.screen()
            active=self.journal.data['active']
            if active['index']!=index:raise RuntimeError('進度與已啟用任務不一致。')
            track=self.expected_tracker(s,q)
            if not track or not s.report():raise RuntimeError('現有任務未確認可回報；請恢复追蹤或檢查缺少素材。')
            if active.get('identity') and track.text!=active['identity']:raise RuntimeError('追蹤任務名稱已變更。')
            active['identity']=track.text;self.journal.save()
            self.progress('開啟任務回報，等待交付畫面（最多 30 秒）')
            self.click(track.point)
            dialogues=0;deadline=time.monotonic()+30
            while True:
                s=self.screen()
                if s.submission():break
                if s.dialogue() and dialogues<3:self.key(0x20);dialogues+=1
                if time.monotonic()>deadline:raise RuntimeError('未到達交付畫面；請確認人在佈告欄旁。')
                self.rest(.4)
            if not s.has(q.material,(240,230,440,420)):raise RuntimeError('提交畫面的素材名稱不符。')
            if not s.submitted_ready(q.material):
                self.progress('啟用自動放入')
                self.click((98,625))
                s=self.wait(lambda s:s.submitted_ready(q.material),'自動放入後提交按鈕未就緒；可能素材不足')
            self.progress('提交任務，等待通關（最多 30 秒）')
            self.journal.begin('complete',index)
            self.click((340,558))
            deadline=time.monotonic()+30;dialogues=0
            while True:
                s=self.screen()
                if s.completion(active['identity']):break
                if s.dialogue() and dialogues<3:self.key(0x20);dialogues+=1
                if time.monotonic()>deadline:raise RuntimeError('未確認任務通關；結果待核對，不啟用下一張。')
                self.rest(.3)
            self.key(0x20)
            self.wait(lambda s:s.world() and self.expected_tracker(s,q) is None and not s.report(),'完成畫面／回報追蹤尚未消失')
            self.journal.confirm();self.progress('本次交付已完成')
            self.log(f'已完成 {index+1}/{len(self.batch.completions)}：{q.quest}')
        self.safety.pause(f'{len(self.batch.completions)} 次任務批次已完成；不再啟用剩餘卷軸。')
        return self.safety.reason
