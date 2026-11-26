import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import Mock
import pytest
import yaml
from stage25_30 import repair_cta,retry_kind,valid_draft_response
from review_storage import ReviewStorage
from stage22_resume import ResumableCalls
from stage24_batch import summarize


def test_cross_run_checkpoint(tmp_path):
    p=tmp_path/'one.db'; now=datetime.now(timezone.utc)
    call=Mock(return_value='本文')
    assert ResumableCalls(ReviewStorage(p),['preview'],call,lambda:now)('prompt')=='本文'
    q=tmp_path/'two.db'
    with sqlite3.connect(p) as a, sqlite3.connect(q) as b: a.backup(b)
    other=Mock(return_value='新本文')
    assert ResumableCalls(ReviewStorage(q),['preview'],other,lambda:now)('prompt')=='本文'
    other.assert_not_called()
    assert ResumableCalls(ReviewStorage(q),['production'],other,lambda:now)('prompt')=='新本文'


def test_cta_repair():
    link='https://example.com/ad'
    b={'affiliate_url':link,'social_plan':{'x_posts':[{'text':'記事はこちら：'+link},{'text':'記事はこちら：'+link+'/other'}]}}
    fixed,paths=repair_cta(b)
    assert paths==['x/1'] and fixed['social_plan']['x_posts'][0]['text']=='【PR】広告主の商品ページ：'+link
    assert fixed['social_plan']['x_posts'][1]==b['social_plan']['x_posts'][1]
    assert repair_cta(fixed)[1]==[] and b['social_plan']['x_posts'][0]['text'].startswith('記事')

@pytest.mark.parametrize('code,expected',[(429,'stop_batch'),('403','stop_batch'),(401,'stop_batch'),(503,'retry'),(404,'model_missing'),(400,'stop_request'),(422,'stop_request')])
def test_retry(code,expected):
    e=RuntimeError(); e.code=code
    assert retry_kind(e)==expected

@pytest.mark.parametrize('value',[True,0,-1,1.2,'abc',None])
def test_invalid_id(value):
    with pytest.raises(RuntimeError): valid_draft_response({'status':'draft','review':'needs_review','id':value})

def test_draft_only():
    assert valid_draft_response({'status':'draft','review':'needs_review','id':12})==12
    with pytest.raises(RuntimeError): valid_draft_response({'status':'publish','review':'approved','id':12})


def test_five_simulated_recovery(tmp_path):
    store=ReviewStorage(tmp_path/'resume.db'); now=datetime.now(timezone.utc); calls=Mock(return_value='本文')
    rows=[]; ids={}
    for i in range(5):
        gen=ResumableCalls(store,['preview',i],calls,lambda:now)
        gen('section A'); gen('section B')
        ids.setdefault(i,i+1)
        rows.append({'status':'held_wp_draft','wp_id':valid_draft_response({'status':'draft','review':'needs_review','id':ids[i]})})
    assert calls.call_count==10
    for i in range(5):
        gen=ResumableCalls(store,['preview',i],calls,lambda:now); gen('section A'); gen('section B')
    assert calls.call_count==10
    assert summarize(rows,5)['saved_drafts']==5 and not summarize(rows,5)['publication_approved']


def test_workflow_recovery_isolated():
    w=yaml.load(Path('.github/workflows/affiliate_v5_test.yml').read_text(),Loader=yaml.BaseLoader)
    assert set(w['permissions'].values())=={'read'}
    steps=w['jobs']['live-preview']['steps']
    restore=next(s for s in steps if 'download-artifact' in s.get('uses',''))
    assert restore['with']['run-id']=='${{ inputs.resume_run_id }}'
    save=next(s for s in steps if s.get('name')=='Save isolated preview checkpoint')
    assert save['with']['retention-days']=='1' and 'always()' in save['if'] and 'repository.private == true' in save['if']
    assert not any('WP_' in k for s in steps for k in s.get('env',{}))
