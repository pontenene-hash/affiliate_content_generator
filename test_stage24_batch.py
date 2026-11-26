from stage24_batch import summarize

def test_five_mixed():
    r=summarize([{'status':'held_wp_draft','wp_id':1},{'status':'error'},{'status':'draft','wp_id':2,'creative':'error: timeout'},{'status':'research_required'},{'status':'preview_only'}],5)
    assert r['attempted']==5 and r['saved_drafts']==2 and r['errors']==1 and r['creative_failures']==1 and r['preview_only']==1
    assert not r['publication_approved']

def test_duplicate():
    assert summarize([{'status':'draft','wp_id':7},{'status':'held_wp_draft','wp_id':7}],5)['duplicate_wp_ids']==[7]

def test_empty():
    assert summarize([],5)['saved_drafts']==0
