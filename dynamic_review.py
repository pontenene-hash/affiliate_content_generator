"""Advisory per-claim routing with shared callback budget; never approves publication."""
from claim_review import audit_claims
from review_benchmark import choose_mode, evaluate

def review_article(article, product, records, hosts, now, reviewers=(), budget=0):
    if type(budget) is not int or budget < 0: raise ValueError('invalid budget')
    records=list(records); reviewers=tuple(reviewers)[:2]
    audit=audit_claims(article,product,records,hosts,now)
    remaining=budget; rows=[]; seen=set()
    # Medical claims first, then conflicts, then other claims.
    ordered=sorted(audit['claims'],key=lambda r: ('medical' not in r['kinds'],not bool(r['counter_candidates'])))
    for r in ordered:
        claim=r['claim']
        if claim in seen: continue
        seen.add(claim)
        mode=choose_mode(r['kinds'],bool(r['counter_candidates']),remaining if len(reviewers)==2 else 0)
        result=evaluate(dict(claim=claim,product=product,records=records,hosts=hosts,now=now),mode,reviewers)
        remaining-=result['calls']
        rows.append(dict(claim=claim,mode=mode,**result))
    return dict(audit=audit,rows=rows,calls=budget-remaining,budget=budget,approved=False,human_review_required=True,limitations='Keyword-selected claims only; unselected text is not verified. Callback calls are not API token counts.')
