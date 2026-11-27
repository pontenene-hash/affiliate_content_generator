"""Read-only batch dashboard. Counts and suggestions are not publication approval."""
from collections import Counter
from html import escape


def build_dashboard(batch):
    rows = batch.get('results', [])
    if not isinstance(rows, list):
        raise ValueError('Invalid batch results')
    statuses = Counter(str(row.get('status', 'unknown')) for row in rows if isinstance(row, dict))
    attention = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get('status', 'unknown'))
        if status in ('draft', 'preview_only', 'dry_run'):
            continue
        attention.append({'title': str(row.get('title', ''))[:160],
                          'status': status[:80],
                          'issue_count': len(row.get('quality', {}).get('issues', []))
                          if isinstance(row.get('quality'), dict) else 0})
    return {'schema': 1, 'batch_status': batch.get('batch_status', 'unknown'),
            'stop_reason': batch.get('stop_reason'),
            'unhandled_tasks': batch.get('unhandled_tasks'), 'status_counts': dict(sorted(statuses.items())),
            'attention': attention,
            'generation_attempt_budget': batch.get('generation_attempt_budget', {}),
            'planning': batch.get('editorial_planning', {}),
            'metrics_connected': False, 'human_review_required': True,
            'publication_approved': False,
            'limitations': 'Generated batch data only; no GA4, Search Console or affiliate revenue connection.'}


def render_html(dashboard):
    """Standalone, script-free HTML with escaped product names and no remote assets."""
    counts = ''.join(f'<tr><th>{escape(k)}</th><td>{v}</td></tr>'
                     for k, v in dashboard['status_counts'].items())
    tasks = ''.join('<tr><td>' + escape(x['title']) + '</td><td>'
                    + escape(x['status']) + '</td><td>' + str(x['issue_count']) + '</td></tr>'
                    for x in dashboard['attention'])
    planning = dashboard['planning']
    conflicts = len(planning.get('keyword_conflicts', []))
    queue = len(planning.get('improvement_queue', []))
    return ('<!doctype html><html lang="ja"><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;">'
            '<title>PONTE 運用レポート</title><style>body{font:16px/1.7 system-ui;max-width:860px;margin:2em auto;padding:0 1em;color:#26313a}'
            'table{border-collapse:collapse;width:100%;margin:1em 0}td,th{border:1px solid #ccd5df;padding:.55em;text-align:left}'
            'h1,h2{color:#245878}</style><h1>PONTE 運用レポート</h1>'
            '<p>公開前に人の確認が必要です。検索順位・アクセス・収益とは接続していません。</p>'
            '<h2>処理結果</h2><table><tr><th>状態</th><th>件数</th></tr>' + counts + '</table>'
            f'<p>過去履歴の改善候補: {queue}件 / キーワード重複候補: {conflicts}件'
            '（検索結果の重複は未確認）</p>'
            '<h2>確認が必要な記事</h2><table><tr><th>記事</th><th>状態</th><th>品質指摘数</th></tr>'
            + tasks + '</table></html>')


def render_github_summary(batch, job_status=None):
    """Render a compact, content-free Actions summary for an already saved report."""
    board = batch.get('operations_dashboard')
    if not isinstance(board, dict):
        board = build_dashboard(batch)
    counts = board.get('status_counts', {})
    if not isinstance(counts, dict):
        raise ValueError('Invalid dashboard status counts')
    status_labels = {'success': '成功', 'failure': '失敗', 'cancelled': 'キャンセル',
                     'skipped': 'スキップ'}
    job_label = status_labels.get(str(job_status), '不明')
    lines = ['## PONTE 記事生成レポート', '', f'GitHub Actions状態: {job_label}',
             f"処理件数: {int(batch.get('processed', 0) or 0)}",
             '停止理由: ' + {'generation_budget_exhausted': '生成回数上限', 'history_write_failed': '履歴保存失敗', 'fatal_provider_error': '継続不能な外部処理エラー'}.get(batch.get('stop_reason'), '停止報告なし（成功保証ではありません）'),
             '未処理件数: ' + (str(int(batch['unhandled_tasks'])) if batch.get('unhandled_tasks') is not None else '不明'), '',
             '| 状態 | 件数 |', '| --- | ---: |']
    for status, count in sorted(counts.items(), key=lambda pair: str(pair[0])):
        # Status values originate in the report; keep Markdown structure inert.
        label = str(status).replace('`', "'").replace('|', '&#124;').replace('\n', ' ')
        lines.append(f'| `{label}` | {int(count)} |')
    lines.extend(['', '> 公開前に人の確認が必要です。公開承認は行っていません。',
                  '> GA4・Search Console・ASP収益データとは未接続です。', ''])
    return '\n'.join(lines)


def render_missing_report_summary(job_status=None):
    """Static fallback when a run fails before producing its JSON report."""
    status_labels = {'success': '成功', 'failure': '失敗', 'cancelled': 'キャンセル',
                     'skipped': 'スキップ'}
    job_label = status_labels.get(str(job_status), '不明')
    return ('## PONTE 記事生成レポート\n\n'
            f'GitHub Actions状態: {job_label}\n\n'
            '実行レポートを読み取れませんでした。記事の生成件数や保存状態は未確認です。\n\n'
            'ログを確認し、人による確認が終わるまで記事を公開しないでください。\n')
