"""Regenerate creative briefs from an existing WordPress draft; never create posts."""
import argparse
import hashlib
import json
import os
import re
import time
from html import unescape

import requests
from bs4 import BeautifulSoup

from auto_pipeline import config, gemini_model, public_url
from auto_creative import build_bundle, save_bundle
from article_history import load_history
from product_registry import read_items


def wordpress_article(post_id):
    base = config('WP_SITE_URL').rstrip('/')
    user = config('WP_USERNAME')
    password = config('WP_APP_PASSWORD')
    if not all((base, user, password)):
        raise RuntimeError('WordPress connection settings missing')
    url = public_url(base + f'/wp-json/wp/v2/posts/{post_id}')
    response = requests.get(url, params={'context': 'edit'}, auth=(user, password), timeout=40)
    response.raise_for_status()
    data = response.json()
    if data.get('status') != 'draft':
        raise ValueError('Only existing WordPress drafts can be regenerated')
    return data


def markdown_from_html(html):
    soup = BeautifulSoup(html or '', 'html.parser')
    for node in soup(['script', 'style', 'iframe']):
        node.decompose()
    lines = []
    for node in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'blockquote']):
        # Avoid duplicating paragraphs nested within blockquotes.
        if node.name == 'p' and node.find_parent('blockquote'):
            continue
        text = node.get_text(' ', strip=True)
        if not text:
            continue
        if node.name.startswith('h'):
            text = '#' * int(node.name[1]) + ' ' + text
        elif node.name == 'li':
            text = '- ' + text
        lines.append(text)
    if not lines:
        raise ValueError('WordPress draft body is empty')
    return '\n\n'.join(lines)


def registered_product(history_record):
    product_id = history_record.get('product_id')
    for product in read_items():
        link = product.get('affiliate_url', '').strip()
        product_url = product.get('product_url', '').strip()
        if not link or not product_url:
            continue
        digest = hashlib.sha256((link or product_url).encode('utf-8')).hexdigest()[:16]
        if digest == product_id:
            return product
    raise ValueError('Matching approved product is not registered; no affiliate link will be invented')


def regenerate(post_id):
    history = load_history()
    records = [r for r in history if str(r.get('wp_id')) == str(post_id)]
    if len(records) != 1:
        raise ValueError('Exactly one matching article-history record is required for this post ID')
    product = registered_product(records[0])
    article = wordpress_article(post_id)
    title = unescape(BeautifulSoup(article.get('title', {}).get('raw') or article['title']['rendered'], 'html.parser').get_text(' ', strip=True))
    raw = article.get('content', {}).get('raw')
    if not raw:
        raise ValueError('WordPress raw draft content is unavailable')
    markdown = markdown_from_html(raw)
    if not markdown.lstrip().startswith('# '):
        markdown = '# ' + title + '\n\n' + markdown
    bundle = build_bundle(markdown, title, product['name'], int(post_id), product['affiliate_url'], config('GEMINI_API_KEY'), gemini_model())
    folder = save_bundle(bundle)
    return {'status': 'creative_regenerated', 'wp_id': int(post_id), 'title': title, 'creative': 'saved', 'output': str(folder), 'wordpress_modified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--post-id', type=int, required=True)
    args = parser.parse_args()
    if args.post_id < 1:
        parser.error('post ID must be positive')
    result = regenerate(args.post_id)
    with open('affiliate_run_report.json', 'w', encoding='utf-8') as f:
        json.dump({'processed': 0, 'results': [result]}, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
