import unittest
from stage4_metadata import source_issues, seo_metadata
from social_tools import _load_json_response
class Run95Tests(unittest.TestCase):
    def test_neutral(self):
        self.assertFalse(source_issues('### 4. 配送先・支払い方法の入力と注文確定手順\n最新の送料を公式サイトで確認しましょう。',''))
    def test_claim(self):
        self.assertTrue(source_issues('税込3,300円以上で全国一律送料無料が適用されます。','税込3300円'))
    def test_category(self):
        self.assertEqual(seo_metadata('HARIO NETSHOP','使い方','ペット商品',article='コーヒー 茶器 調理 家庭用品 コーヒー ペット')['category'],'暮らし・生活用品')
    def test_json_string(self):
        self.assertEqual(_load_json_response('{"text":"a,}"}')['text'],'a,}')
