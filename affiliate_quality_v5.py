"""Conservative post-generation review. No article, WordPress, or scheduler changes."""
import copy
import re

RISK = re.compile(r'全身のがん|早期発見|早期がん|人間ドック(?:の代わり|より)|がんリスク(?:を|が|の)?(?:チェック|判定|分かる)|(?:必ず|絶対)(?:治る|改善)|(?:検査精度|感度)\s*[0-9０-９]|がんを(?:発見|診断|予防|治療)|お得な定期プラン', re.I)
MARK = re.compile(r'【(?:PR|商品案内)】')
URL = re.compile(r'https?://[^\s<>「」]+')
FALLBACK = '商品の特徴と利用前の注意点を記事でご確認ください。'


def safe_sentences(value, fallback=FALLBACK):
    parts = re.split(r'(?<=[。！？!?])|\n', str(value or ''))
    kept = [p.strip() for p in parts if p.strip() and not RISK.search(p)]
    return '\n'.join(kept) or fallback


def short_copy(value, maximum, fallback):
    text = re.sub(r'\s+', ' ', safe_sentences(value, fallback)).strip()
    if len(text) <= maximum:
        return text
    boundaries = [m.end() for m in re.finditer(r'[。！？、，\s]', text[:maximum])]
    if boundaries and boundaries[-1] >= 6:
        return text[:boundaries[-1]].rstrip('、， ')
    return fallback


def normalize_post(value, affiliate_url='', include_url=False, disclosure='【PR】'):
    body = MARK.sub('', str(value or ''))
    if affiliate_url:
        # Accept whitespace around query delimiters from generated copy.
        parts = re.split(r'([?&=])', affiliate_url.strip())
        pattern = ''.join(r'\s*' + re.escape(x) + r'\s*' if x in '?&=' else re.escape(x) for x in parts if x)
        body = re.sub(pattern, '', body, flags=re.I)
        # Remove only a dangling base URL when the full tracking query was broken.
        base = affiliate_url.split('?', 1)[0]
        if '?' in affiliate_url:
            body = re.sub(re.escape(base) + r'\s*\?(?=\s|$)', '', body, flags=re.I)
    body = safe_sentences(body)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    return disclosure + '\n' + body + ('\n' + affiliate_url if include_url and affiliate_url else '')


def _update_item(item, source, fields):
    if not isinstance(item, dict) or not isinstance(source, dict):
        return
    prompt = str(source.get('prompt', ''))
    for key, max_chars, fallback in fields:
        if key not in item:
            continue
        old = str(source.get(key, ''))
        new = short_copy(old, max_chars, fallback)
        item[key] = new
        if old and old != new:
            prompt = prompt.replace('「' + old + '」', '「' + new + '」')
    item['prompt'] = prompt
    if RISK.search(prompt):
        item['review_required'] = True


def review_bundle(bundle):
    """Review a deep copy; retain media inventory and original creative directions."""
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
                    slide['title'] = short_copy(slide.get('title'), 26, '商品のポイント')
                    slide['body'] = short_copy(slide.get('body'), 46, FALLBACK)
        else:
            for scene in post.get('scenes', []):
                if isinstance(scene, dict):
                    scene['caption'] = short_copy(scene.get('caption'), 28, '記事のポイント')
                    scene['narration'] = short_copy(scene.get('narration'), 45, FALLBACK)
    prompts = plan.get('creative_prompts', {})
    for key, entry in prompts.items():
        source_entry = bundle.get('social_plan', {}).get('creative_prompts', {}).get(key)
        originals = source_entry if isinstance(source_entry, list) else [source_entry]
        items = entry if isinstance(entry, list) else [entry]
        for index, item in enumerate(items):
            original = originals[index] if index < len(originals) else {}
            if not isinstance(item, dict):
                continue
            _update_item(item, original, (
                ('catch_copy', 28, '商品のポイント'),
                ('sub_copy', 46, FALLBACK),
                ('body_text', 46, FALLBACK),
            ))
            # For carousel and video, align the displayed copy with reviewed scenes.
            if key == 'instagram_carousel' and index < len(plan.get('carousel', {}).get('slides', [])):
                slide = plan['carousel']['slides'][index]
                old_title = str(item.get('catch_copy', ''))
                old_body = str(item.get('body_text', ''))
                item['catch_copy'], item['body_text'] = slide['title'], slide['body']
                item['sub_copy'] = slide['body']
                item['prompt'] = item['prompt'].replace('「' + old_title + '」', '「' + slide['title'] + '」').replace('「' + old_body + '」', '「' + slide['body'] + '」')
            if key in ('reel_video', 'youtube_video', 'tiktok_video'):
                platform = {'reel_video': 'reel', 'youtube_video': 'youtube', 'tiktok_video': 'tiktok'}[key]
                source_scenes = bundle['social_plan'][platform].get('scenes', [])
                reviewed_scenes = plan[platform].get('scenes', [])
                for before, after in zip(source_scenes, reviewed_scenes):
                    for field in ('caption', 'narration'):
                        old, new = str(before.get(field, '')), str(after.get(field, ''))
                        if old and old != new:
                            item['prompt'] = item['prompt'].replace('「' + old + '」', '「' + new + '」')
            if RISK.search(item.get('prompt', '')):
                item['review_required'] = True
    gbp = data.get('gbp', {})
    if isinstance(gbp, dict):
        gbp['post'] = normalize_post(gbp.get('post'), '', False, disclosure)
        for key in ('image_prompt', 'video_prompt'):
            if RISK.search(str(gbp.get(key, ''))):
                gbp['review_required'] = True
    validate_bundle(data)
    return data


def validate_bundle(bundle):
    plan = bundle['social_plan']
    if len(plan['carousel']['slides']) != 9:
        raise ValueError('Instagram carousel must have 9 slides')
    for key in ('reel', 'youtube', 'tiktok'):
        scenes = plan[key]['scenes']
        if len(scenes) < 3 or sum(int(re.search(r'\d+', str(s['duration'])).group()) for s in scenes) != 42:
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
