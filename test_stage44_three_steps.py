from types import SimpleNamespace as S
import pytest
from provider_metrics import capture, measured, report
from editorial_dashboard import dashboard
from partial_repair import repair_duplicates

@pytest.mark.parametrize('value',[True,-1,1.5,'12',None])
def test_usage_invalid(value):
    events=[]
    with capture(events): measured('lite',lambda:S(usage_metadata=S(total_token_count=value)))
    assert report(events)['total_tokens'] is None

def test_usage_breakdown():
    events=[{'model':'a','status':'ok','total_tokens':10},{'model':'b','status':'transient','total_tokens':None}]
    r=report(events)
    assert r['known_total_tokens']==10 and r['unknown_usage_attempts']==1
    assert r['attempts_by_model']=={'a':1,'b':1} and r['attempts_by_status']=={'ok':1,'transient':1}

@pytest.mark.parametrize('prefix',['    ','\t','  1. ','  - '])
def test_indented_protection(prefix):
    p=prefix+'購入前に自分の用途と必要な機能を整理して、選択肢を比較することが大切です。'
    a=p+'\n\n'+p+'\n\n'+'本文'*3000
    assert repair_duplicates(a,{'issues':[{'code':'dup'}]},lambda _: {'issues':[]},len)[0]==a

def test_dashboard_unapproved_empty():
    r=dashboard('本文',{'analysis':{'intents':[]}}, {'claims':[]},{'quotes':[],'similar_articles':[]},{'approved':True,'issues':[]})
    assert r['publication_approved'] is False and r['human_review_required'] is True
    assert r['review_dimensions']['evidence']=='not_detected_not_verified'
    assert r['review_dimensions']['search_intent']=='not_assessed'

def test_dashboard_candidates():
    r=dashboard('## 価格\n料金',{'analysis':{'intents':['cost']}},{'claims':[{'kinds':['commercial'],'source_ids':['s1']}]},{'quotes':[{'candidate_urls':['https://example.org']}],'similar_articles':[]},{'approved':True,'issues':[]})
    assert r['review_dimensions']['evidence']=='human_confirmation_required'
    assert r['review_dimensions']['testimonials']=='human_confirmation_required'
