"""Advisory editorial metrics; keyword coverage is not factual verification."""
import re
from search_intent import INTENTS


def dashboard(article, intent_plan, claim_audit, release, quality):
    headings = '\n'.join(re.findall(r'^#{2,3}\s+(.+)$', article, re.M))
    body = '\n'.join(line for line in article.splitlines() if not line.lstrip().startswith('#'))
    intents = intent_plan['analysis']['intents']
    coverage = {k: {'heading': any(t in headings for t in INTENTS[k]),
                    'body': any(t in body for t in INTENTS[k])} for k in intents}
    claims = claim_audit['claims']
    counts = {k: {'total': sum(k in c['kinds'] for c in claims),
                  'exact_candidates': sum(k in c['kinds'] and bool(c['source_ids']) for c in claims)}
              for k in ('medical','commercial','comparison','testimonial')}
    pending = sum(not c['source_ids'] for c in claims)
    quotes = sum(not q['candidate_urls'] for q in release['quotes'])
    tasks = []
    if pending: tasks.append('verify_claims')
    if quotes: tasks.append('verify_quotes')
    if any(c['source_ids'] for c in claims): tasks.append('confirm_claim_candidates')
    if any(q['candidate_urls'] for q in release['quotes']): tasks.append('confirm_quote_candidates')
    if any(not v['body'] for v in coverage.values()): tasks.append('review_search_intent')
    if release['similar_articles']: tasks.append('review_similarity')
    if not quality.get('approved'): tasks.append('resolve_quality_issues')
    dimensions = {
        'search_intent': 'not_assessed' if not coverage else ('keyword_gap' if any(not v['body'] for v in coverage.values()) else 'keywords_present_not_verified'),
        'evidence': 'unmatched_claims' if pending else ('human_confirmation_required' if claims else 'not_detected_not_verified'),
        'testimonials': 'unmatched_quotes' if quotes else ('human_confirmation_required' if release['quotes'] else 'not_detected_not_verified'),
        'originality': 'similarity_review_required' if release['similar_articles'] else 'no_match_reported_not_verified',
        'quality': 'issues_reported' if quality.get('issues') or not quality.get('approved') else 'no_issues_reported_not_verified',
    }
    return {'review_dimensions':dimensions,'schema':1,'intent_coverage':coverage,'intent_body_percent':round(100*sum(v['body'] for v in coverage.values())/len(coverage)) if coverage else None,
            'claim_counts':counts,'unmatched_claims':pending,'unverified_quotes':quotes,
            'quality_issue_count':len(quality.get('issues',[])), 'tasks':tasks,
            'human_review_required':True,'publication_approved':False,
            'limitations':'Keyword coverage and exact excerpt candidates only; not SEO ranking, authenticity or medical accuracy.'}
