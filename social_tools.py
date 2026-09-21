import base64
import io
import json
import math
import re
import subprocess
import tempfile
import wave
import zipfile
from pathlib import Path
from typing import Callable

import imageio_ffmpeg
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps


TTS_MODEL = "gemini-3.1-flash-tts-preview"
AI_IMAGE_MODEL = "black-forest-labs/flux.1-schnell"
AI_IMAGE_ENDPOINT = "https://gen.pollinations.ai/v1/images/generations"
SAMPLE_RATE = 24_000
MAX_AI_ILLUSTRATIONS = 8


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _load_json_response(raw: str) -> dict:
    cleaned = _strip_code_fence(raw)
    candidates = [cleaned]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        candidates.append(cleaned[start : end + 1])
    for candidate in candidates:
        normalized = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            data = json.loads(normalized)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("SNS構成のJSONを解析できません。", cleaned, 0)


def _validate_social_plan(data: dict) -> None:
    required = ("x_posts", "threads", "facebook", "line", "gbp", "carousel", "reel", "youtube", "tiktok")
    missing = [key for key in required if key not in data]
    if missing:
        raise ValueError(f"SNS構成に必要な項目が不足しています：{', '.join(missing)}")
    if len(data.get("carousel", {}).get("slides", [])) != 9:
        raise ValueError("カルーセル構成が9枚ではありません。")
    for key in ("reel", "youtube", "tiktok"):
        if not data.get(key, {}).get("scenes"):
            raise ValueError(f"{key}の動画構成がありません。")


def generate_social_plan(client, model: str, article: str, call_llm, affiliate_url: str = "") -> dict:
    prompt = f"""【完成記事からSNS展開素材を作成】
以下の完成記事だけを情報源として、各SNS向けコンテンツを作成してください。

完成記事：
---
{article}
---

購入・詳細確認に使用するアフィリエイトURL：
{affiliate_url}

厳格な条件：
- 記事にない数値、実績、料金、資格、口コミ、効果、人物、店舗情報、研究結果を追加しない
- 医療・健康情報を断定しない
- すべての投稿の冒頭または目立つ位置に「【PR】」を入れる
- X、Facebook、Threads、LINE、YouTube概要欄にはアフィリエイトURLを省略せず1回入れる
- InstagramはURLに加えて「プロフィールのリンクから確認」と案内する
- リールとTikTokのcaptionにもURLを入れ、動画内CTAでは「プロフィールのリンクを確認」と案内する
- 同じ文章の使い回しを避け、媒体ごとに最適化する
- ハッシュタグは文字列配列にする
- カルーセルは必ず9枚。1枚目は表紙、9枚目はまとめ・行動喚起
- リールとTikTokは45〜60秒程度の日本語ナレーション
- YouTubeは3〜5分程度の日本語ナレーション
- 動画のcaptionは画面に表示する短文、narrationは読み上げる自然な文章
- visualは内容を最もよく表すイラスト種別を、次から1つだけ選ぶ：relax、pain、treatment、exercise、sleep、nutrition、beauty、work、smartphone、checklist、location、conversation、recovery、learning
- JSONを途中で省略しない。すべての括弧と引用符を必ず閉じる
- 次のJSON以外は一切出力しない

JSON形式：
{{
  "x_posts": [
    {{"text": "投稿文", "hashtags": ["#タグ"]}},
    {{"text": "別角度の投稿文", "hashtags": ["#タグ"]}},
    {{"text": "別角度の投稿文", "hashtags": ["#タグ"]}}
  ],
  "x_image": {{"title": "X投稿画像の見出し", "body": "60文字以内の説明", "visual": "イラスト種別"}},
  "threads": {{
    "text": "少し長めの投稿文",
    "hashtags": ["#タグ"],
    "image_title": "Threads画像の見出し",
    "image_body": "60文字以内の説明",
    "visual": "イラスト種別"
  }},
  "facebook": {{
    "text": "信頼感のある詳しい投稿文",
    "hashtags": ["#タグ"],
    "image_title": "画像に表示する短い見出し",
    "image_body": "画像に表示する60文字以内の説明",
    "visual": "イラスト種別"
  }},
  "line": {{
    "text": "親しみやすく簡潔なLINE配信用文。PR表記とURLを含める"
  }},
  "gbp": {{
    "text": "Googleビジネスプロフィール最新情報の投稿文",
    "image_title": "GBP画像の短い見出し",
    "image_body": "80文字以内の説明",
    "visual": "イラスト種別"
  }},
  "carousel": {{
    "caption": "Instagramキャプション",
    "hashtags": ["#タグ"],
    "slides": [{{"title": "短い見出し", "body": "80文字以内の本文", "visual": "イラスト種別"}}]
  }},
  "reel": {{
    "caption": "Instagramリールキャプション",
    "hashtags": ["#タグ"],
    "cover_title": "リール表紙の短い見出し",
    "cover_body": "短い補足",
    "scenes": [{{"caption": "画面表示20文字以内", "narration": "読み上げ文", "visual": "ナレーションを表すイラスト種別"}}]
  }},
  "youtube": {{
    "title": "YouTubeタイトル",
    "description": "概要欄",
    "hashtags": ["#タグ"],
    "thumbnail_title": "サムネイルの短い見出し",
    "thumbnail_body": "短い補足",
    "scenes": [{{"caption": "画面見出し", "narration": "読み上げ文", "visual": "ナレーションを表すイラスト種別"}}]
  }},
  "tiktok": {{
    "caption": "TikTokキャプション",
    "hashtags": ["#タグ"],
    "cover_title": "TikTok表紙の短い見出し",
    "cover_body": "短い補足",
    "scenes": [{{"caption": "画面表示20文字以内", "narration": "読み上げ文", "visual": "ナレーションを表すイラスト種別"}}]
  }}
}}"""
    last_error: Exception | None = None
    for attempt in range(2):
        retry_note = ""
        if attempt:
            retry_note = (
                "\n\n【重要】前回はJSONが不完全でした。文章量を調整してもよいので、"
                "必ず最後まで閉じた有効なJSONを出力してください。"
            )
        raw = call_llm(
            client,
            model,
            prompt + retry_note,
            16_000,
            response_mime_type="application/json",
            temperature=0.3,
        )
        try:
            data = _load_json_response(raw)
            _validate_social_plan(data)
            return data
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
    if isinstance(last_error, json.JSONDecodeError):
        raise last_error
    raise ValueError(f"SNS構成を完成できませんでした：{last_error}")


