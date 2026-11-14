
#!/usr/bin/env python3
"""Generate ChatGPT image prompts; insert an approved A8 banner and three AI images into WP drafts."""
import argparse
import json
import mimetypes
import os
import re
import sys
import uuid
import zipfile
from base64 import b64encode
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SLOTS = [
    ('01_official', '公式商品画像', '登録済みの許諾済み公式商品画像。AIでパッケージを再現しない。'),
    ('02_lifestyle', '生活シーン', '日本人の成人が日常生活で商品ジャンルに関連する行動をしている自然な写真。実際の利用者・体験談を装わない。'),
    ('03_explainer', '解説画像', '記事の重要なポイントを視覚的に整理した、文字なしの上品な概念図・イラスト。'),
    ('04_empathy', '共感シーン', '読者の悩みや検討シーンを自然に表現した写真。効果・診断結果・利用体験を捏造しない。'),
]
AI_SLOTS = SLOTS[1:]
START = '<!-- affiliate-chatgpt-images:start -->'
END = '<!-- affiliate-chatgpt-images:end -->'


def create(args):
    article = json.loads(Path(args.article).read_text(encoding='utf-8'))
    title = article.get('title', '')
    product = article.get('product_name', '')
    audience = article.get('audience', '日本の成人読者')
    if not title or not product:
        raise ValueError('article JSON needs title and product_name')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    prompts = []
    for i, (stem, kind, brief) in enumerate(SLOTS):
        if i == 0:
            prompt = 'A8.netに登録済みの許諾された公式バナーHTMLを使用します。ChatGPTで偽の製品パッケージは作らないでください。'
        else:
            prompt = (f'アフィリエイト記事「{title}」用の{kind}画像を1枚生成。商品ジャンル: {product}。対象: {audience}。'
                      f'{brief} 横長16:9、清潔感のある自然な日本の生活空間、広告に使える高品質、自然な人体・手指、'
                      '文字・ロゴ・透かしなし。商品の外観、検査結果、数値、効能、使用体験、専門家の推奨を捏造しない。'
                      '医療的な断定表現や恐怖を煽る表現を避ける。')
        prompts.append({'slot': i + 1, 'filename': (stem + '.png') if i else None,
                        'type': kind, 'prompt': prompt})
    (out / 'prompts.json').write_text(json.dumps({'article': article, 'images': prompts}, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'prompts.md').write_text('# ChatGPT画像制作指示\n\n' + '\n\n'.join(
        f"## {x['slot']}枚目：{x['type']}（{x['filename'] or 'A8.net公式バナーHTML'}）\n{x['prompt']}" for x in prompts) + '\n', encoding='utf-8')
    (out / 'manifest.json').write_text(json.dumps({'post_id': article.get('post_id'), 'title': title,
        'images': [x['filename'] for x in prompts if x['filename']], 'banner': 'data/affiliate_products.json の banner_html'},
        ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Created: {out}/prompts.md and manifest.json')


def api(site, user, password, endpoint, method='GET', body=None, content_type=None, filename=None):
    auth = b64encode(f'{user}:{password}'.encode()).decode()
    headers = {'Authorization': 'Basic ' + auth, 'Accept': 'application/json',
               'User-Agent': 'AffiliateImageWorkflow/2.0'}
    if content_type:
        headers['Content-Type'] = content_type
    if filename:
        headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False).encode()
        headers['Content-Type'] = 'application/json'
    req = Request(site.rstrip('/') + '/wp-json/wp/v2/' + endpoint.lstrip('/'),
                  data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=40) as response:
            return json.loads(response.read().decode())
    except HTTPError as exc:
        raise RuntimeError(f'WordPress API HTTP {exc.code}: {exc.read(300).decode(errors="replace")}') from exc


class BannerParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []
        self.active_link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            self.active_link = attrs.get('href')
            self.links.append(self.active_link)
        if tag == 'img':
            self.images.append((attrs.get('src'), self.active_link))

    def handle_endtag(self, tag):
        if tag == 'a':
            self.active_link = None


def valid_banner(html):
    """Use supplied A8 HTML unchanged; reject unrelated links or unsafe markup."""
    if not isinstance(html, str) or not html.strip():
        raise ValueError('Selected product has no banner_html')
    if re.search(r'<\s*(script|iframe|object|embed|form|svg)\b|\bon\w+\s*=|javascript:', html, re.I):
        raise ValueError('Unexpected markup in banner_html')
    parser = BannerParser()
    parser.feed(html)
    if len(parser.links) != 1 or not parser.images:
        raise ValueError('banner_html must have one A8 ad link and image(s)')
    link = parser.links[0]
    if not link or urlparse(link).scheme != 'https' or urlparse(link).hostname != 'px.a8.net':
        raise ValueError('banner_html link must use https://px.a8.net/')
    if not any(src and associated == link and urlparse(src).hostname in ('www21.a8.net', 'www15.a8.net', 'www10.a8.net')
               for src, associated in parser.images):
        raise ValueError('banner_html has no linked A8 banner image')
    for src, _ in parser.images:
        parsed = urlparse(src or '')
        if parsed.scheme != 'https' or not (parsed.hostname == 'a8.net' or (parsed.hostname or '').endswith('.a8.net')):
            raise ValueError('Unexpected banner image source')
    return html


def get_product(path, product_id):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    products = payload.get('products', []) if isinstance(payload, dict) else payload
    matches = [p for p in products if p.get('id') == product_id and p.get('enabled', True)]
    if len(matches) != 1:
        raise ValueError('Exactly one enabled product with --product-id is required')
    product = matches[0]
    if product.get('asp') != 'A8.net':
        raise ValueError('Banner installation currently supports A8.net products only')
    return product


def read_images(archive):
    images = {}
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        for stem, _, _ in AI_SLOTS:
            matches = [n for n in names if not n.endswith('/') and not n.startswith('__MACOSX/')
                       and Path(n).name.lower() in (stem + '.png', stem + '.jpg', stem + '.jpeg', stem + '.webp')]
            if len(matches) != 1:
                raise ValueError(f'ZIP needs exactly one {stem}.png/.jpg/.jpeg/.webp')
            data = z.read(matches[0])
            if not data or len(data) > 10 * 1024 * 1024:
                raise ValueError(f'Invalid image size: {matches[0]}')
            ext = Path(matches[0]).suffix.lower()
            valid = {'.png': data.startswith(b'\x89PNG\r\n\x1a\n'),
                     '.jpg': data.startswith(b'\xff\xd8'),
                     '.jpeg': data.startswith(b'\xff\xd8'),
                     '.webp': data.startswith(b'RIFF') and data[8:12] == b'WEBP'}[ext]
            if not valid:
                raise ValueError(f'Invalid image file: {matches[0]}')
            images[stem] = (data, ext)
    return images


def insert_figures(content, figures):
    headings = list(re.finditer(r'</h[2-3]\s*>', content, re.I))
    positions = [headings[min(len(headings) - 1, (i * len(headings)) // len(figures))].end()
                 if headings else len(content) for i in range(len(figures))]
    # Reverse by index too, so equal-position inserts preserve intended image order.
    for i in sorted(range(len(figures)), key=lambda i: (positions[i], i), reverse=True):
        pos = positions[i]
        content = content[:pos] + '\n' + figures[i] + '\n' + content[pos:]
    return content


def install(args):
    site = os.getenv('WP_SITE_URL', '')
    user = os.getenv('WP_USERNAME', '')
    password = os.getenv('WP_APP_PASSWORD', '')
    if not all((site, user, password)):
        raise ValueError('WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD are required')
    product = get_product(args.products, args.product_id)
    banner = valid_banner(product.get('banner_html', ''))
    images = read_images(args.zip)
    post = api(site, user, password, f'posts/{args.post_id}?context=edit')
    if post.get('status') != 'draft':
        raise ValueError('Only WordPress draft posts can be modified')
    content = post.get('content', {}).get('raw', '')
    if START in content or END in content:
        raise ValueError('Images already installed; refusing duplicate insertion')
    if not content.strip():
        raise ValueError('Post content is empty')
    if not args.apply:
        print(f'DRY RUN OK: draft #{args.post_id}; product {product["id"]}; A8 banner + 3 AI images validated. No changes made.')
        return
    uploaded = []
    for stem, _, label in AI_SLOTS:
        data, ext = images[stem]
        mime = mimetypes.types_map.get(ext, 'image/jpeg' if ext in ('.jpg', '.jpeg') else 'image/png')
        filename = f'affiliate-{args.post_id}-{stem}-{uuid.uuid4().hex[:8]}{ext}'
        media = api(site, user, password, 'media', method='POST', body=data,
                    content_type=mime, filename=filename)
        src, media_id = media.get('source_url'), media.get('id')
        if not src or not media_id:
            raise ValueError('WordPress media response missing source_url/id')
        uploaded.append((src, media_id, label))
    title = post.get('title', {}).get('raw') or post.get('title', {}).get('rendered') or '記事'
    figures = ['<div class="affiliate-a8-banner">' + banner + '</div>']
    for src, media_id, label in uploaded:
        figures.append(f'<figure class="wp-block-image"><img src="{escape(src, quote=True)}" '
                       f'alt="{escape(title + " - " + label, quote=True)}" '
                       f'class="wp-image-{media_id}"/></figure>')
    new_content = START + '\n' + insert_figures(content, figures) + '\n' + END
    # Featured image is the lifestyle image, not the small A8 advertising banner.
    updated = api(site, user, password, f'posts/{args.post_id}', method='POST',
                  body={'content': new_content, 'featured_media': uploaded[0][1], 'status': 'draft'})
    print(f'Updated WordPress draft #{updated.get("id")} with A8 banner and 3 AI images.')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('prompts')
    c.add_argument('--article', required=True)
    c.add_argument('--output', default='image_prompts')
    c.set_defaults(func=create)
    i = sub.add_parser('install')
    i.add_argument('--post-id', type=int, required=True)
    i.add_argument('--zip', required=True)
    i.add_argument('--products', default='data/affiliate_products.json')
    i.add_argument('--product-id', required=True)
    i.add_argument('--apply', action='store_true')
    i.set_defaults(func=install)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
