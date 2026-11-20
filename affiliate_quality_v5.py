"""Additive creative quality review. Never writes articles or WordPress data."""
import copy
import re

RISK = re.compile(
    r'全身のがん|早期発見|早期がん|人間ドック(?:の代わり|より)|'
    r'がんリスク(?:を|が|の)?(?:チェック|判定|分かる)|'
    r'(?:必ず|絶対)(?:治る|改善)|(?:検査精度|感度)\s*[0-9０-９]|'
    r'がんを(?:発見|診断|予防|治療)|お得な定期プラン|'
    r'がんリスクチェック|がんリスクが分かる|'
    r'病院に行かずに自宅で完結|通院不要で(?:手軽|安心)|'
    r'医療機関(?:の検査|での検査)が不要', re.I
)
MARK = re.compile(r'【(?:PR|商品案内)】')
HOLD = re.compile(r'【要確認・生成保留】|生成保留')
FALLBACK = '商品の特徴と利用前の注意点を記事でご確認ください。'
SAFE_TITLE = '商品・サービスの確認ポイント'
SAFE_BODY = '特徴や利用条件は公式情報で確認しましょう。'
SAFE_VISUAL = '明るく清潔感のある日本の生活場面。実物の商品や検査結果を再現しない。'


def safe_sentences(value, fallback=FALLBACK):
    """Remove unsafe claims without inventing replacement facts."""
    source = str(value or '')
    parts = re.split(r'(?<=[。！？!?])|\n', source)
    kept = []
    for part in parts:
        part = part.strip()
        if not part or RISK.search(part) or HOLD.search(part):
            continue
        part = part.strip('「」『』“”\" \n\t')
        if part:
            kept.append(part)
    return '\n'.join(kept) or fallback


def short_copy(value, maximum, fallback):
    """Keep complete sentences; never truncate at a comma or mid-sentence."""
    if maximum <= 0:
        return ''
    text = re.sub(r'\s+', ' ', safe_sentences(value, fallback)).strip()
    if len(text) <= maximum:
        return text
    sentences = re.findall(r'[^。！？!?]+[。！？!?]', text)
    result = ''
    for sentence in sentences:
        sentence = sentence.strip()
        if len(result) + len(sentence) > maximum:
            break
        result += sentence
    if result:
        return result
    return fallback if len(fallback) <= maximum else fallback[:maximum]


def normalize_post(value, affiliate_url='', include_url=False, disclosure='【PR】'):
    body = MARK.sub('', str(value or ''))
    if affiliate_url:
        parts = re.split(r'([?&=])', affiliate_url.strip())
        pattern = ''.join(
            r'\s*' + re.escape(x) + r'\s*' if x in '?&=' else re.escape(x)
            for x in parts if x
        )
        body = re.sub(pattern, '', body, flags=re.I)
        base = affiliate_url.split('?', 1)[0]
        if '?' in affiliate_url:
            body = re.sub(re.escape(base) + r'\s*\?(?=\s|$)', '', body, flags=re.I)
    body = safe_sentences(body)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    return disclosure + '\n' + body + (
        '\n' + affiliate_url if include_url and affiliate_url else ''
    )


def _safe_label(value, fallback=SAFE_TITLE):
    text = str(value or '').strip()
    if RISK.search(text) or HOLD.search(text):
        return fallback
    return text or fallback


def _safe_visual(value):
    text = str(value or '').strip()
    return SAFE_VISUAL if RISK.search(text) or HOLD.search(text) else (text or SAFE_VISUAL)


