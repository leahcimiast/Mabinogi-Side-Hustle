"""Page-scoped inventory preview. Quest-scroll counts never represent materials."""
from dataclasses import dataclass, field, replace
from pathlib import Path
import os
import re
import time
from PIL import Image, ImageOps, ImageDraw, ImageFont
from .recognition import Detection, match_items
from .ocr_session import OcrSession
from .name_candidates import make_review

@dataclass
class Preview:
    words: list
    detections: list
    mode: str
    note: str
    reviews: list = field(default_factory=list)
    timings: dict = field(default_factory=dict)


def compact(text):
    return ''.join(text.split()).replace('：', ':')


def line_text(words):
    rows=[]
    for word in sorted(words,key=lambda w:(w['y']+w['h']/2,w['x'])):
        center=word['y']+word['h']/2
        row=next((r for r in rows if abs(r[0]['y']+r[0]['h']/2-center)<max(5,word['h']*.6)),None)
        if row is None:
            rows.append([word])
        else:
            row.append(word)
    return ''.join(''.join(w['text'] for w in sorted(row,key=lambda w:w['x'])) for row in rows)


def selected_tab(image,words,label):
    # Restrict to the inventory header, and require a white selected-tab background.
    candidates=[w for w in words if image.width*.53<w['x']<image.width*.99 and image.height*.08<w['y']<image.height*.20]
    candidates.sort(key=lambda w:w['x'])
    for i in range(len(candidates)):
        for n in (1,2):
            part=candidates[i:i+n]
            if compact(''.join(w['text'] for w in part))!=label:
                continue
            if len(part)==2 and (abs(part[0]['y']-part[1]['y'])>8 or part[1]['x']-part[0]['x']-part[0]['w']>12):
                continue
            x=min(w['x'] for w in part);y=min(w['y'] for w in part)
            right=max(w['x']+w['w'] for w in part);bottom=max(w['y']+w['h'] for w in part)
            pad=max(6,round(image.width/1280*8))
            crop=image.crop((max(0,int(x-pad)),max(0,int(y-pad)),min(image.width,int(right+pad)),min(image.height,int(bottom+pad)))).convert('RGB')
            pixels=list(crop.get_flattened_data())
            if pixels and sum(min(p)>200 for p in pixels)/len(pixels)>.40:
                return True
    return False


def cell_boxes(index):
    row,col=divmod(index,5)
    cx=755+103*col;y=257+123*row
    return (cx-48,y-10,cx+48,y+40),(cx-26,y-30,cx+40,y-8)


def atlas_words(words,index,pitch,offset,source,scale=4):
    col,row=index%5,index//5
    left,top=col*pitch[0]+offset[0],row*pitch[1]+offset[1]
    width,height=(source[2]-source[0])*scale,(source[3]-source[1])*scale
    found=[]
    for word in words:
        # Entire OCR box must lie in the original pixel crop, never a layout cue or adjacent cell.
        if left<=word['x'] and top<=word['y'] and word['x']+word['w']<=left+width and word['y']+word['h']<=top+height:
            found.append(dict(text=word['text'],x=source[0]+(word['x']-left)/scale,y=source[1]+(word['y']-top)/scale,w=word['w']/scale,h=word['h']/scale))
    return found


def resolve_cell(label_words,count_words,entries,box):
    raw=line_text(label_words)
    matches=[q.quest for q in entries if compact(q.quest)==compact(raw)]
    if len(matches)!=1:
        if '卷' in raw:
            return Detection('未確認卷軸',None,box,'完整名稱未符合白名單；不計入任何數量','unconfirmed',raw)
        return None
    count=None
    if len(count_words)==1 and re.fullmatch('[0-9]+',count_words[0]['text']):
        count=int(count_words[0]['text'])
        if count<=0:
            count=None
    return Detection(matches[0],count,box,'卷軸堆疊；非持有材料數量'+('；數量不明' if count is None else '；需人工核對'),'quest',raw)


def choose_retry(original, candidates):
    """Accept only one distinct exact whitelist identity; never synthesize text."""
    exact={item.name:item for item in candidates if item is not None and item.kind=='quest'}
    if len(exact)==1:
        item=next(iter(exact.values()))
        return Detection(item.name,item.count,item.box,item.note+'；二次辨識',item.kind,item.raw_text)
    return original


def count_value(words):
    if len(words)==1 and re.fullmatch('[0-9]+',words[0]['text']):
        value=int(words[0]['text'])
        return value if value>0 else None
    return None


