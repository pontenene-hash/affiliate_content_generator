from datetime import datetime, timezone
from editorial_planning import *
NOW=datetime(2026,11,27,tzinfo=timezone.utc)
def test_conflict_normalized():
    assert keyword_conflicts([{'id':1,'keyword':'Ａ 足'},{'id':2,'keyword':'足 a'}])[0]['ids']==['1','2']
def test_no_self_conflict():
    assert keyword_conflicts([{'id':1,'keyword':'足'}]*2)==[]
def test_no_blank_conflict():
    assert keyword_conflicts([{'id':1},{'id':2}])==[]
def test_conflict_not_verified():
    assert not keyword_conflicts([{'id':1,'keyword':'足'},{'id':2,'keyword':'足'}])[0]['serp_overlap_verified']
def test_heading_gap():
    assert heading_gaps('# 価格\n## 安全性\n本文 口コミ',['価格','安全性','口コミ'])['missing_heading_terms']==['価格','口コミ']
def test_heading_normalized():
    assert heading_gaps('### ＡＢＣ',['abc'])['missing_heading_terms']==[]
def test_heading_duplicate():
    assert heading_gaps('', ['足','足',None])['missing_heading_terms']==['足']
def test_priority_safety():
    rows=[{'id':1,'source_change':'changed'},{'id':2,'safety_review_required':True}]
    assert improvement_queue(rows,NOW)[0]['id']=='2'
def test_priority_link():
    assert improvement_queue([{'id':1,'affiliate_link_verified':False}],NOW)[0]['priority']==90
def test_recent_no_task():
    assert improvement_queue([{'id':1,'last_checked':NOW.isoformat()}],NOW)==[]
def test_invalid_rows():
    assert improvement_queue([None,{}],NOW)==[]
def test_report_no_write():
    r=planning_report(iter([{'id':1}]),NOW)
    assert r['record_count']==1 and not r['publication_approved'] and not r['automatic_rewrite']
