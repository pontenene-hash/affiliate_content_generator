"""Review actual exported copy, not just the proposed creative brief."""
import re, unicodedata
from collections import defaultdict

def normalized(text):
    return re.sub(r'[\W_]+','',unicodedata.normalize('NFKC',str(text)).casefold())

def audit_bundle(bundle):
    plan=bundle.get('social_plan',{}); flags=[]
    def flag(kind,paths): flags.append({'kind':kind,'paths':paths})
    groups=defaultdict(list)
    for i,s in enumerate(plan.get('carousel',{}).get('slides',[])):
        key=normalized(s.get('body',''))
        if len(key)>=8: groups[key].append(f'carousel/{i+1}')
    for paths in groups.values():
        if len(paths)>1: flag('repeated_slide_body',paths)
    videos=defaultdict(list)
    for medium in ('reel','youtube','tiktok'):
        scenes=plan.get(medium,{}).get('scenes',[])
        key=tuple(normalized(s.get('caption','')) for s in scenes if s.get('scene_type')=='content')
        if key and any(key): videos[key].append(medium)
    for paths in videos.values():
        if len(paths)>1: flag('repeated_video_content',paths)
    link=bundle.get('affiliate_url','')
    posts=[(f'x/{i+1}',p.get('text','')) for i,p in enumerate(plan.get('x_posts',[]))]
    posts += [(k,plan.get(k,{}).get('description' if k=='youtube' else 'text','')) for k in ('threads','facebook','line','youtube')]
    for path,copy in posts:
        if link and link in copy and re.search(r'記事(?:はこちら|を読む|へ|をご覧|をチェック)|ブログ(?:はこちら|を読む)',copy): flag('ambiguous_article_destination',[path])
    return {'flags':flags,'human_review_required':True,'publication_approved':False,'limitations':'Exact normalized repetition and selected CTA phrases only; not semantic verification.'}
