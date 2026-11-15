
"""Generate reusable creative briefs from the actual saved affiliate article."""

import json
import re
from pathlib import Path

from google import genai
from google.genai import types
from social_tools import generate_social_plan, social_text, creative_prompt_text


HEALTH_SAFETY = (
    '健康・美容関連の商品について、診断・治療・予防・改善の効果を断定しない。'
    '検査サービスは医療機関での診断や検査の代わりになると表現しない。'
    '感度・精度・対象疾患・料金・送料などの数値は、確認できる情報のみ使用する。'
    '架空の口コミ、体験談、利用者、医師の推薦、認証、比較結果を創作しない。'
    '広告表記を明確にし、不安を過度にあおらない。'
)


def _gemini_call(client, model, prompt, max_tokens, **kwargs):
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=kwargs.get('temperature', 0.35),
            response_mime_type=kwargs.get('response_mime_type')
        )
    )

    if not response.text:
        raise ValueError('Gemini returned an empty creative plan')

    return response.text


def _blog_prompts(article, title, product):
    heads = re.findall(r'^#{2,3}\s+(.+)$', article, re.M)

    subjects = [title] + (
        heads[:3] + ['商品の特徴', '選び方', '注意点']
    )[:3]

    items = []

    for i, subject in enumerate(subjects):
        items.append({
            'filename': f'blog_{i:02d}.png',
            'purpose': 'アイキャッチ' if i == 0 else f'本文画像{i}',
            'suggested_section': '記事冒頭' if i == 0 else subject,
            'prompt': (
                f'日本のWebメディア向け高品質な横長16:9画像。'
                f'商品名「{product}」。テーマ「{subject}」。'
                '読者に分かりやすい自然な日本人の生活場面、'
                '明るい自然光、清潔感、正確な人体と手指、'
                '文字を置ける余白。'
                '記事にない効果・価格・体験談・'
                '商品パッケージ・認証マークを創作しない。'
                '商品現物の再現は、正規の参考写真がない場合は行わない。'
                '文字なし、透かしなし、実在企業ロゴなし。'
                + HEALTH_SAFETY
            )
        })

    return items


def _clean_article_snippet(article, title, max_chars=145):
    """Create a readable GBP excerpt without duplicated PR/title lines."""

    lines = article.splitlines()
    cleaned = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        # Remove markdown headings, formatting and links.
        line = re.sub(r'^#{1,6}\s*', '', line)
        line = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', line)
        line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        line = re.sub(r'[*`>_]', '', line)
        line = re.sub(r'<[^>]+>', '', line)
        line = re.sub(r'\s+', ' ', line).strip()

        if not line:
            continue

        # Avoid repeated title and advertising disclosure.
        if line == title:
            continue

        if re.match(
            r'^(?:※\s*)?(?:本記事には|この記事には).*'
            r'アフィリエイト広告',
            line
        ):
            continue

        if re.match(
            r'^(?:【PR】|PR\s*[:：]|広告\s*[:：])',
            line,
            re.I
        ):
            continue

        # Skip headings and short fragments.
        if len(line) < 25:
            continue

        cleaned.append(line)

        if len(' '.join(cleaned)) >= max_chars:
            break

    snippet = re.sub(r'\s+', ' ', ' '.join(cleaned)).strip()

    if not snippet:
        return '商品の特徴や利用前に確認したいポイントを記事で紹介しています。'

    snippet = snippet[:max_chars].rstrip('、。・ ')

    return snippet + '。'


