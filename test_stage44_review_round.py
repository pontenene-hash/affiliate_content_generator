import pytest
from release_review import review_quotes, recover
from editorial_dashboard import dashboard
from stage44_operations import verify_manifest
from test_manifest_integrity import sample

@pytest.mark.parametrize('article',['口コミ：\n「良かった」','レビュー**：**\n> 「良かった」','体験談：\n『良かった』','口コミ：「良かった」'])
def test_multiline_quote(article):
    assert review_quotes(article,[])[0]['quote']=='良かった'

@pytest.mark.parametrize('attempts',[True,1.5,0,4])
def test_retry_invalid(attempts):
    with pytest.raises(ValueError): recover(lambda:None,attempts=attempts)

def test_candidate_still_pending():
    d=dashboard('本文',{'analysis':{'intents':[]}}, {'claims':[{'kinds':['medical'],'source_ids':['a']}]}, {'quotes':[{'candidate_urls':['https://example.org']}],'similar_articles':[]}, {'approved':True})
    assert 'confirm_claim_candidates' in d['tasks'] and 'confirm_quote_candidates' in d['tasks']

def test_internal_symlink(sample):
    root,m=sample; f=m['articles'][0]['files'][0]; p=root/f['path']; other=root/'copy'; other.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(other)
    with pytest.raises(ValueError): verify_manifest(root,m)

def test_parent_symlink(sample):
    root,m=sample; p=root/'preview_outputs'; p.rename(root/'copy'); p.symlink_to(root/'copy',target_is_directory=True)
    with pytest.raises(ValueError): verify_manifest(root,m)

@pytest.mark.parametrize('article',['口コミ：\n「良かった」\n「便利だった」','口コミ：\n- 「良かった」\n- 「便利だった」'])
def test_multiple_quotes(article):
    assert [q['quote'] for q in review_quotes(article,[])]==['良かった','便利だった']
