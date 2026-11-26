import pytest
from review_storage import ReviewStorage
from stage22_resume import ResumableCalls,code_fingerprint
from stage20_quality import initial_sections
from generation_control import CallBudget

def test_resume_second_half(tmp_path):
    store=ReviewStorage(tmp_path/'db'); calls=[]
    def fail(p,**kw):
        calls.append(p)
        if len(calls)==2: raise TimeoutError()
        return '前半'
    with pytest.raises(TimeoutError): initial_sections(ResumableCalls(store,['A'],fail),'p','A','暮らし','comparison_first')
    resume=ResumableCalls(store,['A'],lambda p,**kw:'後半')
    assert initial_sections(resume,'p','A','暮らし','comparison_first')=='前半\n\n後半'
    assert (resume.reused,resume.fresh)==(1,1)

def test_isolation(tmp_path):
    store=ReviewStorage(tmp_path/'db')
    for identity,kw in [('preview',1),('production',1),('preview',2)]:
        r=ResumableCalls(store,identity,lambda p,**k:identity+str(kw))
        assert r('p',max_tokens=kw)==identity+str(kw) and r.reused==0

def test_budget_counts_cache(tmp_path):
    r=ResumableCalls(ReviewStorage(tmp_path/'db'),'A',lambda p:'text')
    b=CallBudget(r,2); b('p');b('p')
    assert r.reused==1
    with pytest.raises(RuntimeError): b('p')

def test_code_change(tmp_path):
    p=tmp_path/'module.py';p.write_text('a');a=code_fingerprint(tmp_path);p.write_text('b');assert a!=code_fingerprint(tmp_path)

def test_empty_second():
    answers=iter(['first',''])
    with pytest.raises(ValueError): initial_sections(lambda *a,**k:next(answers),'p','A','暮らし','comparison_first')
