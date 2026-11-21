import copy
import json
import unittest
from pathlib import Path
from affiliate_publish_guard import guard_bundle, UNSAFE

class GuardTests(unittest.TestCase):
    def test_medical_bundle(self):
        d = {'title': '自宅でがんリスクが分かる', 'product_name': '尿がん検査くん',
             'affiliate_url': 'https://example.com/?ref=1',
             'social_plan': {'x_posts': [{'text': '通院不要'}],
                 'carousel': {'slides': [{'title': '早期発見', 'body': '通院不要'} for _ in range(9)]},
                 'reel': {'total_duration': '42秒', 'scenes': [{'duration': '14秒', 'caption': '早期発見'} for _ in range(3)]},
                 'creative_prompts': {'instagram_carousel': [{'prompt': '早期発見' * 1000, 'size': '1080×1350'} for _ in range(9)]}},
             'gbp': {'video_prompt': '総尺45秒、40〜45秒 CTA'}, '[V5_REVIEWED]': True}
        old = copy.deepcopy(d)
        result, report = guard_bundle(d)
        self.assertEqual(d, old)
        self.assertEqual(set(result), set(d))
        self.assertEqual(len(result['social_plan']['carousel']['slides']), 9)
        self.assertEqual(result['social_plan']['reel']['total_duration'], '42秒')
        self.assertIn('45秒', result['gbp']['video_prompt'])
        self.assertTrue(report['medical_review_required'])
        self.assertEqual(len(report['hold_items']), 9)
        self.assertEqual(result['social_plan']['x_posts'][0]['text'].count(d['affiliate_url']), 1)
        self.assertFalse(UNSAFE.search(result['social_plan']['x_posts'][0]['text']))
        self.assertTrue(all(len(p['prompt']) <= 1100 for p in result['social_plan']['creative_prompts']['instagram_carousel']))
        second, _ = guard_bundle(result)
        self.assertEqual(result, second)

    def test_unrelated_copy_preserved(self):
        d = {'title':'枕の紹介','product_name':'枕', 'social_plan': {'threads': {'text': '寝具の特徴をご紹介'},
             'creative_prompts': {'x_image': {'prompt': '短い安全な画像説明'}}}}
        result, report = guard_bundle(d)
        self.assertEqual(result, d)
        self.assertFalse(report['medical_review_required'])

if __name__ == '__main__':
    unittest.main()
