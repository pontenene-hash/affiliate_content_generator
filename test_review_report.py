from datetime import datetime, timezone, timedelta
from evidence_ledger import Evidence
from claim_review import audit_claims
import pytest
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
@pytest.mark.parametrize('excerpt,days,host,product,reason',[
 ('送料は500円。ただし離島は別途。',0,'example.com','A','条件・例外確認'),
 ('送料は500円。',2,'example.com','A','取得日時確認'),
 ('送料は500円。',-1,'example.com','A','取得日時確認'),
 ('送料は500円。',0,'evil.com','A','根拠不足'),
 ('送料は500円。',0,'example.com','B','根拠不足'),
 ('送料は700円。',0,'example.com','A','矛盾候補'),
 ('送料は500円。',0,'example.com','A','原文・文脈確認'),
])
def test_report(excerpt,days,host,product,reason):
 e=Evidence('1',product,'https://'+host,excerpt,NOW-timedelta(days=days))
 r=audit_claims('送料は500円。','A',[e],{'example.com'},NOW)['review_report']
 assert reason in r['rows'][0]['reasons']
 assert not r['approved'] and r['human_review_required']
 if host=='evil.com' or product=='B': assert not r['rows'][0]['sources']
def test_priority():
 e=Evidence('1','A','https://example.com','送料は500円。治療効果がある。',NOW)
 r=audit_claims('送料は500円。治療効果がある。','A',[e],{'example.com'},NOW)['review_report']
 assert r['rows'][0]['claim']=='治療効果がある。' and r['high_priority']==1

def test_empty():
 r=audit_claims('こんにちは。','A',[],set(),NOW)['review_report']
 assert r['total']==0 and not r['approved']
