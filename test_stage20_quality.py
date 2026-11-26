import unittest
from datetime import datetime,timezone,timedelta
from evidence_ledger import Evidence
from stage20_quality import candidate_sources,initial_sections,public_snippet,neutral_review_line
from affiliate_article_guard import _has_unverified_review_reference,_review_text_requires_verification
from stage19_context import creative_context
class Stage20(unittest.TestCase):
 def test_faq(self): self.assertFalse(_has_unverified_review_reference('### Q. 口コミや評判はどこで確認できますか？'))
 def test_mixed(self): self.assertTrue(_review_text_requires_verification('口コミでは評判が良い。'))
 def test_quoted(self): self.assertTrue(_has_unverified_review_reference('口コミ：「最高だった」'))
 def test_candidate(self):
  now=datetime.now(timezone.utc); e=Evidence('1','P','https://example.com/a','送料は500円。',now)
  self.assertEqual(candidate_sources('送料は無料','P',[e],{'example.com'},now,1)[0]['status'],'retrieval_only')
  self.assertFalse(candidate_sources('送料は無料','Q',[e],{'example.com'},now,1))
  self.assertFalse(candidate_sources('送料は無料','P',[e],{'other.com'},now,1))
  self.assertFalse(candidate_sources('送料は無料','P',[e],{'example.com'},now+timedelta(days=2),1))
 def test_sections(self):
  calls=[]
  def gen(p,**kw): calls.append(p);return '前半' if len(calls)==1 else '後半'
  self.assertEqual(initial_sections(gen,'ルール','P','暮らし','comparison_first'),'前半\n\n後半');self.assertEqual(len(calls),2);self.assertIn('前半',calls[1])
 def test_simple(self): self.assertEqual(initial_sections(lambda p:p,'prompt','P','暮らし','single_then_targeted_repair'),'prompt')
 def test_public(self):
  text=creative_context('## 送料\n## ギフト\n## 部品\n## 比較','P','fallback')
  self.assertNotIn('断定しない',text); self.assertNotIn('断定しない',public_snippet(text));self.assertIn('包装条件',public_snippet(text))
