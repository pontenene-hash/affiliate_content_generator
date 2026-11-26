import pytest
from release_review import *

def test_retry():
    calls=[]
    def f():
        calls.append(1)
        if len(calls)==1: raise TimeoutError()
        return 'ok'
    assert recover(f,sleep=lambda _:None)=='ok' and len(calls)==2

def test_no_retry_unknown():
    calls=[]
    def f(): calls.append(1); raise ValueError()
    with pytest.raises(ValueError): recover(f,sleep=lambda _:None)
    assert len(calls)==1

def test_limit():
    with pytest.raises(ValueError): recover(lambda:None,attempts=4)

def test_similarity():
    assert similarity('商品Ａの使い方','商品Aの使い方')==1
    assert similarity('商品Ａの使い方','返品条件の確認')==0
    assert similarity('','')==0

def test_quote():
    assert not review_quotes('口コミ「良かった」',[{'url':'https://example.com','text':'良かった'}])[0]['candidate_urls']
    assert review_quotes('口コミ「良かった」',[{'url':'https://example.com','text':'良かった','verified_by_human':True}])[0]['candidate_urls']

def test_patch():
    assert partial_patch('送料500円','500','700',lambda s:{'issues':[]})[0]=='送料700円'
    assert partial_patch('送料500円','500','700',lambda s:{'issues':['bad'] if '700' in s else []})[0]=='送料500円'
    assert not partial_patch('500 500','500','700',lambda s:{'issues':[]})[1]['accepted']

def test_patch_error():
    def fail(s): raise RuntimeError()
    assert partial_patch('500','500','700',fail)[0]=='500'

def test_models():
    def fail(c): raise RuntimeError()
    r=model_compare({'a':lambda c:c['id'],'b':fail},[{'id':1},{'id':2}],lambda c,v:v==c['id'])
    assert len(r)==4 and sum(x['status']=='error' for x in r)==2

def test_batch():
    def gen(i):
        if i['id']==3: raise RuntimeError()
        return i
    r=batch_preview([{'id':i} for i in range(5)],gen,lambda i:{'issues':[]})
    assert len(r)==5 and r[3]['status']=='error' and r[4]['status']=='held' and not any(x['approved'] for x in r)
