"""Advisory context checks: never a semantic proof or publication approval."""
import re
from evidence_ledger import check

MARKERS = {
    'negation': r'ない|ません|不可|禁止|対象外|除外|非対応|できず|ではなく',
    'condition': r'場合|限り|以上|未満|条件|ただし|一部|初回|地域|別途',
    'uncertainty': r'可能性|目安|予定|見込み|保証し|個人差|未確認',
}

def context_flags(claim, product, records, hosts, now, age):
    rows=[]
    for e in records:
        if check(e.excerpt,product,e,hosts,now,age) not in ('traceable_excerpt_review_required','conditions_review_required'):
            continue
        for m in re.finditer(re.escape(claim.strip().rstrip('。！？')),e.excerpt) if claim.strip().rstrip('。！？') else []:
            context=e.excerpt[max(0,m.start()-100):m.end()+100]
            flags=[k for k,p in MARKERS.items() if re.search(p,context)]
            if e.conditions and 'condition' not in flags: flags.append('condition')
            if flags: rows.append({'source_id':e.id,'context':context,'flags':flags,'human_review_required':True})
            if len(rows)>=5: return rows
    return rows
