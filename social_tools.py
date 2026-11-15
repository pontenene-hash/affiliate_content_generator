"""SNS copy and independent image/video creative briefs for saved affiliate articles."""
import json
import re
from creative_quality import COMMON_QUALITY, apply_quality_rules

MEDIA_FILENAMES = {
    'product_promo_image': '商品紹介画像.png', 'store_pop_image': '店内POP_A4.png',
    'x_image': 'X_投稿画像.png', 'facebook_eyecatch': 'Facebook_アイキャッチ.png',
    'threads_image': 'Threads_投稿画像.png', 'line_image': 'LINE_配信用画像.png',
    'reel_cover': 'Instagram_リール表紙.png', 'reel_video': 'Instagram_リール動画.mp4',
    'youtube_thumbnail': 'YouTube_サムネイル.png', 'youtube_video': 'YouTube_動画.mp4',
    'tiktok_cover': 'TikTok_表紙.png', 'tiktok_video': 'TikTok_動画.mp4',
}
CAROUSEL_LAYOUT = '上部見出し18％・中央イラスト57％・下部説明カード25％。文字とイラストの領域を完全分離'
CAROUSEL_FONT = '太めの日本語ゴシック。見出し64〜80px、説明36〜44px以上、最大4行、行間1.25〜1.4倍'
ARTICLE_IMAGE_LAYOUT = '左側35％を文字専用、右側65％をイラスト専用。人物や商品に文字を重ねない'
ARTICLE_IMAGE_FONT = '太めの日本語ゴシック。見出し56〜72px、補足30〜38px以上、行間1.25〜1.4倍'
IMAGE_QUALITY = ('広告・出版分野で経験豊富なプロのイラストレーターによる高品質な商用イラスト。'
                 '明るい自然光、清潔感、奥行き、正確な人体と手指、自然な日本の生活場面。'
                 '安価な素材集風、架空の認証、実在ロゴ、透かし、意味不明な文字を禁止。')
BRIGHT_VISUAL_RULES = ('白を基調とした明るいハイキー表現。コーラル、黄色、空色、ミントを適切に調和。'
                       '暗い色調や恐怖をあおる構図を避け、主役と内容がひと目で伝わる。')
CONTENT_VISUAL_RULES = ('記事の要点に合う人物の表情・視線・動作・場所・小物を具体的に描く。'
                        '記事にない効果・数値・設備・資格・商品パッケージを創作しない。')
TEXT_LAYOUT_RULES = ('文字専用領域とイラスト領域を完全分離し、1ピクセルも越境させない。'
                     '自然な日本語の文節で改行し、固有名詞・商品名・数字と単位を分割しない。'
                     '助詞や句読点を行頭に置かず、中央揃えと余白を調整する。')
PROFESSIONAL_REVIEW = ('スマートフォン縮小表示と原寸で、誤字・文字切れ・人物・手指・越境・'
                       '可読性を点検する。確認できない場合は検品済みと称さない。')
MARKETING_REVIEW = ('対象読者の悩み、最初の3秒、押し売りしないCTA、広告表示、'
                    '誇張や効果保証の有無を確認する。')


def _strip_code_fence(text):
    text = str(text or '').strip()
    return re.sub(r'\s*```$', '', re.sub(r'^```(?:json)?\s*', '', text, flags=re.I)).strip()


def _load_json_response(raw):
    cleaned = _strip_code_fence(raw)
    candidates = [cleaned]
    start, end = cleaned.find('{'), cleaned.rfind('}')
    if 0 <= start < end:
        candidates.append(cleaned[start:end + 1])
    for candidate in candidates:
        try:
            result = json.loads(re.sub(r',\s*([}\]])', r'\1', candidate))
            if isinstance(result, dict):
                return result
        except (ValueError, TypeError):
            pass
    raise ValueError('SNS構成のJSONを解析できません。')


def _as_dict(value, text_key='text'):
    return value if isinstance(value, dict) else ({text_key: value} if isinstance(value, str) else {})


def _as_list(value):
    return value if isinstance(value, list) else ([] if value in (None, '') else [value])


def _hashtags(value):
    return ' '.join(map(str, value)) if isinstance(value, list) else str(value or '')


def _five_hashtags(value, article=''):
    raw = value if isinstance(value, list) else re.findall(r'[#＃][^\s#＃]+', str(value or ''))
    tags = []
    for entry in raw:
        tag = str(entry).strip().replace('＃', '#')
        tag = '#' + tag.lstrip('#').split()[0] if tag else ''
        if tag and tag not in tags:
            tags.append(tag)
    for tag in ('#商品選び', '#購入前に確認', '#暮らしのヒント', '#商品レビュー', '#おすすめ情報'):
        if len(tags) >= 5:
            break
        if tag not in tags:
            tags.append(tag)
    return tags[:5]


