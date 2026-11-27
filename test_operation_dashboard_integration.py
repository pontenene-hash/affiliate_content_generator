import auto_pipeline
from operation_dashboard import (
    render_html, render_github_summary, render_missing_report_summary,
)


def test_batch_dashboard_is_advisory_and_escapes_external_titles(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(auto_pipeline, '_run_batch', lambda *args: {
        'results': [{'title': '<script>alert(1)</script>', 'status': 'quality_review_required',
                     'quality': {'issues': [{'code': 'unverified_testimonial'}]}},
                    {'title': '確認済み記事', 'status': 'draft'}],
        'editorial_planning': {'keyword_conflicts': [{'keyword_key': '足 冷え'}],
                               'improvement_queue': [{'id': 'draft-1'}]}})
    output = auto_pipeline.run_batch(2)
    board = output['operations_dashboard']
    assert board['status_counts'] == {'draft': 1, 'quality_review_required': 1}
    assert board['attention'][0]['issue_count'] == 1
    assert board['metrics_connected'] is False and board['publication_approved'] is False
    html = render_html(board)
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert 'キーワード重複候補: 1件' in html


def test_html_write_replaces_file_atomically(tmp_path):
    from batch_safety import atomic_text
    file = tmp_path / 'reports' / 'dashboard.html'
    atomic_text(file, render_html({'status_counts': {}, 'attention': [], 'planning': {}}))
    assert '<title>PONTE 運用レポート</title>' in file.read_text()
    assert list(file.parent.iterdir()) == [file]


def test_github_summary_excludes_article_content_and_escapes_markdown():
    summary = render_github_summary({
        'processed': 1,
        'results': [{'title': 'secret article body', 'status': 'draft|`\nInjected'}],
        'operations_dashboard': {'status_counts': {'draft|`\nInjected': 1}},
    })
    assert 'secret article body' not in summary
    assert '`draft|`' not in summary
    assert '&#124;' in summary and "'" in summary
    assert '公開前に人の確認が必要' in summary
    assert 'GitHub Actions状態: 不明' in summary


def test_failure_summary_reports_unknown_without_leaking_details():
    summary = render_missing_report_summary('failure')
    assert 'GitHub Actions状態: 失敗' in summary
    assert '生成件数や保存状態は未確認' in summary
    assert 'token' not in summary.lower()


def test_five_item_dry_run_routes_into_dashboard_without_wp(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    items = [{'title': f'商品{i}', 'genre': '暮らし',
              'product_url': f'https://example.com/product/{i}',
              'affiliate_url': f'https://example.com/ad/{i}'} for i in range(5)]
    monkeypatch.setattr(auto_pipeline, 'load_verified_items', lambda: items)
    monkeypatch.setattr(auto_pipeline, 'affiliate_links', lambda: {})
    monkeypatch.setattr(auto_pipeline, 'public_url', lambda url: url)
    monkeypatch.setattr(auto_pipeline, 'page_text', lambda url: {
        'title': '公式商品', 'url': url, 'text': '公式情報'})
    monkeypatch.setattr(auto_pipeline, 'brave_search', lambda *args: [])
    monkeypatch.setattr(auto_pipeline, 'wp_draft', lambda *args, **kwargs:
                        (_ for _ in ()).throw(AssertionError('WordPress was contacted')))
    batch = auto_pipeline.run_batch(5, dry_run=True)
    assert batch['processed'] == 5
    assert batch['operations_dashboard']['status_counts'] == {'dry_run': 5}
    assert batch['operations_dashboard']['publication_approved'] is False
