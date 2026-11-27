import pytest
from editorial_dashboard import dashboard

def run(article='', intents=(), claims=(), quotes=(), similar=(), approved=True):
    return dashboard(article, {'analysis':{'intents':intents}}, {'claims':claims}, {'quotes':quotes,'similar_articles':similar}, {'approved':approved,'issues':[]})

def test_empty():
    d=run(); assert d['intent_body_percent'] is None and not d['publication_approved']

@pytest.mark.parametrize('intent,term',[('cost','料金'),('comparison','比較'),('reputation','口コミ'),('usage','注文'),('terms','返品'),('safety','注意')])
def test_heading_only(intent,term):
    d=run('## '+term,[intent]); assert d['intent_body_percent']==0 and 'review_search_intent' in d['tasks']
    assert run('本文：'+term,[intent])['intent_body_percent']==100

def test_claims():
    d=run(claims=[{'kinds':['medical','commercial'],'source_ids':[]},{'kinds':['medical'],'source_ids':['a']}]); assert d['claim_counts']['medical']=={'total':2,'exact_candidates':1}; assert d['unmatched_claims']==1 and 'verify_claims' in d['tasks']

def test_review_tasks():
    d=run(quotes=[{'candidate_urls':[]}],similar=[{}],approved=False); assert d['tasks']==['verify_quotes','review_similarity','resolve_quality_issues']
