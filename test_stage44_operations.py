import pytest
import requests
from stage44_operations import status_code, safe_error, wordpress_endpoint, reject_redirect, preview_manifest
from stage25_30 import retry_kind

@pytest.mark.parametrize('code,expected', [(401,'stop_batch'),(403,'stop_batch'),(429,'stop_batch'),(503,'retry'),(404,'model_missing'),(400,'stop_request')])
def test_http_error(code,expected):
    response=requests.Response(); response.status_code=code
    exc=requests.HTTPError('secret=DO_NOT_EXPORT',response=response)
    assert status_code(exc)==code
    assert retry_kind(exc)==expected
    assert 'DO_NOT_EXPORT' not in safe_error(exc)

@pytest.mark.parametrize('base',['http://example.com','https://user:pass@example.com','https://example.com?x=1','https://example.com/#x','https:///'])
def test_bad_base(base):
    with pytest.raises(ValueError): wordpress_endpoint(base,'/api')

def test_good_base():
    assert wordpress_endpoint('https://example.com/blog/','/api')=='https://example.com/blog/api'

@pytest.mark.parametrize('code',[301,302,303,307,308])
def test_redirect(code):
    r=requests.Response(); r.status_code=code
    with pytest.raises(RuntimeError): reject_redirect(r)

def test_manifest(tmp_path):
    from stage31_45 import preview_paths
    import json
    for i in range(5):
        dest,post=preview_paths(5,i)
        for p in [dest/'article.md',dest/'article.html',dest/'article.json',__import__('pathlib').Path('creative_outputs')/f'post_{post}'/'all_prompts.json']:
            f=tmp_path/p; f.parent.mkdir(parents=True,exist_ok=True); f.write_text('{}')
    result={'processed':5,'results':[dict(keyword=str(i),angle='比較',status='preview_only',creative='saved') for i in range(5)]}
    m=preview_manifest(tmp_path,result,5)
    assert len(m['articles'])==5 and not m['publication_approved']
    assert len(m['articles'][0]['files'][0]['sha256'])==64
    assert m['articles'][0]['creative_flags']
    (tmp_path/'preview_outputs/article_01/article.md').unlink()
    with pytest.raises(RuntimeError): preview_manifest(tmp_path,result,5)

@pytest.mark.parametrize('value',[None,[],{'social_plan':None},{'social_plan':{'carousel':{'slides':None}}}])
def test_invalid_creative_schema(value):
    from stage44_operations import creative_flags
    assert creative_flags(value)==['invalid_creative_schema']

def test_valid_creative_schema():
    from stage44_operations import creative_flags
    assert 'carousel_count' in creative_flags({})
