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


def seo_metadata(product, keyword, genre, title=""):
    product = str(product).strip()
    tags = list(dict.fromkeys([product] + str(keyword).split()))[:8]
    suffix = 'の特徴と選び方'
    if 'FAQ' in keyword or 'よくある質問' in keyword:
        suffix = 'のよくある質問と注意点'
    elif '料金' in keyword:
        suffix = 'の料金と利用前の確認事項'
    elif '比較' in keyword:
        suffix = 'の比較ポイントと選び方'
    seo_title = (product + suffix)[:32]
    description = (f'{product}を検討している方へ。特徴や選び方、利用前に確認したいポイントを整理します。'
                   '料金や利用条件、口コミの出典を確認する際の注意点も踏まえ、ご自身に合うサービスか判断するための参考にしてください。')[:120]
    return {'category':str(genre)[:80], 'keyword':str(keyword)[:120],
            'seo_title':seo_title, 'meta_keywords':','.join(tags), 'tags':tags,
            'description':description}
