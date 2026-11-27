
"""Additive creative quality review.

This module never writes articles, WordPress data, or scheduler settings.
"""

import copy
import re
from medical_expression_rules import MEDICAL_RISK_PATTERN

RISK = re.compile(
    MEDICAL_RISK_PATTERN + r'|' +
    r'全身のがん|早期発見|早期がん|人間ドック(?:の代わり|より)|'
    r'がんリスク(?:を|が|の)?(?:チェック|判定|分かる)|'
    r'(?:必ず|絶対)(?:治る|改善)|'
    r'(?:検査精度|感度)\s*[0-9０-９]|'
    r'がんを(?:発見|診断|予防|治療)|'
    r'お得な定期プラン|'
    r'がんリスクチェック|がんリスクが分かる|'
    r'病院に行かずに自宅で完結|'
    r'通院不要で(?:手軽|安心)|'
    r'医療機関(?:の検査|での検査)が不要',
    re.I,
)

MARK = re.compile(r'【(?:PR|商品案内)】')
HOLD = re.compile(r'【要確認・生成保留】|生成保留')

FALLBACK = (
    '商品の特徴と利用前の注意点を記事でご確認ください。'
)

SAFE_TITLE = '商品のポイント'
SAFE_BODY = FALLBACK

SAFE_VISUAL = (
    '明るく清潔感のある日本の生活場面。'
    '実物の商品や検査結果を想像で再現しない。'
)

HOLD_NOTICE = '【要確認・生成保留】'


def _unsafe(value):
    text = str(value or '')
    return bool(RISK.search(text) or HOLD.search(text))


def safe_sentences(value, fallback=FALLBACK):
    """Remove unsafe claims without inventing replacement facts."""
    source = str(value or '')
    parts = re.split(r'(?<=[。！？!?])|\n', source)

    kept = []

    for part in parts:
        part = part.strip()

        if not part:
            continue

        if _unsafe(part):
            continue

        part = part.strip('「」『』“”" \n\t')

        if part:
            kept.append(part)

    return '\n'.join(kept) or fallback


def short_copy(value, maximum, fallback):
    """Return complete short copy; never cut a sentence halfway."""
    text = re.sub(
        r'\s+',
        ' ',
        safe_sentences(value, fallback)
    ).strip()

    if len(text) <= maximum:
        return text

    sentences = re.split(r'(?<=[。！？!?])', text)
    result = ''

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(result + sentence) <= maximum:
            result += sentence
        else:
            break

    if result:
        return result

    return fallback[:maximum]


def normalize_post(
    value,
    affiliate_url='',
    include_url=False,
    disclosure='【PR】'
):
    """Normalize PR disclosure and affiliate URL."""
    body = MARK.sub('', str(value or ''))

    if affiliate_url:
        parts = re.split(
            r'([?&=])',
            affiliate_url.strip()
        )

        pattern = ''.join(
            r'\s*' + re.escape(part) + r'\s*'
            if part in '?&='
            else re.escape(part)
            for part in parts
            if part
        )

        body = re.sub(
            pattern,
            '',
            body,
            flags=re.I
        )

        base = affiliate_url.split('?', 1)[0]

        if '?' in affiliate_url:
            body = re.sub(
                re.escape(base) + r'\s*\?(?=\s|$)',
                '',
                body,
                flags=re.I
            )

    body = safe_sentences(body)

    body = re.sub(
        r'\n{3,}',
        '\n\n',
        body
    ).strip()

    result = disclosure + '\n' + body

    if include_url and affiliate_url:
        result += '\n' + affiliate_url

    return result


def _safe_label(value, fallback=SAFE_TITLE):
    text = str(value or '').strip()

    if _unsafe(text):
        return fallback

    return text or fallback


def _safe_visual(value):
    text = str(value or '').strip()

    if _unsafe(text):
        return SAFE_VISUAL

    return text or SAFE_VISUAL


