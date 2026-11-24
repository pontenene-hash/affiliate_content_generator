import unittest
from stage4_metadata import source_issues, seo_metadata
class MetadataTests(unittest.TestCase):
    def test_unmatched(self):
        self.assertTrue(source_issues('料金2,980円','料金1980円'))
    def test_normalized(self):
        self.assertFalse(source_issues('料金２，９８０円','料金2980円'))
    def test_context(self):
        self.assertTrue(source_issues('送料無料','送料無料'))
    def test_metadata(self):
        self.assertEqual(seo_metadata('商品','選び方','暮らし')['category'],'暮らし・生活用品')
    def test_after_use(self):
        result = seo_metadata('エイペックスダビング','エイペックスダビング 利用後 確認','エンタメ',article='## 納品物の確認')
        self.assertIn('利用後', result['seo_title'])
        self.assertIn('納品物の確認', result['description'])
        self.assertEqual(result['category'],'エンタメ')