def _gbp_video_prompt(title, product):
    """Produce a timed 45-second GBP video brief."""

    return (
        'Googleビジネスプロフィール用の縦型9:16動画。'
        '総尺45秒。ナレーションなし。'
        '優しく明るいBGM、タイプライター風字幕。'
        '重要な文字は画面中央の安全領域に配置する。'
        '最初から最後まで広告であることが分かるようPR表示を入れる。'
        f'商品名：{product}。テーマ：{title}。\n\n'

        '【シーン構成】\n'
        '0〜5秒：読者の疑問を紹介する導入（5秒）。\n'
        '5〜13秒：商品・サービスの概要（8秒）。\n'
        '13〜23秒：記事で確認できる特徴や手順（10秒）。\n'
        '23〜33秒：利用前の注意点・確認事項（10秒）。\n'
        '33〜40秒：記事で詳しく解説している内容を紹介（7秒）。\n'
        '40〜45秒：ブログ記事への案内・CTA（5秒）。\n\n'

        '【制作上の注意】\n'
        '上記の各シーンの秒数を守り、合計45秒にする。'
        '字幕は読みやすい長さにする。'
        '記事にない価格・効果・口コミ・商品画像を創作しない。'
        '検査結果だけで病気を診断できると誤解させない。'
        + HEALTH_SAFETY
    )


def build_bundle(
    article,
    title,
    product,
    post_id,
    affiliate_url,
    api_key,
    model
):
    client = genai.Client(api_key=api_key)

    # Preserve all existing social channels and creative output.
    plan = generate_social_plan(
        client,
        model,
        article,
        _gemini_call,
        affiliate_url=affiliate_url,
        promotion_context=(
            'アフィリエイト販売。記事への誘導を基本とする。'
            '広告表示を明確にする。'
            + HEALTH_SAFETY
        )
    )

    blog = _blog_prompts(article, title, product)

    snippet = _clean_article_snippet(article, title)

    gbp = {
        'post': (
            f'【PR】{title}\n\n'
            f'{snippet}\n\n'
            '詳しくはブログ記事をご確認ください。'
        ),
        'image_prompt': (
            'Googleビジネスプロフィール用1:1の明るい説明画像。'
            f'テーマ：{title}。商品名：{product}。'
            '文字は最小限にし、PR表示を明確にする。'
            '事実にない商品効果や口コミを描かない。'
            + HEALTH_SAFETY
        ),
        'video_prompt': _gbp_video_prompt(title, product)
    }

    return {
        'post_id': post_id,
        'title': title,
        'product_name': product,
        'affiliate_url': affiliate_url,
        'blog_images': blog,
        'social_plan': plan,
        'gbp': gbp
    }


def save_bundle(bundle, root='creative_outputs'):
    dest = Path(root) / f"post_{bundle['post_id']}"
    dest.mkdir(parents=True, exist_ok=True)

    (dest / 'all_prompts.json').write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    blog = '\n\n'.join(
        f"## {x['purpose']} — {x['suggested_section']}\n"
        f"ファイル名：{x['filename']}\n"
        f"{x['prompt']}"
        for x in bundle['blog_images']
    )

    (dest / 'blog_images.md').write_text(
        '# ブログ画像4枚分のChatGPT用プロンプト\n\n'
        + blog + '\n',
        encoding='utf-8'
    )

    (dest / 'social_posts.md').write_text(
        social_text(bundle['social_plan']) + '\n',
        encoding='utf-8'
    )

    (dest / 'social_image_video_prompts.md').write_text(
        creative_prompt_text(bundle['social_plan']) + '\n',
        encoding='utf-8'
    )

    (dest / 'gbp.md').write_text(
        '# GBP投稿・画像・動画\n\n'
        + '\n\n'.join(
            f'## {k}\n{v}'
            for k, v in bundle['gbp'].items()
        )
        + '\n',
        encoding='utf-8'
    )

    (dest / 'README.md').write_text(
        f"# {bundle['title']}\n"
        f"WordPress記事ID：{bundle['post_id']}\n\n"
        '画像・動画はこのファイルでは生成されません。'
        'ChatGPTで画像を作成し、WordPressへ手動でアップロードしてください。\n'
        '各SNSでの広告表示・投稿先の規約・'
        '記事の事実確認を行ってください。\n',
        encoding='utf-8'
    )

    return dest
