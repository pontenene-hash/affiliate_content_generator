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
- 日本語文字は画像AIに描かせず「文字なし・指定位置に文字用の余白」と指示し、overlay_textを別に出す
- カルーセル9枚は同じ人物設定・画風・カラーパレットで統一しつつ、構図を変えて単調さを防ぐ

動画プロンプト共通条件：
- 必ず「プロのイラストレーターと映像ディレクターが共同制作する、求心力のある高品質なイラスト動画」と明記
- 冒頭3秒のフック、場面ごとの構図、人物の動き、カメラワーク、テンポ、転換、光、配色を具体化
- 画面内の文字は後入れ前提とし、字幕用の安全余白を確保
- 不自然な身体変形、激しい点滅、過剰な動き、ロゴ、透かし、文字化けを避ける

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
    "x_image": {{"size": "1200×675", "overlay_text": "後入れ文字", "prompt": "完成された詳細プロンプト"}},
    "facebook_eyecatch": {{"size": "1200×630", "overlay_text": "後入れ文字", "prompt": "完成された詳細プロンプト"}},
    "threads_image": {{"size": "1080×1080", "overlay_text": "後入れ文字", "prompt": "完成された詳細プロンプト"}},
    "line_image": {{"size": "1200×900", "overlay_text": "後入れ文字", "prompt": "完成された詳細プロンプト"}},
    "instagram_carousel": [
      {{"slide": 1, "size": "1080×1350", "overlay_text": "後入れ文字", "prompt": "1枚単独で使える完成された詳細プロンプト"}}
    ],
    "reel_video": {{"size": "1080×1920", "duration": "45〜60秒", "prompt": "全シーンを含む完成された動画生成プロンプト"}},
    "youtube_thumbnail": {{"size": "1280×720", "overlay_text": "後入れ文字", "prompt": "完成された詳細プロンプト"}},
    "youtube_video": {{"size": "1920×1080", "duration": "3〜5分", "prompt": "全シーンを含む完成された動画生成プロンプト"}},
    "tiktok_cover": {{"size": "1080×1920", "overlay_text": "後入れ文字", "prompt": "完成された詳細プロンプト"}},
    "tiktok_video": {{"size": "1080×1920", "duration": "45〜60秒", "prompt": "全シーンを含む完成された動画生成プロンプト"}}
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
            f"後入れ文字：{item.get('overlay_text', '')}\n{item.get('prompt', '')}"
        )
    parts.append("\n\n## Instagramカルーセル9枚")
    for item in prompts.get("instagram_carousel", []):
        parts.append(
            f"\n\n### {item.get('slide', '')}枚目\nサイズ：{item.get('size', '')}\n"
            f"後入れ文字：{item.get('overlay_text', '')}\n{item.get('prompt', '')}"
        )
    return "\n".join(parts).strip()
