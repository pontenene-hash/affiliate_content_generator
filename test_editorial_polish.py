import unittest
from editorial_polish import display_name, polish
from stage4_metadata import seo_metadata
class EditorialTests(unittest.TestCase):
    def test_hario(self):
        original='家庭用品からペット・アウトドア用品を販売【HARIO NETSHOP】'
        name=display_name(original)
        self.assertEqual(name,'HARIO NETSHOP')
        md=polish('# '+original+'の口コミ・評判\n\n'+original,original,name)
        self.assertNotIn('口コミ',md)
        self.assertNotIn(original,md)
        meta=seo_metadata(name,name+' 口コミ 評判','ペット商品',md.splitlines()[0][2:],md)
        self.assertEqual(meta['tags'],[name])
    def test_url(self):
        self.assertIn('https://example.com/a?x=1&y=2',polish('https://example.com/a?x=1&y=2','a','b'))
