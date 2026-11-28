import copy
import json
from datetime import date
from pathlib import Path
from zipfile import ZipFile
import pytest
from editorial_review import editorial_review, evidence_status
from improvement_workbench import *
from workbench_ui import report_rows

TODAY = date(2026, 11, 28)


def evidence():
    return {'claim': '価格1000円', 'quote': '商品の価格1000円です',
            'source_url': 'https://example.com/product', 'checked_on': '2026-11-28'}


def archive():
    return {'schema': 1, 'article_id': 'item-1', 'revisions': []}


def metric(**changes):
    return dict(article_id='item-1', source='fixture', currency='JPY', timezone='Asia/Tokyo',
                start='2026-11-01', end='2026-11-07', impressions=100, clicks=10, conversions=2, revenue=200, **changes)


@pytest.mark.parametrize('genre', ['コスメ・スキンケア','エステ・ダイエット','美容グッズ','ペット商品','グルメ・食品','健康','暮らし','エンタメ','学び・資格'])
def test_nine_genre_synthetic_editorial_boundaries(genre):
    text = f'# {genre}\n## FAQ\n価格1000円\n## よくある質問（追加分）\n価格1000円'
    r = editorial_review(text, [evidence()], TODAY)
    assert 'fragmented_faq' in {x['code'] for x in r['findings']}
    assert r['evidence'][0]['status'] == 'supplied_unverified'
    assert not r['facts_verified'] and not r['publication_approved']
    assert evidence_status(evidence(), text.replace('1000', '2000'), TODAY) == 'claim_changed'


@pytest.mark.parametrize('patch,status', [({'source_url': 'http://example.com'}, 'invalid_source'),
    ({'source_url': 'https://user:password@example.com'}, 'invalid_source'),
    ({'checked_on': '2027-01-01'}, 'future_date'), ({'checked_on': '2026-01-01'}, 'stale'),
    ({'checked_on': 'bad'}, 'invalid_record'), ({'quote': '別の金額'}, 'quote_mismatch'),
    ({'claim': ''}, 'incomplete')])
def test_invalid_evidence_stays_unverified(patch, status):
    row = evidence(); row.update(patch)
    assert evidence_status(row, '価格1000円', TODAY) == status


def test_saved_articles_detect_fragmentation_without_modifying_text():
    for number, count in [(97, 3), (98, 1)]:
        p = Path(__file__).parent / f'tests/fixtures/affiliate-review-required-{number}.zip'
        with ZipFile(p) as z:
            text = z.read(next(n for n in z.namelist() if n.endswith('.md'))).decode()
        result = editorial_review(text, [], TODAY)
        assert result['faq_sections'] == count
        assert 'evidence_review' in {x['code'] for x in result['findings']}
        assert ('fragmented_faq' in {x['code'] for x in result['findings']}) == (number == 97)


def test_duplicate_headings_code_fences_and_normalization():
    result = editorial_review('## ＡＢＣ\n## abc\n```\n## FAQ\n## FAQ\n```')
    assert result['faq_sections'] == 0
    assert result['findings'][0]['code'] == 'duplicate_heading'


def test_revision_export_import_edit_restore_round_trip():
    initial = archive()
    a = add_revision(initial, '元の本文', '初回保存', {'source_text': '根拠'}, [evidence()])
    b = add_revision(a, '修正本文', '反復削減', {}, [])
    restored = restore_revision(validate_archive(load_json(json.dumps(b).encode())), 1)
    assert initial['revisions'] == [] and len(a['revisions']) == 1
    assert len(restored['revisions']) == 3
    assert restored['revisions'][-1]['article'] == '元の本文'
    assert restored['revisions'][-1]['context'] == {'source_text': '根拠'}
    assert '-元の本文' in revision_diff(a['revisions'][0]['article'], b['revisions'][1]['article'])


@pytest.mark.parametrize('mutation', ['article', 'parent', 'article_id', 'version'])
def test_tampered_archives_rejected(mutation):
    a = add_revision(archive(), '本文', '理由', {}, [])
    a['revisions'][0][mutation] = '改変'
    with pytest.raises(ValueError): validate_archive(a)


