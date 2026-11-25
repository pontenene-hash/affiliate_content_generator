import unittest, zipfile, re
from pathlib import Path
from section_engine import complete_sections
ROOT=Path(__file__).resolve().parent / 'tests' / 'fixtures'
def load(n):
    with zipfile.ZipFile(ROOT/f'affiliate-review-required-{n}.zip') as z:
        return z.read(next(x for x in z.namelist() if x.endswith('.md'))).decode()
class RealTests(unittest.TestCase):
    def test_real_retention(self):
        for n in (97,98):
            a=load(n)
            result,q,log=complete_sections(a,lambda *_:'',lambda _: {'issues':[]},len,20000,30000)
            self.assertEqual(result,a)
            self.assertIn('minimum not reached; human review required',log)
    def test_rotation(self):
        a=load(98); seen=[]
        def gen(h,*_): seen.append(h); return ''
        complete_sections(a,gen,lambda _: {'issues':[]},len,20000,30000)
        self.assertEqual(len(set(seen)),3)
    def test_changed_issue(self):
        a=load(98)
        def check(s): return {'issues':[{'code':'source','message':'new' if '架空条件' in s else 'old'}]}
        self.assertEqual(complete_sections(a,lambda *_:'架空条件を追加します。',check,len,20000,30000)[0],a)
    def test_normalized_duplicate(self):
        a='## 比較\n\n用途を整理します。\n\n## まとめ\n\n確認します。'
        self.assertEqual(complete_sections(a,lambda *_:'用途を 整理します！',lambda _: {'issues':[]},len,100,200)[0],a)
if __name__=='__main__': unittest.main()
