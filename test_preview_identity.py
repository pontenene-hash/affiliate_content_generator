import json
import pytest
from stage31_45 import preview_paths, validate_preview_identity

@pytest.fixture
def batch(tmp_path):
    rows=[]
    for i in range(5):
        d,p=preview_paths(5,i)
        row=dict(title=f'記事{i}',keyword=f'語{i}',angle='比較',status='preview_only',creative='saved')
        rows.append(row)
        for path,data in [(d/'article.json',row),(tmp_path/'creative_outputs'/f'post_{p}'/'all_prompts.json',dict(title=row['title'],post_id=p))]:
            f=tmp_path/path; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(json.dumps(data))
    return tmp_path,dict(results=rows,processed=5)

def test_correct(batch): validate_preview_identity(batch[1],5,batch[0])

@pytest.mark.parametrize('mode',['swap','bad_json','wrong_title','wrong_id','bool_id','missing_keyword','list','empty_title'])
def test_invalid(batch,mode):
    root,result=batch
    a=root/'preview_outputs/article_01/article.json'; b=root/'preview_outputs/article_02/article.json'; c=root/'creative_outputs/post_0/all_prompts.json'
    data=json.loads(a.read_text()); bundle=json.loads(c.read_text())
    if mode=='swap': a.write_bytes(b.read_bytes())
    if mode=='bad_json': a.write_text('{')
    if mode=='wrong_title': bundle['title']='別記事'; c.write_text(json.dumps(bundle))
    if mode=='wrong_id': bundle['post_id']=1; c.write_text(json.dumps(bundle))
    if mode=='bool_id': bundle['post_id']=False; c.write_text(json.dumps(bundle))
    if mode=='missing_keyword': del data['keyword']; a.write_text(json.dumps(data))
    if mode=='list': a.write_text('[]')
    if mode=='empty_title': result['results'][0]['title']=''; data['title']=''; bundle['title']=''; a.write_text(json.dumps(data)); c.write_text(json.dumps(bundle))
    with pytest.raises(RuntimeError): validate_preview_identity(result,5,root)
