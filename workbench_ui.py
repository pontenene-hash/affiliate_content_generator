"""Offline UI for saved batch reports and portable editorial revisions."""
import json
from collections import Counter
from improvement_workbench import (load_json, validate_archive, add_revision, restore_revision,
                                   revision_diff, metrics_summary, compare_metrics)
from editorial_review import editorial_review


def report_rows(batch, label):
    if not isinstance(batch, dict) or not isinstance(batch.get('results'), list):
        raise ValueError('results配列を持つバッチレポートを指定してください')
    rows = []
    for result in batch['results']:
        if not isinstance(result, dict) or not isinstance(result.get('status'), str):
            raise ValueError('記事の状態が不正です')
        quality = result.get('quality') or {}
        if not isinstance(quality, dict) or not isinstance(quality.get('issues', []), list):
            raise ValueError('品質レポートが不正です')
        reasons = [str(x.get('message', x.get('code', '要確認'))) for x in quality.get('issues', []) if isinstance(x, dict)]
        rows.append({'レポート': label, '記事': str(result.get('title', '名称不明')),
                     '状態': result['status'], '理由': ' / '.join(reasons) or str(result.get('reason', '')),
                     '次の操作': '本文・根拠を確認。再実行は別途判断（この画面から実行しません）'})
    n = batch.get('unhandled_tasks')
    if n is not None and (type(n) is not int or n < 0):
        raise ValueError('未処理件数が不正です')
    return {'rows': rows, 'unhandled': n, 'batch_status': str(batch.get('batch_status', '不明')),
            'stop_reason': str(batch.get('stop_reason') or '記録なし'),
            'planning': batch.get('editorial_planning', {})}


def render_operations(st):
    with st.expander('📊 保存済みレポート・分析データ', expanded=False):
        st.caption('読み取り専用です。GitHub Actions等で保存したJSONを選択できます。実APIやWordPressには接続しません。')
        files = st.file_uploader('バッチ結果JSON（複数可）', type=['json'], accept_multiple_files=True, key='ops_reports')
        rows, seen = [], set()
        for file in files or []:
            raw = file.getvalue()
            if raw in seen:
                st.info(f'{file.name}：同じ内容のレポートを除外しました')
                continue
            seen.add(raw)
            try:
                board = report_rows(load_json(raw), file.name)
                rows.extend(board['rows'])
                st.write({'レポート': file.name, 'バッチ状態': board['batch_status'],
                          '未処理': board['unhandled'] if board['unhandled'] is not None else '不明',
                          '停止理由': board['stop_reason']})
                st.json(board['planning'])
            except ValueError as exc:
                st.error(f'{file.name}: {exc}')
        if rows:
            st.write(dict(Counter(r['状態'] for r in rows)))
            status = st.selectbox('状態で絞り込み', ['すべて'] + sorted({r['状態'] for r in rows}))
            st.dataframe([r for r in rows if status == 'すべて' or r['状態'] == status], hide_index=True)
        metric_file = st.file_uploader('分析データJSON（任意）', type=['json'], key='offline_metrics')
        previous_file = st.file_uploader('比較する前期間の分析データ（任意）', type=['json'], key='previous_metrics')
        if metric_file:
            try:
                current_metrics = load_json(metric_file.getvalue())
                st.json(metrics_summary(current_metrics))
                if previous_file:
                    st.json(compare_metrics(load_json(previous_file.getvalue()), current_metrics))
            except ValueError as exc:
                st.error(str(exc))
        st.caption('分析レコード: article_id, source, currency, timezone, start/end（YYYY-MM-DD）, impressions/clicks/conversions/revenue。未取得値はnull。期間は両端を含みます。')


