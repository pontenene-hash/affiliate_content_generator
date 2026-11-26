from datetime import datetime, timezone, timedelta
import sqlite3
import pytest
from review_storage import ReviewStorage
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
@pytest.fixture
def store(tmp_path): return ReviewStorage(tmp_path/'review.sqlite')
def page(text='送料500円'): return {'url':'https://example.org','sources':[{'url':'https://example.org','text':text}]}
def test_changes(store):
    assert store.observe('A',page(),NOW)=='first_or_expired'
    assert store.observe('A',page(),NOW)=='unchanged'
    assert store.observe('A',page('送料700円'),NOW)=='changed'
def test_product_isolation(store):
    store.observe('A',page(),NOW)
    assert store.observe('B',page(),NOW)=='first_or_expired'
def test_empty(store): assert store.observe('A',{'url':'x'},NOW)=='unavailable'
def test_restart(store):
    assert store.generate(['A'],'p',lambda p:'article',NOW)==('article',False)
    assert ReviewStorage(store.path).generate(['A'],'p',lambda p:pytest.fail('called'),NOW)==('article',True)
@pytest.mark.parametrize('identity,prompt,offset', [(['B'],'p',0),(['A'],'q',0),(['A'],'p',25),(['A'],'p',-1)])
def test_invalidated(store,identity,prompt,offset):
    store.generate(['A'],'p',lambda p:'old',NOW)
    assert store.generate(identity,prompt,lambda p:'new',NOW+timedelta(hours=offset))==('new',False)
def test_corruption(store):
    store.generate(['A'],'p',lambda p:'old',NOW)
    with sqlite3.connect(store.path) as db: db.execute("UPDATE snapshots SET payload='null'")
    assert store.generate(['A'],'p',lambda p:'new',NOW)==('new',False)
def test_failure(store):
    def fail(p): raise RuntimeError('failure')
    with pytest.raises(RuntimeError): store.generate(['A'],'p',fail,NOW)
    assert store.generate(['A'],'p',lambda p:'new',NOW)==('new',False)
def test_five_resume(store):
    for i in range(3): store.generate([i],'p',lambda p:'article',NOW)
    restarted=ReviewStorage(store.path)
    assert [restarted.generate([i],'p',lambda p:'article',NOW)[1] for i in range(5)]==[True,True,True,False,False]
