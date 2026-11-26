import pytest
from dynamic_review import review_article
from test_review_benchmark import NOW, reviewer, case

def run(text, texts, budget=0, reviewers=()):
    c=case('x',text,texts,True)
    return review_article(text,'X',c['records'],c['hosts'],NOW,reviewers,budget)

def test_priority_budget():
    r=run('送料は500円。治療効果があります。予防効果があります。',['送料は500円。治療効果があります。予防効果があります。'],2,[reviewer,reviewer]); assert [x['mode'] for x in r['rows']]==['E','D','C']; assert r['calls']==2

def test_no_approval():
    r=run('送料は500円。',['送料は500円。']); assert not r['approved'] and r['human_review_required'] and not r['rows'][0]['approved']

def test_duplicate(): assert len(run('送料は500円。送料は500円。',['送料は500円。'])['rows'])==1

def test_no_callbacks(): assert run('治療効果があります。',['治療効果があります。'],2)['rows'][0]['mode']=='D'

def test_one_callback(): assert run('治療効果があります。',['治療効果があります。'],2,[reviewer])['calls']==0

def test_failure_counts():
    def fail(*a): raise RuntimeError()
    r=run('治療効果があります。',['治療効果があります。'],2,[fail,fail]); assert r['calls']==2 and r['rows'][0]['flagged']

def test_conflict(): assert run('送料は500円。',['送料は500円。','送料は700円。'])['rows'][0]['mode']=='D'

def test_empty(): assert run('こんにちは。',[])['rows']==[]

@pytest.mark.parametrize('budget',[-1,True,1.5])
def test_invalid_budget(budget):
    with pytest.raises(ValueError):run('送料は500円。',[],budget)

def test_five_articles():
    for i in range(5):
        r=run('治療効果があります。',['治療効果があります。'],2,[reviewer,reviewer]); assert r['calls']==2 and not r['approved']
