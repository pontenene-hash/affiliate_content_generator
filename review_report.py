"""Advisory review queue; never grants approval or authenticates a source."""
import re
from evidence_ledger import check

CONDITIONS = re.compile(r'以上|未満|場合|限定|一部|除く|対象|条件|初回|地域|別途|税込|税別|キャンペーン|に限り|ただし')

def build_review_report(audit, product, records, hosts, now):
    rows=[]
    for c in audit['claims']:
        age=1 if 'commercial' in c['kinds'] else 7
        sources=[]
        for e in records:
            state=check(c['claim'],product,e,hosts,now,age)
            if state not in ('traceable_excerpt_review_required','conditions_review_required','stale_or_future'): continue
            if c['claim'] not in e.excerpt: continue
            # Include surrounding source text, not just the matched claim.
            pos=e.excerpt.index(c['claim'])
            context=e.excerpt[max(0,pos-180):pos+len(c['claim'])+180]
            sources.append({'id':e.id,'url':e.url,'freshness':state,'context':context,'conditions':e.conditions,'scope_review':bool(e.conditions or CONDITIONS.search(context))})
        reasons=[]
        if 'medical' in c['kinds']: reasons.append('専門家確認')
        if c.get('counter_candidates'): reasons.append('矛盾候補')
        if any(s['scope_review'] for s in sources): reasons.append('条件・例外確認')
        if any(s['freshness']=='stale_or_future' for s in sources): reasons.append('取得日時確認')
        if c['status']!='exact_candidate': reasons.append('根拠不足')
        priority='high' if reasons else 'normal'
        rows.append({'claim':c['claim'],'priority':priority,'reasons':reasons or ['原文・文脈確認'],'sources':sources,'human_review_required':True})
    rows.sort(key=lambda r:r['priority']!='high')
    return {'approved':False,'human_review_required':True,'total':len(rows),'high_priority':sum(r['priority']=='high' for r in rows),'rows':rows,'limitations':'条件候補は周辺180文字のルール検出。情報源の真正性・意味・医学的妥当性は未確認。'}
