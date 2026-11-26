from datetime import datetime, timezone, timedelta
from evidence_ledger import Evidence
from source_review import source_review, followup_plan
from claim_review import audit_claims
import pytest
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
HOSTS={'a.example','b.example','c.example'}
def e(i,host,txt='送料は500円。',product='A',days=0):
    return Evidence(i,product,'https://'+host,txt,NOW-timedelta(days=days))
@pytest.mark.parametrize('records,count',[
 ([e('1','a.example'),e('2','a.example','送料は500円。詳細')],1),
 ([e('1','a.example'),e('2','b.example')],1),
 ([e('1','a.example'),e('2','b.example','送料は500円。詳細')],2),
 ([e('1','a.example'),e('2','b.example',product='B')],1),
 ([e('1','a.example'),e('2','b.example',days=8)],1),
 ([e('1','evil.example')],0),
 ([e('1','a.example'),e('2','b.example','送料は500円。詳細'),e('3','a.example','送料は500円。詳細')],1),
])
def test_groups(records,count):
    r=source_review('送料は500円。','A',records,HOSTS,NOW)
    assert len(r['candidate_groups'])==count
    assert not r['independence_verified'] and r['human_review_required']
def test_plan():
    r=audit_claims('送料は無料。治療効果がある。口コミが良い。','A',[e('1','a.example')],HOSTS,NOW)
    assert len(r['followup_queries'])==3 and '公的機関' in r['followup_queries'][0]
    assert not r['approved']
def test_zero(): assert followup_plan('A',[],0)==[]
def test_invalid():
    with pytest.raises(ValueError): followup_plan('A',[],11)
def test_exact():
    assert not audit_claims('送料は500円。','A',[e('1','a.example')],HOSTS,NOW)['followup_queries']
