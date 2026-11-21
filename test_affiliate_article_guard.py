import unittest
from affiliate_article_guard import review_article

URL = 'https://example.com/affiliate?ref=1'


def article(title='生活用品の紹介', body='使い方や注意点を確認できます。'):
    return ('# ' + title + '\n\n※本記事にはアフィリエイト広告が含まれます。\n\n'
            '## 特徴\n' + body * 35 + '\n\n## まとめ\n[詳細を見る](' + URL + ')')


class ArticleGuardTests(unittest.TestCase):
    def check_issue(self, markdown, code, product='収納ケース', genre='暮らし', source='公式の説明'):
        result = review_article(markdown, product, genre, URL, source)
        self.assertFalse(result['approved'])
        self.assertIn(code, [issue['code'] for issue in result['issues']])

    def test_ordinary_article_passes(self):
        self.assertTrue(review_article(article(), '収納ケース', '暮らし', URL, '公式の説明')['approved'])

    def test_medical_claims_block(self):
        self.check_issue(article('尿がん検査くん', 'ステージ1から全身のがんリスクが分かる。'),
                         'medical_human_review', '尿がん検査くん', '健康', '商品ページ')

    def test_missing_pr_blocks(self):
        self.check_issue(article().replace('※本記事にはアフィリエイト広告が含まれます。', ''), 'missing_disclosure')

    def test_missing_link_blocks(self):
        self.check_issue(article().replace(URL, 'https://example.com/other'), 'missing_link')

    def test_unsourced_review_blocks(self):
        self.check_issue(article(body='口コミで評判が良い。'), 'testimonial_verification_required')

    def test_price_without_source_blocks(self):
        self.check_issue(article(body='価格は13,500円。'), 'price_source_missing', source='')

    def test_price_mismatch_blocks(self):
        self.check_issue(article(body='価格は15,000円。'), 'price_mismatch', source='価格は13,500円です。')

    def test_matching_price_can_pass(self):
        result = review_article(article(body='価格は13,500円。商品情報を確認してください。'), '収納ケース', '暮らし', URL, '価格は13,500円です。')
        self.assertTrue(result['approved'])

    def test_other_markdown_link_blocks(self):
        self.check_issue(article() + '\n[別サイト](https://example.com/other)', 'unregistered_link')

    def test_ordinary_review_discussion_does_not_require_source(self):
        result = review_article(article(body='口コミは確認できないため紹介しない。'), '収納ケース', '暮らし', URL, '公式の説明')
        self.assertTrue(result['approved'])

    def test_high_risk_claim_blocks(self):
        self.check_issue(article(body='ステージ1から早期発見できる。'), 'high_risk_claim')

    def test_no_mutation(self):
        original = article()
        review_article(original, '収納ケース', '暮らし', URL)
        self.assertEqual(original, article())


if __name__ == '__main__':
    unittest.main()
