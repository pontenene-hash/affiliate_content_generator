import pytest
from cross_review import cross_review, source_changes, revision_review
@pytest.mark.parametrize('claim',['送料は700円。','必ず治る。','100％改善。','返品無料。','口コミで最高。','副作用なし。','全員に効果。','最安です。'])
def test_injected(claim):
    r=cross_review('送料は500円。',{'social_plan':{'video':[claim]}})
    assert r['flags'][0]['path']=='/social_plan/video/0' and not r['approved']

def test_same():
    assert not cross_review('送料は500円。',{'gbp':{'post':'送料は５００円。'}})['flags']

def test_neutral():
    assert not cross_review('商品紹介。',{'gbp':{'post':'詳しくは記事へ。'}})['flags']

def test_channels():
    b={k:'必ず治る。' for k in ['gbp','blog_images','social_plan']}
    assert len(cross_review('',b)['flags'])==3

def test_change():
    r=source_changes('送料は500円。\n商品紹介。','送料は700円。\n商品紹介。')
    assert len(r)==1 and 'money' in r[0]['kinds']

def test_no_change():
    assert not source_changes('送料は５００円。','送料は500円。')

def test_revision():
    r=revision_review('正常','必ず治る',lambda s:{'issues':['medical'] if '治る' in s else []})
    assert r['new_issues']==['medical'] and not r['approved']

def test_revision_failure():
    with pytest.raises(RuntimeError): revision_review('a','b',lambda s: (_ for _ in ()).throw(RuntimeError()))