def build_atlases(image):
    labels=Image.new('RGB',(2100,1100),'white')
    green=Image.new('RGB',(2100,1100),'white')
    counts=Image.new('RGB',(2250,1000),'white')
    extra=[Image.new('RGB',(2100,1100),'white') for _ in range(3)]
    painter=ImageDraw.Draw(counts)
    font=ImageFont.truetype(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/arial.ttf'),48)
    for i in range(25):
        label_box,count_box=cell_boxes(i);row,col=divmod(i,5)
        crop=ImageOps.autocontrast(ImageOps.invert(image.crop(label_box).convert('L')))
        labels.paste(crop.resize((384,200)),(col*420+15,row*220+15))
        crop=ImageOps.autocontrast(ImageOps.invert(image.crop(label_box).getchannel('G')))
        green.paste(crop.resize((384,200),Image.Resampling.LANCZOS),(col*420+15,row*220+15))
        raw=image.crop(label_box);gray=ImageOps.autocontrast(raw.convert('L'))
        for atlas,variant in zip(extra,[raw,gray,ImageOps.invert(gray.point(lambda p:255 if p>120 else 0))]):
            atlas.paste(variant.resize((384,200)),(col*420+15,row*220+15))
        digit=ImageOps.invert(image.crop(count_box).convert('L').point(lambda v:255 if v>185 else 0))
        counts.paste(digit.resize((264,88)),(col*450+140,row*200+40))
        # This cue is never part of count evidence; atlas_words enforces crop bounds.
        painter.text((col*450+15,row*200+55),'Qty',font=font,fill='black')
    return (labels,counts,green,*extra)


def retry_unconfirmed(image,entries,session,cells,alternate,times=None):
    prep_started=time.perf_counter()
    pending=[i for i,(item,_,_) in enumerate(cells) if item is not None and item.kind=='unconfirmed']
    if not pending:
        return cells,0
    isolated=[]
    for i in pending[:8]:
        box,_=cell_boxes(i)
        crop=ImageOps.autocontrast(ImageOps.invert(image.crop(box).getchannel('G')))
        isolated.append(ImageOps.expand(crop.resize((480,250),Image.Resampling.LANCZOS),20,'white'))
    if times is not None:
        times['preprocess_ms']+=(time.perf_counter()-prep_started)*1000
    results=session.recognize_many(isolated,timeout=20) if isolated else []
    match_started=time.perf_counter()
    recovered=0
    for order,i in enumerate(pending):
        original,lw,cw=cells[i];box,_=cell_boxes(i)
        candidates=[resolve_cell(atlas_words(alternate,i,(420,220),(15,15),box),cw,entries,box)]
        if order<len(results):
            mapped=[dict(text=w['text'],x=box[0]+(w['x']-20)/5,y=box[1]+(w['y']-20)/5,w=w['w']/5,h=w['h']/5)
                    for w in results[order] if w['x']>=20 and w['y']>=20 and w['x']+w['w']<=500 and w['y']+w['h']<=270]
            candidates.append(resolve_cell(mapped,cw,entries,box))
        chosen=choose_retry(original,candidates)
        recovered+=chosen.kind=='quest'
        cells[i]=(chosen,lw,cw)
    if times is not None:
        times['matching_ms']+=(time.perf_counter()-match_started)*1000
    return cells,recovered


def preview(image,entries,script,mode='quest',cancelled=None):
    if mode not in ('quest','material'):
        raise ValueError('Unknown inventory mode')
    started=time.perf_counter()
    times=dict(preprocess_ms=0.0,matching_ms=0.0,retry_stage_ms=0.0,fuzzy_matching_ms=0.0)
    with OcrSession(script,cancelled) as session:
        result=_preview(image,entries,session,mode,times)
    result.timings={**session.metrics,**times,'total_ms':(time.perf_counter()-started)*1000}
    result.timings['transport_overhead_ms']=max(0,session.metrics['batch_roundtrip_ms']-session.metrics['decode_ms']-session.metrics['recognition_ms'])
    result.note+=f" 掃描 {result.timings['total_ms']/1000:.2f} 秒；{len(result.reviews)} 格候選待核對。"
    return result


def _preview(image,entries,session,mode,times):
    from .flow_vision import Vision
    label='任務' if mode=='quest' else '材料'
    if image.size==(1280,960):
        screen=Vision(session).observe(image);words=list(screen.words);tab_ok=screen.selected_tab(label)
    else:
        words=session.recognize_many([image])[0];tab_ok=selected_tab(image,words,label)
    if not tab_ok:
        return Preview(words,[],mode,f'未確認選取「{label}」子分類；只顯示文字框，不推算卷軸或材料數量。')
    if mode=='material':
        start=time.perf_counter()
        detections=match_items(words,entries,image.size,mode='material')
        times['matching_ms']+=(time.perf_counter()-start)*1000
        return Preview(words,detections,mode,'材料頁候選；需人工核對，與卷軸數量分開。')
    if image.size!=(1280,960):
        return Preview(words,[],mode,'任務分格辨識只支援原始 1280 × 960 遊戲擷取，請勿使用助手縮圖截圖。')
    start=time.perf_counter()
    atlases=build_atlases(image)
    times['preprocess_ms']+=(time.perf_counter()-start)*1000
    label_sets=session.recognize_many([atlases[0],*atlases[2:]])
    label_words,alternate=label_sets[:2]
    start=time.perf_counter()
    cells=[]
    for i in range(25):
        label_box,count_box=cell_boxes(i)
        lw=atlas_words(label_words,i,(420,220),(15,15),label_box)
        cw=[]  # Scroll quantities are supplied by the player, never OCR.
        candidates=[resolve_cell(atlas_words(variant,i,(420,220),(15,15),label_box),cw,entries,label_box) for variant in label_sets]
        exact={item.name:item for item in candidates if item is not None and item.kind=='quest'}
        if len(exact)>1:
            item=Detection('辨識衝突',None,label_box,'不同 OCR 指向不同卷軸，禁止啟用','conflict',' / '.join(exact))
        elif exact:item=next(iter(exact.values()))
        else:item=next((item for item in candidates if item is not None),None)
        words.extend(lw);words.extend(cw)
        cells.append((item,lw,cw))
    times['matching_ms']+=(time.perf_counter()-start)*1000
    start=time.perf_counter()
    # Preserve the validated isolated-pixel inputs, but send them as one batch
    # to the same process instead of starting PowerShell for every cell.
    cells,recovered=retry_unconfirmed(image,entries,session,cells,alternate,times)
    times['retry_stage_ms']=(time.perf_counter()-start)*1000
    start=time.perf_counter()
    detections=[];reviews=[]
    for item,_,cw in cells:
        if item is None:
            continue
        index=len(detections)
        item=replace(item,count=3,note="卷軸數量：玩家設定，預設 3；可選取後修改，非 OCR／材料數量")
        detections.append(item)
        if item.kind=='unconfirmed':
            fuzzy_start=time.perf_counter()
            review=make_review(index,item,3,entries)
            times['fuzzy_matching_ms']+=(time.perf_counter()-fuzzy_start)*1000
            if review:
                best=review.candidates[0]
                if best.score>=.75 and not review.ambiguous and not best.type_conflict:
                    detections[index]=replace(item,name=best.name,kind='quest_fuzzy',
                        note=f'模糊比對 {best.score:.0%}；數量為玩家設定（預設 3），可修改')
                else:
                    reviews.append(review)
    times['matching_ms']+=(time.perf_counter()-start)*1000
    known=sum(d.kind=='quest' for d in detections)
    return Preview(words,detections,mode,f'任務頁：{known} 格完整符合白名單（重讀補回 {recovered} 格）。另有 {sum(d.kind=="quest_fuzzy" for d in detections)} 格模糊採用；卷軸數量由玩家輸入，預設 3。只涵蓋本頁。',reviews)


def match_scroll_tail(raw,entries):
    """Match the item half, without confusing quest materials with scroll names."""
    from .name_candidates import distance,material_candidate_allowed
    text=compact(raw)
    if ':' in text:tail=text.split(':',1)[1]
    else:
        match=re.match(r'^.*?卷[軸帕鮋]?(.*)$',text)
        tail=match.group(1) if match else text
    if len(tail.replace('+',''))<2:return None
    ranked=[];materials={compact(q.material) for q in entries}
    for q in entries:
        expected=compact(q.quest).split(':',1)[-1]
        if tail in materials and tail!=expected:continue
        if tail.count('+')!=expected.count('+') or not material_candidate_allowed(tail,expected):continue
        if ('級' in tail or '級' in expected) and tail.split('級')[0]!=expected.split('級')[0]:continue
        score=1-distance(tail,expected)/max(len(tail),len(expected))
        if score>=.66:ranked.append((score,q.quest))
    ranked.sort(reverse=True)
    if not ranked or len(ranked)>1 and ranked[0][0]-ranked[1][0]<.08:return None
    return ranked[0][1]


def scroll_label_candidates(image,quest,entries,session,scale=2):
    """Read only name cells; a unique item-tail match identifies the selected scroll."""
    boxes=[cell_boxes(i)[0] for i in range(25)];images=[]
    for box in boxes:
        crop=ImageOps.autocontrast(ImageOps.invert(image.crop(box).getchannel('G')))
        images.append(ImageOps.expand(crop.resize((96*scale,50*scale),Image.Resampling.LANCZOS),40,'white'))
    results=[]
    for start in range(0,len(images),12):results.extend(session.recognize_many(images[start:start+12]))
    found=[]
    for box,words in zip(boxes,results):
        inside=[w for w in words if 40<=w['x'] and 40<=w['y'] and w['x']+w['w']<=40+96*scale and w['y']+w['h']<=40+50*scale]
        raw=compact(line_text(inside))
        if match_scroll_tail(raw,entries)==quest:found.append((box,raw))
    return found