def _update_item(item, source, fields):
    if not isinstance(item, dict):
        return
    for key, max_chars, fallback in fields:
        if key in item:
            item[key] = short_copy(item.get(key), max_chars, fallback)
    original_prompt = str(item.get('prompt', ''))
    if RISK.search(original_prompt) or HOLD.search(original_prompt):
        # Preserve output size, layout and filename while removing the unsafe
        # source instructions. Do not claim that product facts were verified.
        lines = [
            '【PR】日本向けの清潔感ある商用クリエイティブ。',
            '元記事の紹介用。事実確認が済んでいない医療効果・数値・口コミは表示しない。',
            '医療機関の検査や診断の代わりになると示唆しない。',
            '実物の商品、検査キット、ロゴ、認証マークを想像で描かない。',
            '明るい自然光、自然な日本の生活場面、文字を置ける余白。',
        ]
        for label, key in (('サイズ', 'size'), ('配置', 'layout'), ('文字', 'font_spec')):
            if item.get(key):
                lines.append(label + '：' + str(item[key]))
        if item.get('catch_copy'):
            lines.append('見出し：「' + str(item['catch_copy']) + '」')
        if item.get('sub_copy'):
            lines.append('補足：「' + str(item['sub_copy']) + '」')
        if item.get('body_text'):
            lines.append('本文：「' + str(item['body_text']) + '」')
        if item.get('duration'):
            lines.append('総尺：' + str(item['duration']))
        item['prompt'] = '\n'.join(lines)
        item['review_required'] = True
    else:
        # Keep original artistic instructions, but synchronize quoted copy.
        prompt = original_prompt
        for key, _, _ in fields:
            old = str(source.get(key, '')) if isinstance(source, dict) else ''
            new = str(item.get(key, ''))
            if old and old != new:
                prompt = prompt.replace('「' + old + '」', '「' + new + '」')
        item['prompt'] = prompt


def _safe_gbp_prompt(value, video=False):
    text = str(value or '')
    if not (RISK.search(text) or HOLD.search(text)):
        return text
    base = (
        '【PR】明るく清潔感のある日本向け説明クリエイティブ。'
        '未確認の医療効果、検査性能、料金、口コミ、商品パッケージは創作しない。'
        '医療機関での診断や検査の代替であると示唆しない。'
        '商品の特徴と利用前の注意点は公式資料で確認するよう案内する。'
    )
    if not video:
        return base + '1:1の静止画像。短い文字とPR表記。'
    return (
        base + '縦型9:16、総尺45秒、ナレーションなし、穏やかなBGM。'
        '0〜5秒：導入（5秒）。5〜13秒：概要（8秒）。'
        '13〜23秒：確認ポイント（10秒）。'
        '23〜33秒：利用前の注意（10秒）。'
        '33〜40秒：記事の紹介（7秒）。'
        '40〜45秒：記事への案内（5秒）。'
        '各シーンに短い字幕を表示し、PR表記を維持する。'
    )


