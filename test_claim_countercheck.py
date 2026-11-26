from datetime import datetime, timezone, timedelta
import pytest
from evidence_ledger import Evidence
from claim_review import audit_claims
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
@pytest.mark.parametrize('claim,source,product,host,days,conditions,expected',[
 ('送料は500円。','送料は700円。','A','example.com',0,'','possible_conflict'),
 ('送料は無料。','送料は５００円。','A','example.com',0,'','possible_conflict'),
 ('送料は500円。','送料は500円。','A','example.com',0,'',None),
 ('送料は500円。','価格は700円。','A','example.com',0,'',None),
 ('送料は500円。','送料は700円。','B','example.com',0,'',None),
 ('送料は500円。','送料は700円。','A','evil.com',0,'',None),
 ('送料は500円。','送料は700円。','A','example.com',2,'',None),
 ('送料は500円。','送料は700円。','A','example.com',-1,'',None),
 ('送料は500円。','一部地域は送料700円。','A','example.com',0,'','scope_review'),
 ('送料は500円。','送料700円。','A','example.com',0,'離島','scope_review'),
])
def test_counter(claim,source,product,host,days,conditions,expected):
 e=Evidence('1',product,'https://'+host,source,NOW-timedelta(days=days),conditions)
 result=audit_claims(claim,'A',[e],{'example.com'},NOW)
 flags=result['claims'][0]['counter_candidates']
 assert (flags[0]['status'] if flags else None)==expected
 assert result['approved'] is False

def test_support_and_counter_coexist():
 es=[Evidence(str(i),'A','https://example.com',s,NOW) for i,s in enumerate(['送料500円。','送料700円。'])]
 r=audit_claims('送料500円。','A',es,{'example.com'},NOW)['claims'][0]
 assert r['status']=='exact_candidate' and r['counter_candidates'] and r['human_review_required']
