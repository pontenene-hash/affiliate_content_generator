import unittest
from affiliate_article_guard import review_article

URL = 'https://example.com/affiliate?ref=1'

def article(title='生活用品の紹介', body='使い方や注意点を確認できます。'):
    return ('# ' + title + '\n\n※本記事にはアフィリエイト広告が含まれます。\n\n'
            '## 特徴\n' + body * 35 + '\n\n## まとめ\n[詳細を見る](' + URL + ')')

class ArticleGuardTests(unittest.TestCase):
    def test_ordinary_article_passes(self):
        self.assertTrue(review_article(article(), '収納ケース', '暮らし', URL, '公式の説明')['approved'])
    def test_medical_claims_block(self):
        r = review_article(article('尿がん検査くん', 'ステージ1から全身のがんリスクが分かる。'), '尿がん検査くん', '健康', URL, '商品ページ')
        self.assertFalse(r['approved'])
        self.assertIn('medical_human_review', [x['code'] for x in r['issues']])
    def test_missing_pr_blocks(self):
        self.assertFalse(review_article(article().replace('※本記事にはアフィリエイト広告が含まれます。',''), '収納ケース', '暮らし', URL)['approved'])
    def test_missing_link_blocks(self):
        self.assertFalse(review_article(article().replace(URL, 'https://example.com/other'), '収納ケース', '暮らし', URL)['approved'])
    def test_unsourced_review_blocks(self):
        self.assertFalse(review_article(article(body='口コミで評判が良い。'), '収納ケース', '暮らし', URL)['approved'])
    def test_price_without_source_blocks(self):
        self.assertFalse(review_article(article(body='価格は13,500円。'), '収納ケース', '暮らし', URL)['approved'])
    def test_no_mutation(self):
        s = article(); review_article(s, '収納ケース', '暮らし', URL); self.assertEqual(s, article())

if __name__ == '__main__': unittest.main()