def review_bundle(bundle):
    """Review a deep copy, retaining media counts and durations."""
    data = copy.deepcopy(bundle)
    plan = data.get('social_plan', {})
    affiliate_url = str(data.get('affiliate_url') or '').strip()
    disclosure = '【PR】' if affiliate_url else '【商品案内】'
    for post in plan.get('x_posts', []):
        if isinstance(post, dict):
            post['text'] = normalize_post(post.get('text'), affiliate_url, True, disclosure)
    for key in ('threads', 'facebook', 'line'):
        post = plan.get(key)
        if isinstance(post, dict):
            post['text'] = normalize_post(post.get('text'), affiliate_url, True, disclosure)
    for key in ('carousel', 'reel', 'youtube', 'tiktok'):
        post = plan.get(key)
        if not isinstance(post, dict):
            continue
        field = 'description' if key == 'youtube' else 'caption'
        post[field] = normalize_post(
            post.get(field), affiliate_url, key == 'youtube', disclosure
        )
        if key == 'carousel':
            for slide in post.get('slides', []):
                if isinstance(slide, dict):
                    slide['title'] = short_copy(slide.get('title'), 26, '商品のポイント')
                    slide['body'] = short_copy(slide.get('body'), 46, SAFE_BODY)
                    if 'visual' in slide:
                        slide['visual'] = _safe_visual(slide['visual'])
        else:
            for cover_key, limit in (
                ('cover_title', 28), ('cover_body', 46),
                ('thumbnail_title', 28), ('thumbnail_body', 46),
            ):
                if cover_key in post:
                    post[cover_key] = short_copy(post[cover_key], limit, SAFE_BODY)
            if 'title' in post:
                post['title'] = _safe_label(post['title'])
            for scene in post.get('scenes', []):
                if isinstance(scene, dict):
                    scene['caption'] = short_copy(scene.get('caption'), 28, '記事のポイント')
                    scene['narration'] = short_copy(scene.get('narration'), 45, SAFE_BODY)
                    if 'visual' in scene:
                        scene['visual'] = _safe_visual(scene['visual'])
    prompts = plan.get('creative_prompts', {})
    original_prompts = bundle.get('social_plan', {}).get('creative_prompts', {})
    for key, entry in prompts.items():
        source_entry = original_prompts.get(key)
        originals = source_entry if isinstance(source_entry, list) else [source_entry]
        items = entry if isinstance(entry, list) else [entry]
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            source = originals[index] if index < len(originals) else {}
            _update_item(item, source, (
                ('catch_copy', 28, SAFE_TITLE),
                ('sub_copy', 46, SAFE_BODY),
                ('body_text', 46, SAFE_BODY),
            ))
            if key == 'instagram_carousel' and index < len(plan.get('carousel', {}).get('slides', [])):
                slide = plan['carousel']['slides'][index]
                item['catch_copy'] = slide['title']
                item['sub_copy'] = slide['body']
                item['body_text'] = slide['body']
                # Rebuild only when source was unsafe or copy no longer matches.
                if item.get('review_required') and '【シーン別字幕】' not in item['prompt'] and '見出し：「' + slide['title'] + '」\n本文：' not in item['prompt']:
                    _update_item(item, {}, ())
                    item['prompt'] += '\n見出し：「' + slide['title'] + '」\n本文：「' + slide['body'] + '」'
                else:
                    for field, new in (('catch_copy', slide['title']), ('body_text', slide['body'])):
                        old = str(source.get(field, '')) if isinstance(source, dict) else ''
                        if old and old != new:
                            item['prompt'] = item['prompt'].replace('「' + old + '」', '「' + new + '」')
            if key in ('reel_video', 'youtube_video', 'tiktok_video'):
                platform = {'reel_video': 'reel', 'youtube_video': 'youtube', 'tiktok_video': 'tiktok'}[key]
                before = bundle['social_plan'][platform].get('scenes', [])
                after = plan[platform].get('scenes', [])
                if item.get('review_required') and '【シーン別字幕】' not in item['prompt']:
                    item['prompt'] += '\n【シーン別字幕】\n' + '\n'.join(
                        f"{i + 1}（{s.get('duration', '')}）：{s.get('caption', '')}"
                        for i, s in enumerate(after)
                    )
                else:
                    for b, a in zip(before, after):
                        for field in ('caption', 'narration'):
                            old, new = str(b.get(field, '')), str(a.get(field, ''))
                            if old and old != new:
                                item['prompt'] = item['prompt'].replace('「' + old + '」', '「' + new + '」')
            if RISK.search(item.get('prompt', '')) or HOLD.search(item.get('prompt', '')):
                raise ValueError('Unsafe creative prompt remains: ' + key)
    gbp = data.get('gbp', {})
    if isinstance(gbp, dict):
        gbp['post'] = normalize_post(gbp.get('post'), '', False, disclosure)
        gbp['image_prompt'] = _safe_gbp_prompt(gbp.get('image_prompt'))
        gbp['video_prompt'] = _safe_gbp_prompt(gbp.get('video_prompt'), True)
        if gbp.get('review_required') or gbp['image_prompt'] != bundle.get('gbp', {}).get('image_prompt') or gbp['video_prompt'] != bundle.get('gbp', {}).get('video_prompt'):
            gbp['review_required'] = True
    validate_bundle(data)
    return data


def validate_bundle(bundle):
    plan = bundle['social_plan']
    if len(plan['carousel']['slides']) != 9:
        raise ValueError('Instagram carousel must have 9 slides')
    for key in ('reel', 'youtube', 'tiktok'):
        scenes = plan[key]['scenes']
        durations = []
        for scene in scenes:
            match = re.search(r'\d+', str(scene.get('duration', '')))
            if not match:
                raise ValueError('Missing duration in ' + key)
            durations.append(int(match.group()))
        if len(scenes) < 3 or sum(durations) != 42:
            raise ValueError(key + ' must be exactly 42 seconds')
    prompts = plan['creative_prompts']
    for key in ('instagram_carousel', 'article_section_images'):
        if not prompts.get(key):
            raise ValueError('Missing prompts: ' + key)
    if len(prompts['instagram_carousel']) != 9:
        raise ValueError('Nine carousel image prompts required')
    for key, value in prompts.items():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, dict):
                prompt = str(item.get('prompt', ''))
                if not prompt or RISK.search(prompt) or HOLD.search(prompt):
                    raise ValueError('Unsafe or empty prompt: ' + key)
    video = bundle.get('gbp', {}).get('video_prompt', '')
    if '45秒' not in video or '40〜45秒' not in video:
        raise ValueError('Expected 45-second GBP video brief')
    return True
