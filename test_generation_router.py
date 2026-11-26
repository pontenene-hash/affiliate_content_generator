import pytest
from generation_router import route

@pytest.mark.parametrize('name,genre,context,count,comparison,budget,expected',[
('HARIO','一般','','2',False,8,'invalid'),
('HARIO','一般','',2,False,8,'single_then_targeted_repair'),
('HARIO','一般','',2,True,8,'comparison_first'),
('尿がん検査くん','一般','',2,False,8,'evidence_first_sections'),
('商品','一般','医療',2,True,8,'evidence_first_sections'),
('サプリ','健康食品','定期購入',2,False,8,'evidence_first_sections'),
('美容液','美容','',0,False,8,'hold_for_research'),
('HARIO','一般','',0,False,8,'hold_for_research'),
('尿がん検査くん','一般','',2,False,2,'hold_for_research'),
('HARIO','一般','',2,True,1,'hold_for_research'),
('HARIO','一般','',2,False,0,'hold_for_research'),
('HARIO','一般','',2,False,1,'single_then_targeted_repair'),
('商品','健康','',2,False,8,'evidence_first_sections'),
('HARIO','一般','',-1,False,8,'invalid'),
])
def test_route(name,genre,context,count,comparison,budget,expected):
    if expected=='invalid':
        with pytest.raises(ValueError): route(name,genre,context,evidence_count=count,comparison=comparison,call_budget=budget)
    else:
        r=route(name,genre,context,evidence_count=count,comparison=comparison,call_budget=budget)
        assert r.strategy==expected
        assert 0<=r.max_generation_calls<=budget
        assert r.human_review_required is True
