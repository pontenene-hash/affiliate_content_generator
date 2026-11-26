from datetime import datetime, timezone, timedelta
from dataclasses import replace
import pytest
from evidence_ledger import Evidence, check
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
E=Evidence('1','A','https://example.com/guide','送料は500円です。',NOW)
@pytest.mark.parametrize('e,claim,expected',[
(E,'送料は500円です。','traceable_excerpt_review_required'),
(None,'送料は500円です。','missing_evidence'),
(replace(E,product='B'),'送料は500円です。','wrong_product'),
(replace(E,url='https://example.com.evil.test/'),'送料は500円です。','untrusted_source'),
(replace(E,url='https://evil.test@example.com/'),'送料は500円です。','untrusted_source'),
(replace(E,url='http://example.com/'),'送料は500円です。','untrusted_source'),
(replace(E,fetched_at=NOW-timedelta(days=31)),'送料は500円です。','stale_or_future'),
(replace(E,fetched_at=NOW+timedelta(days=1)),'送料は500円です。','stale_or_future'),
(replace(E,fetched_at=NOW.replace(tzinfo=None)),'送料は500円です。','invalid_date'),
(E,'送料無料です。','semantic_review_required'),
(replace(E,conditions='一部地域を除く'),'送料は500円です。','conditions_review_required'),
(E,'','missing_claim'),
(replace(E,excerpt=''),'送料は500円です。','semantic_review_required'),
])
def test_check(e,claim,expected):
    assert check(claim,'A',e,{'example.com'},NOW)==expected
