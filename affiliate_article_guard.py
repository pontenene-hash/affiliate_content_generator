"""Deterministic, fail-closed pre-WordPress screening of affiliate articles.

This is not independent fact-checking. It does not mutate articles or make
network requests. Medical/health claims and unsupported commercial assertions
require human review. An approved result is NOT a factual guarantee.
"""
import re
from urllib.parse import urlparse

DISCLOSURE = re.compile(r'アフィリエイト広告|広告(?:が)?含まれ|【PR】|\bPR\b', re.I)
MEDICAL = re.compile(r'がん|癌|腫瘍|検査キット|尿検査|血液検査|疾患|診断|医療|治療|検診|スクリーニング|医薬品|サプリ|健康食品|血糖|血圧|更年期|脂肪燃焼|ダイエット|育毛|発毛|美容医療', re.I)
RISK = re.compile(r'早期発見|ステージ\s*[1１一]|全身.{0,8}がん|がんリスク|検出感度|特異度|人間ドック.{0,12}(?:代わり|比較|安い)|(?:必ず|絶対|確実に).{0,12}(?:治|改善|効|発見)|(?:通院|検診|病院).{0,8}不要|副作用.{0,5}なし|100\s*[%％]|完治', re.I)
QUOTE = re.compile(r'口コミ|評判|レビュー|体験談|利用者の声', re.I)
TESTIMONIAL = re.compile(r'(?:口コミ|評判|レビュー|体験談|利用者の声).{0,45}(?:良い|高い|多い|寄せられ|好評|満足|おすすめ|という声|との声)|(?:利用者|購入者|お客様).{0,30}(?:声|評価|感想)', re.I)
PRICE = re.compile(r'(?:[¥￥]\s*\d[\d,]*|\d[\d,]*\s*円|送料無料|\d+\s*[%％]\s*(?:OFF|オフ|割引))', re.I)
PLACEHOLDER = re.compile(r'【要確認|要確認・生成保留|\[V5_REVIEWED\]|\bTODO\b', re.I)
MARKDOWN_LINK = re.compile(r'\[[^\]]*\]\((https?://[^\s)]+)(?:\s+[^)]*)?\)', re.I)
BARE_URL = re.compile(r'https?://[^\s<>\]\)"\'、。]+', re.I)
HOLD = 'quality_review_required'

# Only unambiguous statements that reviews have not been presented are exempt.
NO_REVIEW_CLAIM = re.compile(
    r'(?:口コミ|評判|レビュー|体験談).{0,32}'
    r'(?:確認できな(?:い|かった)|掲載されていな(?:い|かった)|'
    r'見つからな(?:い|かった)|紹介しない|引用しない|'
    r'出典を確認できない|未確認)', re.I
)
PRICE_GUIDANCE = re.compile(
    r'(?:価格|料金|送料|割引|購入条件).{0,35}'
    r'(?:公式(?:サイト|ページ)|販売元).{0,18}'
    r'(?:確認(?:してください|しましょう|が必要)|ご確認)', re.I
)


def _normalized_url(url):
    try:
        p = urlparse(url.strip())
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
            return None
        return p
    except (ValueError, AttributeError, TypeError):
        return None


def _article_without_links(text):
    """Exclude URL strings from textual claim detection, not link labels."""
    return BARE_URL.sub('', text)


def _money_values(text):
    values = set()
    for match in re.finditer(r'[¥￥]\s*([\d,]+)|([\d,]+)\s*円', text):
        digits = (match.group(1) or match.group(2)).replace(',', '')
        if digits.isdigit():
            values.add(int(digits))
    return values


def _sentences(text):
    """Keep price/negative review disclaimers local to their own sentence."""
    return [part.strip() for part in re.split(r'[。！？\n]+', text) if part.strip()]


def _has_review_claim(text):
    for sentence in _sentences(text):
        if not QUOTE.search(sentence):
            # Keep the original positive-review detection for non-keyword claims.
            if TESTIMONIAL.search(sentence):
                return True
            continue
        if NO_REVIEW_CLAIM.search(sentence) and not TESTIMONIAL.search(sentence):
            continue
        return True
    return False


def review_article(markdown, product_name='', genre='', affiliate_url='', product_source=''):
    """Return a stable report. approved=False must prevent WordPress writes."""
    if not isinstance(markdown, str):
        raise TypeError('markdown must be text')

    issues = []

    def add(code, message):
        if not any(issue['code'] == code for issue in issues):
            issues.append({'code': code, 'severity': 'block', 'message': message})

    text = markdown.strip()
    if len(text) < 500:
        add('short_or_empty', '記事が短すぎるか、生成されていません')
    if not DISCLOSURE.search(text[:1200]):
        add('missing_disclosure', '記事冒頭にアフィリエイト広告の明示がありません')
    if not re.search(r'^#\s+\S+', text, re.M):
        add('missing_title', 'MarkdownのH1見出しがありません')
    if not re.search(r'^##\s+\S+', text, re.M):
        add('missing_sections', 'MarkdownのH2見出しがありません')

    parsed = _normalized_url(affiliate_url)
    if parsed is None:
        add('missing_affiliate_url', '正規アフィリエイトURLがありません')
    else:
        count = text.count(affiliate_url)
        if count == 0:
            add('missing_link', '正規アフィリエイトURLが記事内にありません')
        if count > 3:
            add('excess_links', 'アフィリエイトURLが3回を超えています')
        # Keep the existing conservative rule: unregistered markdown links block.
        for found in MARKDOWN_LINK.findall(text):
            if found != affiliate_url:
                add('unregistered_link', '未登録のリンクがあります。出典URLを含め人による確認が必要です')
                break

    if PLACEHOLDER.search(text):
        add('unresolved_placeholder', '未確認・生成保留の記載があります')

    if MEDICAL.search(' '.join([product_name, genre, text[:3000]])):
        add('medical_human_review', '医療・健康・美容関連は根拠と広告表現の人による確認が必要です')
    if RISK.search(text):
        add('high_risk_claim', '診断性能・早期発見・効能等の強い表現を確認してください')

    content = _article_without_links(text)
    if _has_review_claim(content):
        if TESTIMONIAL.search(content) or re.search(r'[「『][^」』]{2,100}[」』].{0,30}(?:口コミ|声|評価)', content):
            add('testimonial_verification_required', '口コミ・体験談の原文と掲載許可・出典を確認してください')
        else:
            add('review_source_missing', '口コミ・評判の出典が確認できません')

    # Prices must be present in the source, but matching a number alone is not
    # independent proof of the commercial terms or currency.
    claimed = _money_values(content)
    if claimed:
        if not isinstance(product_source, str) or not product_source.strip():
            add('price_source_missing', '価格の一次情報がありません')
        elif not claimed.issubset(_money_values(product_source)):
            add('price_mismatch', '記事の金額が取得した商品情報と一致しません')

    for sentence in _sentences(content):
        if re.search(r'送料無料|\d+\s*[%％]\s*(?:OFF|オフ|割引)', sentence, re.I):
            add('commercial_terms_review', '送料・割引・購入条件は最新の公式情報を確認してください')
            if not isinstance(product_source, str) or not product_source.strip():
                add('price_source_missing', '価格・送料等の一次情報がありません')
            break

    return {
        'status': 'approved' if not issues else HOLD,
        'approved': not issues,
        'product_name': product_name,
        'issues': issues,
        'word_count_approx': len(text),
        'note': '機械的な一次チェックです。承認は事実の正しさを保証しません。',
    }