def _clean_prompt(value):
    """Remove unsafe instructions while retaining safe directions."""
    text = str(value or '')

    if not _unsafe(text):
        return text

    parts = re.split(r'(?<=[。！？!?])|\n', text)

    kept = []

    for part in parts:
        part = part.strip()

        if part and not _unsafe(part):
            kept.append(part)

    return '\n'.join(kept)


def _replacement_prompt(item, original_prompt=''):
    """Create a conservative prompt and explicitly hold it for review."""
    lines = [
        HOLD_NOTICE,
        '事実確認が完了するまで画像・動画の生成と公開を保留する。',
        '未確認の医療効果、数値、口コミ、商品情報を表示しない。',
        '医療機関での診断や検査の代替と示唆しない。',
        '実物の商品、検査キット、ロゴ、認証マークを創作しない。',
        '明るい自然光と清潔感のある日本の生活場面。',
    ]

    for label, key in (
        ('サイズ', 'size'),
        ('配置', 'layout'),
        ('文字', 'font_spec'),
        ('総尺', 'duration'),
    ):
        if item.get(key):
            lines.append(label + '：' + str(item[key]))

    for label, key in (
        ('見出し', 'catch_copy'),
        ('補足', 'sub_copy'),
        ('本文', 'body_text'),
    ):
        if item.get(key):
            lines.append(
                label + '：「' + str(item[key]) + '」'
            )

    return '\n'.join(lines)


def _update_item(item, source, fields):
    if not isinstance(item, dict):
        return

    original_prompt = str(item.get('prompt', ''))
    unsafe_prompt = _unsafe(original_prompt)

    for key, maximum, fallback in fields:
        if key in item:
            item[key] = short_copy(
                item.get(key),
                maximum,
                fallback
            )

    # A previously held prompt must remain held.
    # Do not bypass review if risky text has been added.
    if (
        HOLD.search(original_prompt)
        and item.get('review_required') is True
        and not RISK.search(original_prompt)
    ):
        return

    if unsafe_prompt:
        item['prompt'] = _replacement_prompt(item)
        item['review_required'] = True
        return

    prompt = original_prompt

    for key, _, _ in fields:
        old = (
            str(source.get(key, ''))
            if isinstance(source, dict)
            else ''
        )
        new = str(item.get(key, ''))

        if old and old != new:
            prompt = prompt.replace(
                '「' + old + '」',
                '「' + new + '」'
            )

    item['prompt'] = prompt


def _safe_gbp_prompt(value, video=False):
    text = str(value or '')

    if not _unsafe(text):
        return text

    base = (
        '【PR】明るく清潔感のある日本向け説明クリエイティブ。'
        '未確認の医療効果、検査性能、料金、口コミ、'
        '商品パッケージは創作しない。'
        '医療機関での診断や検査の代替と示唆しない。'
        '商品の特徴と利用前の注意点は公式資料で確認する。'
    )

    if not video:
        return base + '1:1の静止画像。短い文字とPR表記。'

    return (
        base
        + '縦型9:16、総尺45秒、ナレーションなし、穏やかなBGM。'
        + '0〜5秒：導入（5秒）。'
        + '5〜13秒：概要（8秒）。'
        + '13〜23秒：確認ポイント（10秒）。'
        + '23〜33秒：利用前の注意（10秒）。'
        + '33〜40秒：記事の紹介（7秒）。'
        + '40〜45秒：記事への案内（5秒）。'
        + '各シーンに短い字幕を表示し、PR表記を維持する。'
    )


def _sync_carousel_prompt(item, source, slide):
    old_title = (
        str(source.get('catch_copy', ''))
        if isinstance(source, dict)
        else ''
    )

    old_body = (
        str(source.get('body_text', ''))
        if isinstance(source, dict)
        else ''
    )

    item['catch_copy'] = slide['title']
    item['sub_copy'] = slide['body']
    item['body_text'] = slide['body']

    prompt = str(item.get('prompt', ''))

    if item.get('review_required'):
        if RISK.search(prompt):
            item['prompt'] = _replacement_prompt(item)
        return

    if old_title:
        prompt = prompt.replace(
            '「' + old_title + '」',
            '「' + slide['title'] + '」'
        )

    if old_body:
        prompt = prompt.replace(
            '「' + old_body + '」',
            '「' + slide['body'] + '」'
        )

    item['prompt'] = prompt


