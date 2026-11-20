"""Conservative post-generation quality review; never writes to WordPress.

Keep the original media inventory, durations and article content unchanged.
Potentially unsupported claims are replaced with neutral copy and flagged.
"""
import copy
import re

RISK = re.compile(
    r'全身のがん|早期発見|早期がん|人間ドック(?:の代わり|より)|'
    r'がんリスク(?:を|が|の)?(?:チェック|判定|分かる)|'
    r'(?:必ず|絶対)(?:治る|改善)|(?:検査精度|感度)\s*[0-9０-９]|'
    r'がんを(?:発見|診断|予防|治療)|お得な定期プラン|'
    r'(?:病気|疾患|がん)(?:が|を)?(?:分かる|わかる|見つかる|判定できる)|'
    r'(?:医師|専門医)(?:が|も)?(?:推薦|推奨)|'
    r'(?:利用者|お客様|患者様|購入者)(?:の声|の口コミ|の体験談)|'
    r'(?:使って|試して)(?:みた|よかった)|'
    r'(?:治療|予防|完治)(?:できる|します|効果)|'
    r'(?:100|１００)\s*[%％](?:の|確実|保証)',
    re.I,
)
MARK = re.compile(r'【(?:PR|商品案内)】')
URL = re.compile(r'https?://[^\s<>「」]+')
FALLBACK = '商品の特徴と利用前の注意点を記事でご確認ください。'
TITLE_FALLBACK = '商品のポイント'
SCENE_FALLBACK = '記事のポイント'


def _sentences(value):
    """Keep sentence boundaries; never emit a clipped sentence fragment."""
    text = str(value or '').replace('\r\n', '\n').strip()
    if not text:
        return []
    result = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Preserve a short heading or complete short label as one unit.
        units = re.findall(r'[^。！？!?]+[。！？!?]|[^。！？!?]+$', line)
        result.extend(x.strip() for x in units if x.strip())
    return result


def safe_sentences(value, fallback=FALLBACK):
    kept = [s for s in _sentences(value) if not RISK.search(s)]
    return '\n'.join(kept) if kept else fallback


def short_copy(value, maximum, fallback):
    """Fit whole sentences; fall back rather than cut a word or sentence."""
    if maximum <= 0:
        return ''
    fallback = fallback if len(fallback) <= maximum else ''
    candidates = [s for s in _sentences(value) if not RISK.search(s)]
    output = ''
    for sentence in candidates:
        separator = ' ' if output else ''
        if len(output) + len(separator) + len(sentence) <= maximum:
            output += separator + sentence
        else:
            break
    if output:
        return output
    # For a short label without punctuation, keep it only when complete.
    return fallback


def _strip_affiliate_url(body, affiliate_url):
    if not affiliate_url:
        return body
    url = affiliate_url.strip()
    parts = re.split(r'([?&=])', url)
    pattern = ''.join(
        r'\s*' + re.escape(part) + r'\s*' if part in '?&=' else re.escape(part)
        for part in parts if part
    )
    body = re.sub(pattern, '', body, flags=re.I)
    base = url.split('?', 1)[0]
    if '?' in url:
        body = re.sub(re.escape(base) + r'\s*\?(?=\s|$)', '', body, flags=re.I)
    return body


def normalize_post(value, affiliate_url='', include_url=False, disclosure='【PR】'):
    body = MARK.sub('', str(value or ''))
    body = _strip_affiliate_url(body, affiliate_url)
    # Remove other generated URLs rather than preserve unverified destinations.
    body = URL.sub('', body)
    body = safe_sentences(body)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    return disclosure + '\n' + body + ('\n' + affiliate_url if include_url and affiliate_url else '')


def _replace_display_text(prompt, old, new):
    if not old or old == new:
        return prompt
    # Replace both quoted and plain occurrences; keeps instructions in sync.
    return prompt.replace(str(old), str(new))


def _review_prompt(item, original, replacements=()):
    """Align rendered text; do not silently approve unsupported prompt claims."""
    prompt = str(original.get('prompt', item.get('prompt', '')))
    for old, new in replacements:
        prompt = _replace_display_text(prompt, old, new)
    if RISK.search(str(original.get('prompt', ''))) or RISK.search(prompt) or item.get('review_required'):
        item['review_required'] = True
        # The original unsafe prompt must not be sent to an image/video model.
        item['prompt'] = (
            '【要確認・生成保留】元の制作指示に未確認の医療効果・口コミ等が含まれます。'
            '元記事と公式資料で事実確認後、制作指示を作り直してください。'
        )
    else:
        item['prompt'] = prompt


