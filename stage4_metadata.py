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


def seo_metadata(product, keyword, genre):
    return {'category':str(genre)[:80], 'keyword':str(keyword)[:120],
            'description':f'{product}を検討している方へ。サービスや商品の特徴、選び方、利用前に確認したいポイントを解説します。'[:160]}