def _sync_video_prompt(item, before, after):
    if item.get('review_required'):
        prompt = str(item.get('prompt', ''))

        if RISK.search(prompt):
            item['prompt'] = _replacement_prompt(item)
            prompt = item['prompt']

        if '【シーン別字幕】' not in prompt:
            lines = [
                f"{index + 1}（{scene.get('duration', '')}）："
                f"{scene.get('caption', '')}"
                for index, scene in enumerate(after)
            ]

            item['prompt'] += (
                '\n【シーン別字幕】\n'
                + '\n'.join(lines)
            )

        return

    prompt = str(item.get('prompt', ''))

    for old_scene, new_scene in zip(before, after):
        for field in ('caption', 'narration'):
            old = str(old_scene.get(field, ''))
            new = str(new_scene.get(field, ''))

            if old and old != new:
                prompt = prompt.replace(
                    '「' + old + '」',
                    '「' + new + '」'
                )

    item['prompt'] = prompt


def review_bundle(bundle):
    """Review a deep copy without modifying source data."""
    data = copy.deepcopy(bundle)

    plan = data.get('social_plan', {})

    affiliate_url = str(
        data.get('affiliate_url') or ''
    ).strip()

    disclosure = (
        '【PR】'
        if affiliate_url
        else '【商品案内】'
    )

    for post in plan.get('x_posts', []):
        if isinstance(post, dict):
            post['text'] = normalize_post(
                post.get('text'),
                affiliate_url,
                True,
                disclosure
            )

    for key in ('threads', 'facebook', 'line'):
        post = plan.get(key)

        if isinstance(post, dict):
            post['text'] = normalize_post(
                post.get('text'),
                affiliate_url,
                True,
                disclosure
            )

    for key in ('carousel', 'reel', 'youtube', 'tiktok'):
        post = plan.get(key)

        if not isinstance(post, dict):
            continue

        field = (
            'description'
            if key == 'youtube'
            else 'caption'
        )

        post[field] = normalize_post(
            post.get(field),
            affiliate_url,
            key == 'youtube',
            disclosure
        )

        if key == 'carousel':
            for slide in post.get('slides', []):
                if not isinstance(slide, dict):
                    continue

                slide['title'] = short_copy(
                    slide.get('title'),
                    26,
                    SAFE_TITLE
                )

                slide['body'] = short_copy(
                    slide.get('body'),
                    46,
                    SAFE_BODY
                )

                if 'visual' in slide:
                    slide['visual'] = _safe_visual(
                        slide['visual']
                    )

        else:
            for cover_key, maximum in (
                ('cover_title', 28),
                ('cover_body', 46),
                ('thumbnail_title', 28),
                ('thumbnail_body', 46),
            ):
                if cover_key in post:
                    post[cover_key] = short_copy(
                        post[cover_key],
                        maximum,
                        SAFE_BODY
                    )

            if 'title' in post:
                post['title'] = _safe_label(
                    post['title']
                )

            for scene in post.get('scenes', []):
                if not isinstance(scene, dict):
                    continue

                scene['caption'] = short_copy(
                    scene.get('caption'),
                    28,
                    '記事のポイント'
                )

                scene['narration'] = short_copy(
                    scene.get('narration'),
                    45,
                    SAFE_BODY
                )

                if 'visual' in scene:
                    scene['visual'] = _safe_visual(
                        scene['visual']
                    )

    prompts = plan.get('creative_prompts', {})

    original_prompts = (
        bundle.get('social_plan', {})
        .get('creative_prompts', {})
    )

    for key, entry in prompts.items():
        source_entry = original_prompts.get(key)

        originals = (
            source_entry
            if isinstance(source_entry, list)
            else [source_entry]
        )

        items = (
            entry
            if isinstance(entry, list)
            else [entry]
        )

        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue

            source = (
                originals[index]
                if index < len(originals)
                else {}
            )

            _update_item(
                item,
                source,
                (
                    ('catch_copy', 28, SAFE_TITLE),
                    ('sub_copy', 46, SAFE_BODY),
                    ('body_text', 46, SAFE_BODY),
                )
            )

            if (
                key == 'instagram_carousel'
                and index < len(
                    plan.get('carousel', {}).get('slides', [])
                )
            ):
                slide = plan['carousel']['slides'][index]

                _sync_carousel_prompt(
                    item,
                    source,
                    slide
                )

            if key in (
                'reel_video',
                'youtube_video',
                'tiktok_video',
            ):
                platform = {
                    'reel_video': 'reel',
                    'youtube_video': 'youtube',
                    'tiktok_video': 'tiktok',
                }[key]

                before = (
                    bundle['social_plan'][platform]
                    .get('scenes', [])
                )

                after = (
                    plan[platform]
                    .get('scenes', [])
                )

                _sync_video_prompt(
                    item,
                    before,
                    after
                )

            prompt = str(item.get('prompt', ''))

            if RISK.search(prompt):
                raise ValueError(
                    'Unsafe creative prompt remains: ' + key
                )

            if HOLD.search(prompt):
                item['review_required'] = True

    gbp = data.get('gbp', {})

    if isinstance(gbp, dict):
        gbp['post'] = normalize_post(
            gbp.get('post'),
            '',
            False,
            disclosure
        )

        original_image = gbp.get('image_prompt', '')
        original_video = gbp.get('video_prompt', '')

        gbp['image_prompt'] = _safe_gbp_prompt(
            original_image
        )

        gbp['video_prompt'] = _safe_gbp_prompt(
            original_video,
            True
        )

        if (
            gbp['image_prompt'] != original_image
            or gbp['video_prompt'] != original_video
        ):
            gbp['review_required'] = True

    validate_bundle(data)

    return data


