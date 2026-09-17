"""Name suggestions only. Similarity is an edit score, never a probability."""
from dataclasses import dataclass, field, replace
import re
from .recognition import Detection


def normalize(text):
    return ''.join(text.split())


def material_candidate_allowed(observed,expected):
    # Wool has a distinct premium item. A fuzzy/remembered match must not erase
    # its grade, even when OCR drops the leading 高 from 高級羊毛.
    return normalize(expected)!='羊毛' or normalize(observed)=='羊毛'


def distance(a,b):
    row=list(range(len(b)+1))
    for i,ca in enumerate(a,1):
        current=[i]
        for j,cb in enumerate(b,1):
            current.append(min(current[-1]+1,row[j]+1,row[j-1]+(ca!=cb)))
        row=current
    return row[-1]


def parts(text):
    text=normalize(text)
    match=re.match(r'^(採集|採礦|料理)卷軸?[:：]?(.*)$',text)
    return (match.group(1),match.group(2)) if match else (None,'')


@dataclass(frozen=True)
class Candidate:
    name: str
    score: float
    type_conflict: bool = False


@dataclass
class ReviewItem:
    detection_index: int
    raw_text: str
    box: tuple
    observed_count: int | None
    candidates: list[Candidate]
    ambiguous: bool
    state: str = 'pending'
    accepted_name: str | None = None

    @property
    def can_accept(self):
        return bool(self.candidates) and not self.ambiguous and self.state=='pending'


def suggest(raw,entries):
    source=normalize(raw);source_type,tail=parts(source)
    if source_type is None or len(tail.replace('+',''))<2:
        return []
    ranked=[]
    for entry in entries:
        target=normalize(entry.quest);target_type,target_tail=parts(target)
        # '+' changes item identity. Never suggest silently adding/removing it.
        if not target_type or tail.count('+')!=target_tail.count('+'):
            continue
        edits=distance(tail,target_tail)
        tail_score=1-edits/max(len(tail),len(target_tail))
        full_score=1-distance(source,target)/max(len(source),len(target))
        conflict=source_type!=target_type
        if tail_score<.66 or full_score<.72 or edits>max(1,len(target_tail)//3):
            continue
        # A conflicting scroll type is only a candidate when its item name is exact.
        if conflict and tail!=target_tail:
            continue
        ranked.append(Candidate(entry.quest,round(.7*tail_score+.3*full_score,4),conflict))
    ranked.sort(key=lambda c:(-c.score,c.name))
    return ranked[:3]


def make_review(index,item,count,entries):
    candidates=suggest(item.raw_text,entries)
    if not candidates:
        return None
    ambiguous=len(candidates)>1 and candidates[0].score-candidates[1].score<.08
    return ReviewItem(index,item.raw_text,item.box,count,candidates,ambiguous)


class ReviewSession:
    """Review belongs only to one immutable preview; reset on image/list/mode changes."""
    def __init__(self):
        self.token=0
        self.items=[]
        self.detections=[]

    def reset(self,detections=(),reviews=()):
        self.token+=1
        self.detections=list(detections)
        # A reopened UI cannot revive decisions from a previous preview.
        self.items=[replace(item,state='pending',accepted_name=None) for item in reviews]
        return self.token

    def decide(self,token,indices,accept,allow_type_conflict=False):
        if token!=self.token:
            raise ValueError('Preview changed; review the new capture')
        chosen=[self.items[i] for i in dict.fromkeys(indices)]
        if any(item.state!='pending' for item in chosen):
            raise ValueError('Already reviewed')
        if accept and any(not item.can_accept or (item.candidates[0].type_conflict and not allow_type_conflict) for item in chosen):
            raise ValueError('Ambiguous candidates or scroll-type conflicts require separate review')
        for item in chosen:
            item.state='accepted' if accept else 'rejected'
            if accept:
                item.accepted_name=item.candidates[0].name
                self.detections[item.detection_index]=Detection(item.accepted_name,item.observed_count,item.box,
                    '名稱已由使用者核對；卷軸數量為玩家設定，非材料持有量','quest_reviewed',item.raw_text)
        return self.detections