@pytest.mark.parametrize('raw', [b'not json', b'NaN', b'\xff', b' ' * (MAX_BYTES + 1)])
def test_bad_or_oversized_json_rejected(raw):
    with pytest.raises(ValueError): load_json(raw)


def test_missing_metrics_are_unknown_not_zero():
    a = metric(); a['revenue'] = None
    r = metrics_summary([a])
    assert r['totals']['revenue'] is None and r['ctr'] == .1
    assert not r['metrics_connected'] and not r['attribution_verified']
    assert all(v is None for v in metrics_summary([])['totals'].values())


@pytest.mark.parametrize('field,value', [('clicks', True), ('revenue', float('nan')), ('conversions', -1),
                                        ('clicks', 101), ('end', '2026-10-01'), ('start', 'bad')])
def test_bad_metrics_block_all_totals(field, value):
    a = metric(); a[field] = value
    r = metrics_summary([a])
    assert not r['valid'] and all(v is None for v in r['totals'].values())


@pytest.mark.parametrize('field,value', [('source','other'),('currency','USD'),('timezone','UTC'),('article_id','item-2')])
def test_mixed_metrics_scopes_not_summed(field, value):
    a = metric(); a[field] = value
    assert not metrics_summary([metric(), a])['valid']


def test_overlapping_and_duplicate_periods_rejected_but_adjacent_accepted():
    assert not metrics_summary([metric(), metric()])['valid']
    a = metric(); a.update(start='2026-11-07', end='2026-11-14')
    assert not metrics_summary([metric(), a])['valid']
    a['start'] = '2026-11-08'
    r = metrics_summary([metric(), a])
    assert r['valid'] and r['totals']['revenue'] == 400


def test_dashboard_preserves_failure_hold_and_unknown_unhandled():
    b = {'results': [{'title':'<script>', 'status':'error','reason':'通信失敗'},
                      {'title':'保留', 'status':'quality_review_required', 'quality':{'issues':[{'message':'要確認'}]}}],
         'batch_status':'stopped','stop_reason':'generation_budget_exhausted'}
    before = copy.deepcopy(b)
    r = report_rows(b, 'sample')
    assert b == before and r['unhandled'] is None
    assert r['rows'][1]['理由'] == '要確認'
    assert r['rows'][0]['状態'] == 'error'


@pytest.mark.parametrize('batch', [{}, {'results':[None]}, {'results':[{'status':'error','quality':{'issues':None}}]}, {'results':[], 'unhandled_tasks':True}])
def test_bad_dashboard_input_rejected(batch):
    with pytest.raises(ValueError): report_rows(batch, 'bad')


def test_registry_defaults_to_v2_and_uses_explicit_branch(monkeypatch):
    import product_registry
    monkeypatch.setenv('GITHUB_TOKEN', 'test-token')
    monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/repo')
    monkeypatch.delenv('PONTE_REGISTRY_BRANCH', raising=False)
    assert product_registry.github_config()[2] == 'feature-affiliate-v2-validation'
    monkeypatch.setenv('PONTE_REGISTRY_BRANCH', 'test-registry')
    assert product_registry.github_config()[2] == 'test-registry'


def test_resume_after_session_loss_preserves_source_and_evidence():
    from workbench_ui import resume_record
    a = add_revision(archive(), '価格1000円', '初回', {'source_text': '価格1000円'}, [evidence()])
    resumed = resume_record(load_json(json.dumps(a).encode()))
    assert resumed['article'] == '価格1000円'
    assert resumed['quality_context']['source_text'] == '価格1000円'
    assert resumed['evidence'] == [evidence()]


def test_short_evidence_does_not_cover_other_claims_on_same_line():
    r = editorial_review('価格1000円、送料無料、返品可能', [evidence()], TODAY)
    assert any(x['code'] == 'evidence_review' for x in r['findings'])


def test_evidence_edit_changes_manual_review_fingerprint():
    from manual_quality import review_manual_outputs
    result = {'article': '価格1000円', 'sales_mode': '院内・店舗販売'}
    before = review_manual_outputs(result, {}, {})
    result['evidence'] = [evidence()]
    after = review_manual_outputs(result, {}, {})
    assert before['review_sha256'] != after['review_sha256']
    assert after['evidence_records'] == [evidence()]


