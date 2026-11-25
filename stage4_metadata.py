"""Conservative source checks and editorial SEO metadata."""
import re
import unicodedata


def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s)).replace(',', '')


def commercial_claim_lines(md):
    """Only exempt narrow, explicitly non-assertive headings or instructions."""
    for line in md.splitlines():
        line = line.strip()
        if not line: continue
        heading = re.sub(r'^#{1,6}\s+(?:\d+[.、]\s*)?', '', line)
        if re.match(r'^#{1,6}\s', line) and not re.search(r'\d|無料です|適用され|対応しています|保証します|最安|業界初|必ず|全品|全国一律', heading):
            if re.search(r'確認|注意点|目安|選び方|方法|手順|条件$', line): continue
        if re.fullmatch(r'(?:最新の)?(?:送料|支払い方法|送料無料条件|割引条件)(?:を|について)(?:公式サイトで)?確認(?:しましょう|してください|する必要があります)[。！]?', line): continue
        # Exempt only complete, non-assertive instructions; never exempt a
        # factual claim merely because a later sentence says to check it.
        if re.fullmatch(r'(?:最新の)?(?:送料|送料無料条件|支払い方法|割引条件|返品条件|保証条件|納期)(?:や(?:送料|支払い方法|割引条件|返品条件|保証条件|納期))*を(?:公式サイト|ご利用ガイド|注文画面|カート画面)で確認(?:しましょう|してください|することをおすすめします)[。！]?', line):
            continue
        yield line


def source_issues(md, source):
    # Exact numeric match is necessary, never sufficient to establish context.
    patterns = r'\d+(?:\.\d+)?(?:円|%|営業日|日間|週間|か月|ヶ月|分|本以上)'
    source_raw = unicodedata.normalize('NFKC', source)
    source = norm(source_raw)
    issues = []
    for token in sorted(set(re.findall(patterns, norm(md)))):
        if token not in source:
            issues.append({'code':'source_numeric_unmatched','message':f'公式取得本文に一致する数値表現なし：{token}'})
    for line in commercial_claim_lines(md):
        # A standalone question about certification is not an acquisition claim.
        if re.fullmatch(r'[-*\s]*(?:情報セキュリティに関する)?認証[（(][^）)]+[）)]\s*の取得有無[*\s]*', line):
            continue
        if re.search(r'送料無料|返金|保証|認証|支払い方法|営業時間|納期|割引|最安|業界初', line):
            issues.append({'code':'source_context_review','message':'条件・適用範囲を公式情報と照合：'+line[:180]})
    # Matching numbers alone cannot establish the kind of charge. Keep
    # ambiguous claims on hold, even if the same number occurs elsewhere.
    labels = r'送料|配送料|商品価格|販売価格|月額|年額|手数料|料金|割引'
    for line in commercial_claim_lines(md):
        for match in re.finditer(r'(' + labels + r')\s*(?:は|が|：|:|税込|税抜|\s)*([0-9]+(?:\.[0-9]+)?(?:円|%))', norm(line)):
            label, amount = match.groups()
            # Require local proximity, without crossing sentence boundaries.
            windows = re.split(r'[。！？\n]', source_raw)
            if amount in source and not any(re.search(re.escape(label) + r'[^。！？]{0,24}' + re.escape(amount) + r'(?![0-9])', norm(w)) for w in windows):
                issues.append({'code':'source_numeric_context_review','message':f'数値と条件の対応を確認：{label}{amount}'})
    # Aggregate by issue type, retaining all distinct evidence excerpts.
    grouped = {}
    for issue in issues:
        grouped.setdefault(issue['code'], [])
        if issue['message'] not in grouped[issue['code']]:
            grouped[issue['code']].append(issue['message'])
    return [{'code': code, 'message': '\n'.join(messages)} for code, messages in grouped.items()]


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
    from editorial_polish import display_name
    product = display_name(product)
    remainder = keyword.replace(product, '')
    tags = list(dict.fromkeys([product] + [x for x in remainder.split() if x not in ('口コミ','評判','レビュー','体験談') and len(x) <= 30 and not re.search(r'[【】]', x)]))[:8]
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
    if title and product in title and not re.search(r'口コミ|評判|レビュー|体験談', title):
        suffix = 'の特徴と選び方' if re.search(r'口コミ|評判', suffix) else suffix
    seo_title = title if title and product in title and len(title) <= 40 and not re.search(r'口コミ|評判|レビュー|体験談', title) else product + suffix
    if len(seo_title) > 40:
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
    if category == 'ペット用品' and re.search(r'通販|ショップ|NETSHOP', product, re.I) and len(set(re.findall(r'コーヒー|調理|茶器|キッチン|家庭用品', article))) >= 3 and not re.search(r'ペット|犬|猫', keyword.replace(product, '')):
        category = '暮らし・生活用品'
    return {'category': category, 'keyword': keyword[:120], 'seo_title': seo_title,
            'meta_keywords': ','.join(tags), 'tags': tags, 'description': description}
