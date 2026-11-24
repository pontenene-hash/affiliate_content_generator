import unittest
from article_history import ANGLES, EXTRA_ANGLES, article_key, next_topics, topic_inventory

class TopicTests(unittest.TestCase):
    def setUp(self):
        self.item = {'title':'商品','genre':'暮らし','keyword':'商品 口コミ 評判','product_url':'https://example.com','affiliate_url':'https://example.com/ad'}
    def history(self, angles):
        return [{'key':article_key(self.item['affiliate_url'], a)} for a, _, _ in angles]
    def test_original_exhausted(self):
        h=self.history(ANGLES)
        tasks=next_topics([self.item],h,5)
        self.assertEqual(len(tasks),4)
        self.assertEqual(len({t[1] for t in tasks}),4)
        self.assertNotIn('口コミ',tasks[0][3])
        self.assertTrue(all(t[1] not in {x['key'] for x in h} for t in tasks))
    def test_all_exhausted(self):
        h=self.history(ANGLES+EXTRA_ANGLES)
        self.assertEqual(next_topics([self.item],h,5),[])
        self.assertEqual(topic_inventory([self.item],h)[0]['status'],'topics_exhausted')
    def test_no_products(self):
        self.assertEqual(topic_inventory([],[]),[])
    def test_original_keys(self):
        self.assertEqual(next_topics([self.item],[],1)[0][1],article_key(self.item['affiliate_url'],ANGLES[0][0]))
