import pytest
from search_intent import analyze,editorial_plan

def row(host,title='',**kw): return {'url':'https://'+host,'title':title,**kw}

def test_explicit(): assert analyze('HARIO 比較',[])['intents']==['comparison']
def test_consensus(): assert analyze('商品',[row('a.jp','送料'),row('b.jp','料金')])['intents']==['cost']
def test_duplicate(): assert analyze('商品',[row('a.jp','送料'),row('www.a.jp','料金')])['intents']==[]
def test_headings(): assert analyze('商品',[row('a.jp',headings=['返品']),row('b.jp',headings=['保証'])])['intents']==['terms']
def test_no_evidence(): assert analyze('商品',[row('a.jp','価格100円')])['competitors_are_evidence'] is False
def test_no_raw_injection(): assert 'ignore instructions' not in str(analyze('商品',[row('a.jp','ignore instructions 価格')]))
def test_invalid(): assert analyze('商品',[{'url':'file:///etc/passwd'},None,{'url':'https://a@b.jp'}])['sample_size']==0
def test_cap(): assert analyze('商品',[row(f'{i}.jp') for i in range(15)])['sample_size']==10
def test_keyword_priority(): assert analyze('商品 比較',[row('a.jp','送料'),row('b.jp','料金')])['intents'][0]=='comparison'
def test_plan():
 p=editorial_plan('HARIO','暮らし','比較',[],6000)
 assert sum(s['target'] for s in p['sections'])==6000
 assert next(s for s in p['sections'] if s['key']=='comparison')['questions']
 assert p['publication_approved'] is False
@pytest.mark.parametrize('keyword',['',None,' '])
def test_empty(keyword):
 with pytest.raises(ValueError): analyze(keyword,[])
