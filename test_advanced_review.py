import pytest
from advanced_review import *
@pytest.mark.parametrize('url,expected',[('https://pmda.go.jp/a','public'),('https://pmda.go.jp.evil.org','unknown'),('https://pmda.go.jp@evil.org','unknown'),('http://pmda.go.jp','unknown'),('https://pmda.go.jp:99','unknown')])
def test_source(url,expected): assert source_type(url,{'pmda.go.jp':'public'})==expected

def test_study():
    p=dict(population='adult',intervention='A',comparator='B',outcome='pain',product='X')
    r=study_review(p,dict(p,product='Y')); assert r['mismatches']==['product'] and len(r['unassessed'])==5 and not r['approved']

def test_empty_study(): assert len(study_review({}, {})['mismatches'])==5

def test_review():
    def a(c,e): return dict(verdict='supports',quote='abc',source_id='1')
    def b(c,e): return dict(verdict='contradicts',quote='abc',source_id='1')
    assert not independent_review('claim',{'1':'abc'},[a,b])['agreement']
    assert independent_review('claim',{'1':'abc'},[a,a])['agreement']
    assert not independent_review('claim',{'1':'abc'},[a,a])['approved']

def test_fake_quote():
    def a(c,e): return dict(verdict='supports',quote='fake',source_id='1')
    assert independent_review('claim',{'1':'abc'},[a,a])['results'][0]['verdict']=='unavailable'

def test_budget():
    calls=[]
    def a(c,e): calls.append(1); raise RuntimeError()
    independent_review('x',{},[a,a,a]); assert len(calls)==2

def test_revision():
    a={'review_report':{'rows':[]}}; b={'review_report':{'rows':[dict(claim='x',reasons=['根拠不足'],priority='high')]}}
    assert compare_revision(a,b)['regression_candidate']; assert not compare_revision(b,a)['approved']

def test_reuse():
    notes={review_key('p','c','h','v'):'要確認'}
    assert reuse_note(notes,'p','c','h','v')['prior_note']=='要確認'
    assert reuse_note(notes,'p','c','changed','v')['prior_note'] is None
    assert not reuse_note(notes,'p','c','h','v')['approved']