def _font_path() -> str:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansJP-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise RuntimeError("日本語フォントが見つかりません。packages.txtの設定を確認してください。")


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_font_path(), size=size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text.replace("\n", " "):
        candidate = current + char
        if current and draw.textlength(candidate, font=font) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _gradient(width: int, height: int, top=(239, 250, 247), bottom=(211, 238, 231)) -> Image.Image:
    ratio = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
    top_color = np.array(top, dtype=np.float32)[None, None, :]
    bottom_color = np.array(bottom, dtype=np.float32)[None, None, :]
    rows = top_color * (1 - ratio) + bottom_color * ratio
    pixels = np.repeat(rows.astype(np.uint8), width, axis=1)
    return Image.fromarray(pixels, mode="RGB")


def _infer_visual(text: str, hint: str = "") -> str:
    allowed = {
        "relax", "pain", "treatment", "exercise", "sleep", "nutrition", "beauty",
        "work", "smartphone", "checklist", "location", "conversation", "recovery", "learning",
    }
    normalized_hint = hint.strip().lower()
    if normalized_hint in allowed:
        return normalized_hint
    rules = (
        ("pain", ("痛", "こり", "肩", "腰", "膝", "首", "不調", "しびれ")),
        ("treatment", ("施術", "整体", "鍼灸", "治療", "マッサージ", "ケア")),
        ("exercise", ("運動", "筋力", "トレーニング", "ストレッチ", "歩行", "リハビリ")),
        ("sleep", ("睡眠", "眠", "夜", "休息")),
        ("nutrition", ("食事", "栄養", "食品", "野菜", "ビタミン", "水分")),
        ("beauty", ("美容", "肌", "フェイシャル", "毛穴", "シミ", "美し")),
        ("work", ("仕事", "デスク", "パソコン", "会社", "在宅")),
        ("smartphone", ("スマホ", "携帯", "SNS", "画面")),
        ("location", ("店舗", "院", "サロン", "アクセス", "予約", "相談", "来店")),
        ("checklist", ("ポイント", "手順", "確認", "まとめ", "チェック", "方法")),
        ("conversation", ("家族", "会話", "一緒", "お客様", "専門家")),
        ("recovery", ("改善", "回復", "元気", "変化", "未来", "予防")),
        ("learning", ("知識", "原因", "解説", "理由", "仕組み")),
        ("relax", ("リラックス", "アロマ", "癒", "自律神経", "深呼吸")),
    )
    for visual, words in rules:
        if any(word in text for word in words):
            return visual
    return "learning"


def _illustration_sources(plan: dict) -> dict[str, str]:
    """内容の近い場面を同じ絵として再利用し、無料クレジットを節約する。"""
    sources: dict[str, str] = {}

    def add(visual: str, text: str) -> None:
        key = _infer_visual(text, visual)
        cleaned = re.sub(r"\s+", " ", text).strip()[:420]
        if cleaned and key not in sources and len(sources) < MAX_AI_ILLUSTRATIONS:
            sources[key] = cleaned

    for slide in plan.get("carousel", {}).get("slides", []):
        add(slide.get("visual", ""), f"{slide.get('title', '')}。{slide.get('body', '')}")
    for platform in ("reel", "youtube", "tiktok"):
        for scene in plan.get(platform, {}).get("scenes", []):
            add(
                scene.get("visual", ""),
                f"{scene.get('caption', '')}。{scene.get('narration', '')}",
            )
    for item, title_key, body_key in (
        (plan.get("x_image", {}), "title", "body"),
        (plan.get("threads", {}), "image_title", "image_body"),
        (plan.get("facebook", {}), "image_title", "image_body"),
        (plan.get("gbp", {}), "image_title", "image_body"),
    ):
        add(item.get("visual", ""), f"{item.get(title_key, '')}。{item.get(body_key, '')}")
    return sources


def _professional_prompt(scene_text: str) -> str:
    return f"""Create a premium editorial illustration for a Japanese wellness and lifestyle social media post.
Scene meaning: {scene_text}
Art direction: highly polished professional digital illustration, warm human emotion, refined facial expressions and natural body language, carefully drawn hands, clothing, environment and small relevant objects, sophisticated soft color palette of teal, sage green, warm coral and cream, gentle natural light, subtle depth and texture, clean contemporary Japanese magazine aesthetic, trustworthy and welcoming, balanced composition with the main subject centered, suitable for an adult audience.
Important: illustration only. No text, no letters, no captions, no logos, no watermark, no brand marks, no UI, no border. Avoid graphic medical imagery, distorted anatomy, extra fingers, duplicated people and clutter."""