def _plain_text(value, limit=90):
    value = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', str(value or ''))
    value = re.sub(r'[*_`>#]', '', value)
    return re.sub(r'\s+', ' ', value).strip()[:limit]


def _safe_filename_part(value, limit=24):
    return re.sub(r'[\\/:*?"<>|]', '', _plain_text(value, limit)).replace(' ', '_').strip('._') or '記事セクション'


def _article_title(article):
    for line in article.splitlines():
        match = re.match(r'^#\s+(.+)', line.strip())
        if match:
            return _plain_text(match.group(1), 80)
    return '記事のポイント'


def _article_sections(article):
    sections, current, body = [], None, []
    for line in article.splitlines():
        match = re.match(r'^(#{2,3})\s+(.+)', line.strip())
        if match:
            if current:
                current['summary'] = _plain_text(' '.join(body), 120)
                sections.append(current)
            current = {'level': 'H2' if len(match.group(1)) == 2 else 'H3',
                       'heading': _plain_text(match.group(2), 80)}
            body = []
        elif current and line.strip():
            body.append(line.strip())
    if current:
        current['summary'] = _plain_text(' '.join(body), 120)
        sections.append(current)
    return sections[:30]


def _affiliate_mode(context):
    return 'アフィリエイト' in context or '両方' in context


def _store_only(context):
    return '販売目的：院内・店舗販売' in context and '案内先URL：未設定' in context


def _disclosure(context):
    return '【PR】' if _affiliate_mode(context) else '【商品案内】'


def _mark_text(value, context):
    """Show the appropriate disclosure exactly once, at the beginning."""
    value = str(value or '').strip()
    mark = _disclosure(context)
    # Remove only disclosure labels, never product names or supplied links.
    value = re.sub(r'【(?:PR|商品案内)】', '', value)
    value = re.sub(r'\n[ \t]*\n[ \t]*\n+', '\n\n', value).strip()
    return mark + ('\n' + value if value else '')


def _fallback_line(article):
    """Use article-derived wording, never invent a product claim."""
    title = _article_title(article)
    sections = _article_sections(article)
    summary = next((x['summary'] for x in sections if x.get('summary')), '')
    if not summary:
        summary = '商品の特徴や利用前に確認したいポイントをまとめました。'
    return f'{title}\n{summary[:110]}\n詳しくは記事でご確認ください。'


def _fallback_video_points(article):
    """Create distinct content scenes using only article headings and excerpts."""
    sections = _article_sections(article)
    result = []
    for section in sections:
        heading = _plain_text(section.get('heading'), 30)
        summary = _plain_text(section.get('summary'), 45)
        if not heading or not summary:
            continue
        result.append({
            'scene_type': 'content', 'caption': heading,
            'narration': summary,
            'visual': f'記事の「{heading}」を表す具体的な生活場面。記事にない事実を描かない。',
        })
    return result


def _strip_affiliate_link(value, url):
    """Remove the supplied affiliate URL from profile-link-only platforms."""
    value = str(value or '').strip()
    url = str(url or '').strip()
    if not url:
        return value
    pieces = re.split(r'([?&=])', url)
    flexible = ''.join(r'\s*' + re.escape(p) + r'\s*' if p in '?&=' else re.escape(p)
                       for p in pieces if p)
    value = re.sub(flexible, '', value, flags=re.I)
    base = url.split('?', 1)[0]
    if base:
        value = re.sub(re.escape(base) + r'\s*\?\s*(?:\n|$)', '', value, flags=re.I)
    if '?' in url:
        query = url.split('?', 1)[1]
        value = re.sub(r'(?m)^\s*' + re.escape(query) + r'\s*$', '', value)
    return re.sub(r'\n{3,}', '\n\n', value).strip()


def _ensure_link(value, url):
    """Output one complete affiliate URL; remove broken/duplicate versions."""
    value = str(value or '').strip()
    url = str(url or '').strip()
    if not url:
        return value
    # A Gemini response can split a query string after '?' or '&'.
    # Match only the supplied affiliate URL, with optional whitespace at
    # those boundaries, rather than deleting unrelated external links.
    pieces = re.split(r'([?&=])', url)
    flexible = ''.join(r'\s*' + re.escape(p) + r'\s*' if p in '?&=' else re.escape(p)
                       for p in pieces if p)
    value = re.sub(flexible, '', value, flags=re.I)
    # Also strip a partial link emitted on a separate line, such as
    # https://px.a8.net/svt/ejp? followed by a8mat=... on the next line.
    base = url.split('?', 1)[0]
    if base:
        value = re.sub(re.escape(base) + r'\s*\?\s*(?:\n|$)', '', value, flags=re.I)
    # Remove a stray query line only if it exactly matches the known query.
    if '?' in url:
        query = url.split('?', 1)[1]
        value = re.sub(r'(?m)^\s*' + re.escape(query) + r'\s*$', '', value)
    value = re.sub(r'\n{3,}', '\n\n', value).strip()
    return value + '\n' + url


