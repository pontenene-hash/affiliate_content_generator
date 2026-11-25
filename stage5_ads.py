"""Deterministic registered tracking links; no model-generated advertising URLs."""
import re
from html import escape
from urllib.parse import urlsplit

MARKER = re.compile(r'[-_\s]*\[\s*A8[ _-]*AD\s*\][-_]*', re.I)
CTA = '公式サイトでサービス・商品情報を確認する（広告）'

def insert_ads(md, link, product=""):
    p = urlsplit(link)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or re.search(r'[\s<>"\'()]', link):
        raise ValueError('登録広告URLの形式を確認してください')
    # Remove previous deterministic CTAs and known placeholders, not arbitrary source links.
    md = re.sub(r'(?m)^\[[^\n\]]+\]\(' + re.escape(link) + r'\)[ \t]*$', '', md)
    md = MARKER.sub('\n\n', md)
    md = re.sub(r'\n{3,}', '\n\n', md).strip()
    existing = md.count(link)
    if existing:
        return md + '\n'  # Existing model links remain subject to the guard.
    name = re.sub(r'[\[\]\n\r<>]', '', product).strip()
    labels = [f'{name}の詳細を確認する（広告）', f'{name}の利用条件を確認する（広告）', f'{name}が自分に合うか公式情報を確認する（広告）'] if name else [CTA]*3
    heads = list(re.finditer(r'(?m)^##\s+\S', md))
    positions = []
    if len(heads) >= 2:
        positions.append(heads[0].start())
    if len(heads) >= 4:
        positions.append(heads[len(heads)//2].start())
    for i, pos in reversed(list(enumerate(sorted(set(positions))))):
        md = md[:pos].rstrip() + '\n\n' + f'[{labels[i]}]({link})' + '\n\n' + md[pos:]
    return md.rstrip() + '\n\n' + f'[{labels[2]}]({link})' + '\n'

def ad_issues(md, html, link):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    anchors = [a for a in soup.find_all('a', href=True) if a['href'] == link]
    issues = []
    if not 1 <= len(anchors) <= 3:
        issues.append({'code':'ad_anchor_invalid','message':'正規広告リンクの実際のHTML配置が1〜3件ではありません'})
    if re.search(r'A8[ _-]*AD', soup.get_text(), re.I):
        issues.append({'code':'ad_marker_remaining','message':'広告仮文字列が残っています'})
    return issues

def mark_sponsored(html, link):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a', href=True):
        if a['href'] == link:
            a['rel'] = ['sponsored', 'nofollow']
    return str(soup)
