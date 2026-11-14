"""Generate reusable creative briefs from the actual saved affiliate article."""
import json
import re
from pathlib import Path

from google import genai
from google.genai import types
from social_tools import generate_social_plan, social_text, creative_prompt_text


def _gemini_call(client, model, prompt, max_tokens, **kwargs):
    response = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=max_tokens,
            temperature=kwargs.get('temperature', 0.35),
            response_mime_type=kwargs.get('response_mime_type')))
    if not response.text:
        raise ValueError('Gemini returned an empty creative plan')
    return response.text


def _blog_prompts(article, title, product):
    heads = re.findall(r'^#{2,3}\s+(.+)$', article, re.M)
    subjects = [title] + (heads[:3] + ['商品の特徴', '選び方', '注意点'])[:3]
    items = []
    for i, subject in enumerate(subjects):
        items.append({
            'filename': f'blog_{i:02d}.png',
            'purpose': 'アイキャッチ' if i == 0 else f'本文画像{i}',
            'suggested_section': '記事冒頭' if i == 0 else subject,
            'prompt': (
                f'日本のWebメディア向け高品質な横長16:9画像。商品名「{product}」。'
                f'テーマ「{subject}」。読者に分かりやすい自然な日本人の生活場面、明るい自然光、'
                '清潔感、正確な人体と手指、文字を置ける余白。'
                '記事にない効果・価格・体験談・商品パッケージ・認証マークを創作しない。'
                '商品現物の再現は、正規の参考写真がない場合は行わない。'
                '文字なし、透かしなし、実在企業ロゴなし。')})
    return items


def build_bundle(article, title, product, post_id, affiliate_url, api_key, model):
    client = genai.Client(api_key=api_key)
    plan = generate_social_plan(client, model, article, _gemini_call,
                                affiliate_url=affiliate_url,
                                promotion_context='アフィリエイト販売。記事への誘導を基本とする。')
    blog = _blog_prompts(article, title, product)
    # The original social_tools covers the main social channels; GBP is added here.
    snippet = re.sub(r'[#*`>\[\]]', '', article).strip().replace('\n', ' ')
    gbp = {
        'post': f'【PR】{title}\n{snippet[:160]}…\n詳しくはブログ記事をご確認ください。',
        'image_prompt': f'Googleビジネスプロフィール用1:1の明るい説明画像。テーマ：{title}。事実にない商品効果や口コミを描かない。文字は最小限。',
        'video_prompt': f'Googleビジネスプロフィール用の縦型9:16・約40秒の無音ナレーション動画。テーマ：{title}。字幕はタイプライター風。優しく明るいBGMを想定。PR表示を明確にし、効果を断定しない。記事にない事実を足さない。',
    }
    return {'post_id':post_id,'title':title,'product_name':product,
            'affiliate_url':affiliate_url,'blog_images':blog,
            'social_plan':plan,'gbp':gbp}


def save_bundle(bundle, root='creative_outputs'):
    dest = Path(root)/f"post_{bundle['post_id']}"
    dest.mkdir(parents=True, exist_ok=True)
    (dest/'all_prompts.json').write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
    blog = '\n\n'.join(f"## {x['purpose']} — {x['suggested_section']}\nファイル名：{x['filename']}\n{x['prompt']}" for x in bundle['blog_images'])
    (dest/'blog_images.md').write_text('# ブログ画像4枚分のChatGPT用プロンプト\n\n'+blog+'\n',encoding='utf-8')
    (dest/'social_posts.md').write_text(social_text(bundle['social_plan'])+'\n',encoding='utf-8')
    (dest/'social_image_video_prompts.md').write_text(creative_prompt_text(bundle['social_plan'])+'\n',encoding='utf-8')
    (dest/'gbp.md').write_text('# GBP投稿・画像・動画\n\n'+ '\n\n'.join(f'## {k}\n{v}' for k,v in bundle['gbp'].items())+'\n',encoding='utf-8')
    (dest/'README.md').write_text(f"# {bundle['title']}\nWordPress記事ID：{bundle['post_id']}\n\n画像・動画はこのファイルでは生成されません。ChatGPTで画像を作成し、WordPressへ手動でアップロードしてください。\n各SNSでの広告表示・投稿先の規約・記事の事実確認を行ってください。\n",encoding='utf-8')
    return dest
