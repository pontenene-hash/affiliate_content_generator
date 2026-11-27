from datetime import datetime, timezone, timedelta
import sqlite3
import pytest
from review_storage import ReviewStorage
from article_history import next_topics, make_record
from stage24_batch import summarize
NOW=datetime(2026,1,1,tzinfo=timezone.utc)

@pytest.mark.parametrize('days,expected',[(31,15),(90,45),(365,180)])
def test_schedule(days,expected):
    items=[dict(title=f'商品{i}',genre=str(i%9),product_url=f'https://example.org/{i}') for i in range(20)]
    history=[]
    for day in range(days):
        date=NOW+timedelta(days=day)
        if date.day not in (5,15,25): continue
        tasks=next_topics(items,history,5)
        assert len(tasks)==5
        for item,key,angle,kw,_ in tasks:
            history.append(make_record(item,key,angle,kw,kw,len(history)+1))
    assert len(history)==expected
    assert len({r['key'] for r in history})==expected
    assert not summarize(history,expected)['duplicate_wp_ids']

def test_exhaustion():
    item=dict(title='A',genre='g',product_url='https://example.org/a')
    tasks=next_topics([item],[],100)
    assert len(tasks)==12
    assert next_topics([item],[{'key':t[1]} for t in tasks],5)==[]

def test_restart_and_prune(tmp_path):
    s=ReviewStorage(tmp_path/'cache.db')
    s.generate(['A'],'p',lambda p:'old',NOW)
    s.observe('A',{'url':'x','sources':[{'url':'x','text':'a'}]},NOW)
    s=ReviewStorage(s.path)
    assert s.prune(NOW+timedelta(hours=24))==0
    assert s.prune(NOW+timedelta(hours=25))==1
    assert s.generate(['A'],'p',lambda p:'new',NOW+timedelta(hours=25))==('new',False)
    assert s.prune(NOW+timedelta(days=32))==2
    assert s.prune(NOW+timedelta(days=32))==0

def test_invalid_timestamp(tmp_path):
    s=ReviewStorage(tmp_path/'cache.db')
    s.generate(['A'],'p',lambda p:'old',NOW)
    with sqlite3.connect(s.path) as db: db.execute("UPDATE snapshots SET saved='invalid'")
    assert s.prune(NOW)==1

def test_naive_clock(tmp_path):
    with pytest.raises(ValueError): ReviewStorage(tmp_path/'cache.db').prune(NOW.replace(tzinfo=None))
