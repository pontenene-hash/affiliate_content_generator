"""Advisory provenance and bounded logical article generation calls."""
from datetime import datetime, timezone
from urllib.parse import urlsplit
from evidence_ledger import Evidence
from integrated_review import prepare


def prepare_page(product, genre, page, angle, now=None):
    now = now or datetime.now(timezone.utc)
    host = urlsplit(page['url']).hostname
    records = []
    for i, source in enumerate(page.get('sources', [])):
        if not isinstance(source.get('text'), str) or not source['text'].strip():
            continue
        try:
            fetched = datetime.fromisoformat(source['fetched_at'])
        except (ValueError, KeyError, TypeError):
            continue
        records.append(Evidence(str(i), product, source['url'], source['text'], fetched))
    result = prepare(product, genre, '', records, {host}, now,
                     comparison='比較' in angle)
    return result, records


class CallBudget:
    def __init__(self, generate, limit):
        self.generate, self.limit, self.calls = generate, limit, 0

    @property
    def remaining(self):
        return max(0, self.limit - self.calls)

    def __call__(self, *args, **kwargs):
        if not self.remaining:
            raise RuntimeError('Article generation call budget exhausted')
        self.calls += 1
        return self.generate(*args, **kwargs)
