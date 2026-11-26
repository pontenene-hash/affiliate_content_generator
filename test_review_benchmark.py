from datetime import datetime,timezone,timedelta
import pytest
from evidence_ledger import Evidence
from review_benchmark import *
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
def case(id,claim,texts,expected,age=0):
    return dict(id=id,claim=claim,product='X',records=[Evidence(str(i),'X','https://example.com/'+str(i),t,NOW-timedelta(days=age)) for i,t in enumerate(texts)],hosts={'example.com'},now=NOW,expected_flag=expected)
CASES=[case('correct','送料は500円。',['送料は500円。'],False),case('wrong','送料は500円。',['送料は700円。'],True),case('conflict','送料は500円。',['送料は500円。','送料は700円。'],True),case('scope','送料は500円。',['送料は500円。ただし離島は別途料金。'],True),case('medical','治療効果があります。',['治療効果があります。'],True),case('stale','送料は500円。',['送料は500円。'],True,3),case('no_source','送料は500円。',[],True),case('correct2','価格は1000円。',['価格は1000円。'],False)]
def reviewer(c,e):
    for k,v in e.items():
        if c in v:return dict(verdict='supports',quote=c,source_id=k)
    raise ValueError()
def test_metrics():
    r=benchmark(CASES,[reviewer,reviewer]); assert r['A']['fn']==4 and r['D']['fn']==0 and r['D']['fp']==0
    assert r['E']['calls']==16
@pytest.mark.parametrize('mode',MODES)
def test_never_approves(mode): assert not evaluate(CASES[0],mode)['approved']
@pytest.mark.parametrize('kinds,conflict,budget,expected',[(['medical'],False,2,'E'),(['medical'],False,1,'D'),(['commercial'],False,0,'C'),([],False,0,'B'),([],True,0,'D')])
def test_route(kinds,conflict,budget,expected): assert choose_mode(kinds,conflict,budget)==expected
def test_no_reviewers(): assert evaluate(CASES[0],'E')['flagged']
def test_empty():
    with pytest.raises(ValueError):benchmark([])
def test_duplicate():
    c=dict(CASES[0]); c['records']*=2; assert 'duplicate_source_id' in evaluate(c,'E',[reviewer])['reasons']
