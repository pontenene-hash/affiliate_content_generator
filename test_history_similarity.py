import sqlite3
import pytest
from history_similarity import DraftIndex
from release_bridge import release_audit, attach_release_audit

def test_restart_and_hold(tmp_path):
    p=tmp_path/'index.db'; body='商品説明と利用条件を確認します。'*20
    DraftIndex(p).save('branch','a',body)
    audit=release_audit(body,DraftIndex(p).previous('branch','b'))
    assert audit['similar_articles'][0]['id']=='a'
    assert not attach_release_audit({'approved':True,'issues':[]},audit)['approved']

def test_scope_and_self(tmp_path):
    i=DraftIndex(tmp_path/'i.db'); i.save('a','1','本文')
    assert i.previous('b','2')==[] and i.previous('a','1')==[]

def test_corruption(tmp_path):
    p=tmp_path/'i.db'; i=DraftIndex(p); i.save('a','1','本文')
    with sqlite3.connect(p) as db: db.execute("UPDATE draft_index SET body='changed'")
    with pytest.raises(ValueError): i.previous('a','2')

def test_empty(tmp_path):
    i=DraftIndex(tmp_path/'i.db')
    with pytest.raises(ValueError): i.save('a','1',' ')
    assert i.previous('a','2')==[]
