"""Offline regression of the actual download path and editable review state."""
import ast
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import pytest
from manual_quality import review_manual_outputs, AFFILIATE_ONLY
from social_tools import social_text, creative_prompt_text


def sample():
    return {'article': '# 商品の選び方\n## 用途\n' + '容量と手入れの方法を比較しましょう。' * 35,
            'intent': '用途を知りたい', 'outline': '選び方', 'generated_at': 'offline',
            'page': {'text': '価格1000円'}, 'sales_mode': '院内・店舗販売',
            'quality_context': {'sales_mode': '院内・店舗販売', 'source_text': '価格1000円',
                                'product_name': 'カップ', 'destination_url': ''}}, {}, {}


def codes(report, section='article'):
    return {i['code'] for i in report['sections'][section]['issues']}


@pytest.mark.parametrize('section', ['article', 'landing_page', 'gbp_post', 'store_pop', 'social', 'creative'])
def test_edited_risky_text_checked_in_each_export(section):
    result, plan, assets = sample()
    if section == 'article':
        result['article'] += '\n必ず治る。'
    elif section in ('social', 'creative'):
        result[section + ('_text_override' if section == 'social' else '_prompt_override')] = '必ず治る。'
    else:
        assets[section] = '必ず治る。'
    report = review_manual_outputs(result, plan, assets)
    assert 'high_risk_claim' in codes(report, section)
    assert report['human_review_required'] and not report['publication_approved']


def test_store_mode_preserves_health_and_price_checks_without_affiliate_requirements():
    result, plan, assets = sample()
    result['article'] += '\nサプリの価格2000円'
    found = codes(review_manual_outputs(result, plan, assets))
    assert not found & AFFILIATE_ONLY
    assert {'medical_human_review', 'price_mismatch'} <= found


def test_original_context_cannot_be_replaced_by_research_editor_or_sidebar_mode():
    result, plan, assets = sample()
    result['article'] += '\n価格2000円'
    result['page']['text'] = '価格2000円'
    result['sales_mode'] = 'アフィリエイト'
    found = codes(review_manual_outputs(result, plan, assets))
    assert 'price_mismatch' in found
    assert 'missing_disclosure' not in found


def test_affiliate_still_requires_disclosure_and_link():
    result, plan, assets = sample()
    result['quality_context']['sales_mode'] = 'アフィリエイト'
    result['quality_context']['destination_url'] = 'https://example.com/item'
    assert {'missing_disclosure', 'missing_link'} <= codes(review_manual_outputs(result, plan, assets))


def test_clean_output_never_becomes_publication_approval_and_is_not_modified():
    args = sample()
    before = copy.deepcopy(args)
    report = review_manual_outputs(*args)
    assert args == before
    assert not codes(report)
    assert report['status'] == 'review_required'
    assert not report['publication_approved']
    args[0]['article'] += '\n追記'
    assert review_manual_outputs(*args)['review_sha256'] != report['review_sha256']


def test_legacy_result_missing_context_is_explicit():
    result, plan, assets = sample()
    del result['quality_context']
    report = review_manual_outputs(result, plan, assets)
    assert report['context_missing'] and report['human_review_required']
    assert not report['publication_approved']


def test_actual_downloads_include_review_of_current_text_and_keep_all_previous_files():
    # Execute production functions, avoiding Streamlit's top-level UI and API setup.
    tree = ast.parse(Path(__file__).with_name('app.py').read_text())
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and
             n.name in ('download_payloads', 'markdown_to_wordpress_html')]
    namespace = dict(json=json, re=re, escape=escape, datetime=datetime, JST=timezone.utc,
                     social_text=social_text, creative_prompt_text=creative_prompt_text)
    exec(compile(ast.Module(body=funcs, type_ignores=[]), 'app.py', 'exec'), namespace)
    result, plan, assets = sample()
    result.update(social_text_override='編集済みSNS', creative_prompt_override='編集済み制作指示')
    stamp, files = namespace['download_payloads'](result, plan, assets)
    assert len(files) == 8
    review = json.loads(files[f'quality_review_{stamp}.json'])
    for section, filename in [('social', f'affiliate_social_posts_{stamp}.txt'),
                              ('creative', f'affiliate_creative_prompts_{stamp}.md')]:
        text = files[filename].decode('utf-8-sig')
        assert hashlib.sha256(text.encode()).hexdigest() == review['sections'][section]['content_sha256']
    assert result['article'] in files[f'affiliate_article_{stamp}.md'].decode('utf-8-sig')
    result['article'] += '\n必ず治る。'
    _, changed = namespace['download_payloads'](result, plan, assets)
    latest = json.loads(changed[f'quality_review_{stamp}.json'])
    assert 'high_risk_claim' in codes(latest)
    assert latest['review_sha256'] != review['review_sha256']
    assert '必ず治る。' in changed[f'affiliate_article_wordpress_{stamp}.html'].decode('utf-8-sig')


def test_streamlit_edit_reruns_review_without_network(monkeypatch):
    from streamlit.testing.v1 import AppTest
    import requests
    import product_registry
    from google import genai

    def blocked(*args, **kwargs):
        raise AssertionError('Network/API calls are forbidden in this UI test')

    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)
    monkeypatch.setattr(genai, 'Client', blocked)
    monkeypatch.setattr(product_registry, 'read_items', lambda: [])
    monkeypatch.setattr(product_registry, 'github_config', lambda: None)
    result, _, assets = sample()
    app = AppTest.from_file(str(Path(__file__).with_name('app.py')), default_timeout=20)
    app.session_state['affiliate_result'] = result
    app.session_state['affiliate_social_plan'] = {'x_posts': []}
    app.session_state['affiliate_sales_assets'] = assets
    app.run()
    assert not app.exception
    assert any('公開前に人の確認' in w.value for w in app.warning)
    app.text_area(key='edit_article_offline').set_value(result['article'] + '\n必ず治る。').run()
    assert not app.exception
    assert any('強い表現を確認' in m.value for m in app.markdown)
