import pytest
from pathlib import Path
from stage44_operations import preview_manifest, verify_manifest

@pytest.fixture
def sample(tmp_path):
    for p in ['preview_outputs/article.md','preview_outputs/article.html','preview_outputs/article.json','creative_outputs/post_0/all_prompts.json']:
        f=tmp_path/p; f.parent.mkdir(parents=True,exist_ok=True); f.write_text('{}')
    r={'processed':1,'results':[dict(keyword='a',angle='b',status='preview_only',creative='saved')]}
    return tmp_path,preview_manifest(tmp_path,r,1)

def test_ok(sample): assert verify_manifest(*sample)

@pytest.mark.parametrize('mode',['tamper','delete','traversal','duplicate','index','schema','symlink'])
def test_bad(sample,mode):
    root,m=sample; e=m['articles'][0]; f=e['files'][0]; p=root/f['path']
    if mode=='tamper': p.write_text('[]')
    if mode=='delete': p.unlink()
    if mode=='traversal': f['path']='../secret'
    if mode=='duplicate': e['files'][1]=f.copy()
    if mode=='index': e['index']=2
    if mode=='schema': m['schema']=2
    if mode=='symlink': p.unlink(); p.symlink_to('/etc/passwd')
    with pytest.raises(ValueError): verify_manifest(root,m)