def test_registry_write_sends_v2_branch_without_real_request(monkeypatch):
    import product_registry
    monkeypatch.setenv('GITHUB_TOKEN', 'test-token')
    monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/repo')
    monkeypatch.delenv('PONTE_REGISTRY_BRANCH', raising=False)
    class Response:
        status_code = 404
        def raise_for_status(self): pass
    calls = []
    monkeypatch.setattr(product_registry.requests, 'get', lambda url, **kw: (calls.append(('get', kw)), Response())[1])
    monkeypatch.setattr(product_registry.requests, 'put', lambda url, **kw: (calls.append(('put', kw)), Response())[1])
    product_registry.write_items([])
    assert calls[0][1]['params']['ref'] == 'feature-affiliate-v2-validation'
    assert calls[1][1]['json']['branch'] == 'feature-affiliate-v2-validation'


def test_ui_save_edit_diff_restore_rechecks_current_article(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from test_manual_quality import sample
    import requests, product_registry
    from google import genai
    def blocked(*args, **kwargs):
        raise AssertionError('Network/API call is forbidden')
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)
    monkeypatch.setattr(genai, 'Client', blocked)
    monkeypatch.setattr(product_registry, 'read_items', lambda: [])
    monkeypatch.setattr(product_registry, 'github_config', lambda: None)
    result, _, assets = sample()
    original = result['article']
    app = AppTest.from_file(str(Path(__file__).with_name('app.py')), default_timeout=20)
    app.session_state['affiliate_result'] = result
    app.session_state['affiliate_social_plan'] = {'x_posts': []}
    app.session_state['affiliate_sales_assets'] = assets
    app.run()
    assert not app.exception
    app.text_input(key='revision_note_offline').set_value('初回保存')
    app.button(key='save_revision_offline').click().run()
    assert not app.exception
    app.text_area(key='edit_article_offline').set_value(original + '\n必ず治る。').run()
    assert not app.exception
    app.text_input(key='revision_note_offline').set_value('検証用の追記')
    app.button(key='save_revision_offline').click().run()
    assert len(app.session_state['revision_archive_offline']['revisions']) == 2
    assert any('必ず治る。' in x.value for x in app.code)
    app.selectbox(key='revision_select_offline').set_value(1)
    app.button(key='restore_revision_offline').click().run()
    assert not app.exception
    assert app.text_area(key='edit_article_offline').value == original
    assert len(app.session_state['revision_archive_offline']['revisions']) == 3
    assert not any('強い表現を確認' in x.value for x in app.markdown)


def test_metric_before_after_comparison_requires_equal_ordered_periods():
    before = metric()
    after = metric(); after.update(start='2026-11-08', end='2026-11-14', revenue=300)
    r = compare_metrics([before], [after])
    assert r['comparable'] and r['delta']['revenue'] == 100
    assert not r['causation_verified']
    after['revenue'] = None
    assert compare_metrics([before], [after])['delta']['revenue'] is None
    after['end'] = '2026-11-15'
    assert not compare_metrics([before], [after])['comparable']
    assert not compare_metrics([before], [before])['comparable']


def test_metric_comparison_rejects_different_sources_and_invalid_rows():
    after = metric(); after.update(start='2026-11-08', end='2026-11-14', source='other')
    assert not compare_metrics([metric()], [after])['comparable']
    assert not compare_metrics([], [after])['comparable']


def test_nonfinite_sum_and_huge_counts_are_rejected():
    a, b = metric(), metric()
    a['revenue'] = b['revenue'] = 1e308
    b.update(start='2026-11-08', end='2026-11-14')
    r = metrics_summary([a, b])
    assert not r['valid'] and r['totals']['revenue'] is None
    a['impressions'] = 10 ** 1000
    assert not metrics_summary([a])['valid']


def test_invalid_evidence_not_hidden_in_zero_issue_count():
    from manual_quality import review_manual_outputs
    r = review_manual_outputs({'article': '# 題\n## 節\n' + '説明。' * 200,
                               'sales_mode': '院内・店舗販売', 'evidence': [{}]}, {}, {})
    assert r['issue_count'] > 0
    assert 'invalid_evidence' in {x['code'] for x in r['editorial']['findings']}
