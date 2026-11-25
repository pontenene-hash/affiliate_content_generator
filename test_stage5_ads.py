import unittest
from stage5_ads import insert_ads, ad_issues, mark_sponsored
import markdown
class AdsTest(unittest.TestCase):
    def test_insert(self):
        link='https://px.a8.net/svt/ejp?a8mat=TEST&x=2'
        md='# 題\n\n導入\n\n---[A8_AD]_--\n\n## 一\n本文\n\n## 二\n本文\n\n## 三\n本文\n\n## まとめ\n結論'
        out=insert_ads(md,link)
        self.assertEqual(out.count(link),3)
        self.assertNotIn('A8_AD',out)
        self.assertEqual(insert_ads(out,link),out)
        html=mark_sponsored(markdown.markdown(out),link)
        self.assertEqual(ad_issues(out,html,link),[])
        self.assertIn('sponsored',html)
    def test_invalid(self):
        with self.assertRaises(ValueError): insert_ads('本文','javascript:bad')
    def test_existing(self):
        link='https://px.a8.net/svt/ejp?a8mat=TEST'
        self.assertEqual(insert_ads(f'[広告]({link})',link).count(link),1)
if __name__=='__main__': unittest.main()