def render_revisions(st, result):
    """Call before article editor so explicit restore can update its widget state."""
    with st.expander('🗂️ 改善履歴：保存・比較・復元', expanded=False):
        st.caption('保存するのは現在の本文と参照情報です。編集欄を確定してから保存してください。公開承認・自動投稿は行いません。')
        article_id = str(result.get('generated_at', 'current'))
        key = 'revision_archive_' + article_id
        if key not in st.session_state:
            st.session_state[key] = {'schema': 1, 'article_id': article_id, 'revisions': []}
        archive = st.session_state[key]
        uploaded = st.file_uploader('改善履歴JSONを読み込む', type=['json'], key='archive_upload_' + article_id)
        if uploaded and st.button('履歴を読み込む（本文は変更しない）', key='import_' + article_id):
            try:
                candidate = validate_archive(load_json(uploaded.getvalue()))
                if candidate['article_id'] != article_id:
                    raise ValueError('記事IDが異なります。元の記事で読み込んでください')
                archive = st.session_state[key] = candidate
            except ValueError as exc:
                st.error(str(exc))
        note = st.text_input('変更理由・確認した根拠', key='revision_note_' + article_id)
        if st.button('現在の本文を版として保存', key='save_revision_' + article_id):
            try:
                archive = add_revision(archive, result['article'], note,
                                       result.get('quality_context', {}), result.get('evidence', []))
                st.session_state[key] = archive
                st.success('版を保存しました。終了前に履歴JSONをダウンロードしてください。')
            except ValueError as exc:
                st.error(str(exc))
        if archive['revisions']:
            version = st.selectbox('比較・復元する版', [r['version'] for r in archive['revisions']], key='revision_select_' + article_id)
            old = archive['revisions'][version - 1]
            st.write({'版': version, '変更理由': old['note'], '保存日時': old['created_at']})
            st.code(revision_diff(old['article'], result['article']) or '本文の差分なし', language='diff')
            st.write('選択版の編集チェック')
            st.json(editorial_review(old['article'], old['evidence']))
            if st.button('選択版を本文へ復元（新しい版として記録）', key='restore_revision_' + article_id):
                try:
                    archive = restore_revision(archive, version)
                    st.session_state[key] = archive
                    result['article'] = old['article']
                    result['quality_context'] = old['context']
                    result['evidence'] = old['evidence']
                    st.session_state['edit_article_' + article_id] = old['article']
                    st.session_state['evidence_json_' + article_id] = json.dumps(old['evidence'], ensure_ascii=False, indent=2)
                    st.success('本文と参照情報を復元しました。LP・SNSは別途整合を確認してください。')
                except ValueError as exc:
                    st.error(str(exc))
            st.download_button('改善履歴JSONを保存', json.dumps(archive, ensure_ascii=False, indent=2),
                               file_name='improvement_history.json', mime='application/json', key='archive_download_' + article_id)
        st.caption('履歴はこのセッション内に保持します。長期保管はJSONを書き出してください。ハッシュは破損検出用で、第三者による認証ではありません。')


def resume_record(archive):
    archive = validate_archive(archive)
    if not archive['revisions']:
        raise ValueError('保存版がありません')
    row = archive['revisions'][-1]
    return {'article': row['article'], 'generated_at': archive['article_id'],
            'intent': '', 'outline': '', 'page': {'text': row['context'].get('source_text', '')},
            'sales_mode': row['context'].get('sales_mode'), 'quality_context': row['context'],
            'evidence': row['evidence']}


def render_resume(st):
    with st.expander('保存した改善履歴から本文編集を再開', expanded=False):
        uploaded = st.file_uploader('再開用の改善履歴JSON', type=['json'], key='resume_archive_file')
        st.caption('現在の編集画面を保存版に切り替えます。LP・SNS・構成案は履歴の対象外です。必要な場合は先にダウンロードしてください。')
        if uploaded and st.button('保存版の本文で編集を再開', key='resume_archive'):
            try:
                archive = validate_archive(load_json(uploaded.getvalue()))
                result = resume_record(archive)
                article_id = result['generated_at']
                st.session_state['affiliate_result'] = result
                st.session_state['affiliate_social_plan'] = {'x_posts': []}
                st.session_state['affiliate_sales_assets'] = {}
                st.session_state['revision_archive_' + article_id] = archive
                for prefix, value in [('edit_article_', result['article']), ('edit_research_', result['page']['text']),
                                      ('edit_intent_', ''), ('edit_outline_', ''), ('edit_product_summary_', ''),
                                      ('edit_landing_page_', ''), ('edit_social_', ''), ('edit_prompts_', ''),
                                      ('evidence_json_', json.dumps(result['evidence'], ensure_ascii=False, indent=2))]:
                    st.session_state[prefix + article_id] = value
                st.success('本文と参照情報を読み込みました。再チェック結果を確認してください。')
            except ValueError as exc:
                st.error(str(exc))