def _review_text_field(item, key, limit, fallback):
    old = str(item.get(key, ''))
    new = short_copy(old, limit, fallback)
    item[key] = new
    return old, new


def review_bundle(bundle):
    """Review a deep copy; retain media inventory and original directions."""
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
        post[field] = normalize_post(post.get(field), affiliate_url, key == 'youtube', disclosure)
        if key == 'carousel':
            for slide in post.get('slides', []):
                if isinstance(slide, dict):
                    _review_text_field(slide, 'title', 26, TITLE_FALLBACK)
                    _review_text_field(slide, 'body', 46, FALLBACK)
        else:
            for scene in post.get('scenes', []):
                if isinstance(scene, dict):
                    _review_text_field(scene, 'caption', 28, SCENE_FALLBACK)
                    _review_text_field(scene, 'narration', 45, FALLBACK)

    prompts = plan.get('creative_prompts', {})
    source_prompts = bundle.get('social_plan', {}).get('creative_prompts', {})
    for key, entry in prompts.items():
        source_entry = source_prompts.get(key)
        originals = source_entry if isinstance(source_entry, list) else [source_entry]
        items = entry if isinstance(entry, list) else [entry]
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            original = originals[index] if index < len(originals) and isinstance(originals[index], dict) else {}
            replacements = []
            for field, limit, fallback in (
                ('catch_copy', 28, TITLE_FALLBACK),
                ('sub_copy', 46, FALLBACK),
                ('body_text', 46, FALLBACK),
            ):
                if field in item:
                    old, new = _review_text_field(item, field, limit, fallback)
                    replacements.append((old, new))

            if key == 'instagram_carousel':
                slides = plan.get('carousel', {}).get('slides', [])
                if index < len(slides):
                    slide = slides[index]
                    for field, new in (('catch_copy', slide['title']),
                                       ('body_text', slide['body']),
                                       ('sub_copy', slide['body'])):
                        if field in item:
                            replacements.append((str(item[field]), new))
                            item[field] = new
            if key in ('reel_video', 'youtube_video', 'tiktok_video'):
                platform = {'reel_video': 'reel', 'youtube_video': 'youtube',
                            'tiktok_video': 'tiktok'}[key]
                before_scenes = bundle.get('social_plan', {}).get(platform, {}).get('scenes', [])
                after_scenes = plan.get(platform, {}).get('scenes', [])
                for before, after in zip(before_scenes, after_scenes):
                    if isinstance(before, dict) and isinstance(after, dict):
                        for field in ('caption', 'narration'):
                            replacements.append((str(before.get(field, '')),
                                                 str(after.get(field, ''))))
            _review_prompt(item, original, replacements)

    gbp = data.get('gbp', {})
    if isinstance(gbp, dict):
        gbp['post'] = normalize_post(gbp.get('post'), '', False, disclosure)
        for key in ('image_prompt', 'video_prompt'):
            if RISK.search(str(gbp.get(key, ''))):
                gbp['review_required'] = True
                # Keep timing/instructions intact for GBP video, but flag for review.
    validate_bundle(data)
    return data


def validate_bundle(bundle):
    plan = bundle['social_plan']
    if len(plan['carousel']['slides']) != 9:
        raise ValueError('Instagram carousel must have 9 slides')
    for key in ('reel', 'youtube', 'tiktok'):
        scenes = plan[key]['scenes']
        if len(scenes) < 3:
            raise ValueError(key + ' must have at least 3 scenes')
        total = 0
        for scene in scenes:
            match = re.fullmatch(r'\s*(\d+)\s*(?:秒|s|sec)?\s*', str(scene.get('duration', '')))
            if not match:
                raise ValueError(key + ' has invalid scene duration')
            total += int(match.group(1))
        if total != 42:
            raise ValueError(key + ' must be exactly 42 seconds')
    prompts = plan['creative_prompts']
    for key in ('instagram_carousel', 'article_section_images'):
        if not prompts.get(key):
            raise ValueError('Missing prompts: ' + key)
    if len(prompts['instagram_carousel']) != 9:
        raise ValueError('Nine carousel image prompts required')
    gbp_video = bundle.get('gbp', {}).get('video_prompt', '')
    if not gbp_video or not ('45秒' in gbp_video and '40〜45秒' in gbp_video):
        raise ValueError('Expected 45-second GBP video brief')
    return True
