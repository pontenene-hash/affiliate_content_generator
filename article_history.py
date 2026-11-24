"""Persist completed WordPress drafts in a branch-scoped GitHub JSON file.

No affiliate URLs, API keys or article body are stored in the history.
"""
import base64
import hashlib
import json
import os
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

def load_history():
    cfg = _config()
    if not cfg:
        path = Path(HISTORY_PATH)
        return json.loads(path.read_text(encoding='utf-8')).get('articles', []) if path.exists() else []
    token, _, branch = cfg
    response = requests.get(_url(cfg), params={'ref': branch},
        headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'}, timeout=20)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return json.loads(base64.b64decode(response.json()['content']).decode('utf-8')).get('articles', [])

def save_article(record):
    cfg = _config()
    if not cfg:
        path = Path(HISTORY_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = load_history()
        if not any(x.get('key') == record['key'] for x in existing):
            existing.append(record)
        path.write_text(json.dumps({'articles': existing}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return
    token, _, branch = cfg
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'}
    for attempt in range(3):
        response = requests.get(_url(cfg), params={'ref': branch}, headers=headers, timeout=20)
        if response.status_code not in (200, 404):
            response.raise_for_status()
        if response.status_code == 200:
            data = response.json()
            current = json.loads(base64.b64decode(data['content']).decode('utf-8')).get('articles', [])
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
            for angle, suffix, focus in ANGLES:
                key = article_key(product, angle)
                if key not in existing:
                    choices.append((product_counts[pid], genre_counts[item['genre']], index, item, key, angle, suffix, focus, pid))
                    break
        if not choices:
            break
        _, _, _, item, key, angle, suffix, focus, pid = min(choices, key=lambda x: x[:3])
        base = item.get('keyword', '').strip() or item['title']
        tasks.append((item, key, angle, f'{base} {suffix}', focus))
        existing.add(key)
        product_counts[pid] += 1
        genre_counts[item['genre']] += 1
    return tasks

def make_record(item, key, angle, keyword, title, wp_id):
    return {'key': key, 'product_id': hashlib.sha256((item.get('affiliate_url') or item['product_url']).encode()).hexdigest()[:16],
        'product_name': item['title'], 'angle': angle, 'keyword': keyword, 'title': title,
        'wp_id': wp_id, 'status': 'draft', 'created_at': datetime.now(timezone.utc).isoformat()}
