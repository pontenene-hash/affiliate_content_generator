"""Offline review of the editable outputs; never grants publication approval."""
import hashlib
import json
from affiliate_article_guard import review_article
from social_tools import social_text, creative_prompt_text

STRUCTURE = {'short_or_empty', 'missing_title', 'missing_sections'}
AFFILIATE_ONLY = {'missing_disclosure', 'missing_affiliate_url', 'missing_link', 'excess_links', 'unregistered_link'}

def review_manual_outputs(result, plan, assets):
    context = result.get('quality_context') or {}
    mode = context.get('sales_mode', result.get('sales_mode'))
    affiliate = mode != '院内・店舗販売'
    outputs = {
        'article': result.get('article', ''),
        'landing_page': str(assets.get('landing_page', '')),
        'gbp_post': str(assets.get('gbp_post', '')),
        'store_pop': str(assets.get('store_pop', '')),
        'social': result.get('social_text_override', social_text(plan)),
        'creative': result.get('creative_prompt_override', creative_prompt_text(plan)),
    }
    sections = {}
    for name, text in outputs.items():
        if name != 'article' and not text.strip():
            continue
        review = review_article(text, product_name=context.get('product_name', ''),
                                affiliate_url=context.get('destination_url', ''),
                                product_source=context.get('source_text', ''))
        ignored = set() if name == 'article' else STRUCTURE | {'missing_link', 'excess_links'}
        if not affiliate:
            ignored |= AFFILIATE_ONLY
        issues = [i for i in review['issues'] if i['code'] not in ignored]
        sections[name] = {'issues': issues, 'content_sha256': hashlib.sha256(text.encode()).hexdigest()}
    missing_context = not context
    return {
        'schema': 1, 'publication_approved': False, 'human_review_required': True,
        'status': 'review_required', 'context_missing': missing_context,
        'sections': sections,
        'issue_count': sum(len(s['issues']) for s in sections.values()),
        'review_sha256': hashlib.sha256(json.dumps({'outputs': outputs, 'context': context, 'mode': mode},
                                        ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        'limitations': '文章の機械チェックです。根拠・医学的正確性・適法性・画像内の文言は未確認。調査欄の編集は元の参照資料を変更しません。',
    }
