from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
import pytest
from generation_control import prepare_page, CallBudget

NOW=datetime(2026,11,26,tzinfo=timezone.utc)
def page(host='example.com', age=0):
    return {'url':'https://example.com/product','sources':[{'url':f'https://{host}/product','text':'商品情報','fetched_at':(NOW-timedelta(days=age)).isoformat()}]}

@pytest.mark.parametrize('host,age',[('evil.com',0),('example.com',2),('example.com',-1)])
def test_unusable(host,age):
    p,_=prepare_page('商品','暮らし',page(host,age),'比較',NOW)
    assert p.max_calls==0

def test_comparison():
    p,r=prepare_page('商品','暮らし',page(),'比較',NOW)
    assert p.strategy=='comparison_first' and p.max_calls==6 and p.human_review_required
    assert r[0].url=='https://example.com/product'

def test_medical():
    p,_=prepare_page('がん検査','健康',page(),'選び方',NOW)
    assert p.max_calls==8 and p.human_review_required

def test_budget_counts_failed_calls():
    f=Mock(side_effect=ValueError('failed'))
    b=CallBudget(f,1)
    with pytest.raises(ValueError): b('x')
    with pytest.raises(RuntimeError): b('x')
    assert f.call_count==1 and b.remaining==0

def test_budget_forwards_arguments():
    f=Mock(return_value='ok'); b=CallBudget(f,2)
    assert b('x',max_tokens=5)=='ok'
    f.assert_called_once_with('x',max_tokens=5)
