
"""Deterministic, fail-closed pre-WordPress screening of affiliate articles.

This is not independent fact-checking. It does not mutate the article or make
network requests. High-risk medical/health claims require human review.
"""

import re
from urllib.parse import urlparse

DISCLOSURE = re.compile(
    r'アフィリエイト広告|広告(?:が)?含まれ|【PR】|\bPR\b',
    re.I,
)

MEDICAL = re.compile(
    r'がん|癌|腫瘍|検査キット|尿検査|血液検査|疾患|診断|'
    r'医療|治療|検診|スクリーニング|医薬品|サプリ|健康食品|'
    r'血糖|血圧|更年期|脂肪燃焼|ダイエット|育毛|発毛|美容医療',
    re.I,
)

RISK = re.compile(
    r'早期発見|ステージ\s*[1１一]|全身.{0,8}がん|がんリスク|'
    r'検出感度|特異度|人間ドック.{0,12}(?:代わり|比較|安い)|'
    r'(?:必ず|絶対|確実に).{0,12}(?:治|改善|効|発見)|'
    r'(?:通院|検診|病院).{0,8}不要|副作用.{0,5}なし|'
    r'100\s*[%％]|完治',
    re.I,
)

QUOTE = re.compile(
    r'口コミ|評判|レビュー|体験談|利用者の声',
    re.I,
)

TESTIMONIAL = re.compile(
    r'(?:口コミ|評判|レビュー|体験談|利用者の声)'
    r'.{0,45}(?:良い|高い|多い|寄せられ|好評|満足|'
    r'おすすめ|という声|との声)|'
    r'(?:利用者|購入者|お客様).{0,30}(?:声|評価|感想)',
    re.I,
)

PRICE = re.compile(
    r'(?:[¥￥]\s*\d[\d,]*|\d[\d,]*\s*円|送料無料|'
    r'\d+\s*[%％]\s*(?:OFF|オフ|割引))',
    re.I,
)

COMMERCIAL_TERMS = re.compile(
    r'送料無料|\d+\s*[%％]\s*(?:OFF|オフ|割引)',
    re.I,
)

PLACEHOLDER = re.compile(
    r'【要確認|要確認・生成保留|\[V5_REVIEWED\]|\bTODO\b',
    re.I,
)

MARKDOWN_LINK = re.compile(
    r'\[[^\]]*\]\((https?://[^\s)]+)(?:\s+[^)]*)?\)',
    re.I,
)

BARE_URL = re.compile(
    r'https?://[^\s<>\]\)"\'、。]+',
    re.I,
)

NEGATIVE_REVIEW = re.compile(
    r'(?:口コミ|評判|レビュー|体験談|利用者の声)'
    r'.{0,45}(?:確認できな|掲載されていな|見つからな|'
    r'紹介しない|確認できません|掲載がありません|'
    r'引用しません|転載しません)',
    re.I,
)

HOLD = 'quality_review_required'


def _normalized_url(url):
    """Validate a URL without accessing the network."""
    if not isinstance(url, str):
        return None

    try:
        parsed = urlparse(url.strip())

        if parsed.scheme not in ('http', 'https'):
            return None

        if not parsed.hostname:
            return None

        if parsed.username or parsed.password:
            return None

        if any(char.isspace() for char in url):
            return None

        return parsed

    except (ValueError, AttributeError):
        return None


def _article_without_links(text):
    """Remove URLs so affiliate links are not mistaken for evidence."""
    return BARE_URL.sub('', text)


def _money_values(text):
    """Extract explicitly stated yen amounts."""
    values = set()

    pattern = r'[¥￥]\s*([\d,]+)|([\d,]+)\s*円'

    for match in re.finditer(pattern, text):
        digits = (
            match.group(1) or match.group(2)
        ).replace(',', '')

        if digits.isdigit():
            values.add(int(digits))

    return values


def _review_text_requires_verification(text):
    """Detect testimonial claims without blocking neutral review guidance."""
    if TESTIMONIAL.search(text):
        return True

    if re.search(
        r'[「『][^」』]{2,100}[」』].{0,30}(?:口コミ|声|評価)',
        text,
    ):
        return True

    if re.search(
        r'(?:口コミ|評判|レビュー|体験談)'
        r'.{0,30}(?:によると|では|によれば)',
        text,
        re.I,
    ):
        return True

    return False


