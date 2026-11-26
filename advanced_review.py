"""Advisory structured review. No automated approval, no network side effects."""
import hashlib, json
from urllib.parse import urlsplit


def source_type(url, registry):
    try:
        u=urlsplit(url)
        if u.scheme!='https' or u.username or u.password or u.port not in (None,443): return 'unknown'
        return registry.get(u.hostname,'unknown')
    except (ValueError,TypeError): return 'unknown'


def study_review(expected, study):
    fields=('population','intervention','comparator','outcome','product')
    mismatches=[k for k in fields if not expected.get(k) or expected.get(k)!=study.get(k)]
    limitations=[k for k in ('bias','precision','consistency','directness','publication_bias') if study.get(k)!='assessed_by_human']
    return {'mismatches':mismatches,'unassessed':limitations,'design':study.get('design','unknown'),'approved':False,'human_review_required':True}


def independent_review(claim, excerpts, reviewers):
    """Callbacks receive identical inputs, not each other's verdict. At most two calls."""
    results=[]
    for reviewer in list(reviewers)[:2]:
        try:
            r=reviewer(claim,dict(excerpts))
            if r['verdict'] not in ('supports','contradicts','insufficient') or not isinstance(r['quote'],str) or not r['quote'].strip() or r['quote'] not in excerpts.get(r['source_id'],''): raise ValueError('invalid citation')
            results.append({k:r[k] for k in ('verdict','quote','source_id')})
        except Exception:
            results.append({'verdict':'unavailable'})
    return {'results':results,'agreement':len(results)==2 and results[0]['verdict']==results[1]['verdict'] and results[0]['verdict']!='unavailable','approved':False,'human_review_required':True}


def compare_revision(before, after):
    def issues(a):
        return {(r['claim'],reason) for r in a['review_report']['rows'] for reason in r['reasons'] if r['priority']=='high'}
    old,new=issues(before),issues(after)
    return {'new_issues':sorted(new-old),'removed_issues':sorted(old-new),'regression_candidate':bool(new-old),'approved':False,'human_review_required':True}


def review_key(product, claim, evidence_hash, policy_version):
    return hashlib.sha256(json.dumps([product,claim,evidence_hash,policy_version],ensure_ascii=False).encode()).hexdigest()


def reuse_note(notes, product, claim, evidence_hash, policy_version):
    note=notes.get(review_key(product,claim,evidence_hash,policy_version))
    return {'prior_note':note if isinstance(note,str) else None,'approved':False,'human_review_required':True}
