"""Fixed three-completion batch and durable progress, without stock/count OCR."""
from dataclasses import dataclass,asdict,replace
from pathlib import Path
import json,os,hashlib,time

@dataclass(frozen=True)
class MaterialRequest:
    name: str
    quantity: int

@dataclass(frozen=True)
class Completion:
    quest: str
    material: str
    quantity: int
    ordinal: int

@dataclass(frozen=True)
class Batch:
    materials: tuple
    completions: tuple
    fingerprint: str

def fixed_batch(entries):
    if len(entries)!=19 or len({q.quest for q in entries})!=19:
        raise ValueError('固定批次需要 19 種不同的白名單任務。')
    totals={};completions=[]
    for q in entries:
        if type(q.quantity) is not int or q.quantity<=0:
            raise ValueError('每次需求必須是正整數。')
        totals[q.material]=totals.get(q.material,0)+q.quantity*3
        completions.extend(Completion(q.quest,q.material,q.quantity,i+1) for i in range(3))
    data=json.dumps([asdict(q) for q in entries],ensure_ascii=False,sort_keys=True)
    return Batch(tuple(MaterialRequest(k,v) for k,v in totals.items()),tuple(completions),hashlib.sha256(data.encode()).hexdigest())

def submission_plan(batch,names):
    templates={q.quest:q for q in batch.completions}
    ordinals={};result=[]
    for name in names:
        if name not in templates:raise ValueError('交付清單包含未知任務。')
        ordinals[name]=ordinals.get(name,0)+1
        result.append(replace(templates[name],ordinal=ordinals[name]))
    return replace(batch,completions=tuple(result))

class Journal:
    """Persist intent BEFORE irreversible input; unresolved intent blocks replay."""
    def __init__(self,path,batch):
        self.path=Path(path);self.batch=batch
        self.data={'fingerprint':batch.fingerprint,'withdrawn':[],'completed':0,'pending':None,'active':None,'skipped':{},'manual':[]}
        if self.path.exists():
            self.data=json.loads(self.path.read_text(encoding='utf-8'))
            if self.data.get('fingerprint')!=batch.fingerprint:
                raise ValueError('批次白名單已改變，請先結束／重設原批次。')
            if 'submission_plan' in self.data:
                self.batch=submission_plan(batch,self.data['submission_plan'])
            if not set(self.data.get('withdrawn',[]))<=set(m.name for m in batch.materials) or not 0<=self.data.get('completed',-1)<=len(self.batch.completions):
                raise ValueError('本機進度資料無效，禁止自動操作。')
        self.data.setdefault('skipped',{});self.data.setdefault('manual',[])
    @classmethod
    def fresh(cls,path,batch):
        path=Path(path)
        if path.exists():
            archive=path.parent/'batch-history'
            archive.mkdir(parents=True,exist_ok=True)
            path.rename(archive/f'fixed-batch-{time.time_ns()}.json')
        journal=cls(path,batch);journal.save()
        return journal

    def set_remaining(self,entries,counts):
        self.ready()
        if self.data['active'] is not None:raise RuntimeError('請先完成已啟用的任務，再修改剩餘數量。')
        if set(counts)!={q.quest for q in entries} or any(type(n) is not int or not 0<=n<=9999 for n in counts.values()):
            raise ValueError('交付數量必須為 0 至 9999 的整數。')
        names=[q.quest for q in self.batch.completions[:self.data['completed']]]
        names.extend(q.quest for q in entries for _ in range(counts[q.quest]))
        updated=submission_plan(fixed_batch(entries),names)
        previous=self.data.get('submission_plan');self.data['submission_plan']=names
        try:self.save()
        except Exception:
            if previous is None:self.data.pop('submission_plan',None)
            else:self.data['submission_plan']=previous
            raise
        self.batch=updated

    def skip_missing_quest(self,quest,reason):
        self.ready()
        if self.data['active'] is not None:raise RuntimeError('已有啟用任務，不能略過。')
        done=self.data['completed'];names=[q.quest for q in self.batch.completions]
        removed=names[done:].count(quest)
        if not removed:raise ValueError('任務沒有剩餘次數。')
        names=names[:done]+[name for name in names[done:] if name!=quest]
        updated=submission_plan(self.batch,names)
        previous=dict(self.data)
        skipped=dict(self.data.get('skipped_quests',{}))
        skipped[quest]={'count':removed,'reason':reason}
        self.data.update(submission_plan=names,skipped_quests=skipped)
        try:self.save()
        except Exception:self.data=previous;raise
        self.batch=updated
        return removed

    def adopt_active(self,entries,quest,identity):
        """Move one planned completion forward; credit it only after submission."""
        self.ready()
        if self.data['active'] is not None:raise RuntimeError('已有已啟用任務，不能取代。')
        if quest not in {q.quest for q in entries}:raise ValueError('未知佈告欄任務。')
        done=self.data['completed'];names=[q.quest for q in self.batch.completions]
        remaining=names[done:]
        if quest in remaining:remaining.remove(quest)
        # An already-active quest must be finished even if its configured remainder was zero.
        names=names[:done]+[quest]+remaining
        updated=submission_plan(fixed_batch(entries),names)
        previous=dict(self.data)
        self.data['submission_plan']=names;self.data['active']={'index':done,'identity':identity}
        try:self.save()
        except Exception:
            self.data=previous
            raise
        self.batch=updated

    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp')
        with temp.open('w',encoding='utf-8') as f:
            json.dump(self.data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(temp,self.path)
    def ready(self):
        if self.data['pending']:
            raise RuntimeError('上次動作結果未確認，請先用「處理中斷結果」核對；不會自動重送。')
    def skip(self,name,reason):
        self.ready()
        if name not in {m.name for m in self.batch.materials} or name in self.data['withdrawn']:
            raise ValueError('無效的手動補領素材')
        self.data['skipped'][name]=reason;self.save()
    def confirm_manual(self,name):
        self.ready()
        if name not in self.data['skipped']:raise ValueError('此素材不在手動補領清單')
        self.data['withdrawn'].append(name);self.data['manual'].append(name)
        del self.data['skipped'][name];self.save()
    def begin(self,kind,value):
        self.ready();self.data['pending']={'kind':kind,'value':value};self.save()
    def confirm(self):
        p=self.data['pending']
        if not p:raise RuntimeError('No pending action')
        if p['kind']=='complete' and (p['value']!=self.data['completed'] or self.data['active'] is None):
            raise RuntimeError('完成進度與已啟用任務不一致')
        if p['kind']=='activate' and (self.data['active'] is not None or p['value']['index']!=self.data['completed']):
            raise RuntimeError('已有啟用任務或索引不符')
        if p['kind']=='withdraw' and p['value'] not in {m.name for m in self.batch.materials}:
            raise RuntimeError('未知領取素材')
        if p['kind']=='withdraw':
            if p['value'] not in self.data['withdrawn']:self.data['withdrawn'].append(p['value'])
        elif p['kind']=='activate':self.data['active']=p['value']
        elif p['kind']=='complete':
            self.data['completed']+=1;self.data['active']=None
        else:raise ValueError('Unknown pending action')
        self.data['pending']=None;self.save()
    def reconcile(self,happened):
        if not self.data['pending']:return
        if happened:self.confirm()
        else:self.data['pending']=None;self.save()
