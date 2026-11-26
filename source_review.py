"""Advisory source grouping and bounded follow-up search planning."""
import re
import unicodedata
from urllib.parse import urlsplit
from evidence_ledger import check

def normalize(s):
    return re.sub(r'\W+', '', unicodedata.normalize('NFKC', s).casefold())

def source_review(claim, product, records, hosts, now, age=7):
    groups=[]
    for e in records:
        if check(claim, product, e, hosts, now, age) not in ('traceable_excerpt_review_required','conditions_review_required'):
            continue
        host=urlsplit(e.url).hostname
        content=normalize(e.excerpt)
        # Shared publisher host or identical excerpt is not independent evidence.
        matches=[g for g in groups if host in g['hosts'] or content in g['texts']]
        merged={'hosts':{host},'texts':{content},'ids':{e.id}}
        for g in matches:
            for k in merged: merged[k].update(g[k])
            groups.remove(g)
        groups.append(merged)
    return {'candidate_groups':[{'hosts':sorted(g['hosts']),'source_ids':sorted(g['ids'])} for g in groups], 'independence_verified':False,'human_review_required':True}

def followup_plan(product, claims, limit=3):
    if not isinstance(limit,int) or not 0<=limit<=10: raise ValueError('invalid limit')
    terms={'medical':'公的機関 診療ガイドライン 研究 限界','commercial':'公式 利用条件 料金 例外','comparison':'比較 条件 検証','testimonial':'口コミ 原文 掲載元'}
    name=re.sub(r'[^\w\s・-]', ' ', product)[:100].strip()
    if not name or limit==0: return []
    out=[]
    for c in sorted(claims,key=lambda c: 'medical' not in c['kinds']):
        if c['status']=='exact_candidate' and not c.get('counter_candidates') and 'medical' not in c['kinds']: continue
        for k in c['kinds']:
            if k not in terms: continue
            q=f'{name} {terms[k]}'
            if q not in out: out.append(q)
            if len(out)>=limit: return out
    return out
