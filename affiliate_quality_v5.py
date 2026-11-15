"""Additive V5 review for auto_creative.build_bundle output; no WP or scheduler changes."""
import copy
import re

RISK = re.compile(r'全身のがん|早期発見|早期がん|人間ドック(?:の代わり|より)|がんリスク(?:を|が|の)?(?:チェック|判定|分かる)|(?:必ず|絶対)(?:治る|改善)|(?:検査精度|感度)\s*[0-9０-９]', re.I)
URL = re.compile(r'https?://[^\s<>]+')

def safe_sentences(value, fallback='商品の特徴と利用前の注意点を記事でご確認ください。'):
    text = str(value or '')
    pieces = re.split(r'(?<=[。！？!?])|\n', text)
    kept = [p.strip() for p in pieces if p.strip() and not RISK.search(p)]
    return '\n'.join(kept) or fallback

def short_copy(value, maximum, fallback):
    text = re.sub(r'\s+', ' ', safe_sentences(value, fallback)).strip()
    if len(text) <= maximum:
        return text
    # Prefer a complete sentence or phrase; do not silently truncate product names.
    candidates = [m.end() for m in re.finditer(r'[。！？、，\s]', text[:maximum])]
    if candidates and candidates[-1] >= 6:
        return text[:candidates[-1]].rstrip('、， ') 
    return fallback

def normalize_post(text, affiliate_url='', include_url=False):
    body = re.sub(r'【(?:PR|商品案内)】', '', str(text or ''))
    # Remove known link only, never indiscriminately replace other links.
    if affiliate_url:
        body = body.replace(affiliate_url, '')
    body = safe_sentences(body)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    result = '【PR】\n' + body
    if include_url and affiliate_url:
        result += '\n' + affiliate_url
    return result

def review_bundle(bundle):
    """Return a reviewed copy; preserve existing keys and asset inventory."""
    data = copy.deepcopy(bundle)
    plan = data.get('social_plan', {})
    url = data.get('affiliate_url', '')
    for post in plan.get('x_posts', []):
        post['text'] = normalize_post(post.get('text'), url, True)
    for key in ('threads', 'facebook', 'line'):
        post = plan.get(key)
        if isinstance(post, dict):
            post['text'] = normalize_post(post.get('text'), url, True)
    for key in ('carousel', 'reel', 'youtube', 'tiktok'):
        post = plan.get(key)
        if not isinstance(post, dict):
            continue
        field = 'description' if key == 'youtube' else 'caption'
        post[field] = normalize_post(post.get(field), url, key == 'youtube')
        if key == 'carousel':
            for slide in post.get('slides', []):
                slide['title'] = short_copy(slide.get('title'), 26, '商品のポイント')
                slide['body'] = short_copy(slide.get('body'), 46, '詳しくは記事をご確認ください。')
        else:
            for scene in post.get('scenes', []):
                scene['caption'] = short_copy(scene.get('caption'), 28, '記事のポイント')
                scene['narration'] = short_copy(scene.get('narration'), 45, '詳しくは記事をご確認ください。')
    # Retain the original creative prompt text, scene visuals, and layout instructions.
    # Replace only display copy; avoid changing quality and timing requirements.
    prompts = plan.get('creative_prompts', {})
    for entry in prompts.values():
        for item in entry if isinstance(entry, list) else [entry]:
            if not isinstance(item, dict):
                continue
            original = dict(item)
            for key, max_chars in (('catch_copy', 28), ('sub_copy', 46), ('body_text', 46)):
                if key in item:
                    item[key] = short_copy(item[key], max_chars, '商品の特徴と注意点')
            prompt = str(original.get('prompt', ''))
            for key in ('catch_copy', 'sub_copy', 'body_text'):
                old = str(original.get(key, ''))
                if old and old != item.get(key, old):
                    prompt = prompt.replace('「' + old + '」', '「' + item[key] + '」')
            # Prompt can include risk claims elsewhere: require human review instead of deleting creative direction.
            if RISK.search(prompt):
                item['review_required'] = True
            item['prompt'] = prompt
    gbp = data.get('gbp', {})
    if isinstance(gbp, dict):
        gbp['post'] = normalize_post(gbp.get('post'), '', False)
        for key in ('image_prompt', 'video_prompt'):
            if RISK.search(gbp.get(key, '')):
                gbp['review_required'] = True
        # Preserve existing 45-second video brief and image brief.
    validate_bundle(data)
    return data

def validate_bundle(bundle):
    plan = bundle['social_plan']
    if len(plan['carousel']['slides']) != 9:
        raise ValueError('Instagram carousel must have 9 slides')
    for key in ('reel', 'youtube', 'tiktok'):
        scenes = plan[key]['scenes']
        if sum(int(re.search(r'\d+', str(s['duration'])).group()) for s in scenes) != 42:
            raise ValueError(key + ' must be exactly 42 seconds')
    for key in ('instagram_carousel', 'article_section_images'):
        if not plan['creative_prompts'].get(key):
            raise ValueError('Missing prompts: ' + key)
    if not bundle.get('gbp', {}).get('video_prompt'):
        raise ValueError('GBP video brief missing')
    return True
