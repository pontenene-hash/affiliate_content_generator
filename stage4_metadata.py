"""Conservative source checks and editorial SEO metadata."""
import re
import unicodedata


def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s)).replace(',', '')


def source_issues(md, source):
    # Exact numeric match is necessary, never sufficient to establish context.
    patterns = r'\d+(?:\.\d+)?(?:円|%|営業日|日間|週間|か月|ヶ月|分|本以上)'
    source = norm(source)
    issues = []
    for token in sorted(set(re.findall(patterns, norm(md)))):
        if token not in source:
            issues.append({'code':'source_numeric_unmatched','message':f'公式取得本文に一致する数値表現なし：{token}'})
    for line in md.splitlines():
        if re.search(r'送料無料|返金|保証|認証|支払い方法|営業時間|納期|割引|最安|業界初', line):
            issues.append({'code':'source_context_review','message':'条件・適用範囲を公式情報と照合：'+line[:180]})
    return issues[:30]


CATEGORY_MAP = {
    '健康': '健康・サプリメント', 'コスメ・スキンケア': '美容・スキンケア',
    'エステ・ダイエット': '美容・スキンケア', '美容グッズ': '美容・スキンケア',
    'ペット商品': 'ペット用品', 'グルメ・食品': '食品・宅配食',
    '暮らし': '暮らし・生活用品', 'エンタメ': 'エンタメ', '学び・資格': 'その他のサービス',
}
CATEGORIES = set(CATEGORY_MAP.values()) | {'スポーツ・フィットネス', 'ファッション'}


def seo_metadata(product, keyword, genre, title="", article=""):
    product = str(product).strip()
    keyword = str(keyword)
    tags = list(dict.fromkeys([product] + keyword.split()))[:8]
    suffix = 'の特徴と選び方'
    for terms, candidate in [
        (('利用後',), 'の利用後の確認ポイント'),
        (('問い合わせ','相談'), 'の問い合わせと相談のポイント'),
        (('初めて',), 'の初めての利用ガイド'),
        (('FAQ','よくある質問'), 'のよくある質問と注意点'),
        (('料金',), 'の料金と利用前の確認事項'),
        (('比較',), 'の比較ポイントと選び方'),
        (('申し込み','申込','準備'), 'の申し込み前の確認事項'),
        (('口コミ','評判'), 'の口コミを確認する際の注意点'),
    ]:
        if any(t in keyword for t in terms):
            suffix = candidate
            break
    seo_title = product + suffix
    if len(seo_title) > 32:
        seo_title = product if len(product) > 32 else (title if product in title and len(title) <= 32 else product + 'の確認事項')
    description = f'{product}{suffix}を解説します。'
    headings = [re.sub(r'[*`]', '', x).strip() for x in re.findall(r'^#{2,3}\s+(.+)$', article, re.M)]
    headings = [h for h in headings if h and h not in ('まとめ','FAQ') and len(h) <= 45]
    for h in headings:
        part = f'「{h}」'
        if len(description + part + 'などを紹介します。') > 120: break
        description += part
    if description.endswith('」'): description += 'などを紹介します。'
    else: description += '利用を検討する際の参考にしてください。'
    category = genre if genre in CATEGORIES else CATEGORY_MAP.get(genre, 'その他のサービス')
    return {'category': category, 'keyword': keyword[:120], 'seo_title': seo_title,
            'meta_keywords': ','.join(tags), 'tags': tags, 'description': description}
