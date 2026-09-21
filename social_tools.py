import json
import re


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _load_json_response(raw: str) -> dict:
    cleaned = _strip_code_fence(raw)
    candidates = [cleaned]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        candidates.append(cleaned[start : end + 1])
    for candidate in candidates:
        try:
            data = json.loads(re.sub(r",\s*([}\]])", r"\1", candidate))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("SNS構成のJSONを解析できません。", cleaned, 0)


def _validate_social_plan(data: dict) -> None:
    required = (
        "x_posts", "threads", "facebook", "line", "carousel",
        "reel", "youtube", "tiktok", "creative_prompts",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"SNS構成に必要な項目が不足しています：{', '.join(missing)}")
    if len(data.get("carousel", {}).get("slides", [])) != 9:
        raise ValueError("Instagramカルーセル構成が9枚ではありません。")
    prompts = data.get("creative_prompts", {})
    prompt_keys = (
        "x_image", "facebook_eyecatch", "threads_image", "line_image",
        "instagram_carousel", "reel_video", "youtube_thumbnail",
        "youtube_video", "tiktok_cover", "tiktok_video",
    )
    if any(key not in prompts for key in prompt_keys):
        raise ValueError("画像・動画制作用プロンプトが不足しています。")
    if len(prompts.get("instagram_carousel", [])) != 9:
        raise ValueError("Instagramカルーセル用プロンプトが9枚ではありません。")


