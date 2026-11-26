from datetime import datetime, timezone, timedelta
import pytest
from evidence_ledger import Evidence
from claim_review import audit_claims
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
@pytest.mark.parametrize('text,excerpt,product,host,days,expected',[
 ('送料は500円。','送料は500円。','A','example.com',0,'exact_candidate'),
 ('送料は無料。','送料は500円。','A','example.com',0,'unverified'),
 ('送料は500円。','送料は500円。','B','example.com',0,'unverified'),
 ('送料は500円。','送料は500円。','A','evil.com',0,'unverified'),
 ('送料は500円。','送料は500円。','A','example.com',2,'unverified'),
 ('治療効果がある。','治療効果がある。','A','example.com',0,'exact_candidate'),
 ('返品できます。','返品できます。','A','example.com',-1,'unverified'),
])
def test_candidates(text,excerpt,product,host,days,expected):
 e=Evidence('1',product,'https://'+host,excerpt,NOW-timedelta(days=days))
 r=audit_claims(text,'A',[e],{'example.com'},NOW)
 assert r['claims'][0]['status']==expected
 assert not r['approved'] and r['claims'][0]['human_review_required']

def test_conditions():
 e=Evidence('1','A','https://example.com','送料無料。',NOW,'一万円以上')
 assert audit_claims('送料無料。','A',[e],{'example.com'},NOW)['claims'][0]['status']=='unverified'
