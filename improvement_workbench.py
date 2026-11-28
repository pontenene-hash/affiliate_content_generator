"""Portable, append-only editorial revisions and strictly scoped offline metrics."""
import copy
import difflib
import hashlib
import json
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from datetime import date, datetime, timezone

MAX_BYTES = 5_000_000


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     allow_nan=False).encode()).hexdigest()


def load_json(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('ファイルが大きすぎます（上限5MB）')
    try:
        return json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError('非有限値')))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('JSON形式を確認してください') from exc


def validate_archive(archive):
    if not isinstance(archive, dict) or archive.get('schema') != 1 or not isinstance(archive.get('revisions'), list):
        raise ValueError('改善履歴の形式が不正です')
    if not isinstance(archive.get('article_id'), str) or not archive['article_id'].strip():
        raise ValueError('記事IDが必要です')
    parent = None
    for index, row in enumerate(archive['revisions']):
        if not isinstance(row, dict):
            raise ValueError('改善版の形式が不正です')
        body = {k: v for k, v in row.items() if k != 'hash'}
        if (row.get('hash') != digest(body) or row.get('parent') != parent or row.get('version') != index + 1
                or row.get('article_id') != archive['article_id']
                or any(not isinstance(row.get(k), str) for k in ('article', 'note', 'created_at'))
                or not isinstance(row.get('context'), dict) or not isinstance(row.get('evidence'), list)):
            raise ValueError('改善履歴の内容・連鎖が不正です')
        if any(not isinstance(row['context'].get(k, ''), str) for k in ('source_text', 'product_name', 'destination_url')):
            raise ValueError('参照文章の形式が不正です')
        if any(not isinstance(e, dict) or any(not isinstance(e.get(k, ''), str) for k in ('claim', 'source_url', 'checked_on', 'quote')) for e in row['evidence']):
            raise ValueError('根拠記録の形式が不正です')
        parent = row['hash']
    return copy.deepcopy(archive)


def add_revision(archive, article, note, context, evidence):
    result = validate_archive(archive)
    if not isinstance(article, str) or not article.strip() or not isinstance(note, str) or not note.strip():
        raise ValueError('本文と変更理由を入力してください')
    if not isinstance(context, dict) or not isinstance(evidence, list):
        raise ValueError('参照情報の形式が不正です')
    row = {'version': len(result['revisions']) + 1, 'article_id': result['article_id'],
           'parent': result['revisions'][-1]['hash'] if result['revisions'] else None,
           'article': article, 'note': note, 'context': copy.deepcopy(context),
           'evidence': copy.deepcopy(evidence), 'created_at': datetime.now(timezone.utc).isoformat()}
    row['hash'] = digest(row)
    result['revisions'].append(row)
    if len(json.dumps(result, ensure_ascii=False).encode()) > MAX_BYTES:
        raise ValueError('改善履歴が5MBを超えます。別の記事IDで続けてください')
    return result


def restore_revision(archive, version):
    archive = validate_archive(archive)
    if type(version) is not int or not 1 <= version <= len(archive['revisions']):
        raise ValueError('復元対象の版がありません')
    old = archive['revisions'][version - 1]
    return add_revision(archive, old['article'], f'版{version}から復元', old['context'], old['evidence'])


def revision_diff(before, after):
    return '\n'.join(difflib.unified_diff(before.splitlines(), after.splitlines(),
                                         fromfile='変更前', tofile='変更後', lineterm=''))


def metrics_summary(rows):
    """Reject duplicates, overlapping periods and mixed attribution scopes; missing != zero."""
    if not isinstance(rows, list):
        raise ValueError('分析データはレコードの配列で指定してください')
    errors, accepted, spans = [], [], {}
    measures = ('impressions', 'clicks', 'conversions', 'revenue')
    for index, row in enumerate(rows):
        try:
            if not isinstance(row, dict):
                raise ValueError('レコード形式')
            key = tuple(row.get(k) for k in ('article_id', 'source', 'currency', 'timezone'))
            if any(not isinstance(v, str) or not v.strip() for v in key):
                raise ValueError('記事ID・データ元・通貨・タイムゾーン')
            try:
                ZoneInfo(row['timezone'])
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError('タイムゾーンが不正です')
            if row['currency'] not in ('JPY', 'USD', 'EUR', 'GBP'):
                raise ValueError('未対応の通貨です')
            start, end = date.fromisoformat(row['start']), date.fromisoformat(row['end'])
            if start > end:
                raise ValueError('期間の逆転')
            for k in measures:
                v = row.get(k)
                if v is not None and (type(v) not in (int, float) or not math.isfinite(v) or v < 0
                                      or (k != 'revenue' and type(v) is not int)):
                    raise ValueError('数値の形式')
            if row.get('clicks') is not None and row.get('impressions') is not None and row['clicks'] > row['impressions']:
                raise ValueError('クリック数が表示数を超過')
            if any(start <= b and a <= end for a, b in spans.get(key, [])):
                raise ValueError('期間の重複')
            spans.setdefault(key, []).append((start, end))
            accepted.append(row)
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            errors.append({'row': index + 1, 'reason': str(exc)})
    scopes = {tuple(r[k] for k in ('article_id', 'source', 'currency', 'timezone')) for r in accepted}
    if len(scopes) > 1:
        errors.append({'row': None, 'reason': '異なる記事・データ元・通貨・タイムゾーンは合算しません'})
    valid = not errors and bool(accepted)
    totals = {k: sum(r[k] for r in accepted) if valid and all(r.get(k) is not None for r in accepted) else None for k in measures}
    if any(v is not None and (isinstance(v, float) and not math.isfinite(v)) for v in totals.values()):
        valid = False
        errors.append({'row': None, 'reason': '合計値が大きすぎます'})
        totals = dict.fromkeys(measures)
    return {'valid': valid, 'errors': errors, 'records': len(accepted), 'totals': totals,
            'ctr': totals['clicks'] / totals['impressions'] if totals['impressions'] and totals['clicks'] is not None else None,
            'metrics_connected': False, 'attribution_verified': False,
            'limitations': '入力データの集計です。欠損は未取得。因果関係・収益改善は判定しません。'}


def compare_metrics(before, after):
    a, b = metrics_summary(before), metrics_summary(after)
    result = {'comparable': False, 'causation_verified': False, 'delta': {}, 'reason': ''}
    if not a['valid'] or not b['valid']:
        result['reason'] = '両期間の入力エラーを解消してください'
        return result
    keys = ('article_id', 'source', 'currency', 'timezone')
    if tuple(before[0][k] for k in keys) != tuple(after[0][k] for k in keys):
        result['reason'] = '記事・データ元・通貨・タイムゾーンが一致しません'
        return result
    spans = [[(date.fromisoformat(r['start']), date.fromisoformat(r['end'])) for r in rows] for rows in (before, after)]
    days = [sum((end - start).days + 1 for start, end in group) for group in spans]
    if days[0] != days[1] or max(end for _, end in spans[0]) >= min(start for start, _ in spans[1]):
        result['reason'] = '日数をそろえ、重複しない前後期間を指定してください'
        return result
    result.update(comparable=True, reason='入力値の差分です。改善による効果とは断定できません。',
                  delta={k: b['totals'][k] - a['totals'][k] if a['totals'][k] is not None and b['totals'][k] is not None else None
                         for k in a['totals']})
    return result