def generate_social_plan(client, model: str, article: str, call_llm, affiliate_url: str = "") -> dict:
    prompt = f"""【完成記事からSNS投稿文・制作プロンプトを作成】
以下の完成記事だけを情報源として、媒体ごとの投稿文、動画台本、画像・動画制作用プロンプトを作成してください。

完成記事：
---
{article}
---

購入・詳細確認用アフィリエイトURL：
{affiliate_url}

共通条件：
- 記事にない価格、数値、実績、口コミ、効果、人物、研究結果を追加しない
- すべての投稿の冒頭または目立つ位置に「【PR】」を入れる
- X、Facebook、Threads、LINE、YouTube概要欄にはURLを省略せず1回入れる
- Instagram、リール、TikTokはURLに加え「プロフィールのリンクから確認」と案内する
- 同じ文章を使い回さず、媒体ごとの閲覧行動に最適化する
- ハッシュタグは文字列配列にする
- Instagramカルーセルは必ず9枚。1枚目は表紙、9枚目はまとめと行動喚起
- リールとTikTokは45〜60秒、YouTubeは3〜5分を目安にする

画像プロンプト共通条件：
- 必ず「広告・出版分野で経験豊富なプロのイラストレーターが制作する、細部まで丁寧で求心力のある商用イラスト」と明記
- 記事内容と読者の感情に合う人物、表情、仕草、背景、小物、光、配色、構図を具体的に指示
- 清潔感、信頼感、親しみやすさを備え、ひと目でテーマが伝わる魅力的なビジュアル
- 安価な素材集風、幼すぎる絵、単調な棒人間、過剰な誇張、不自然な手指、文字化けを避ける
- 実在ブランドのロゴ、著名キャラクター、特定作家の画風を使用しない
- 画像の中に、読者の目を止める短い日本語キャッチコピーを必ず入れる
- キャッチコピーは一目で読める大きな太字。補足文は短くし、スマートフォンでも読める文字サイズにする
- 文字と背景のコントラストを高くし、必要に応じて半透明帯、縁取り、影を使う
- 文字が人物の顔、手、商品、重要なイラスト要素に重ならないよう、安全余白のある構図にする
- 指定した日本語を一字一句正確に描画し、誤字、文字化け、意味不明な記号、余分な文字を入れない
- 日本語が崩れた場合は、正しい文章になるまで文字部分を修正・再生成するよう明記
- カルーセル9枚は同じ人物設定・画風・カラーパレット・文字デザインで統一しつつ、構図を変えて単調さを防ぐ
- カルーセルは各イラスト内に「大見出し」と「2〜4行の短い説明文」を直接入れる
- カルーセル1枚目は強い表紙コピー、2〜8枚目は内容がすぐ分かる見出しと説明、9枚目は行動喚起を入れる

動画プロンプト共通条件：
- 必ず「プロのイラストレーターと映像ディレクターが共同制作する、求心力のある高品質なイラスト動画」と明記
- 冒頭3秒のフック、場面ごとの構図、人物の動き、カメラワーク、テンポ、転換、光、配色を具体化
- 冒頭3秒に強い日本語キャッチコピーを画面内へ大きく表示する
- 各シーンに短い日本語テロップを直接入れ、ナレーションの要点が無音でも伝わるようにする
- テロップはスマートフォンで読める大きさ、高コントラスト、字幕用の安全余白を確保する
- 指定した日本語を一字一句正確に表示し、誤字や文字化けがあれば修正・再生成するよう明記
- 不自然な身体変形、激しい点滅、過剰な動き、ロゴ、透かし、意味不明な文字を避ける

次のJSON以外は出力しないでください：
{{
  "x_posts": [
    {{"text": "投稿文", "hashtags": ["#タグ"]}},
    {{"text": "別角度の投稿文", "hashtags": ["#タグ"]}},
    {{"text": "別角度の投稿文", "hashtags": ["#タグ"]}}
  ],
  "threads": {{"text": "投稿文", "hashtags": ["#タグ"]}},
  "facebook": {{"text": "詳しい投稿文", "hashtags": ["#タグ"]}},
  "line": {{"text": "LINE配信用文"}},
  "carousel": {{
    "caption": "Instagramキャプション",
    "hashtags": ["#タグ"],
    "slides": [{{"title": "短い見出し", "body": "80文字以内の本文"}}]
  }},
  "reel": {{
    "caption": "リールキャプション", "hashtags": ["#タグ"],
    "scenes": [{{"caption": "字幕", "narration": "読み上げ文"}}]
  }},
  "youtube": {{
    "title": "タイトル", "description": "URLを含む概要欄", "hashtags": ["#タグ"],
    "scenes": [{{"caption": "字幕", "narration": "読み上げ文"}}]
  }},
  "tiktok": {{
    "caption": "投稿文", "hashtags": ["#タグ"],
    "scenes": [{{"caption": "字幕", "narration": "読み上げ文"}}]
  }},
  "creative_prompts": {{
    "x_image": {{"size": "1200×675", "catch_copy": "画像内に入れる短いキャッチコピー", "sub_copy": "画像内に入れる短い補足", "prompt": "キャッチコピーと補足を画像内へ正確に配置する完成プロンプト"}},
    "facebook_eyecatch": {{"size": "1200×630", "catch_copy": "画像内キャッチコピー", "sub_copy": "画像内補足", "prompt": "文字入りの完成プロンプト"}},
    "threads_image": {{"size": "1080×1080", "catch_copy": "画像内キャッチコピー", "sub_copy": "画像内補足", "prompt": "文字入りの完成プロンプト"}},
    "line_image": {{"size": "1200×900", "catch_copy": "画像内キャッチコピー", "sub_copy": "画像内補足", "prompt": "文字入りの完成プロンプト"}},
    "instagram_carousel": [
      {{"slide": 1, "size": "1080×1350", "catch_copy": "イラスト内の大見出し", "body_text": "イラスト内に直接入れる2〜4行の説明文", "prompt": "指定した見出しと説明文をイラスト内へ正確に配置する、1枚単独で使える完成プロンプト"}}
    ],
    "reel_video": {{"size": "1080×1920", "duration": "45〜60秒", "catch_copy": "冒頭3秒に入れるキャッチコピー", "prompt": "全シーンに日本語テロップを直接入れる完成動画プロンプト"}},
    "youtube_thumbnail": {{"size": "1280×720", "catch_copy": "サムネイル内キャッチコピー", "sub_copy": "サムネイル内補足", "prompt": "文字入りの完成プロンプト"}},
    "youtube_video": {{"size": "1920×1080", "duration": "3〜5分", "catch_copy": "冒頭キャッチコピー", "prompt": "全シーンに日本語テロップを直接入れる完成動画プロンプト"}},
    "tiktok_cover": {{"size": "1080×1920", "catch_copy": "表紙内キャッチコピー", "sub_copy": "表紙内補足", "prompt": "文字入りの完成プロンプト"}},
    "tiktok_video": {{"size": "1080×1920", "duration": "45〜60秒", "catch_copy": "冒頭3秒に入れるキャッチコピー", "prompt": "全シーンに日本語テロップを直接入れる完成動画プロンプト"}}
  }}
}}"""
    last_error = None
    for attempt in range(2):
        retry_note = "" if not attempt else "\n前回はJSONが不完全でした。文章量を調整し、必ず最後まで有効なJSONで出力してください。"
        raw = call_llm(
            client, model, prompt + retry_note, 20_000,
            response_mime_type="application/json", temperature=0.4,
        )
        try:
            data = _load_json_response(raw)
            _validate_social_plan(data)
            return data
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
    raise ValueError(f"SNS投稿文と制作プロンプトを完成できませんでした：{last_error}")