def _generate_ai_illustration(api_key: str, scene_text: str) -> Image.Image:
    response = requests.post(
        AI_IMAGE_ENDPOINT,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "prompt": _professional_prompt(scene_text),
            "model": AI_IMAGE_MODEL,
            "size": "1024x1024",
            "quality": "medium",
            "response_format": "b64_json",
            "safe": "true",
        },
        timeout=180,
    )
    if response.status_code == 402:
        raise RuntimeError("Pollinationsの無料クレジット残高が不足しています。")
    if response.status_code == 401:
        raise RuntimeError("Pollinations APIキーが正しくありません。")
    response.raise_for_status()
    payload = response.json()
    data = (payload.get("data") or [{}])[0]
    encoded = data.get("b64_json")
    if not encoded:
        raise RuntimeError("高品質イラストの画像データを取得できませんでした。")
    image = Image.open(io.BytesIO(base64.b64decode(encoded)))
    image.load()
    return image.convert("RGB")


def build_professional_illustrations(
    plan: dict,
    api_key: str,
    progress: Callable[[str], None],
) -> dict[str, Image.Image]:
    sources = _illustration_sources(plan)
    illustrations: dict[str, Image.Image] = {}
    errors: list[str] = []
    for index, (visual, scene_text) in enumerate(sources.items(), start=1):
        progress(f"プロ品質のAIイラストを生成しています…（{index}/{len(sources)}）")
        try:
            illustrations[visual] = _generate_ai_illustration(api_key, scene_text)
        except Exception as exc:
            errors.append(str(exc))
    if not illustrations:
        detail = errors[0] if errors else "画像生成サービスから応答がありませんでした。"
        raise RuntimeError(f"高品質AIイラストを生成できませんでした：{detail}")
    if errors:
        progress("一部の絵は取得できなかったため、内容別の標準イラストで補完します。")
    return illustrations


def _draw_person(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float, pose: str = "stand") -> None:
    skin = (244, 190, 154, 255)
    hair = (65, 61, 58, 255)
    shirt = (71, 153, 139, 255)
    pants = (70, 91, 111, 255)
    line = max(5, int(10 * scale))
    r = int(55 * scale)
    draw.ellipse((x - r, y - r, x + r, y + r), fill=skin, outline=hair, width=line)
    draw.pieslice((x - r, y - r, x + r, y + r), 175, 355, fill=hair)
    shoulder_y = y + int(70 * scale)
    hip_y = y + int(240 * scale)
    draw.rounded_rectangle(
        (x - int(75 * scale), shoulder_y, x + int(75 * scale), hip_y),
        radius=int(32 * scale), fill=shirt,
    )
    if pose == "pain":
        draw.line((x - int(50 * scale), shoulder_y + int(35 * scale), x + int(35 * scale), y + int(85 * scale)), fill=skin, width=line * 2)
        draw.line((x + int(55 * scale), shoulder_y + int(30 * scale), x + int(95 * scale), shoulder_y + int(120 * scale)), fill=skin, width=line * 2)
    elif pose == "cheer":
        draw.line((x - int(55 * scale), shoulder_y + int(45 * scale), x - int(130 * scale), y - int(10 * scale)), fill=skin, width=line * 2)
        draw.line((x + int(55 * scale), shoulder_y + int(45 * scale), x + int(130 * scale), y - int(10 * scale)), fill=skin, width=line * 2)
    else:
        draw.line((x - int(60 * scale), shoulder_y + int(35 * scale), x - int(95 * scale), hip_y - int(25 * scale)), fill=skin, width=line * 2)
        draw.line((x + int(60 * scale), shoulder_y + int(35 * scale), x + int(95 * scale), hip_y - int(25 * scale)), fill=skin, width=line * 2)
    draw.line((x - int(35 * scale), hip_y, x - int(60 * scale), hip_y + int(130 * scale)), fill=pants, width=line * 3)
    draw.line((x + int(35 * scale), hip_y, x + int(60 * scale), hip_y + int(130 * scale)), fill=pants, width=line * 3)