def _fix_video_timing(item):
    scenes = item.get('scenes', [])
    if len(scenes) < 3:
        return
    middle = len(scenes) - 2
    durations = [4] + [34 // middle + (1 if i < 34 % middle else 0) for i in range(middle)] + [4]
    for scene, duration in zip(scenes, durations):
        scene['duration'] = f'{duration}秒'
    item['total_duration'] = '42秒'


def _ensure_video_scenes(item, media_key, article, promotion_context='アフィリエイト販売'):
    """Keep article-grounded scenes, avoid repeated points, and total 42 seconds."""
    scenes = [_as_dict(scene, 'narration') for scene in _as_list(item.get('scenes'))]
    title = _plain_text(item.get('title') or item.get('caption') or _article_title(article), 28)
    if not scenes or scenes[0].get('scene_type') != 'opening_cover':
        scenes.insert(0, {'scene_type': 'opening_cover', 'caption': title,
                          'narration': title, 'visual': '記事のテーマが伝わる明るい表紙。人物と文字を分離'})
    else:
        scenes[0]['scene_type'] = 'opening_cover'

    if _store_only(promotion_context):
        caption, narration = '院内でご相談ください', '気になる方は、ご来店時にスタッフへお気軽にご相談ください。'
    elif media_key == 'youtube':
        caption, narration = '概要欄から詳しく確認', '気になる方は、概要欄のリンクから詳しくご確認ください。'
    else:
        caption, narration = '詳しくはプロフィールへ', '気になる方は、プロフィールのリンクから詳しくご確認ください。'

    cta = {'scene_type': 'affiliate_cta', 'caption': caption, 'narration': narration,
           'visual': '明るく自然な商品案内。人物と文字の領域を分離'}
    # Discard any Gemini-generated intermediate CTA; use a single final CTA.
    middle = [scene for scene in scenes[1:] if scene.get('scene_type') != 'affiliate_cta']
    article_points = _fallback_video_points(article)
    seen_headings, seen_bodies = set(), set()
    selected = []
    for scene in middle + article_points:
        heading = _plain_text(scene.get('caption'), 40)
        body = _plain_text(scene.get('narration'), 45)
        if not heading and not body:
            continue
        # Ignore identical or near-identical points after whitespace/punctuation normalization.
        heading_key = re.sub(r'[\W_]+', '', heading).lower()
        body_key = re.sub(r'[\W_]+', '', body).lower()
        if (heading_key and heading_key in seen_headings) or (body_key and body_key in seen_bodies):
            continue
        if heading_key:
            seen_headings.add(heading_key)
        if body_key:
            seen_bodies.add(body_key)
        scene = dict(scene)
        scene.update({'scene_type': 'content', 'caption': heading, 'narration': body})
        selected.append(scene)
        if len(selected) == 6:
            break
    if not selected:
        selected = [{'scene_type': 'content', 'caption': '記事のポイント',
                     'narration': '商品の特徴や注意点を記事で確認できます。',
                     'visual': '記事の要点を示す生活場面'}]
    scenes = [scenes[0]] + selected + [cta]
    for scene in scenes:
        scene['narration'] = _plain_text(scene.get('narration'), 45)
        scene['caption'] = _plain_text(scene.get('caption'), 40)
    item['scenes'] = scenes
    _fix_video_timing(item)
    return item


def _add_filename_instruction(item, filename):
    item['output_filename'] = filename
    item['prompt'] = re.sub(r'\s*完成データの推奨保存ファイル名は『[^』]+』とする。?', '',
                            str(item.get('prompt', ''))).strip()
    return item


def _add_video_audio_instructions(item, media_key):
    # Retained as a public helper for compatibility with existing callers.
    text = ('人の声・ナレーションは禁止。日本語のタイピング風テロップと、'
            '0秒から途切れない著作権上利用可能な明るいBGMを使用する。')
    if text not in item.get('prompt', ''):
        item['prompt'] = str(item.get('prompt', '')).rstrip() + '\n' + text
    return item


def _image_prompt_item(title, body, size, layout, font_spec, filename, scene=''):
    title, body = _plain_text(title, 120), _plain_text(body, 180)
    prompt = (f'キャンバスをイラスト表示エリアとテキスト専用エリアへ完全分離する。'
              f'{IMAGE_QUALITY}{BRIGHT_VISUAL_RULES}{CONTENT_VISUAL_RULES}'
              f'出力サイズ：{size}。配置：{layout}。フォント：{font_spec}。'
              f'画像内の見出しは「{title}」、補足は「{body}」。'
              f'描写する具体的な場面：{_plain_text(scene or title + body, 220)}。'
              f'{TEXT_LAYOUT_RULES}文字は指定した専用領域にのみ置く。'
              f'文字が多ければ意味を保って短縮し、正式名称は切らない。'
              f'{PROFESSIONAL_REVIEW}{MARKETING_REVIEW}')
    return {'size': size, 'catch_copy': title, 'sub_copy': body, 'layout': layout,
            'font_spec': font_spec, 'output_filename': filename, 'prompt': prompt}


def _video_prompt_item(plan_item, size, duration, filename, vertical):
    scenes = [_as_dict(x, 'narration') for x in _as_list(plan_item.get('scenes'))]
    layout = ('上部コピー帯20％・中央映像55％・下部テロップ帯10％・操作UI安全余白15％'
              if vertical else '横型16:9。人物・映像と文字を左右に分離し、下部に独立した字幕帯')
    font = ('太めの日本語ゴシック。表紙96〜120px、通常テロップ72〜88px、最大2行、行間1.25〜1.4倍'
            if vertical else '太めの日本語ゴシック。表紙88〜112px、通常テロップ64〜80px、最大2行、行間1.25〜1.4倍')
    scene_lines = []
    for index, scene in enumerate(scenes, 1):
        scene_lines.append(
            f'シーン{index}（{scene.get("duration", "")}、{scene.get("scene_type", "content")}）：'
            f'上部見出し「{_plain_text(scene.get("caption"), 80)}」。'
            f'下部テロップ「{_plain_text(scene.get("narration"), 90)}」。'
            f'映像「{_plain_text(scene.get("visual") or scene.get("direction"), 180)}」。'
        )
    prompt = (
        '各フレームを映像表示エリアとテロップ専用エリアへ完全分離する。'
        'プロのイラストレーターと映像ディレクターが共同制作する、求心力のある高品質なイラスト動画。'
        f'{BRIGHT_VISUAL_RULES}{CONTENT_VISUAL_RULES}'
        f'サイズ：{size}。総尺は正確に{duration}。配置：{layout}。フォント：{font}。'
        '最初の0.0秒から完成した明るい表紙を4秒表示。黒画面、空白、待機、フェードイン禁止。'
        '最終4秒は記事に基づく自然な商品案内とCTA。広告なら【PR】を明示する。'
        '全シーンの指定秒数を守り、余計な静止や尺の延長をしない。'
        '各シーンの詳細：' + ' '.join(scene_lines) +
        '人の声、音声ナレーション、読み上げ、会話音声を入れない。'
        'narration欄は音声ではなく下部の日本語テロップに使用する。'
        '左から右へ1文字ずつ、1文字0.04〜0.07秒のタイピング演出。'
        '表示後1.5〜2秒保持し、場面転換は0.2〜0.4秒。'
        '明るく穏やかで少しポップな、利用権を確認できるインストゥルメンタルBGMを0秒から流し、'
        '最後だけフェードアウト。BGMの音切れを禁止する。'
        '人物、商品、重要な小物と文字を重ねない。操作UIの安全余白を確保する。'
        'SNS名・SNSロゴ・アプリアイコン・ユーザー名・ファイル名・透かしを画面に出さない。'
        f'{TEXT_LAYOUT_RULES}{PROFESSIONAL_REVIEW}{MARKETING_REVIEW}'
    )
    return {'size': size, 'duration': duration, 'catch_copy': _plain_text(scenes[0].get('caption'), 80) if scenes else '',
            'layout': layout, 'font_spec': font, 'output_filename': filename, 'prompt': prompt}


def _carousel_prompt(slide, number):
    item = _image_prompt_item(slide.get('title'), slide.get('body'), '1080×1350',
                              CAROUSEL_LAYOUT, CAROUSEL_FONT,
                              f'Instagram_カルーセル_{number:02d}.png', slide.get('visual', ''))
    item.update({'slide': number, 'body_text': item['sub_copy']})
    return item


def _article_section_prompt(section, number):
    heading = section.get('heading', '記事のポイント')
    item = _image_prompt_item(heading, section.get('summary'), '1200×675',
                              ARTICLE_IMAGE_LAYOUT, ARTICLE_IMAGE_FONT,
                              f'ブログ_{section.get("level", "H2")}_{number:02d}_{_safe_filename_part(heading)}.png',
                              f'{heading}。{section.get("summary", "")}')
    item.update({'section': number, 'heading_level': section.get('level', 'H2'), 'heading': heading})
    return item


def _build_creative_prompts(plan, article):
    x = _as_dict(plan.get('x_image'))
    facebook, threads, line = (_as_dict(plan.get(k)) for k in ('facebook', 'threads', 'line'))
    reel, youtube, tiktok = (_as_dict(plan.get(k)) for k in ('reel', 'youtube', 'tiktok'))
    sections = _article_sections(article) or [{'level': 'H2', 'heading': '商品のポイント',
                                                'summary': _plain_text(article, 120)}]
    title = _article_title(article)
    horizontal = '左35％文字・右65％イラストの左右分割。領域越境禁止'
    square = '上部25％文字・中央55％イラスト・下部20％補足の3領域。領域越境禁止'
    vertical = '上部20％見出し・中央60％イラスト・下部5％補足・UI安全余白15％'
    hf = '太めの日本語ゴシック。見出し56〜72px、補足30〜38px以上、行間1.25〜1.4倍'
    sf = '太めの日本語ゴシック。見出し64〜80px、補足34〜44px以上、行間1.25〜1.4倍'
    vf = '太めの日本語ゴシック。見出し96〜120px、補足72〜88px以上、最大2行'
    prompts = {
        'product_promo_image': _image_prompt_item(title, sections[0]['summary'], '1200×1200', square, sf,
                                                   MEDIA_FILENAMES['product_promo_image'], '記事の内容に沿った商品紹介の生活場面'),
        'store_pop_image': _image_prompt_item(title, '詳しくはスタッフへご相談ください', 'A4縦・1240×1754', vertical, vf,
                                              MEDIA_FILENAMES['store_pop_image'], '店頭で3秒で内容が伝わる販促POP'),
        'x_image': _image_prompt_item(x.get('title'), x.get('body'), '1200×675', horizontal, hf,
                                      MEDIA_FILENAMES['x_image'], x.get('visual', '')),
        'facebook_eyecatch': _image_prompt_item(facebook.get('image_title'), facebook.get('image_body'), '1200×630', horizontal, hf,
                                                 MEDIA_FILENAMES['facebook_eyecatch'], facebook.get('visual', '')),
        'threads_image': _image_prompt_item(threads.get('image_title'), threads.get('image_body'), '1080×1080', square, sf,
                                            MEDIA_FILENAMES['threads_image'], threads.get('visual', '')),
        'line_image': _image_prompt_item(line.get('image_title'), line.get('image_body'), '1200×900', horizontal, sf,
                                         MEDIA_FILENAMES['line_image'], line.get('visual', '')),
        'reel_cover': _image_prompt_item(reel.get('cover_title'), reel.get('cover_body'), '1080×1920', vertical, vf,
                                         MEDIA_FILENAMES['reel_cover']),
        'youtube_thumbnail': _image_prompt_item(youtube.get('thumbnail_title'), youtube.get('thumbnail_body'), '1280×720', horizontal, hf,
                                                 MEDIA_FILENAMES['youtube_thumbnail']),
        'tiktok_cover': _image_prompt_item(tiktok.get('cover_title'), tiktok.get('cover_body'), '1080×1920', vertical, vf,
                                           MEDIA_FILENAMES['tiktok_cover']),
        'reel_video': _video_prompt_item(reel, '1080×1920', '42秒', MEDIA_FILENAMES['reel_video'], True),
        'youtube_video': _video_prompt_item(youtube, '1920×1080', '42秒', MEDIA_FILENAMES['youtube_video'], False),
        'tiktok_video': _video_prompt_item(tiktok, '1080×1920', '42秒', MEDIA_FILENAMES['tiktok_video'], True),
        'instagram_carousel': [_carousel_prompt(_as_dict(s, 'body'), i) for i, s in
                               enumerate(_as_list(_as_dict(plan.get('carousel')).get('slides'))[:9], 1)],
        'article_section_images': [_article_section_prompt(s, i) for i, s in enumerate(sections, 1)],
    }
    return apply_quality_rules(prompts)



# Claims requiring independent verification are excluded from generated promotional copy.
# This is a conservative text filter, not an official-source fact checker.
_REVIEW_CLAIM = re.compile(
    r'(?:[0-9０-９][0-9０-９,，.．]*\s*円|送料無料|送料(?:が)?無料|'
    r'ステージ\s*[0-9０-９ⅠⅡⅢⅣ]+|早期発見|早期がん|'
    r'全身のがん|特許技術|検査精度|感度\s*[0-9０-９]|'
    r'がんを(?:発見|診断|予防|治療)|お得な定期プラン|'
    r'人間ドック(?:の代わり|に比べて))', re.I)


def _review_safe_copy(value):
    """Drop complete promotional sentences containing unverified claims."""
    text = str(value or '')
    chunks = re.split(r'(?<=[。！？!?])|\n', text)
    retained = [part.strip() for part in chunks if part.strip() and not _REVIEW_CLAIM.search(part)]
    return '\n'.join(retained).strip()


def _strip_duplicate_tags(text, tags):
    """Keep hashtags in a single final tag line, not repeated in the caption."""
    text = str(text or '').strip()
    for tag in tags:
        text = re.sub(r'(?<![\w#＃])' + re.escape(tag) + r'(?![\w])', '', text)
    return re.sub(r'\n[ \t]*\n[ \t]*\n+', '\n\n', text).strip()


def _render_tags_once(text, tags):
    tags = _as_list(tags)
    clean = _strip_duplicate_tags(text, tags)
    return clean + ('\n' + _hashtags(tags) if tags else '')

def _normalize_social_plan(data, article, promotion_context='アフィリエイト販売', affiliate_url=''):
    if not isinstance(data, dict):
        raise ValueError('SNS構成が正しい形式ではありません。')
    mark = _disclosure(promotion_context)
    data['x_posts'] = [_as_dict(x) for x in _as_list(data.get('x_posts'))]
    for post in data['x_posts']:
        post['text'] = _mark_text(_ensure_link(_review_safe_copy(post.get('text')), affiliate_url), promotion_context)
    data['x_image'] = _as_dict(data.get('x_image'))
    for post in data['x_posts']:
        post['hashtags'] = [t for t in _as_list(post.get('hashtags')) if not _REVIEW_CLAIM.search(str(t))]
    for key in ('threads', 'facebook', 'line'):
        item = _as_dict(data.get(key))
        base_text = item.get('text')
        if key == 'line' and not re.sub(r'(?:【PR】|【商品案内】|https?://\S+|\s)+', '', str(base_text or '')):
            base_text = _fallback_line(article)
        item['text'] = _mark_text(_ensure_link(_review_safe_copy(base_text), affiliate_url), promotion_context)
        item['hashtags'] = [t for t in _as_list(item.get('hashtags')) if not _REVIEW_CLAIM.search(str(t))]
        data[key] = item
    carousel = _as_dict(data.get('carousel'), 'caption')
    carousel['caption'] = _mark_text(_review_safe_copy(carousel.get('caption')), promotion_context)
    carousel['hashtags'] = _five_hashtags([t for t in _five_hashtags(carousel.get('hashtags'), article) if not _REVIEW_CLAIM.search(t)], article)
    slides = [_as_dict(x, 'body') for x in _as_list(carousel.get('slides'))]
    sections = _article_sections(article)
    while len(slides) < 9:
        idx = len(slides)
        source = sections[min(idx, len(sections) - 1)] if sections else {}
        slides.append({'title': source.get('heading', '記事のポイント'),
                       'body': source.get('summary', '詳しい内容は記事をご確認ください。'),
                       'visual': '記事の要点を表す具体的な日本の生活場面'})
    slides = slides[:9]
    for slide in slides:
        slide['title'] = _review_safe_copy(slide.get('title')) or '記事のポイント'
        slide['body'] = _review_safe_copy(slide.get('body')) or '詳しい内容は記事でご確認ください。'
        slide['visual'] = _review_safe_copy(slide.get('visual')) or '記事の内容に沿った生活場面'
    slides[-1]['title'] = '詳しく確認してみませんか'
    slides[-1]['body'] = (('気になる方は、ご来店時にスタッフへご相談ください。' if _store_only(promotion_context)
                          else '詳しくはプロフィールの案内先からご確認ください。') + mark)
    carousel['slides'] = slides
    data['carousel'] = carousel
    for key in ('reel', 'youtube', 'tiktok'):
        item = _as_dict(data.get(key), 'caption')
        field = 'description' if key == 'youtube' else 'caption'
        item[field] = _mark_text(_ensure_link(_review_safe_copy(item.get(field)), affiliate_url if key == 'youtube' else ''), promotion_context)
        if key == 'reel':
            item['hashtags'] = _five_hashtags([t for t in _five_hashtags(item.get('hashtags'), article) if not _REVIEW_CLAIM.search(t)], article)
        item['hashtags'] = [t for t in _as_list(item.get('hashtags')) if not _REVIEW_CLAIM.search(str(t))]
        data[key] = _ensure_video_scenes(item, key, article, promotion_context)
        for scene in data[key]['scenes']:
            if scene.get('scene_type') == 'content':
                scene['caption'] = _review_safe_copy(scene.get('caption')) or '記事のポイント'
                scene['narration'] = _review_safe_copy(scene.get('narration')) or '詳しくは記事をご確認ください。'
                scene['visual'] = _review_safe_copy(scene.get('visual')) or '記事の内容を紹介する明るい生活場面'

    # Profile-only platforms: do not print raw affiliate links in captions.
    carousel['caption'] = _mark_text(_strip_affiliate_link(carousel.get('caption'), affiliate_url), promotion_context)
    for media_key in ('reel', 'tiktok'):
        media = _as_dict(data.get(media_key), 'caption')
        media['caption'] = _mark_text(_strip_affiliate_link(media.get('caption'), affiliate_url), promotion_context)
        data[media_key] = media
    data['creative_prompts'] = _build_creative_prompts(data, article)
    return data


def _validate_social_plan(data):
    required = ('x_posts', 'threads', 'facebook', 'line', 'carousel', 'reel',
                'youtube', 'tiktok', 'creative_prompts')
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError('SNS構成の不足項目：' + ', '.join(missing))
    if len(_as_dict(data['carousel']).get('slides', [])) != 9:
        raise ValueError('Instagramカルーセルが9枚ではありません。')
    if not re.sub(r'(?:【PR】|【商品案内】|https?://\S+|\s)+', '', str(data.get('line', {}).get('text', ''))):
        raise ValueError('LINE配信文に本文がありません。')
    prompts = data['creative_prompts']
    required_prompts = set(MEDIA_FILENAMES) | {'instagram_carousel', 'article_section_images'}
    if required_prompts - set(prompts):
        raise ValueError('画像・動画制作プロンプトが不足しています。')
    if len(prompts['instagram_carousel']) != 9 or not prompts['article_section_images']:
        raise ValueError('カルーセルまたは記事セクション画像が不足しています。')
    for key in ('reel', 'youtube', 'tiktok'):
        scenes = data[key].get('scenes', [])
        if len(scenes) < 3 or sum(int(re.search(r'\d+', x['duration']).group()) for x in scenes) != 42:
            raise ValueError(f'{key}の動画構成が42秒ではありません。')


def _generate_social_plan_legacy(client, model, article, call_llm, affiliate_url=''):
    """Compatibility entry point: uses the maintained generation pipeline."""
    return generate_social_plan(client, model, article, call_llm, affiliate_url=affiliate_url)


def generate_social_plan(client, model, article, call_llm, affiliate_url='',
                         promotion_context='アフィリエイト販売'):
    prompt = f'''あなたは日本語の広告・SNS制作の専門家です。次の完成記事だけを情報源に、投稿文と映像台本をJSONで返してください。
記事中に記載された数値も裏付けが不明な場合はSNSで強調しないでください。価格・送料・ステージ別の検査性能・早期発見・特許・定期プラン・医療機関との比較は、記事に書かれていても公式一次資料の確認ができない限りSNS本文・画像文字・動画テロップに含めない。文章は助詞で途切れず一文を完結させる。ハッシュタグは本文に重複記載せず、別フィールドだけに置く。
医療・健康・美容商品の診断・治療・予防効果を断定せず、架空の価格、送料、検査精度、口コミ、人物、限定性、認証を追加しない。
検査サービスを医療機関での診断の代わりと表現しない。正式名称を変更しない。
アフィリエイトなら全投稿に【PR】、店頭案内のみなら【商品案内】を表示。
Xは異なる角度で3案。Instagramカルーセルは9枚で、表紙・悩み・要点・注意点・まとめ・CTAを重複なく整理。
リール、YouTube、TikTokは各42秒、冒頭表紙と最後のCTAを含む5〜8シーンを作成。
各sceneにscene_type、caption、narration（音声ではなく45文字以内の画面テロップ）、visualを入れる。
テロップはナレーションなしのタイピング表示、明るいインストゥルメンタルBGM。記事にない描写を創作しない。
カルーセルとリールのハッシュタグは5個。画像用の短い見出し、補足、具体的なvisualも作る。
URLがある場合、X・Threads・Facebook・LINE・YouTubeの投稿に1回含める。Instagram・TikTokはプロフィール導線。
店舗販売のみでURLがなければ院内相談へ案内し、URLを創作しない。
制作品質基準：{COMMON_QUALITY}
販売・案内条件：{promotion_context}
購入・確認URL：{affiliate_url or '未設定'}
完成記事：\n---\n{article}\n---
JSONの形式：
{{
"x_posts":[{{"text":"","hashtags":["#タグ"]}},{{"text":"","hashtags":["#タグ"]}},{{"text":"","hashtags":["#タグ"]}}],
"x_image":{{"title":"","body":"","visual":""}},
"threads":{{"text":"","hashtags":["#タグ"],"image_title":"","image_body":"","visual":""}},
"facebook":{{"text":"","hashtags":["#タグ"],"image_title":"","image_body":"","visual":""}},
"line":{{"text":"","image_title":"","image_body":"","visual":""}},
"carousel":{{"caption":"","hashtags":["#タグ"],"slides":[{{"title":"","body":"","visual":""}}]}},
"reel":{{"caption":"","hashtags":["#タグ"],"cover_title":"","cover_body":"","scenes":[{{"scene_type":"opening_cover/content/affiliate_cta","caption":"","narration":"","visual":""}}]}},
"youtube":{{"title":"","description":"","hashtags":["#タグ"],"thumbnail_title":"","thumbnail_body":"","scenes":[{{"scene_type":"opening_cover/content/affiliate_cta","caption":"","narration":"","visual":""}}]}},
"tiktok":{{"caption":"","hashtags":["#タグ"],"cover_title":"","cover_body":"","scenes":[{{"scene_type":"opening_cover/content/affiliate_cta","caption":"","narration":"","visual":""}}]}}
}}
JSON以外を出力しない。'''
    last_error = None
    for attempt in range(2):
        try:
            raw = call_llm(client, model, prompt + ('\n前回のJSONが不完全でした。短く有効なJSONを返してください。' if attempt else ''),
                           16000, response_mime_type='application/json', temperature=0.35)
            data = _normalize_social_plan(_load_json_response(raw), article, promotion_context, affiliate_url)
            _validate_social_plan(data)
            return data
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
    raise ValueError(f'SNS投稿文と制作プロンプトを完成できませんでした：{last_error}')


def social_text(plan):
    plan = _as_dict(plan)
    parts = ['X（旧Twitter）投稿案']
    for index, raw in enumerate(_as_list(plan.get('x_posts')), 1):
        post = _as_dict(raw)
        parts.append(f'\n【パターン{index}】\n' + _render_tags_once(post.get('text', ''), post.get('hashtags', [])))
    for key, label in (('threads', 'Threads'), ('facebook', 'Facebook')):
        item = _as_dict(plan.get(key))
        parts.append(f'\n\n{label}投稿\n' + _render_tags_once(item.get('text', ''), item.get('hashtags', [])))
    parts.append(f'\n\nLINE配信文\n{_as_dict(plan.get("line")).get("text", "")}')
    carousel = _as_dict(plan.get('carousel'), 'caption')
    parts.append('\n\nInstagram投稿\n' + _render_tags_once(carousel.get('caption', ''), carousel.get('hashtags', [])))
    for key, label in (('reel', 'Instagramリール'), ('youtube', 'YouTube'), ('tiktok', 'TikTok')):
        item = _as_dict(plan.get(key), 'caption')
        parts.append(f'\n\n{label}\n{item.get("title", "")}\n' + _render_tags_once(item.get('caption', item.get('description', '')), item.get('hashtags', [])))
    return '\n'.join(parts).strip()


def creative_prompt_text(plan):
    prompts = _as_dict(_as_dict(plan).get('creative_prompts'))
    labels = [('product_promo_image', '商品紹介画像'), ('store_pop_image', '店内POP画像'),
              ('x_image', 'X投稿画像'), ('facebook_eyecatch', 'Facebookアイキャッチ'),
              ('threads_image', 'Threads投稿画像'), ('line_image', 'LINE配信用画像'),
              ('reel_cover', 'Instagramリール表紙'), ('reel_video', 'Instagramリール動画'),
              ('youtube_thumbnail', 'YouTubeサムネイル'), ('youtube_video', 'YouTube動画'),
              ('tiktok_cover', 'TikTok表紙'), ('tiktok_video', 'TikTok動画')]
    parts = ['画像・動画制作用プロンプト']
    for key, label in labels:
        item = _as_dict(prompts.get(key), 'prompt')
        parts.append(f'\n\n## {label}\nサイズ：{item.get("size", "")}\n'
                     f'推奨保存ファイル名：{item.get("output_filename", "")}\n'
                     f'画像・動画内キャッチコピー：{item.get("catch_copy", "")}\n'
                     f'画像内補足：{item.get("sub_copy", "")}\n'
                     f'レイアウト：{item.get("layout", "")}\n'
                     f'フォント指定：{item.get("font_spec", "")}\n{item.get("prompt", "")}')
    parts.append('\n\n## Instagramカルーセル9枚')
    for raw in _as_list(prompts.get('instagram_carousel')):
        item = _as_dict(raw, 'prompt')
        parts.append(f'\n\n### {item.get("slide", "")}枚目\nサイズ：{item.get("size", "")}\n'
                     f'推奨保存ファイル名：{item.get("output_filename", "")}\n'
                     f'イラスト内の大見出し：{item.get("catch_copy", "")}\n'
                     f'イラスト内の説明文：{item.get("body_text", "")}\n'
                     f'レイアウト：{item.get("layout", "")}\n'
                     f'フォント指定：{item.get("font_spec", "")}\n{item.get("prompt", "")}')
    parts.append('\n\n## ブログ記事の各セクション用イラスト')
    for raw in _as_list(prompts.get('article_section_images')):
        item = _as_dict(raw, 'prompt')
        parts.append(f'\n\n### セクション{item.get("section", "")}｜{item.get("heading_level", "")}：{item.get("heading", "")}\n'
                     f'サイズ：{item.get("size", "")}\n推奨保存ファイル名：{item.get("output_filename", "")}\n'
                     f'画像内キャッチコピー：{item.get("catch_copy", "")}\n'
                     f'画像内補足：{item.get("sub_copy", "")}\nレイアウト：{item.get("layout", "")}\n'
                     f'フォント指定：{item.get("font_spec", "")}\n{item.get("prompt", "")}')
    return '\n'.join(parts).strip()
