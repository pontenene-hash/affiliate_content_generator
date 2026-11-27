import pytest
from stage31_45 import preview_limit, preview_paths, audit_export, validate_preview

@pytest.mark.parametrize('n',range(1,6))
def test_unique_paths(n):
    paths=[preview_paths(n,i) for i in range(n)]
    assert len(set(paths))==n
    assert len({p[0] for p in paths})==n

@pytest.mark.parametrize('n',[0,6,-1,True,None,'1.0','abc',1.5])
def test_invalid_limit(n):
    with pytest.raises(ValueError): preview_limit(n)

def test_export_missing():
    r=audit_export({})
    assert {'carousel_count','gbp_video_prompt','store_pop_image','affiliate_url_review'}<=set(r['flags'])
    assert not r['publication_approved']

def test_export_cta():
    url='https://example.com/a'
    r=audit_export({'affiliate_url':url,'social_plan':{'x_posts':[{'text':'詳細はこちら '+url}]}})
    assert 'x_0_destination_review' in r['flags'] and 'x_0_ad_disclosure' in r['flags']

@pytest.mark.parametrize('n',[1,5])
def test_complete_and_missing(tmp_path,n):
    rows=[]
    for i in range(n):
        d,p=preview_paths(n,i)
        for path in [d/'article.md',d/'article.html',d/'article.json',__import__('pathlib').Path('creative_outputs')/f'post_{p}'/'all_prompts.json']:
            f=tmp_path/path; f.parent.mkdir(parents=True,exist_ok=True); f.write_text('test')
        rows.append(dict(keyword=str(i),angle='angle',status='preview_only',creative='saved'))
    result=dict(results=rows,processed=n)
    validate_preview(result,n,tmp_path)
    f.unlink()
    with pytest.raises(RuntimeError): validate_preview(result,n,tmp_path)

def test_duplicate():
    row=dict(keyword='a',angle='b',status='preview_only',creative='saved')
    with pytest.raises(RuntimeError): validate_preview(dict(results=[row,row],processed=2),2)

def test_incomplete():
    with pytest.raises(RuntimeError): validate_preview(dict(results=[],processed=0),5)
