import unittest
from integrated_quality import extra_issues, repair_article, safe_creative_source, review_leads
from article_history import next_topics, make_record

class IntegratedTests(unittest.TestCase):
    def test_title(self):
        self.assertTrue(extra_issues('# 商品の口コミ・評判\n'))
    def test_leads_not_verified(self):
        self.assertEqual(review_leads(lambda *a:[{'title':'口コミ','url':'https://example.com'}], '商品')[0]['verification'],'原文・掲載条件未確認')
    def test_repair_rejects_short(self):
        link='https://example.com/a'
        md='# 商品の口コミ\n\n※本記事にはアフィリエイト広告が含まれます。\n\n## 選び方\n'+link
        result,_=repair_article(md,'',link,lambda *a:'# 商品の選び方',len,'商品','暮らし')
        self.assertEqual(result,md)
    def test_balance(self):
        a={'title':'A','genre':'暮らし','product_url':'https://example.com/a','affiliate_url':'https://example.com/refa'}
        b={'title':'B','genre':'健康','product_url':'https://example.com/b','affiliate_url':'https://example.com/refb'}
        task=next_topics([a],[],1)[0]
        history=[make_record(a,task[1],task[2],task[3],'A',1)]
        self.assertEqual(next_topics([a,b],history,1)[0][0],b)
    def test_safe_source(self):
        self.assertNotIn('送料無料',safe_creative_source('商品'))
if __name__=='__main__': unittest.main()
