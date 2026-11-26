"""Offline search-result analysis. Competitor text is untrusted, never evidence."""
import re
from urllib.parse import urlsplit
from article_plan import plan

INTENTS = {
 'comparison': ('比較','違い','メリット','デメリット','選び方'),
 'cost': ('価格','料金','送料','費用','値段'),
 'reputation': ('口コミ','評判','レビュー'),
 'usage': ('使い方','購入','注文','利用方法'),
 'terms': ('返品','解約','条件','保証'),
 'safety': ('安全','副作用','注意','検査','受診'),
}
QUESTIONS = {'comparison':'何を基準に比較するか','cost':'総費用と追加費用は何か','reputation':'確認可能な口コミとその限界は何か','usage':'利用前に何を確認するか','terms':'適用条件と例外は何か','safety':'安全上の注意と限界は何か'}
SECTION = {'comparison':'comparison','cost':'criteria','reputation':'faq','usage':'usage','terms':'usage','safety':'usage'}

def analyze(keyword, results):
    if not isinstance(keyword,str) or not keyword.strip(): raise ValueError('keyword required')
    counts={k:0 for k in INTENTS}; seen=set(); accepted=0
    for row in results[:10]:
        if not isinstance(row,dict): continue
        try:
            u=urlsplit(row.get('url',''))
            if u.scheme not in ('https','http') or not u.hostname or u.username or u.password: continue
            host=u.hostname.removeprefix('www.')
        except (ValueError,TypeError,AttributeError): continue
        if host in seen: continue
        seen.add(host); accepted+=1
        fields=[row.get('title',''),row.get('snippet','')]
        headings=row.get('headings',[])
        if isinstance(headings,list): fields.extend(headings[:30])
        text=' '.join(x[:1000] for x in fields if isinstance(x,str))
        for k,terms in INTENTS.items(): counts[k]+=int(any(t in text for t in terms))
    explicit=[k for k,terms in INTENTS.items() if any(t in keyword for t in terms)]
    ranked=sorted(INTENTS,key=lambda k:(k not in explicit,-counts[k],k))
    selected=[k for k in ranked if k in explicit or counts[k]>=2]
    return {'sample_size':accepted,'counts':counts,'intents':selected,'questions':[QUESTIONS[k] for k in selected], 'competitors_are_evidence':False,'human_review_required':True}

def editorial_plan(product,genre,keyword,results,target=6000):
    analysis=analyze(keyword,results)
    sections=plan(product,genre,keyword,target)
    return {'analysis':analysis,'sections':[{'key':s.key,'purpose':s.purpose,'target':s.target,'evidence_required':s.evidence_required,'questions':[QUESTIONS[k] for k in analysis['intents'] if SECTION[k]==s.key]} for s in sections], 'publication_approved':False}
