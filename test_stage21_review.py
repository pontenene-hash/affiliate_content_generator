from datetime import datetime, timezone, timedelta
from evidence_ledger import Evidence
from claim_review import audit_claims
from affiliate_article_guard import _has_unverified_review_reference
from creative_grounding import build_brief
import pytest
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
@pytest.mark.parametrize('text',['口コミでは満足という声。公式サイトで確認してください。','口コミを鵜呑みにせず、評判が良いという声を確認してください。','口コミでは好評ですが確認できません。'])
def test_mixed_review(text): assert _has_unverified_review_reference(text)
@pytest.mark.parametrize('text,flag',[('送料は500円。ただし一部地域は別途。','condition'),('送料は500円。対象外の商品があります。','negation'),('送料は500円。目安です。','uncertainty')])
def test_context(text,flag):
 e=Evidence('1','P','https://example.com/a',text,NOW)
 a=audit_claims('送料は500円。','P',[e],{'example.com'},NOW)
 assert flag in a['claims'][0]['context_flags'][0]['flags']
 assert a['review_report']['rows'][0]['priority']=='high' and not a['approved']
def test_stale():
 e=Evidence('1','P','https://example.com/a','送料は500円。ただし条件あり。',NOW-timedelta(days=2))
 assert not audit_claims('送料は500円。','P',[e],{'example.com'},NOW)['claims'][0]['context_flags']
def test_angles():
 b=build_brief('## 送料\n## ギフト\n## 部品','P')
 assert len({s['angle'] for s in b['slides'][1:-1]})==7
 assert b['videos']['reel']['scenes'][0]['topic']!=b['videos']['youtube']['scenes'][0]['topic']
 assert not b['publication_approved']
