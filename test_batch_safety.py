import json
import pytest
from batch_safety import exclusive_lock, atomic_json, review_queue

def test_lock_contention(tmp_path):
    p=tmp_path/'lock'
    with exclusive_lock(p):
        with pytest.raises(RuntimeError):
            with exclusive_lock(p): pass
    with exclusive_lock(p): pass

def test_lock_exception(tmp_path):
    p=tmp_path/'lock'
    with pytest.raises(ValueError):
        with exclusive_lock(p): raise ValueError()
    with exclusive_lock(p): pass

def test_atomic(tmp_path):
    p=tmp_path/'history.json'; atomic_json(p, {'a':1})
    with pytest.raises(ValueError): atomic_json(p, {'a':float('nan')})
    assert json.loads(p.read_text())=={'a':1}
    assert list(tmp_path.iterdir())==[p]

def test_queue():
    q=review_queue([{'status':'preview_only'},{'status':'draft'},None,{'status':'error'}])
    assert [r['action'] for r in q]==['inspect_preview','inspect_draft','investigate_status','investigate_status']
    assert not any(r['publication_approved'] for r in q)

def test_history(tmp_path,monkeypatch):
    import article_history as h
    monkeypatch.setattr(h,'HISTORY_PATH',str(tmp_path/'history.json'))
    monkeypatch.setattr(h,'_config',lambda:None)
    h.save_article({'key':'a'}); h.save_article({'key':'a'}); h.save_article({'key':'b'})
    assert h.load_history()==[{'key':'a'},{'key':'b'}]

def test_creative_bad_schema():
    from stage44_operations import creative_flags
    assert creative_flags({'social_plan':None})==['invalid_creative_schema']

def test_creative_missing_disclosure():
    from stage31_45 import audit_export
    flags=audit_export({'social_plan':{'x_posts':[{'text':'商品紹介'}]},'affiliate_url':'https://example.com'})['flags']
    assert 'x_0_ad_disclosure' in flags and 'carousel_count' in flags and 'gbp_video_prompt' in flags

def test_lock_cross_process(tmp_path):
    import subprocess,sys
    p=tmp_path/'lock'
    with exclusive_lock(p):
        r=subprocess.run([sys.executable,'-c','from batch_safety import exclusive_lock; import sys;\nwith exclusive_lock(sys.argv[1]): pass',str(p)],capture_output=True)
        assert r.returncode!=0 and b'Another local operation' in r.stderr

@pytest.mark.parametrize('status,action',[('held_wp_draft','inspect_draft'),('quality_review_required','review_quality'),('research_required','research_sources'),('manual_link_required','supply_link')])
def test_queue_specific(status,action):
    assert review_queue([{'status':status}])[0]['action']==action
