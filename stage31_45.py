"""Validation-only checks. Findings are advisory, never publication approval."""
import re
from pathlib import Path
from urllib.parse import urlsplit


def preview_limit(value):
    if isinstance(value, bool) or str(value) not in {'1','2','3','4','5'}:
        raise ValueError('Preview limit must be 1–5')
    return int(value)


def preview_paths(limit, index):
    if not 0 <= index < preview_limit(limit):
        raise ValueError('Invalid preview index')
    return (Path('preview_outputs') if limit == 1 else Path('preview_outputs') / f'article_{index+1:02d}', index)


def valid_timing(scenes):
    if not isinstance(scenes, list) or len(scenes) < 3:
        return False
    values = []
    for scene in scenes:
        if not isinstance(scene, dict): return False
        match = re.fullmatch(r'([1-9][0-9]*)秒', str(scene.get('duration', '')))
        if not match: return False
        values.append(int(match.group(1)))
    return sum(values) == 45 and values[0] == values[-1] == 4


def audit_export(bundle):
    flags=[]
    def flag(code): flags.append(code)
    plan=bundle.get('social_plan',{})
    if len(plan.get('carousel',{}).get('slides',[])) != 9: flag('carousel_count')
    for medium in ('reel','youtube','tiktok'):
        video=plan.get(medium,{})
        if not video.get('scenes'): flag(medium+'_missing_scenes')
        if video.get('total_duration') not in (45, '45秒') or not valid_timing(video.get('scenes', [])): flag(medium+'_duration_review')
    gbp=bundle.get('gbp',{})
    for key in ('post','image_prompt','video_prompt'):
        if not gbp.get(key): flag('gbp_'+key)
    if '45秒' not in gbp.get('video_prompt',''): flag('gbp_duration_review')
    for key in ('product_promo_image','store_pop_image'):
        if not plan.get('creative_prompts',{}).get(key): flag(key)
    link=bundle.get('affiliate_url','')
    try:
        u=urlsplit(link)
        if u.scheme!='https' or not u.hostname or u.username or u.password: flag('affiliate_url_review')
    except ValueError: flag('affiliate_url_review')
    posts=[(f'x_{i}',p.get('text','')) for i,p in enumerate(plan.get('x_posts',[]))]
    posts += [(k,plan.get(k,{}).get('description' if k=='youtube' else 'text','')) for k in ('threads','facebook','line','youtube')]
    for key,copy in posts:
        if not re.search(r'PR|広告',copy): flag(key+'_ad_disclosure')
        if link and link in copy and re.search(r'(?:詳細はこちら|詳しくはこちら|記事はこちら|ブログはこちら)[：:]?\s*'+re.escape(link),copy): flag(key+'_destination_review')
    return {'flags':flags,'human_review_required':True,'publication_approved':False}


def validate_preview(result, limit, root=Path('.')):
    limit = preview_limit(limit)
    rows=result.get('results',[])
    if len(rows)!=limit or result.get('processed')!=limit:
        raise RuntimeError('Preview incomplete: insufficient successful articles or available topics')
    identities=set()
    from unicodedata import normalize
    for i,row in enumerate(rows):
        identity=tuple(re.sub(r'\s+', '', normalize('NFKC', str(row.get(k) or '')).casefold()) for k in ('keyword','angle'))
        if not all(identity) or identity in identities: raise RuntimeError('Missing or duplicate topic')
        identities.add(identity)
        if row.get('status')!='preview_only' or row.get('creative')!='saved' or row.get('wp_id') is not None:
            raise RuntimeError('Preview incomplete or unexpected write')
        dest,post=preview_paths(limit,i)
        for path in [dest/'article.md',dest/'article.html',dest/'article.json',Path('creative_outputs')/f'post_{post}'/'all_prompts.json']:
            if not (root/path).is_file() or not (root/path).stat().st_size: raise RuntimeError(f'Missing preview artifact: {path}')


def validate_preview_identity(result, limit, root=Path('.')):
    """Reject crossed article/creative exports before recording a manifest."""
    import json
    root = Path(root)
    for i, row in enumerate(result['results']):
        dest, post = preview_paths(limit, i)
        try:
            article = json.loads((root / dest / 'article.json').read_text(encoding='utf-8'))
            bundle = json.loads((root / 'creative_outputs' / f'post_{post}' / 'all_prompts.json').read_text(encoding='utf-8'))
            if not isinstance(article, dict) or not isinstance(bundle, dict):
                raise ValueError('Expected objects')
            for key in ('title', 'keyword', 'angle'):
                value = row.get(key)
                if not isinstance(value, str) or not value.strip() or article.get(key) != value:
                    raise ValueError('Article identity mismatch')
            if bundle.get('title') != row['title'] or type(bundle.get('post_id')) is not int or bundle['post_id'] != post:
                raise ValueError('Creative identity mismatch')
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError(f'Invalid preview identity at article {i+1}') from exc
