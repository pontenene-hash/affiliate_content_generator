"""Offline orchestration prototype. Never writes to WordPress or approves publication."""
from dataclasses import dataclass
from evidence_ledger import check
from generation_router import route
from article_plan import plan, section_instruction
from specialist_review import specialist_review

@dataclass(frozen=True)
class Preparation:
    product: str
    genre: str
    strategy: str
    max_calls: int
    sections: tuple
    evidence_ids: tuple
    categories: tuple
    human_review_required: bool = True


def prepare(product, genre, context, evidence, trusted_hosts, now, *, comparison=False, budget=8):
    if not product.strip(): raise ValueError('missing product')
    # Conditional evidence cannot be used automatically; IDs must be unambiguous.
    ids = [e.id for e in evidence]
    if len(set(ids)) != len(ids): raise ValueError('duplicate evidence ID')
    valid = tuple(e.id for e in evidence if e.id.strip() and check(e.excerpt, product, e, trusted_hosts, now, 1) == 'traceable_excerpt_review_required')
    r = route(product, genre, context, evidence_count=len(valid), comparison=comparison, call_budget=budget)
    # Do not pretend that an arbitrary product excerpt supports every section.
    sections = tuple(section_instruction(s, ()) for s in plan(product, genre, context)) if r.max_generation_calls else ()
    return Preparation(product, genre, r.strategy, r.max_generation_calls, sections, valid, r.categories)


def review(preparation, article, *, calls, existing_issues=(), evidence_verified=False):
    if type(calls) is not int or calls < 0: raise ValueError('invalid calls')
    issues = list(existing_issues)
    if preparation.strategy == 'hold_for_research': issues.append('preflight_hold')
    if calls > preparation.max_calls: issues.append('budget_exceeded')
    if len(article.strip()) < 5000: issues.append('article_too_short')
    if not evidence_verified: issues.append('claim_evidence_review_required')
    findings = specialist_review(preparation.product, preparation.genre, article)
    issues.extend(i['code'] for i in findings['issues'])
    if set(findings['categories']) - set(preparation.categories) - {'general'}: issues.append('new_risk_category')
    return {'issues':tuple(dict.fromkeys(issues)), 'status':'held_for_human_review', 'publication_approved':False}
