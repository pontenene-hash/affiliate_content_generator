import pytest
import auto_pipeline as p
import article_history as h
from run_controls import active_budget, BudgetExhausted
from operation_dashboard import render_github_summary

@pytest.mark.parametrize('mode,processed,remaining,reason', [
    ('between', 1, 4, 'generation_budget_exhausted'),
    ('during', 0, 4, 'generation_budget_exhausted'),
    ('normal', 5, 0, None),
])
def test_batch_reports_early_stop_without_external_calls(monkeypatch, tmp_path, mode, processed, remaining, reason):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('PONTE_GENERATION_ATTEMPT_LIMIT', '1')
    monkeypatch.setattr(h, 'load_history', lambda: [])
    monkeypatch.setattr(p, 'load_verified_items', lambda: [
        {'title': f'商品{i}', 'genre': '暮らし', 'product_url': f'https://example.com/{i}',
         'affiliate_url': f'https://example.com/ad/{i}'} for i in range(5)])
    monkeypatch.setattr(p, 'affiliate_links', lambda: {})
    monkeypatch.setattr(p, 'public_url', lambda url: url)
    monkeypatch.setattr(p, 'brave_search', lambda *args: [])
    def page(url):
        if mode == 'during': raise BudgetExhausted('test budget')
        if mode == 'between': active_budget.get().reserve()
        return {'url': url, 'title': '公式商品', 'text': '公式説明'}
    monkeypatch.setattr(p, 'page_text', page)
    def forbid(*args, **kwargs): raise AssertionError('external request')
    monkeypatch.setattr(p.requests.sessions.Session, 'request', forbid)
    monkeypatch.setattr(p, 'wp_draft', forbid)
    result = p.run_batch(5, dry_run=True)
    assert result['processed'] == processed
    assert result['unhandled_tasks'] == remaining
    assert result['stop_reason'] == reason
    assert result['batch_status'] == ('stopped' if reason else 'processed')
    assert result['operations_dashboard']['stop_reason'] == reason
    assert f'未処理件数: {remaining}' in render_github_summary(result)

@pytest.mark.parametrize('stopped', [True, False])
def test_workflow_exit_matches_partial_batch(monkeypatch, tmp_path, stopped):
    from pathlib import Path
    import yaml
    source = Path(__file__).parent / '.github/workflows/affiliate_auto.yml'
    workflow = yaml.load(source.read_text(), Loader=yaml.BaseLoader)
    step = next(s for s in workflow['jobs']['generate']['steps'] if s['name'] == 'Generate affiliate drafts and creative prompts')
    script = step['run'].split("python - <<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('DRY_RUN', 'true')
    monkeypatch.setattr(p, 'run_batch', lambda **kwargs: {
        'results': [{'status': 'dry_run'}], 'processed': 1,
        'batch_status': 'stopped' if stopped else 'processed',
        'unhandled_tasks': 4 if stopped else 0,
    })
    if stopped:
        with pytest.raises(SystemExit) as e: exec(compile(script, str(source), 'exec'), {})
        assert e.value.code == 1
    else:
        exec(compile(script, str(source), 'exec'), {})
    assert (tmp_path / 'affiliate_run_report.json').exists()
