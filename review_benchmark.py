"""Offline advisory benchmark. Labels are fixture author judgments, not clinical truth."""
from time import perf_counter
from evidence_ledger import check
from claim_review import audit_claims
from advanced_review import independent_review

MODES=('A','B','C','D','E')

def choose_mode(kinds, conflict=False, budget=0):
    if 'medical' in kinds or 'comparison' in kinds or conflict:
        return 'E' if budget>=2 else 'D'
    return 'C' if 'commercial' in kinds or 'testimonial' in kinds else 'B'

def evaluate(case, mode, reviewers=()):
    if mode not in MODES: raise ValueError('unknown mode')
    start=perf_counter(); claim=case['claim']; product=case['product']; records=case['records']; hosts=case['hosts']; now=case['now']
    valid=[e for e in records if check(e.excerpt,product,e,hosts,now,1) in ('traceable_excerpt_review_required','conditions_review_required')]
    reasons=[]; calls=0
    if not valid: reasons.append('no_current_source')
    if mode!='A':
        audit=audit_claims(claim,product,records,hosts,now)
        rows=audit['claims']
        if not rows or any(r['status']!='exact_candidate' for r in rows): reasons.append('unverified')
        if mode in ('C','D','E'):
            if any(r['counter_candidates'] for r in rows): reasons.append('counter_candidate')
            if any('条件・例外確認' in r['reasons'] for r in audit['review_report']['rows']): reasons.append('scope_candidate')
        if mode in ('D','E') and any('medical' in r['kinds'] or 'comparison' in r['kinds'] for r in rows): reasons.append('specialist_review')
        if mode=='E':
            def counted(fn):
                def run(c,e):
                    nonlocal calls
                    calls+=1; return fn(c,e)
                return run
            ids=[e.id for e in valid]
            if len(set(ids))!=len(ids): reasons.append('duplicate_source_id')
            else:
                result=independent_review(claim,{e.id:e.excerpt for e in valid},[counted(fn) for fn in list(reviewers)[:2]])
                if not result['agreement'] or any(r['verdict']!='supports' for r in result['results']): reasons.append('independent_review_needed')
    return {'flagged':bool(reasons),'reasons':reasons,'calls':calls,'seconds':perf_counter()-start,'approved':False,'human_review_required':True}

def benchmark(cases, reviewers=()):
    cases=list(cases)
    if not cases or any(type(c['expected_flag']) is not bool for c in cases): raise ValueError('explicit boolean labels required')
    output={}
    for mode in MODES:
        tp=fp=tn=fn=calls=0; seconds=0; details=[]
        for c in cases:
            r=evaluate(c,mode,reviewers); expected=c['expected_flag']; actual=r['flagged']
            tp+=expected and actual; fp+=not expected and actual; tn+=not expected and not actual; fn+=expected and not actual
            calls+=r['calls']; seconds+=r['seconds']; details.append({'id':c['id'],**r})
        output[mode]={'tp':tp,'fp':fp,'tn':tn,'fn':fn,'recall':tp/(tp+fn) if tp+fn else None,'false_positive_rate':fp/(fp+tn) if fp+tn else None,'calls':calls,'seconds':seconds,'details':details}
    return output
