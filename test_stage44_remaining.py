import pytest
from unittest.mock import patch, Mock
from stage44_operations import verify_manifest

@pytest.fixture
def wp(monkeypatch):
    import sys, types
    from importlib import import_module
    try:
        import google.genai
    except ImportError:
        google=types.ModuleType("google"); genai=types.ModuleType("google.genai"); genai.Client=Mock(side_effect=AssertionError("API forbidden")); google.genai=genai
        monkeypatch.setitem(sys.modules,"google",google); monkeypatch.setitem(sys.modules,"google.genai",genai)
    global p
    p=import_module("auto_pipeline")
    for k,v in {'WP_SITE_URL':'https://example.com','WP_USERNAME':'test','WP_APP_PASSWORD':'fake'}.items(): monkeypatch.setenv(k,v)
    with patch.object(p,'public_url',side_effect=lambda x:x), patch.object(p.requests,'get') as get, patch.object(p.requests,'post') as post:
        get.return_value.status_code=200
        get.return_value.json.return_value={'active':True,'idempotent_drafts':True,'human_only_approval':True}
        post.return_value.status_code=200
        post.return_value.json.return_value={'id':42,'status':'draft','review':'needs_review'}
        yield get,post

def test_wp_retry_same_key(wp):
    get,post=wp
    for _ in range(2): assert p.wp_draft('title','body',idempotency_key='a'*64)==42
    assert all(c.kwargs['json']['idempotency_key']=='a'*64 and c.kwargs['allow_redirects'] is False for c in post.call_args_list)

@pytest.mark.parametrize('gate',[None,[],{}, {'active':True,'idempotent_drafts':False,'human_only_approval':True}])
def test_gate_fails_closed(wp,gate):
    get,post=wp; get.return_value.json.return_value=gate
    with pytest.raises(RuntimeError): p.wp_draft('title','body',idempotency_key='a'*64)
    post.assert_not_called()

@pytest.mark.parametrize('response',[None,[],{}, {'id':42,'status':'publish','review':'approved'}, {'id':True,'status':'draft','review':'needs_review'}])
def test_bad_wp_response(wp,response):
    get,post=wp; post.return_value.json.return_value=response
    with pytest.raises(RuntimeError): p.wp_draft('title','body',idempotency_key='a'*64)

def test_invalid_key_no_network(wp):
    get,post=wp
    with pytest.raises(ValueError): p.wp_draft('title','body',idempotency_key='bad')
    get.assert_not_called(); post.assert_not_called()
