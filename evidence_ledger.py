"""Conservative evidence provenance checks; not semantic or legal approval."""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from urllib.parse import urlsplit

@dataclass(frozen=True)
class Evidence:
    id: str
    product: str
    url: str
    excerpt: str
    fetched_at: datetime
    conditions: str = ''

def check(claim, product, evidence, trusted_hosts, now, max_age_days=30):
    """Only exact excerpts qualify as traceable; all claims still need review."""
    if not claim.strip(): return 'missing_claim'
    if evidence is None: return 'missing_evidence'
    if evidence.product != product: return 'wrong_product'
    try:
        u = urlsplit(evidence.url)
        if u.scheme != 'https' or u.hostname not in trusted_hosts or u.username or u.password or u.port not in (None,443): return 'untrusted_source'
        if evidence.fetched_at.utcoffset() is None or now.utcoffset() is None: return 'invalid_date'
        age = now - evidence.fetched_at
        if age < timedelta(0) or age > timedelta(days=max_age_days): return 'stale_or_future'
    except (ValueError, TypeError, AttributeError): return 'invalid_metadata'
    if not evidence.excerpt.strip() or claim.strip() not in evidence.excerpt: return 'semantic_review_required'
    if evidence.conditions: return 'conditions_review_required'
    return 'traceable_excerpt_review_required'
