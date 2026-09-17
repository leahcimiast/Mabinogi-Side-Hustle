"""Local, explicitly approved tooltip OCR corrections; never quantity approvals."""
import json
from pathlib import Path
from .flow_vision import compact
from .name_candidates import material_candidate_allowed

class NameReviewCompleted(Exception):
    """Discard pre-review pixels and re-observe after returning to the game."""

class NameReviewRequired(RuntimeError):
    def __init__(self,expected,observed):
        self.expected=expected;self.observed=observed
        super().__init__(f'請核對遊戲物品：OCR「{observed}」是否為「{expected}」？尚未領取。')

class NameMemory:
    def __init__(self,path,materials):
        self.path=Path(path);self.materials={compact(n) for n in materials};self.aliases={}
        if self.path.exists():
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data,dict):raise ValueError('名稱記憶格式不正確')
            # Ignore obsolete wool aliases without blocking other saved names.
            data={raw:name for raw,name in data.items()
                  if not (name=='羊毛' and raw!='羊毛')}
            for raw,name in data.items():
                if not self.allowed(raw,name):raise ValueError('名稱記憶含有無效對應')
            self.aliases=data
    def allowed(self,raw,name):
        if not isinstance(raw,str) or not isinstance(name,str):return False
        return (bool(raw) and raw==compact(raw) and name in self.materials
                and material_candidate_allowed(raw,name)
                and raw.count('+')==name.count('+')
                and (raw not in self.materials or raw==name))
    def matches(self,raw,name):return self.allowed(compact(raw),compact(name)) and self.aliases.get(compact(raw))==compact(name)
    def remember(self,raw,name):
        raw,name=compact(raw),compact(name)
        if not self.allowed(raw,name):raise ValueError('不能將不同等級、其他白名單素材或不同 + 名稱記為同一物品')
        if raw in self.aliases and self.aliases[raw]!=name:raise ValueError('這個 OCR 名稱已對應其他素材，請先清除名稱記憶')
        updated={**self.aliases,raw:name};self._save(updated)
    def clear(self):self._save({})
    def _save(self,data):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        temp.replace(self.path);self.aliases=data
