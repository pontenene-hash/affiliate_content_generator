"""Offline editorial planning; suggestions are not verified search performance."""
import re
from growth_advice import norm
from run_controls import freshness

def keyword_key(value):
    return ' '.join(sorted(set(norm(value).split())))

def keyword_conflicts(records):
    groups = {}
    for row in records:
        if not isinstance(row, dict) or row.get('id') is None: continue
        key = keyword_key(row.get('keyword'))
        if key: groups.setdefault(key, set()).add(str(row['id']))
    return [{'keyword_key': k, 'ids': sorted(v), 'serp_overlap_verified': False}
            for k,v in sorted(groups.items()) if len(v)>1]

def heading_gaps(article, expected):
    headings = [norm(m) for m in re.findall(r'^#{2,3}\s+(.+)$', article or '', re.M)]
    terms = list(dict.fromkeys(norm(x) for x in expected if norm(x)))
    return {'missing_heading_terms': [t for t in terms if not any(t in h for h in headings)],
            'semantic_coverage_verified': False}

def improvement_queue(records, now):
    result = []
    for row in records:
        if not isinstance(row,dict) or row.get('id') is None: continue
        reasons = []
        if row.get('safety_review_required') is True: reasons.append((100,'safety_review'))
        if row.get('affiliate_link_verified') is False: reasons.append((90,'link_review'))
        state = freshness(row.get('last_checked'),now,row.get('source_change'))
        if state != 'recent_check_not_verified': reasons.append((70 if state=='review_changed_source' else 40,state))
        if row.get('quality_review_required') is True: reasons.append((60,'quality_review'))
        if reasons: result.append({'id':str(row['id']), 'priority':max(x[0] for x in reasons), 'reasons':[x[1] for x in reasons]})
    return sorted(result,key=lambda r:(-r['priority'],r['id']))

def planning_report(records, now):
    rows = list(records)
    return {'improvement_queue':improvement_queue(rows,now), 'keyword_conflicts':keyword_conflicts(rows),
            'record_count':len(rows), 'publication_approved':False, 'automatic_rewrite':False}
