import pytest
from specialist_review import classify,specialist_review
@pytest.mark.parametrize('name,genre,article,expected',[
 ('HARIO NETSHOP','暮らし','収納用品','general'),('尿がん検査くん','健康','','medical'),('美容液','美容','','cosmetic'),('サプリ','健康','','nutrition'),('宅配弁当','食品','','food'),('動画サービス','エンタメ','月額料金','contract'),('商品','健康','','health_unknown'),('一般商品','暮らし','がんを治療','medical')])
def test_classification(name,genre,article,expected):
 assert expected in classify(name,genre,article)
def test_multi():
 assert {'nutrition','contract','food'} <= set(classify('健康食品','','定期購入'))
@pytest.mark.parametrize('name,article,code',[('がん検査','陰性なら安心','medical'),('サプリ','必ず痩せる','nutrition'),('美容液','シミが消える','cosmetic'),('保険','絶対に損しない','contract'),('弁当','アレルギーは心配ない','food')])
def test_claim(name,article,code):
 assert 'specialist_'+code+'_claim' in [i['code'] for i in specialist_review(name,'',article)['issues']]
def test_no_auto_approval():
 assert 'approved' not in specialist_review('がん検査','','医療機関に相談')
