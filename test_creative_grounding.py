import pytest
from creative_grounding import build_brief
A='## 品揃え\n## 送料\n### 交換部品\n## まとめ'
def b(**kw): return build_brief(A,'商品',**kw)
def test_slides(): assert len(b()['slides'])==9
def test_videos(): assert set(b()['videos'])=={'reel','youtube','tiktok','gbp'}
def test_duration(): assert all(sum(s['seconds'] for s in v['scenes'])==45 for v in b()['videos'].values())
def test_styles(): assert len({v['style'] for v in b()['videos'].values()})==4
def test_no_narration(): assert not any(v['narration'] for v in b()['videos'].values())
def test_topics(): assert b()['topics']==['品揃え','送料','交換部品']
def test_hashtags(): assert len(b()['hashtags'])==5
def test_no_approval(): assert b()['human_review_required'] and not b()['publication_approved']
def test_no_url(): assert b()['social']['x']['cta']['url'] is None
def test_affiliate(): assert '広告' in b(affiliate_url='https://example.com/ad')['social']['x']['cta']['text']
def test_article(): assert b(article_url='https://example.com/post')['social']['x']['cta']['text']=='記事を読む'
def test_same_url():
    with pytest.raises(ValueError): b(article_url='https://example.com/ad',affiliate_url='https://example.com/ad')
def test_bad_url():
    with pytest.raises(ValueError): b(article_url='javascript:alert(1)')
def test_short():
    with pytest.raises(ValueError): build_brief('## 一つ','商品')
