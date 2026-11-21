"""Fail-closed, deterministic pre-WordPress review of generated affiliate articles.

This is a screening tool, not independent verification of medical claims.
No network calls and no modification of the supplied article.
"""
import re
from urllib.parse import urlparse

DISCLOSURE = re.compile(r'(?:アフィリエイト広告|広告を含みます|広告が含まれます|【PR】|\bPR\b)', re.I)
MEDICAL = re.compile(r'がん|癌|腫瘍|検査キット|尿検査|血液検査|疾患|診断|医療|治療|検診|スクリーニング|医薬品|サプリ|健康食品|血糖|血圧|更年期|脂肪燃焼|ダイエット|育毛|発毛|美容医療', re.I)
RISK = re.compile(r'早期発見|ステージ\s*[1１一]|全身.{0,8}がん|がんリスク|検出感度|特異度|人間ドック.{0,12}(?:代わり|比較|安い)|(?:必ず|絶対|確実に).{0,12}(?:治|改善|効|発見)|(?:通院|検診|病院).{0,8}不要|副作用.{0,5}なし|100\s*[%％]|完治', re.I)
QUOTE = re.compile(r'口コミ|評判|レビュー|体験談|利用者の声', re.I)
SOURCE = re.compile(r'https?://\S+|出典\s*[:：]|引用元\s*[:：]|調査(?:元|対象|方法)', re.I)
PRICE = re.compile(r'(?:[¥￥]\s*\d[\d,]*|\d[\d,]*\s*円|送料無料|\d+\s*[%％]\s*(?:OFF|オフ|割引))', re.I)
HOLD = 'quality_review_required'


def review_article(markdown, product_name='', genre='', affiliate_url='', product_source=''):
    """Return report. approved=False means never write a WordPress draft."""
    if not isinstance(markdown, str):
        raise TypeError('markdown must be text')
    issues = []
    def add(code, message, severity='block'):
        issues.append({'code': code, 'severity': severity, 'message': message})

    text = markdown.strip()
    if len(text) < 500:
        add('short_or_empty', '記事が短すぎるか、生成されていません')
    if not DISCLOSURE.search(text[:1200]):
        add('missing_disclosure', '記事冒頭にアフィリエイト広告の明示がありません')
    if not re.search(r'^#\s+\S+', text, re.M):
        add('missing_title', 'MarkdownのH1見出しがありません')
    if not re.search(r'^##\s+\S+', text, re.M):
        add('missing_sections', 'MarkdownのH2見出しがありません')
    if not affiliate_url or not urlparse(affiliate_url).scheme in ('http', 'https'):
        add('missing_affiliate_url', '正規アフィリエイトURLがありません')
    else:
        count = text.count(affiliate_url)
        if count == 0:
            add('missing_link', '正規アフィリエイトURLが記事内にありません')
        if count > 3:
            add('excess_links', 'アフィリエイトURLが3回を超えています')
    if re.search(r'【要確認|要確認・生成保留|\[V5_REVIEWED\]|\bTODO\b', text, re.I):
        add('unresolved_placeholder', '未確認・生成保留の記載があります')
    if MEDICAL.search(' '.join([product_name, genre, text[:3000]])):
        add('medical_human_review', '医療・健康・美容関連は根拠と広告表現の人による確認が必要です')
    if RISK.search(text):
        add('high_risk_claim', '診断性能・早期発見・効能等の強い表現を確認してください')
    if QUOTE.search(text) and not SOURCE.search(text):
        add('review_source_missing', '口コミ・評判の出典が確認できません')
    if PRICE.search(text) and not product_source.strip():
        add('price_source_missing', '価格・送料等の一次情報がありません')
    # Presence of a vendor page is not proof that every claim in the article is true.
    # Review pricing and testimonials manually when health claims or other flags exist.
    return {
        'status': 'approved' if not issues else HOLD,
        'approved': not issues,
        'product_name': product_name,
        'issues': issues,
        'word_count_approx': len(text),
        'note': '機械的な一次チェックです。承認は事実の正しさを保証しません。',
    }
