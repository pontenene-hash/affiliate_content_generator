"""Offline planning only: budgets are goals, not permission to invent facts."""
from dataclasses import dataclass
from specialist_review import classify

@dataclass(frozen=True)
class Section:
    key: str
    purpose: str
    target: int
    evidence_required: bool

BASE = [('intro','読者の悩みと検索意図',7,False),('criteria','選ぶ際の判断基準',14,False),('features','確認済みの商品特徴',18,True),('comparison','比較・メリットとデメリット',18,True),('usage','利用前の確認事項',15,True),('faq','よくある質問',12,True),('summary','まとめ・広告明示とCTA',6,False)]
SPECIAL = {'medical':('medical_limits','検査目的・限界・受診相談',20,True),'nutrition':('nutrition_safety','成分・摂取条件・安全性',16,True),'cosmetic':('cosmetic_limits','使用方法・効能表現の範囲',16,True),'contract':('contract_terms','料金・契約・解約条件',16,True),'food':('food_safety','原材料・保存・アレルギー',16,True),'health_unknown':('health_unknown','商品区分と安全性の確認',16,True)}

def plan(name, genre, context='', target=6000):
    if type(target) is not int or not 5000 <= target <= 8000: raise ValueError('target must be 5000–8000')
    tags=classify(name,genre,context)
    rows=BASE[:-2]+[SPECIAL[t] for t in tags if t in SPECIAL]+BASE[-2:]
    total=sum(r[2] for r in rows)
    budgets=[target*r[2]//total for r in rows]
    for i in range(target-sum(budgets)): budgets[i]+=1
    return tuple(Section(k,p,b,e) for (k,p,w,e),b in zip(rows,budgets))

def section_instruction(section, evidence_ids):
    ids=tuple(x for x in evidence_ids if isinstance(x,str) and x.strip())
    return {'section':section.key,'purpose':section.purpose,'target':section.target,'evidence_ids':ids,'mode':'questions_only' if section.evidence_required and not ids else 'grounded_draft','human_review_required':True}