def social_text(plan: dict) -> str:
    parts = ["X（旧Twitter）投稿案"]
    for index, post in enumerate(plan.get("x_posts", []), 1):
        parts.append(f"\n【パターン{index}】\n{post.get('text', '')}\n{' '.join(post.get('hashtags', []))}")
    for key, label in (("threads", "Threads"), ("facebook", "Facebook")):
        item = plan.get(key, {})
        parts.append(f"\n\n{label}投稿\n{item.get('text', '')}\n{' '.join(item.get('hashtags', []))}")
    parts.append(f"\n\nLINE配信文\n{plan.get('line', {}).get('text', '')}")
    carousel = plan.get("carousel", {})
    parts.append(f"\n\nInstagram投稿\n{carousel.get('caption', '')}\n{' '.join(carousel.get('hashtags', []))}")
    for key, label in (("reel", "Instagramリール"), ("youtube", "YouTube"), ("tiktok", "TikTok")):
        item = plan.get(key, {})
        parts.append(f"\n\n{label}\n{item.get('title', '')}\n{item.get('caption', item.get('description', ''))}\n{' '.join(item.get('hashtags', []))}")
    return "\n".join(parts).strip()


def creative_prompt_text(plan: dict) -> str:
    prompts = plan.get("creative_prompts", {})
    labels = (
        ("x_image", "X投稿画像"),
        ("facebook_eyecatch", "Facebookアイキャッチ"),
        ("threads_image", "Threads投稿画像"),
        ("line_image", "LINE配信用画像"),
        ("reel_video", "Instagramリール動画"),
        ("youtube_thumbnail", "YouTubeサムネイル"),
        ("youtube_video", "YouTube動画"),
        ("tiktok_cover", "TikTok表紙"),
        ("tiktok_video", "TikTok動画"),
    )
    parts = ["画像・動画制作用プロンプト"]
    for key, label in labels:
        item = prompts.get(key, {})
        parts.append(
            f"\n\n## {label}\nサイズ：{item.get('size', '')}\n"
            f"画像・動画内キャッチコピー：{item.get('catch_copy', item.get('overlay_text', ''))}\n"
            f"画像内補足：{item.get('sub_copy', '')}\n{item.get('prompt', '')}"
        )
    parts.append("\n\n## Instagramカルーセル9枚")
    for item in prompts.get("instagram_carousel", []):
        parts.append(
            f"\n\n### {item.get('slide', '')}枚目\nサイズ：{item.get('size', '')}\n"
            f"イラスト内の大見出し：{item.get('catch_copy', item.get('overlay_text', ''))}\n"
            f"イラスト内の説明文：{item.get('body_text', '')}\n{item.get('prompt', '')}"
        )
    return "\n".join(parts).strip()
