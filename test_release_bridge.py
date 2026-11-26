from release_bridge import release_audit, attach_release_audit
import pytest

def test_quote_holds():
    a=release_audit('口コミ「とても良かった」')
    q=attach_release_audit({'approved':True,'issues':[]},a)
    assert not q['approved'] and q['status']=='quality_review_required'

def test_similarity_holds():
    a=release_audit('同じ記事の本文です', [{'id':1,'article':'同じ記事の本文です'}])
    assert not attach_release_audit({'approved':True},a)['approved']

def test_preserves_existing_hold():
    q={'approved':False,'issues':[{'code':'medical'}]}
    assert attach_release_audit(q,release_audit('説明'))==q

def test_verified_candidate_not_approval():
    a=release_audit('口コミ「良かった」',sources=[{'url':'https://example.com','text':'良かった','verified_by_human':True}])
    assert a['quotes'][0]['candidate_urls'] and not a['approved']

def test_no_history_explicit():
    assert release_audit('説明')['history_compared']==0

def test_invalid_threshold():
    with pytest.raises(ValueError): release_audit('説明',threshold=0)
