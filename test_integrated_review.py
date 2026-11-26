from datetime import datetime, timezone, timedelta
import pytest
from evidence_ledger import Evidence
from integrated_review import prepare, review
NOW=datetime(2026,11,26,tzinfo=timezone.utc)
def ev(product='HARIO', url='https://example.org/info', age=0, conditions='', id='1'):
    return Evidence(id,product,url,'商品仕様の資料',NOW-timedelta(days=age),conditions)
def prep(evidence=None, product='HARIO', genre='一般', **kw):
    return prepare(product,genre,'', [ev()] if evidence is None else evidence, {'example.org'},NOW,**kw)
@pytest.mark.parametrize('evidence',[[],[ev(product='別商品')],[ev(url='https://example.org.evil.test')],[ev(age=2)],[ev(conditions='限定条件')]])
def test_hold(evidence):
    p=prep(evidence); assert p.max_calls==0 and not p.sections

def test_general():
    p=prep(); assert p.strategy=='single_then_targeted_repair' and p.evidence_ids==('1',)
    assert all(not s['evidence_ids'] for s in p.sections)
def test_medical():
    p=prep([ev(product='尿がん検査くん')],product='尿がん検査くん'); assert p.strategy=='evidence_first_sections'
    assert any(s['section']=='medical_limits' for s in p.sections)
def test_comparison(): assert prep(comparison=True).strategy=='comparison_first'
def test_budget(): assert prep(budget=0).max_calls==0
def test_duplicate():
    with pytest.raises(ValueError): prep([ev(),ev()])
def test_new_risk():
    r=review(prep(),'陰性なら安心。がん検査。',calls=1); assert 'new_risk_category' in r['issues'] and 'specialist_medical_claim' in r['issues']
def test_existing_guard(): assert 'old_guard' in review(prep(),'本文',calls=1,existing_issues=['old_guard'])['issues']
def test_budget_overrun(): assert 'budget_exceeded' in review(prep(),'本文',calls=4)['issues']
def test_hold_final(): assert 'preflight_hold' in review(prep([]),'本文',calls=0)['issues']
def test_never_publish(): assert review(prep(),'説明'*2600,calls=1,evidence_verified=True)['publication_approved'] is False
def test_missing_verification(): assert 'claim_evidence_review_required' in review(prep(),'説明'*2600,calls=1)['issues']
