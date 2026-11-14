#!/usr/bin/env python3
"""ChatGPT image prompt bundle and WordPress draft image installer (stdlib only)."""
import argparse, json, os, re, sys, zipfile, mimetypes, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from base64 import b64encode
from html import escape

SLOTS = [
 ('01_official','公式商品画像','登録済みの許諾済み公式商品画像。AIでパッケージを再現しない。'),
 ('02_lifestyle','生活シーン','日本人の成人が日常生活で商品ジャンルに関連する行動をしている自然な写真。実際の利用者・体験談を装わない。'),
 ('03_explainer','解説画像','記事の重要なポイントを視覚的に整理した、文字なしの上品な概念図・イラスト。'),
 ('04_empathy','共感シーン','読者の悩みや検討シーンを自然に表現した写真。効果・診断結果・利用体験を捏造しない。')]

def create(args):
    article = json.loads(Path(args.article).read_text(encoding='utf-8'))
    title = article.get('title',''); product = article.get('product_name',''); audience=article.get('audience','日本の成人読者')
    if not title or not product: raise ValueError('article JSON needs title and product_name')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    prompts=[]
    for i,(stem,kind,brief) in enumerate(SLOTS):
        if i==0:
            p='公式の商品写真を権利者の許可に基づき用意してください。ChatGPTで偽の製品パッケージは作らないでください。'
        else:
            p=(f'アフィリエイト記事「{title}」用の{kind}画像を1枚生成。商品ジャンル: {product}。対象: {audience}。'
               f'{brief} 横長16:9、清潔感のある自然な日本の生活空間、広告に使える高品質、自然な人体・手指、'
               '文字・ロゴ・透かしなし。商品の外観、検査結果、数値、効能、使用体験、専門家の推奨を捏造しない。'
               '医療的な断定表現や恐怖を煽る表現を避ける。')
        prompts.append({'slot':i+1,'filename':stem+'.png','type':kind,'prompt':p})
    (out/'prompts.json').write_text(json.dumps({'article':article,'images':prompts},ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'prompts.md').write_text('# ChatGPT画像制作指示\n\n'+'\n\n'.join(f"## {x['slot']}枚目：{x['type']}（{x['filename']}）\n{x['prompt']}" for x in prompts)+'\n',encoding='utf-8')
    (out/'manifest.json').write_text(json.dumps({'post_id':article.get('post_id'),'title':title,'images':[x['filename'] for x in prompts]},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Created: {out}/prompts.md and manifest.json')

def api(site, user, password, endpoint, method='GET', body=None, content_type=None, filename=None):
    auth=b64encode(f'{user}:{password}'.encode()).decode()
    headers={'Authorization':'Basic '+auth,'Accept':'application/json','User-Agent':'AffiliateImageWorkflow/1.0'}
    if content_type:headers['Content-Type']=content_type
    if filename:headers['Content-Disposition']=f'attachment; filename="{filename}"'
    if isinstance(body,(dict,list)):
        body=json.dumps(body,ensure_ascii=False).encode();headers['Content-Type']='application/json'
    req=Request(site.rstrip('/')+'/wp-json/wp/v2/'+endpoint.lstrip('/'),data=body,headers=headers,method=method)
    try:
        with urlopen(req,timeout=40) as r:return json.loads(r.read().decode())
    except HTTPError as e:
        raise RuntimeError(f'WordPress API HTTP {e.code}: {e.read(300).decode(errors="replace")}') from e

def install(args):
    site=os.getenv('WP_SITE_URL',''); user=os.getenv('WP_USERNAME',''); password=os.getenv('WP_APP_PASSWORD','')
    if not all((site,user,password)):raise ValueError('WP_SITE_URL, WP_USERNAME, WP_APP_PASSWORD are required')
    archive=Path(args.zip)
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        files={}
        for stem,_,_ in SLOTS:
            matches=[n for n in names if Path(n).name.lower() in (stem+'.png',stem+'.jpg',stem+'.jpeg',stem+'.webp') and not n.startswith('__MACOSX/')]
            if len(matches)!=1:raise ValueError(f'ZIP needs exactly one {stem}.png/.jpg/.jpeg/.webp')
            data=z.read(matches[0]);
            if len(data)>10*1024*1024:raise ValueError(f'Image too large: {matches[0]}')
            ext=Path(matches[0]).suffix.lower();signature={'.png':data.startswith(b'\x89PNG\r\n\x1a\n'),'.jpg':data.startswith(b'\xff\xd8'),'.jpeg':data.startswith(b'\xff\xd8'),'.webp':data.startswith(b'RIFF') and data[8:12]==b'WEBP'}[ext]
            if not signature:raise ValueError(f'Invalid image file: {matches[0]}')
            files[stem]=(data,ext)
    post=api(site,user,password,f'posts/{args.post_id}?context=edit')
    if post.get('status')!='draft':raise ValueError('Only WordPress draft posts can be modified')
    content=post.get('content',{}).get('raw','')
    if '<!-- affiliate-chatgpt-images:start -->' in content:raise ValueError('Images already installed; refusing duplicate insertion')
    if not content.strip():raise ValueError('Post content is empty')
    if not args.apply:
        print(f'Validated 4 images and draft post #{args.post_id}. Run with --apply to upload and insert.');return
    uploaded=[]
    for stem,(data,ext) in files.items():
        mime=mimetypes.types_map.get(ext,'image/png');filename=f'affiliate-{args.post_id}-{stem}-{uuid.uuid4().hex[:8]}{ext}'
        media=api(site,user,password,'media',method='POST',body=data,content_type=mime,filename=filename)
        # WordPress normally expects Content-Disposition for media upload; see upload_media below
        uploaded.append(media)
    figures=[]
    for idx,media in enumerate(uploaded):
        src=media.get('source_url');mid=media.get('id')
        if not src or not mid:raise ValueError('WordPress media response missing source_url/id')
        caption=SLOTS[idx][1];figures.append(f'<figure class="wp-block-image"><img src="{escape(src,quote=True)}" alt="{escape(post.get("title",{}).get("raw", "記事")+" - "+caption,quote=True)}" class="wp-image-{mid}"/></figure>')
    headings=list(re.finditer(r'</h[2-3]\s*>',content,re.I))
    # Insert after evenly spaced headings; if too few, append remaining images to end.
    positions=[]
    for i in range(4):
        if headings:positions.append(headings[min(len(headings)-1,(i*len(headings))//4)].end())
        else:positions.append(len(content))
    for pos,fig in sorted(zip(positions,figures),key=lambda x:x[0],reverse=True):
        content=content[:pos]+'\n'+fig+'\n'+content[pos:]
    content='<!-- affiliate-chatgpt-images:start -->\n'+content+'\n<!-- affiliate-chatgpt-images:end -->'
    updated=api(site,user,password,f'posts/{args.post_id}',method='POST',body={'content':content,'featured_media':uploaded[0]['id'],'status':'draft'})
    print(f'Updated draft #{updated.get("id")} with 4 images. Verify in WordPress editor.')

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='cmd',required=True)
    c=sub.add_parser('prompts');c.add_argument('--article',required=True);c.add_argument('--output',default='image_prompts');c.set_defaults(func=create)
    i=sub.add_parser('install');i.add_argument('--post-id',type=int,required=True);i.add_argument('--zip',required=True);i.add_argument('--apply',action='store_true');i.set_defaults(func=install)
    a=parser.parse_args();a.func(a)
if __name__=='__main__':
    try:main()
    except Exception as e:print(f'ERROR: {e}',file=sys.stderr);sys.exit(1)