def validate_bundle(bundle):
    """Validate media inventory and basic safety constraints."""
    plan = bundle['social_plan']

    slides = plan['carousel']['slides']

    if len(slides) != 9:
        raise ValueError(
            'Instagram carousel must have 9 slides'
        )

    for key in ('reel', 'youtube', 'tiktok'):
        scenes = plan[key]['scenes']
        durations = []

        for scene in scenes:
            match = re.search(
                r'\d+',
                str(scene.get('duration', ''))
            )

            if not match:
                raise ValueError(
                    'Missing duration in ' + key
                )

            durations.append(
                int(match.group())
            )

        if (
            len(scenes) < 3
            or sum(durations) != 45
        ):
            raise ValueError(
                key + ' must be exactly 45 seconds'
            )

    prompts = plan['creative_prompts']

    for key in (
        'instagram_carousel',
        'article_section_images',
    ):
        if not prompts.get(key):
            raise ValueError(
                'Missing prompts: ' + key
            )

    if len(prompts['instagram_carousel']) != 9:
        raise ValueError(
            'Nine carousel image prompts required'
        )

    for key, value in prompts.items():
        items = (
            value
            if isinstance(value, list)
            else [value]
        )

        for item in items:
            if not isinstance(item, dict):
                continue

            prompt = str(
                item.get('prompt', '')
            )

            if not prompt:
                raise ValueError(
                    'Empty creative prompt: ' + key
                )

            if RISK.search(prompt):
                raise ValueError(
                    'Unsafe creative prompt: ' + key
                )

            if HOLD.search(prompt):
                if not item.get('review_required'):
                    raise ValueError(
                        'Hold prompt missing review flag: ' + key
                    )

    video = (
        bundle.get('gbp', {})
        .get('video_prompt', '')
    )

    if (
        '45秒' not in video
        or '40〜45秒' not in video
    ):
        raise ValueError(
            'Expected 45-second GBP video brief'
        )

    return True