def _draw_scene(visual: str, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGBA", (1000, 620), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    accent = (42, 125, 110, 255)
    pale = (218, 242, 235, 255)
    coral = (236, 126, 106, 255)
    gold = (244, 190, 76, 255)
    dark = (42, 61, 59, 255)
    blue = (102, 157, 190, 255)
    draw.ellipse((145, 45, 855, 595), fill=(238, 249, 246, 255))

    if visual == "pain":
        _draw_person(draw, 500, 170, 0.92, "pain")
        draw.ellipse((515, 205, 655, 345), outline=coral, width=18)
        for angle in range(0, 360, 45):
            x1 = 585 + int(math.cos(math.radians(angle)) * 85)
            y1 = 275 + int(math.sin(math.radians(angle)) * 85)
            x2 = 585 + int(math.cos(math.radians(angle)) * 120)
            y2 = 275 + int(math.sin(math.radians(angle)) * 120)
            draw.line((x1, y1, x2, y2), fill=coral, width=10)
    elif visual == "treatment":
        draw.rounded_rectangle((255, 380, 785, 470), radius=28, fill=accent)
        draw.line((320, 470, 290, 560), fill=dark, width=18)
        draw.line((720, 470, 750, 560), fill=dark, width=18)
        draw.ellipse((350, 300, 450, 400), fill=(244, 190, 154, 255), outline=dark, width=8)
        draw.rounded_rectangle((430, 325, 720, 410), radius=35, fill=blue)
        _draw_person(draw, 720, 140, 0.62)
        draw.line((680, 300, 560, 350), fill=(244, 190, 154, 255), width=18)
        draw.line((760, 300, 625, 360), fill=(244, 190, 154, 255), width=18)
    elif visual == "exercise":
        _draw_person(draw, 500, 150, 0.92, "cheer")
        draw.line((265, 130, 735, 130), fill=dark, width=18)
        draw.rounded_rectangle((220, 80, 285, 180), radius=15, fill=coral)
        draw.rounded_rectangle((715, 80, 780, 180), radius=15, fill=coral)
        draw.arc((120, 350, 330, 560), 200, 340, fill=gold, width=18)
        draw.arc((670, 350, 880, 560), 200, 340, fill=gold, width=18)
    elif visual == "sleep":
        draw.rounded_rectangle((220, 385, 790, 500), radius=30, fill=blue)
        draw.rectangle((260, 285, 320, 500), fill=dark)
        draw.ellipse((300, 325, 410, 430), fill=(244, 190, 154, 255), outline=dark, width=7)
        draw.rounded_rectangle((395, 350, 725, 445), radius=42, fill=pale)
        draw.pieslice((570, 65, 790, 285), 55, 290, fill=gold)
        for x, y in ((230, 120), (410, 90), (825, 190)):
            draw.regular_polygon((x, y, 18), 4, rotation=45, fill=gold)
    elif visual == "nutrition":
        draw.ellipse((260, 140, 740, 590), fill=(255, 255, 255, 255), outline=accent, width=18)
        draw.ellipse((350, 245, 500, 405), fill=coral)
        draw.ellipse((490, 220, 650, 390), fill=gold)
        draw.polygon(((430, 245), (470, 125), (520, 255)), fill=accent)
        draw.arc((190, 80, 430, 300), 210, 330, fill=accent, width=16)
        draw.arc((570, 70, 820, 320), 210, 330, fill=accent, width=16)
    elif visual == "beauty":
        draw.ellipse((345, 105, 655, 500), fill=(244, 190, 154, 255), outline=dark, width=10)
        draw.arc((400, 245, 485, 300), 190, 350, fill=dark, width=10)
        draw.arc((515, 245, 600, 300), 190, 350, fill=dark, width=10)
        draw.arc((450, 330, 555, 410), 10, 170, fill=coral, width=10)
        for x, y in ((260, 160), (730, 170), (260, 410), (735, 400)):
            draw.regular_polygon((x, y, 34), 4, rotation=45, fill=gold)
    elif visual == "work":
        _draw_person(draw, 390, 175, 0.65)
        draw.rounded_rectangle((455, 255, 760, 455), radius=18, fill=blue, outline=dark, width=10)
        draw.rectangle((535, 455, 680, 490), fill=dark)
        draw.line((220, 500, 820, 500), fill=accent, width=24)
        draw.rounded_rectangle((205, 105, 355, 220), radius=18, fill=(255, 255, 255, 255), outline=accent, width=8)
        draw.line((240, 150, 320, 150), fill=accent, width=10)
        draw.line((240, 185, 300, 185), fill=accent, width=10)
    elif visual == "smartphone":
        draw.rounded_rectangle((365, 70, 635, 550), radius=45, fill=dark)
        draw.rounded_rectangle((390, 115, 610, 480), radius=20, fill=(255, 255, 255, 255))
        draw.ellipse((475, 500, 525, 550), fill=pale)
        for x, y, color in ((445, 190, coral), (545, 190, gold), (445, 300, blue), (545, 300, accent)):
            draw.rounded_rectangle((x - 40, y - 40, x + 40, y + 40), radius=18, fill=color)
        for x, y in ((245, 200), (755, 210), (250, 390), (750, 410)):
            draw.ellipse((x - 35, y - 35, x + 35, y + 35), fill=gold)
    elif visual == "checklist":
        draw.rounded_rectangle((285, 80, 715, 560), radius=35, fill=(255, 255, 255, 255), outline=accent, width=16)
        draw.rounded_rectangle((405, 45, 595, 125), radius=24, fill=accent)
        for y in (190, 300, 410):
            draw.rounded_rectangle((345, y, 415, y + 70), radius=12, outline=coral, width=10)
            draw.line((360, y + 35, 382, y + 55, 410, y + 12), fill=accent, width=10)
            draw.line((455, y + 22, 650, y + 22), fill=dark, width=12)
            draw.line((455, y + 55, 600, y + 55), fill=blue, width=9)
    elif visual == "location":
        draw.rounded_rectangle((255, 240, 745, 545), radius=25, fill=(255, 255, 255, 255), outline=accent, width=14)
        draw.polygon(((215, 260), (500, 75), (785, 260)), fill=accent)
        draw.rectangle((425, 355, 575, 545), fill=blue)
        draw.rectangle((300, 315, 395, 410), fill=pale)
        draw.rectangle((605, 315, 700, 410), fill=pale)
        draw.ellipse((700, 65, 875, 240), fill=coral)
        draw.polygon(((730, 210), (790, 325), (850, 210)), fill=coral)
        draw.ellipse((755, 105, 820, 170), fill=(255, 255, 255, 255))
    elif visual == "conversation":
        _draw_person(draw, 330, 200, 0.65)
        _draw_person(draw, 670, 200, 0.65)
        draw.rounded_rectangle((190, 65, 440, 185), radius=35, fill=(255, 255, 255, 255), outline=accent, width=9)
        draw.polygon(((370, 175), (420, 225), (405, 170)), fill=accent)
        draw.rounded_rectangle((560, 65, 810, 185), radius=35, fill=(255, 255, 255, 255), outline=blue, width=9)
        draw.polygon(((595, 175), (570, 225), (625, 170)), fill=blue)
    elif visual == "recovery":
        _draw_person(draw, 500, 180, 0.82, "cheer")
        draw.arc((185, 40, 815, 585), 205, 335, fill=accent, width=22)
        draw.polygon(((765, 85), (855, 95), (810, 175)), fill=accent)
        draw.ellipse((735, 230, 865, 360), fill=gold)
        for angle in range(0, 360, 45):
            x1 = 800 + int(math.cos(math.radians(angle)) * 85)
            y1 = 295 + int(math.sin(math.radians(angle)) * 85)
            x2 = 800 + int(math.cos(math.radians(angle)) * 115)
            y2 = 295 + int(math.sin(math.radians(angle)) * 115)
            draw.line((x1, y1, x2, y2), fill=gold, width=10)
    elif visual == "relax":
        _draw_person(draw, 610, 175, 0.72)
        draw.arc((455, 225, 765, 485), 15, 165, fill=accent, width=12)
        draw.rounded_rectangle((220, 290, 385, 535), radius=30, fill=blue)
        draw.rectangle((265, 225, 340, 305), fill=dark)
        draw.arc((215, 85, 345, 280), 250, 70, fill=coral, width=16)
        draw.arc((300, 70, 425, 280), 245, 70, fill=gold, width=16)
        for x, y in ((145, 300), (165, 410), (410, 150)):
            draw.ellipse((x, y, x + 70, y + 120), fill=pale, outline=accent, width=7)
    else:
        draw.polygon(((275, 165), (485, 230), (485, 530), (275, 460)), fill=(255, 255, 255, 255), outline=accent)
        draw.polygon(((725, 165), (515, 230), (515, 530), (725, 460)), fill=(255, 255, 255, 255), outline=accent)
        draw.ellipse((405, 25, 595, 215), fill=gold, outline=dark, width=10)
        draw.rectangle((475, 195, 525, 260), fill=dark)
        for y in (285, 340, 395):
            draw.line((315, y, 445, y + 28), fill=blue, width=10)
            draw.line((555, y + 28, 685, y), fill=blue, width=10)

    return canvas.resize((max(1, width), max(1, height)), Image.Resampling.LANCZOS)


def render_card(
    title: str,
    body: str,
    width: int,
    height: int,
    index: int,
    total: int,
    brand_name: str,
    illustration_hint: str = "",
    semantic_text: str = "",
    professional_illustration: Image.Image | None = None,
) -> Image.Image:
    image = _gradient(width, height)
    draw = ImageDraw.Draw(image)
    margin = int(width * 0.07)
    accent = (42, 125, 110)
    dark = (31, 55, 50)
    white = (255, 255, 255)
    draw.rounded_rectangle(
        (margin, margin, width - margin, height - margin),
        radius=max(28, width // 28),
        fill=(255, 255, 255),
        outline=(184, 220, 211),
        width=max(3, width // 300),
    )
    draw.rounded_rectangle(
        (margin, margin, width - margin, margin + int(height * 0.035)),
        radius=18,
        fill=accent,
    )
    title_font = _font(max(34, min(width // 17, height // 8)))
    body_font = _font(max(24, min(width // 29, height // 18)))
    small_font = _font(max(22, width // 42))
    usable_width = width - margin * 4
    title_lines = _wrap(draw, title, title_font, usable_width)[:3]
    title_y = margin + int(height * 0.075)
    for line in title_lines:
        box = draw.textbbox((0, 0), line, font=title_font)
        line_width = box[2] - box[0]
        draw.text(((width - line_width) / 2, title_y), line, fill=accent, font=title_font)
        title_y += int(title_font.size * 1.35)

    divider_y = title_y + int(height * 0.025)
    draw.line((margin * 2, divider_y, width - margin * 2, divider_y), fill=(207, 226, 221), width=3)
    footer_y = height - int(margin * 2.0)
    illustration_top = divider_y + int(height * 0.018)
    illustration_height = int(height * (0.34 if body else 0.50))
    illustration_bottom_limit = footer_y - (int(height * 0.14) if body else int(height * 0.02))
    illustration_height = max(90, min(illustration_height, illustration_bottom_limit - illustration_top))
    if professional_illustration is not None:
        scene = ImageOps.fit(
            professional_illustration.convert("RGB"),
            (usable_width, illustration_height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.45),
        )
        corner_radius = max(18, width // 45)
        mask = Image.new("L", scene.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            (0, 0, scene.width - 1, scene.height - 1),
            radius=corner_radius,
            fill=255,
        )
        image.paste(scene, (margin * 2, illustration_top), mask)
        draw.rounded_rectangle(
            (
                margin * 2,
                illustration_top,
                margin * 2 + usable_width,
                illustration_top + illustration_height,
            ),
            radius=corner_radius,
            outline=(184, 220, 211),
            width=max(2, width // 360),
        )
    else:
        scene = _draw_scene(
            _infer_visual(f"{title} {body} {semantic_text}", illustration_hint),
            usable_width,
            illustration_height,
        )
        image.paste(scene, (margin * 2, illustration_top), scene)

    body_lines = _wrap(draw, body, body_font, usable_width)[:4]
    body_y = illustration_top + illustration_height + int(height * 0.015)
    for line in body_lines:
        box = draw.textbbox((0, 0), line, font=body_font)
        line_width = box[2] - box[0]
        draw.text(((width - line_width) / 2, body_y), line, fill=dark, font=body_font)
        body_y += int(body_font.size * 1.55)

    if total == 1:
        footer = brand_name
    else:
        footer = f"{brand_name}   {index}/{total}" if brand_name else f"{index}/{total}"
    draw.text((margin * 1.6, height - margin * 1.65), footer, fill=(86, 116, 109), font=small_font)
    if total > 1:
        draw.ellipse(
            (width - margin * 2.1, height - margin * 1.9, width - margin * 1.45, height - margin * 1.25),
            fill=accent,
        )
        draw.text(
            (width - margin * 1.94, height - margin * 1.86),
            "›",
            fill=white,
            font=small_font,
        )
    return image


def _image_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def build_carousel(
    slides: list[dict],
    brand_name: str,
    illustrations: dict[str, Image.Image] | None = None,
) -> tuple[list[bytes], bytes]:
    images = []
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for index, slide in enumerate(slides, start=1):
            visual = _infer_visual(
                f"{slide.get('title', '')} {slide.get('body', '')}",
                slide.get("visual", ""),
            )
            image = render_card(
                slide.get("title", ""),
                slide.get("body", ""),
                1080,
                1080,
                index,
                len(slides),
                brand_name,
                visual,
                professional_illustration=(illustrations or {}).get(visual),
            )
            data = _image_bytes(image)
            images.append(data)
            archive.writestr(f"carousel_{index:02d}.png", data)
    return images, zip_buffer.getvalue()


def build_facebook_image(
    facebook: dict,
    brand_name: str,
    illustrations: dict[str, Image.Image] | None = None,
) -> bytes:
    visual = _infer_visual(
        f"{facebook.get('image_title', '')} {facebook.get('image_body', '')}",
        facebook.get("visual", ""),
    )
    image = render_card(
        facebook.get("image_title", ""),
        facebook.get("image_body", ""),
        1200,
        630,
        1,
        1,
        brand_name,
        visual,
        professional_illustration=(illustrations or {}).get(visual),
    )
    return _image_bytes(image)


def build_platform_image(
    title: str,
    body: str,
    width: int,
    height: int,
    brand_name: str,
    illustration_hint: str = "",
    illustrations: dict[str, Image.Image] | None = None,
) -> bytes:
    visual = _infer_visual(f"{title} {body}", illustration_hint)
    return _image_bytes(
        render_card(
            title,
            body,
            width,
            height,
            1,
            1,
            brand_name,
            visual,
            professional_illustration=(illustrations or {}).get(visual),
        )
    )


def _tts_pcm(client, narration: str, voice: str) -> bytes:
    prompt = (
        "次の日本語原稿を、聞き取りやすく、やさしく信頼感のある自然な速度で、"
        "文章を追加・省略せずに読み上げてください。\n\n" + narration
    )
    interaction = client.interactions.create(
        model=TTS_MODEL,
        input=prompt,
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": voice}]},
    )
    audio = interaction.output_audio
    if not audio or not audio.data:
        raise RuntimeError("ナレーション音声を生成できませんでした。")
    # google-genai 2.xでは音声データがBase64文字列として返ります。
    # 将来のSDK差異でbytesが返る場合も、そのまま受け取れるようにします。
    if isinstance(audio.data, bytes):
        return audio.data
    return base64.b64decode(audio.data)


def _write_wave(path: Path, pcm: bytes) -> float:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)
    return len(pcm) / (SAMPLE_RATE * 2)


def build_voice_demo(client, voice: str) -> bytes:
    sample = "こんにちは。記事の内容を、やさしく分かりやすくお届けします。"
    pcm = _tts_pcm(client, sample, voice)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)
    return buffer.getvalue()


def _write_bgm(path: Path, duration: float) -> None:
    frame_count = max(1, int(duration * SAMPLE_RATE))
    t = np.arange(frame_count, dtype=np.float64) / SAMPLE_RATE
    chord = (
        np.sin(2 * math.pi * 220.00 * t)
        + 0.7 * np.sin(2 * math.pi * 277.18 * t)
        + 0.55 * np.sin(2 * math.pi * 329.63 * t)
    ) / 2.25
    pulse = 0.65 + 0.35 * np.sin(2 * math.pi * 0.18 * t)
    fade = np.minimum(np.clip(t / 1.5, 0, 1), np.clip((duration - t) / 1.5, 0, 1))
    samples = np.int16(np.clip(chord * pulse * fade * 0.18, -1, 1) * 32767)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(samples.tobytes())


def _safe_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def build_video(
    client,
    scenes: list[dict],
    width: int,
    height: int,
    brand_name: str,
    voice: str,
    output_name: str,
    illustrations: dict[str, Image.Image] | None = None,
) -> bytes:
    narration_parts = [scene.get("narration", "").strip() for scene in scenes]
    narration = "\n".join(part for part in narration_parts if part)
    if not narration:
        raise ValueError("ナレーション原稿がありません。")
    pcm = _tts_pcm(client, narration, voice)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        narration_path = tmp_dir / "narration.wav"
        bgm_path = tmp_dir / "bgm.wav"
        output_path = tmp_dir / output_name
        duration = max(_write_wave(narration_path, pcm), len(scenes) * 2.0)
        _write_bgm(bgm_path, duration)

        weights = [max(1, len(text)) for text in narration_parts]
        weight_total = sum(weights)
        durations = [max(1.8, duration * weight / weight_total) for weight in weights]
        duration_scale = duration / sum(durations)
        durations = [value * duration_scale for value in durations]

        concat_lines = []
        for index, (scene, scene_duration) in enumerate(zip(scenes, durations), start=1):
            frame_path = tmp_dir / f"frame_{index:02d}.png"
            visual = _infer_visual(
                f"{scene.get('caption', '')} {scene.get('narration', '')}",
                scene.get("visual", ""),
            )
            image = render_card(
                scene.get("caption", ""),
                "",
                width,
                height,
                index,
                len(scenes),
                brand_name,
                visual,
                scene.get("narration", ""),
                (illustrations or {}).get(visual),
            )
            image.save(frame_path, "PNG")
            concat_lines.append(f"file '{_safe_concat_path(frame_path)}'")
            concat_lines.append(f"duration {scene_duration:.3f}")
        concat_lines.append(f"file '{_safe_concat_path(tmp_dir / f'frame_{len(scenes):02d}.png')}'")
        concat_path = tmp_dir / "frames.txt"
        concat_path.write_text("\n".join(concat_lines), encoding="utf-8")

        command = [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-i",
            str(narration_path),
            "-i",
            str(bgm_path),
            "-filter_complex",
            "[1:a]volume=1.0[a1];[2:a]volume=0.16[a2];[a1][a2]amix=inputs=2:duration=first[a]",
            "-map",
            "0:v:0",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=420)
        if completed.returncode != 0:
            raise RuntimeError(f"動画変換に失敗しました：{completed.stderr[-500:]}")
        return output_path.read_bytes()


def _social_text(plan: dict) -> str:
    parts = ["X（旧Twitter）投稿案"]
    for index, post in enumerate(plan.get("x_posts", []), start=1):
        parts.append(
            f"\n【パターン{index}】\n{post.get('text', '')}\n{' '.join(post.get('hashtags', []))}"
        )
    threads = plan.get("threads", {})
    parts.append(
        f"\n\nThreads投稿\n{threads.get('text', '')}\n{' '.join(threads.get('hashtags', []))}"
    )
    facebook = plan.get("facebook", {})
    parts.append(
        f"\n\nFacebook投稿\n{facebook.get('text', '')}\n{' '.join(facebook.get('hashtags', []))}"
    )
    line = plan.get("line", {})
    parts.append(f"\n\nLINE配信文\n{line.get('text', '')}")
    gbp = plan.get("gbp", {})
    parts.append(f"\n\nGoogleビジネスプロフィール投稿\n{gbp.get('text', '')}")
    carousel = plan.get("carousel", {})
    parts.append(
        f"\n\nInstagramカルーセル キャプション\n{carousel.get('caption', '')}\n{' '.join(carousel.get('hashtags', []))}"
    )
    for key, label in (("reel", "Instagramリール"), ("youtube", "YouTube"), ("tiktok", "TikTok")):
        item = plan.get(key, {})
        parts.append(
            f"\n\n{label}\n{item.get('title', '')}\n{item.get('caption', item.get('description', ''))}\n{' '.join(item.get('hashtags', []))}"
        )
    return "\n".join(parts).strip()


def social_text(plan: dict) -> str:
    return _social_text(plan)


def _serialize_illustrations(illustrations: dict[str, Image.Image]) -> dict[str, bytes]:
    serialized: dict[str, bytes] = {}
    for visual, image in illustrations.items():
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        serialized[visual] = buffer.getvalue()
    return serialized


def _deserialize_illustrations(serialized: dict[str, bytes] | None) -> dict[str, Image.Image]:
    illustrations: dict[str, Image.Image] = {}
    for visual, image_data in (serialized or {}).items():
        image = Image.open(io.BytesIO(image_data))
        image.load()
        illustrations[visual] = image.convert("RGB")
    return illustrations


def build_image_package(
    plan: dict,
    brand_name: str,
    progress: Callable[[str], None],
    pollinations_api_key: str = "",
    use_professional_ai: bool = False,
    save_asset: Callable[[str, object], None] | None = None,
) -> dict[str, object]:
    """画像を作成し、完成した素材をその都度コールバックへ渡す。"""
    assets: dict[str, object] = {}

    def save(key: str, value: object) -> None:
        assets[key] = value
        if save_asset:
            save_asset(key, value)

    illustrations: dict[str, Image.Image] = {}
    if use_professional_ai:
        if not pollinations_api_key:
            raise ValueError("高品質AIイラスト用のPollinations APIキーを設定してください。")
        illustrations = build_professional_illustrations(
            plan,
            pollinations_api_key,
            progress,
        )
        save("_illustration_pngs", _serialize_illustrations(illustrations))

    progress("9枚のカルーセル画像を作成しています…")
    carousel_images, carousel_zip = build_carousel(
        plan["carousel"]["slides"], brand_name, illustrations
    )
    save("carousel_images", carousel_images)
    save("carousel_zip", carousel_zip)

    progress("Facebook投稿画像を作成しています…")
    facebook_image = build_facebook_image(plan.get("facebook", {}), brand_name, illustrations)
    save("facebook_image", facebook_image)

    progress("各SNSの投稿画像・表紙・サムネイルを作成しています…")
    x_image_data = plan.get("x_image", {})
    x_image = build_platform_image(
        x_image_data.get("title", ""), x_image_data.get("body", ""), 1200, 675, brand_name,
        x_image_data.get("visual", ""), illustrations,
    )
    save("x_image", x_image)
    threads = plan.get("threads", {})
    threads_image = build_platform_image(
        threads.get("image_title", ""), threads.get("image_body", ""), 1080, 1080, brand_name,
        threads.get("visual", ""), illustrations,
    )
    save("threads_image", threads_image)
    gbp = plan.get("gbp", {})
    gbp_image = build_platform_image(
        gbp.get("image_title", ""), gbp.get("image_body", ""), 1200, 900, brand_name,
        gbp.get("visual", ""), illustrations,
    )
    save("gbp_image", gbp_image)
    reel = plan.get("reel", {})
    reel_visual = (reel.get("scenes") or [{}])[0].get("visual", "")
    reel_cover = build_platform_image(
        reel.get("cover_title", ""), reel.get("cover_body", ""), 1080, 1920, brand_name,
        reel_visual, illustrations,
    )
    save("reel_cover", reel_cover)
    youtube = plan.get("youtube", {})
    youtube_visual = (youtube.get("scenes") or [{}])[0].get("visual", "")
    youtube_thumbnail = build_platform_image(
        youtube.get("thumbnail_title", ""),
        youtube.get("thumbnail_body", ""),
        1280,
        720,
        brand_name,
        youtube_visual,
        illustrations,
    )
    save("youtube_thumbnail", youtube_thumbnail)
    tiktok = plan.get("tiktok", {})
    tiktok_visual = (tiktok.get("scenes") or [{}])[0].get("visual", "")
    tiktok_cover = build_platform_image(
        tiktok.get("cover_title", ""), tiktok.get("cover_body", ""), 1080, 1920, brand_name,
        tiktok_visual, illustrations,
    )
    save("tiktok_cover", tiktok_cover)
    return assets


VIDEO_SETTINGS = {
    "reel": ("reel_video", 1080, 1920, "instagram_reel.mp4", "Instagramリール"),
    "youtube": ("youtube_video", 1920, 1080, "youtube_video.mp4", "YouTube"),
    "tiktok": ("tiktok_video", 1080, 1920, "tiktok_video.mp4", "TikTok"),
}


def build_single_video(
    client,
    plan: dict,
    platform: str,
    brand_name: str,
    voice: str,
    progress: Callable[[str], None],
    illustration_pngs: dict[str, bytes] | None = None,
) -> tuple[str, bytes]:
    """指定した1媒体だけの音声とMP4を作成する。"""
    if platform not in VIDEO_SETTINGS:
        raise ValueError("対応していない動画形式です。")
    asset_key, width, height, filename, label = VIDEO_SETTINGS[platform]
    progress(f"{label}動画のナレーションとMP4を作成しています…")
    video = build_video(
        client,
        plan[platform]["scenes"],
        width,
        height,
        brand_name,
        voice,
        filename,
        _deserialize_illustrations(illustration_pngs),
    )
    return asset_key, video


def package_available_media(plan: dict, media: dict[str, object]) -> bytes:
    """現在完成している素材だけをZIPにまとめる。"""
    text_data = _social_text(plan).encode("utf-8-sig")
    json_data = json.dumps(plan, ensure_ascii=False, indent=2).encode("utf-8")
    image_files = {
        "facebook_image": "images/facebook_post_1200x630.png",
        "x_image": "images/x_post_1200x675.png",
        "threads_image": "images/threads_post_1080x1080.png",
        "gbp_image": "images/gbp_post_1200x900.png",
        "reel_cover": "images/instagram_reel_cover_1080x1920.png",
        "youtube_thumbnail": "images/youtube_thumbnail_1280x720.png",
        "tiktok_cover": "images/tiktok_cover_1080x1920.png",
    }
    video_files = {
        "reel_video": "videos/instagram_reel.mp4",
        "youtube_video": "videos/youtube_video.mp4",
        "tiktok_video": "videos/tiktok_video.mp4",
    }

    all_buffer = io.BytesIO()
    with zipfile.ZipFile(all_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("social_posts.txt", text_data)
        archive.writestr("social_plan.json", json_data)
        for index, image_data in enumerate(media.get("carousel_images", []), start=1):
            archive.writestr(f"carousel/carousel_{index:02d}.png", image_data)
        for key, filename in image_files.items():
            if media.get(key):
                archive.writestr(filename, media[key])
        for key, filename in video_files.items():
            if media.get(key):
                archive.writestr(filename, media[key])
    return all_buffer.getvalue()


def build_media_package(
    client,
    plan: dict,
    brand_name: str,
    voice: str,
    progress: Callable[[str], None],
    pollinations_api_key: str = "",
    use_professional_ai: bool = False,
) -> dict[str, object]:
    """従来互換用。一括生成でも完成素材を1つの辞書へ集約する。"""
    media = build_image_package(
        plan,
        brand_name,
        progress,
        pollinations_api_key,
        use_professional_ai,
    )
    for platform in VIDEO_SETTINGS:
        key, video = build_single_video(
            client,
            plan,
            platform,
            brand_name,
            voice,
            progress,
            media.get("_illustration_pngs"),
        )
        media[key] = video
    media["all_zip"] = package_available_media(plan, media)
    media["social_text"] = _social_text(plan).encode("utf-8-sig")
    return media
