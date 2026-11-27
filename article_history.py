"""Persist completed WordPress drafts in a branch-scoped GitHub JSON file.

No affiliate URLs, API keys or article body are stored in the history.
"""
import base64
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import requests

HISTORY_PATH = 'data/affiliate_article_history.json'
ANGLES = (
    ('口コミ・評判', '口コミ 評判', '口コミの信頼性、評判を調べる際の注意点。実在する口コミのみ引用'),
    ('使い方・手順', '使い方 手順', '利用方法、手順、利用前の確認事項'),
    ('料金・費用', '料金 費用', '確認できる料金、費用、購入前に注意すべき点'),
    ('メリット・デメリット', 'メリット デメリット', '長所、短所、利用上の制約'),
    ('選び方・向いている人', '選び方 おすすめ', '利用が向いている人と向かない人、選ぶ際の判断材料'),
    ('他サービスとの比較', '比較 違い', '確認できる比較軸と選択時の注意点。比較対象を創作しない'),
    ('よくある疑問', 'よくある質問 FAQ', 'よくある疑問と購入前の確認事項'),
    ('注意点・安全性', '注意点 安全性', '利用上の注意、限界、確認すべき情報'),
)

# Keep the original eight keys stable. Additional topics are finite and distinct.
EXTRA_ANGLES = (
    ('申し込み前の準備', '申し込み前 準備', '申し込み前に整理する情報、必要な準備と確認リスト'),
    ('利用後の確認', '利用後 確認', '利用後の確認事項、問い合わせが必要な場合の判断材料'),
    ('初めての利用', '初めて 初心者', '初心者が迷いやすい判断と準備。既存の手順記事を繰り返さない'),
    ('問い合わせ・相談', '問い合わせ 相談', '問い合わせ前に整理する質問と確認すべき条件'),
)

def topic_keyword(item, suffix):
    base = item.get('keyword', '').strip() or item['title']
    # Generic review modifiers should not contaminate unrelated search intents.
    base = re.sub(r'口コミ|評判|レビュー|体験談', ' ', base)
    return ' '.join(dict.fromkeys((base + ' ' + suffix).split()))

def topic_inventory(items, history):
    existing = {entry.get('key') for entry in history}
    result = []
    for item in items:
        product = item.get('affiliate_url') or item['product_url']
        remaining = [angle for angle, _, _ in ANGLES + EXTRA_ANGLES if article_key(product, angle) not in existing]
        result.append({'product': item['title'], 'remaining_topics': remaining,
                       'status': 'available' if remaining else 'topics_exhausted'})
    return result


def _config():
    token = os.getenv('GH_HISTORY_TOKEN', '').strip()
    repo = os.getenv('GITHUB_REPOSITORY', '').strip()
    branch = os.getenv('GITHUB_BRANCH', '').strip() or os.getenv('GITHUB_REF_NAME', '').strip()
    if token and repo and branch:
        return token, repo, branch
    if os.getenv('GITHUB_ACTIONS') == 'true':
        raise RuntimeError('GitHub記事履歴の接続情報が不足しています（GH_HISTORY_TOKEN / GITHUB_BRANCH）')
    return None

def _url(cfg):
    return f'https://api.github.com/repos/{cfg[1]}/contents/{HISTORY_PATH}'

def validated_articles(payload):
    """Reject corrupt history instead of treating it as an empty first run."""
    if not isinstance(payload, dict) or not isinstance(payload.get('articles'), list):
        raise ValueError('記事履歴の形式が不正です。復旧してから再実行してください')
    records = payload['articles']
    keys = set()
    for row in records:
        if not isinstance(row, dict) or not isinstance(row.get('key'), str) or not row['key'].strip():
            raise ValueError('記事履歴のキーが不正です。復旧してから再実行してください')
        if row['key'] in keys:
            raise ValueError('記事履歴のキーが重複しています。確認が必要です')
        keys.add(row['key'])
    return records


def load_history():
    cfg = _config()
    if not cfg:
        path = Path(HISTORY_PATH)
        return validated_articles(json.loads(path.read_text(encoding='utf-8'))) if path.exists() else []
    token, _, branch = cfg
    response = requests.get(_url(cfg), params={'ref': branch},
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'}, timeout=20)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return validated_articles(json.loads(base64.b64decode(response.json()['content']).decode('utf-8')))

def save_article(record):
    validated_articles({'articles': [record]})
    cfg = _config()
    if not cfg:
        path = Path(HISTORY_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        from batch_safety import exclusive_lock, atomic_json
        with exclusive_lock(path.with_suffix('.lock')):
            existing = load_history()
            if not any(x.get('key') == record['key'] for x in existing):
                existing.append(record)
            atomic_json(path, {'articles': existing})
        return
    token, _, branch = cfg
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'}
    for attempt in range(3):
        response = requests.get(_url(cfg), params={'ref': branch}, headers=headers, timeout=20)
        if response.status_code not in (200, 404):
            response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            current = validated_articles(json.loads(base64.b64decode(data['content']).decode('utf-8')))
        else:
            data, current = None, []
        if any(x.get('key') == record['key'] for x in current):
            return
        current.append(record)
        payload = {'message': 'Record generated affiliate article', 'branch': branch,
            'content': base64.b64encode((json.dumps({'articles': current}, ensure_ascii=False, indent=2)+'\n').encode()).decode()}
        if data:
            payload['sha'] = data['sha']
        result = requests.put(_url(cfg), headers=headers, json=payload, timeout=30)
        if result.status_code in (409, 422) and attempt < 2:
            continue
        result.raise_for_status()
        return

def article_key(product, angle):
    return hashlib.sha256((product + '\n' + angle).encode('utf-8')).hexdigest()

def next_topics(items, history, limit):
    existing = {entry.get('key') for entry in history}
    tasks = []
    # Prefer least-used products and genres, including within this batch.
    from collections import Counter
    product_counts = Counter(x.get('product_id') for x in history)
    genre_counts = Counter()
    for item in items:
        pid = hashlib.sha256((item.get('affiliate_url') or item['product_url']).encode()).hexdigest()[:16]
        genre_counts[item['genre']] += product_counts[pid]
    while len(tasks) < limit:
        choices = []
        for index, item in enumerate(items):
            product = item.get('affiliate_url') or item['product_url']
            pid = hashlib.sha256(product.encode()).hexdigest()[:16]
            for angle, suffix, focus in ANGLES + EXTRA_ANGLES:
                key = article_key(product, angle)
                if key not in existing:
                    choices.append((product_counts[pid], genre_counts[item['genre']], index, item, key, angle, suffix, focus, pid))
                    break
        if not choices:
            break
        _, _, _, item, key, angle, suffix, focus, pid = min(choices, key=lambda x: x[:3])
        tasks.append((item, key, angle, topic_keyword(item, suffix), focus))
        existing.add(key)
        product_counts[pid] += 1
        genre_counts[item['genre']] += 1
    return tasks

def make_record(item, key, angle, keyword, title, wp_id):
    return {'key': key, 'product_id': hashlib.sha256((item.get('affiliate_url') or item['product_url']).encode()).hexdigest()[:16],
        'product_name': item['title'], 'angle': angle, 'keyword': keyword, 'title': title,
        'wp_id': wp_id, 'status': 'draft', 'created_at': datetime.now(timezone.utc).isoformat()}
