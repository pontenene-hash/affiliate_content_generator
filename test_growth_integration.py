from growth_advice import ranked_candidates, compare_titles, performance_summary, related_drafts

def test_rank():
    assert ranked_candidates([{'id':'a'},{'id':'b','approved':True}])[0]['id']=='b'
def test_rank_no_approval():
    assert not ranked_candidates([{'id':1,'approved':True}])[0]['eligible_for_review']
def test_rank_invalid():
    assert ranked_candidates([None,{}])==[]
def test_related_duplicates():
    row={'id':1,'article':'# 足の冷え'}
    assert len(related_drafts('足',[row,row,None]))==1
def test_title_risk():
    assert compare_titles(['絶対 足','足のケア'],'足')[0]['title']=='足のケア'
def test_title_duplicate():
    assert len(compare_titles(['足','足',''],'足'))==1
def test_metrics_weighted():
    r=performance_summary([dict(impressions=100,clicks=10,conversions=2),dict(impressions=10,clicks=5,conversions=1)])
    assert r['ctr']==15/110 and r['conversion_rate']==3/15
def test_metrics_invalid():
    assert performance_summary([dict(impressions=1,clicks=2,conversions=0),dict(impressions=True,clicks=0,conversions=0)])['accepted']==0
def test_metrics_missing():
    assert performance_summary([{}])['ctr'] is None
