import pytest
from article_plan import plan, section_instruction
@pytest.mark.parametrize('name,genre,required',[('HARIO','一般','features'),('尿がん検査くん','検査','medical_limits'),('美容液','美容','cosmetic_limits'),('宅配弁当','食品','food_safety'),('サプリ','定期購入','contract_terms'),('不明','健康','health_unknown')])
def test_plan(name,genre,required):
    p=plan(name,genre)
    assert sum(s.target for s in p)==6000
    assert required in {s.key for s in p}
    assert len({s.key for s in p})==len(p)
    assert all(s.target>0 for s in p)
    assert p[-1].key=='summary'
def test_multiple():
    assert {'nutrition_safety','contract_terms'} <= {s.key for s in plan('サプリ','定期購入')}
def test_context():
    assert 'medical_limits' in {s.key for s in plan('商品','一般','がん検査')}
@pytest.mark.parametrize('target',[4999,8001,True,6000.0])
def test_bad_target(target):
    with pytest.raises(ValueError): plan('商品','一般',target=target)
def test_missing_evidence():
    s=next(s for s in plan('商品','一般') if s.key=='features')
    assert section_instruction(s,[])['mode']=='questions_only'
    assert section_instruction(s,[' '])['mode']=='questions_only'
    assert section_instruction(s,['E1'])['human_review_required'] is True
@pytest.mark.parametrize('target',[5000,8000,6001])
def test_budget(target):
    assert sum(s.target for s in plan('商品','一般',target=target))==target
