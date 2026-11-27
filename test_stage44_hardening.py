import pytest
from stage31_45 import valid_timing, audit_export
from social_tools import _fix_video_timing, _ensure_link

@pytest.mark.parametrize('count', range(3, 9))
def test_video_timing(count):
    item={'scenes':[{} for _ in range(count)]}
    _fix_video_timing(item)
    assert item['total_duration']=='45秒'
    assert valid_timing(item['scenes'])
    for platform in ('reel','youtube','tiktok'):
        assert platform+'_duration_review' not in audit_export({'social_plan':{platform:item}})['flags']

@pytest.mark.parametrize('values', [[], ['4秒','34秒','4秒'], ['4秒','37秒','4秒余分'], ['4秒','0秒','37秒','4秒'], ['5秒','36秒','4秒'], [None,'37秒','4秒']])
def test_bad_timing(values):
    assert not valid_timing([{'duration':v} for v in values])

@pytest.mark.parametrize('label',['詳細はこちら','詳しくはこちら','記事はこちら','ブログはこちら','広告主の商品ページ'])
def test_destination(label):
    url='https://example.com/product?a=1&b=2'
    value=_ensure_link('商品紹介\n'+label+'：'+url,url)
    assert value=='商品紹介\n広告主の商品ページ：'+url
    assert _ensure_link(value,url)==value

def test_no_link():
    assert _ensure_link('商品紹介','')=='商品紹介'

def test_normalized_duplicate(tmp_path):
    from stage31_45 import validate_preview, preview_paths
    rows=[]
    for i,keyword in enumerate(('Ａ B','ab')):
        d,p=preview_paths(2,i)
        for f in (d/'article.md',d/'article.html',d/'article.json',__import__('pathlib').Path('creative_outputs')/f'post_{p}'/'all_prompts.json'):
            path=tmp_path/f; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('test')
        rows.append(dict(keyword=keyword,angle='比較',status='preview_only',creative='saved'))
    with pytest.raises(RuntimeError,match='duplicate'):
        validate_preview(dict(results=rows,processed=2),2,tmp_path)
