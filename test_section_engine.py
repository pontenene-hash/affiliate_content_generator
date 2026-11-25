import unittest
from section_engine import complete_sections
A='# 商品の選び方\n\n## 比較方法\n\n用途を整理します。\n\n## まとめ\n\n条件を確認します。'
def check(s):
    return {'issues':([{'code':'unsupported'}] if '送料無料' in s else [])+([{'code':'article_too_short'}] if len(s)<100 else [])}
class Tests(unittest.TestCase):
    def run_case(self,fn): return complete_sections(A,fn,check,len,100,200,2)
    def test_growth(self):
        a,q,log=self.run_case(lambda *_:'使用する場面を思い浮かべ、収納場所の寸法や手入れに使える時間を整理してから、候補の仕様を比較します。')
        self.assertGreater(len(a),len(A)); self.assertTrue(a.endswith('条件を確認します。'))
    def test_empty(self): self.assertEqual(self.run_case(lambda *_:'')[0],A)
    def test_claim(self): self.assertEqual(self.run_case(lambda *_:'送料無料です。')[0],A)
    def test_duplicate(self): self.assertEqual(self.run_case(lambda *_:'用途を整理します。')[0],A)
    def test_internal_duplicate(self): self.assertEqual(self.run_case(lambda *_:'収納場所を測ります。収納場所を測ります。')[0],A)
    def test_internal_paragraph_duplicate(self): self.assertEqual(self.run_case(lambda *_:'収納場所を測ります。\n\n収納場所を 測ります！')[0],A)
    def test_mixed_duplicate(self): self.assertEqual(self.run_case(lambda *_:'収納場所を測ります。用途を整理します。')[0],A)
    def test_heading(self): self.assertEqual(self.run_case(lambda *_:'## まとめ\n追加')[0],A)
    def test_error(self):
        def fail(*_): raise TimeoutError()
        self.assertEqual(self.run_case(fail)[0],A)
    def test_limit(self): self.assertEqual(self.run_case(lambda *_:'長い説明'*100)[0],A)
if __name__=='__main__': unittest.main()
