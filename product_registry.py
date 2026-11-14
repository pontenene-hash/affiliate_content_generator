"""A8 approved-program registry, optional GitHub-backed storage."""
import base64
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse
import requests

FILE = Path('data/affiliate_products.json')

def parse_ad_code(code):
    m = re.search(r'<a\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\']', code, re.I)
    url = m.group(1) if m else code.strip()
    p = urlparse(url)
    if p.scheme != 'https' or p.hostname not in ('px.a8.net', 'www.a8.net') or not p.path.startswith('/svt/ejp'):
        raise ValueError('A8.netの正規広告コード（px.a8.net/svt/ejp）を貼り付けてください')
    if not p.query or 'a8mat=' not in p.query:
        raise ValueError('広告コードの識別パラメータがありません')
    return url

def github_config():
    token = os.environ.get('GITHUB_TOKEN', '').strip()
    repo = os.environ.get('GITHUB_REPOSITORY', '').strip()
    branch = os.environ.get('GITHUB_BRANCH', 'main').strip()
    if token and re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
        return token, repo, branch
    return None

def read_items():
    cfg = github_config()
    if cfg:
        token, repo, branch = cfg
        r = requests.get(f'https://api.github.com/repos/{repo}/contents/{FILE.as_posix()}', params={'ref':branch}, headers={'Authorization':f'Bearer {token}', 'Accept':'application/vnd.github+json'}, timeout=15)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return json.loads(base64.b64decode(r.json()['content']).decode('utf-8')).get('products', [])
    if not FILE.exists(): return []
    return json.loads(FILE.read_text(encoding='utf-8')).get('products', [])

def write_items(items):
    payload = json.dumps({'products':items}, ensure_ascii=False, indent=2) + '\n'
    cfg = github_config()
    if cfg:
        token, repo, branch = cfg
        url = f'https://api.github.com/repos/{repo}/contents/{FILE.as_posix()}'
        headers = {'Authorization':f'Bearer {token}', 'Accept':'application/vnd.github+json'}
        r = requests.get(url, params={'ref':branch}, headers=headers, timeout=15)
        if r.status_code not in (200,404): r.raise_for_status()
        body = {'message':'Manage approved A8 affiliate products', 'content':base64.b64encode(payload.encode()).decode(), 'branch':branch}
        if r.status_code == 200: body['sha'] = r.json()['sha']
        updated = requests.put(url, json=body, headers=headers, timeout=20)
        updated.raise_for_status()
    else:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(payload, encoding='utf-8')

def normalize_item(name, genre, product_url, ad_code, keyword='', enabled=True):
    name = name.strip()
    if not name: raise ValueError('商品名を入力してください')
    product_url = product_url.strip()
    p = urlparse(product_url)
    if p.scheme not in ('https','http') or not p.hostname or p.username or p.password:
        raise ValueError('公式の商品紹介ページURLを入力してください')
    ad_url = parse_ad_code(ad_code)
    import hashlib
    return {'id':hashlib.sha256(ad_url.encode()).hexdigest()[:16], 'name':name, 'genre':genre, 'product_url':product_url, 'affiliate_url':ad_url, 'affiliate_html':ad_code.strip(), 'keyword':keyword.strip(), 'enabled':bool(enabled)}