def _has_unverified_review_reference(text):
    """Conservatively flag review references lacking clear non-claim context."""
    if not QUOTE.search(text):
        return False

    # A neutral explanation about unavailable testimonials is not itself
    # a claim that positive or negative testimonials exist.
    remaining = NEGATIVE_REVIEW.sub('', text)

    remaining = re.sub(
        r'(?:口コミ|評判|レビュー|体験談)'
        r'.{0,30}(?:公式サイトで確認してください|'
        r'確認することをおすすめします|'
        r'掲載状況をご確認ください)',
        '',
        remaining,
        flags=re.I,
    )

    return bool(QUOTE.search(remaining))


def review_article(
    markdown,
    product_name='',
    genre='',
    affiliate_url='',
    product_source='',
):
    """Return a stable report. approved=False must prevent WordPress writes."""

    if not isinstance(markdown, str):
        raise TypeError('markdown must be text')

    issues = []

    def add(code, message):
        if not any(issue['code'] == code for issue in issues):
            issues.append({
                'code': code,
                'severity': 'block',
                'message': message,
            })

    text = markdown.strip()

    # Basic article structure
    if len(text) < 500:
        add(
            'short_or_empty',
            '記事が短すぎるか、生成されていません',
        )

    if not DISCLOSURE.search(text[:1200]):
        add(
            'missing_disclosure',
            '記事冒頭にアフィリエイト広告の明示がありません',
        )

    if not re.search(r'^#\s+\S+', text, re.M):
        add(
            'missing_title',
            'MarkdownのH1見出しがありません',
        )

    if not re.search(r'^##\s+\S+', text, re.M):
        add(
            'missing_sections',
            'MarkdownのH2見出しがありません',
        )

    # Affiliate URL validation
    parsed = _normalized_url(affiliate_url)

    if parsed is None:
        add(
            'missing_affiliate_url',
            '正規アフィリエイトURLがありません',
        )
    else:
        count = text.count(affiliate_url)

        if count == 0:
            add(
                'missing_link',
                '正規アフィリエイトURLが記事内にありません',
            )

        if count > 3:
            add(
                'excess_links',
                'アフィリエイトURLが3回を超えています',
            )

        for found in MARKDOWN_LINK.findall(text):
            if found != affiliate_url:
                add(
                    'unregistered_link',
                    '未登録のリンクがあります。出典URLを含め人による確認が必要です',
                )
                break

        # Detect bare external URLs as well as Markdown links.
        for found in BARE_URL.findall(text):
            if found != affiliate_url:
                add(
                    'unregistered_link',
                    '未登録のリンクがあります。出典URLを含め人による確認が必要です',
                )
                break

    # Unresolved generation placeholders
    if PLACEHOLDER.search(text):
        add(
            'unresolved_placeholder',
            '未確認・生成保留の記載があります',
        )

    # Medical and health claims
    medical_context = ' '.join([
        str(product_name),
        str(genre),
        text,
    ])

    if MEDICAL.search(medical_context):
        add(
            'medical_human_review',
            '医療・健康・美容関連は根拠と広告表現の人による確認が必要です',
        )

    if RISK.search(text):
        add(
            'high_risk_claim',
            '診断性能・早期発見・効能等の強い表現を確認してください',
        )

    # Testimonial and review checks
    content = _article_without_links(text)

    if _review_text_requires_verification(content):
        add(
            'testimonial_verification_required',
            '口コミ・体験談の原文と掲載許可・出典を確認してください',
        )

    elif _has_unverified_review_reference(content):
        add(
            'review_source_missing',
            '口コミ・評判の出典が確認できません',
        )

    # Price and commercial terms
    if PRICE.search(content):
        if not isinstance(product_source, str) or not product_source.strip():
            add(
                'price_source_missing',
                '価格・送料等の一次情報がありません',
            )
        else:
            claimed = _money_values(content)
            source_values = _money_values(product_source)

            if claimed and not claimed.issubset(source_values):
                add(
                    'price_mismatch',
                    '記事の金額が取得した商品情報と一致しません',
                )

            # Matching amounts are only a mechanical comparison,
            # not proof that prices are current or official.

        if COMMERCIAL_TERMS.search(content):
            add(
                'commercial_terms_review',
                '送料・割引・購入条件は最新の公式情報を確認してください',
            )

    return {
        'status': 'approved' if not issues else HOLD,
        'approved': not issues,
        'product_name': product_name,
        'issues': issues,
        'word_count_approx': len(text),
        'note': (
            '機械的な一次チェックです。'
            '承認は事実の正しさを保証しません。'
        ),
    }
