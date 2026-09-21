import json
import re


CAROUSEL_LAYOUT = "上部見出し18％・中央イラスト57％・下部説明カード25％。3領域を完全分離し、中央イラストへ文字を重ねない"
CAROUSEL_FONT = "太めの日本語ゴシック体。大見出し64〜80px、説明文36〜44px以上、行間1.25〜1.4倍、説明は最大4行"
ARTICLE_IMAGE_LAYOUT = "左側30％をテキスト専用エリア、右側70％をイラスト表示エリアとして完全分離。人物・商品・重要物へ文字や帯を重ねない"
ARTICLE_IMAGE_FONT = "太めの日本語ゴシック体。見出し56〜72px、補足30〜38px以上、行間1.25〜1.4倍、1行15〜18文字以内"

MEDIA_FILENAMES = {
    "x_image": "X_投稿画像.png",
    "facebook_eyecatch": "Facebook_アイキャッチ.png",
    "threads_image": "Threads_投稿画像.png",
    "line_image": "LINE_配信用画像.png",
    "reel_video": "Instagram_リール動画.mp4",
    "youtube_thumbnail": "YouTube_サムネイル.png",
    "youtube_video": "YouTube_動画.mp4",
    "tiktok_cover": "TikTok_表紙.png",
    "tiktok_video": "TikTok_動画.mp4",
}


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
    if not prompts.get("article_section_images"):
        raise ValueError("記事各セクション用の画像プロンプトがありません。")


def _plain_text(value: str, limit: int = 90) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value or "")
    value = re.sub(r"[*_`>#]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit]


def _safe_filename_part(value: str, limit: int = 24) -> str:
    value = _plain_text(value, limit)
    value = re.sub(r'[\\/:*?"<>|]', "", value)
    value = re.sub(r"\s+", "_", value).strip("._")
    return value or "記事セクション"


def _add_filename_instruction(item: dict, filename: str) -> dict:
    item["output_filename"] = filename
    prompt = item.get("prompt", "")
    instruction = f"完成データの推奨保存ファイル名は『{filename}』とする。"
    if instruction not in prompt:
        item["prompt"] = f"{prompt.rstrip()} {instruction}".strip()
    return item


def _article_sections(article: str) -> list[dict]:
    """Markdown本文からH2/H3と直後の要点を抽出する。"""
    sections = []
    current = None
    body = []
    for raw in article.splitlines():
        heading = re.match(r"^(#{2,3})\s+(.+)$", raw.strip())
        if heading:
            if current:
                current["summary"] = _plain_text(" ".join(body), 120)
                sections.append(current)
            current = {
                "level": "H2" if len(heading.group(1)) == 2 else "H3",
                "heading": _plain_text(heading.group(2), 36),
            }
            body = []
        elif current and raw.strip():
            body.append(raw.strip())
    if current:
        current["summary"] = _plain_text(" ".join(body), 120)
        sections.append(current)
    return sections[:30]


def _carousel_prompt(slide: dict, number: int) -> dict:
    title = _plain_text(slide.get("title", ""), 22) or ("内容を確認" if number < 9 else "詳しく確認する")
    body = _plain_text(slide.get("body", ""), 70) or "記事の要点を短く分かりやすく伝える"
    item = {
        "slide": number,
        "size": "1080×1350",
        "catch_copy": title,
        "body_text": body,
        "layout": CAROUSEL_LAYOUT,
        "font_spec": CAROUSEL_FONT,
        "prompt": (
            "キャンバスをテキスト専用エリアとイラスト表示エリアに完全分離する。"
            "広告・出版分野で経験豊富なプロのイラストレーターが制作する、細部まで丁寧で求心力のある商用イラスト。"
            f"1080×1350。{CAROUSEL_LAYOUT}。上部に『{title}』、下部カードに『{body}』を一字一句正確に入れる。"
            f"{CAROUSEL_FONT}。文字が収まらない場合はフォントを小さくせず文章を短くする。"
            "中央57％には人物・商品・背景だけを描き、文字・数字・帯・吹き出しを1ピクセルも侵入させない。"
            "清潔感、信頼感、親しみやすさのある配色と自然な表情。不自然な手指、ロゴ、透かし、文字化けを避ける。"
            "スマートフォン縮小表示で確認し、越境・誤字・読みにくさがあれば修正して再生成する。"
        ),
    }
    return _add_filename_instruction(item, f"Instagram_カルーセル_{number:02d}.png")


def _article_section_prompt(section: dict, number: int) -> dict:
    heading = section.get("heading", "記事のポイント")
    summary = section.get("summary", "このセクションの要点を視覚的に分かりやすく表現する")
    item = {
        "section": number,
        "heading_level": section.get("level", "H2"),
        "heading": heading,
        "size": "1200×675",
        "catch_copy": heading,
        "sub_copy": summary[:55],
        "layout": ARTICLE_IMAGE_LAYOUT,
        "font_spec": ARTICLE_IMAGE_FONT,
        "prompt": (
            "キャンバスをテキスト専用エリアとイラスト表示エリアの2領域へ完全分離する。"
            "広告・出版分野で経験豊富なプロのイラストレーターが制作する、細部まで丁寧で求心力のある高品質な商用イラスト。"
            f"ブログ記事の『{heading}』セクションに挿入する横長画像、1200×675。内容の要点は『{summary}』。"
            f"{ARTICLE_IMAGE_LAYOUT}。左側に見出し『{heading}』と、必要な場合のみ短い補足『{summary[:55]}』を正確に入れる。"
            f"{ARTICLE_IMAGE_FONT}。文字が収まらない場合はフォントを小さくせず補足文を短く要約する。"
            "右側にはセクション内容を一目で理解できる人物・表情・仕草・背景・小物を具体的かつ自然に描く。"
            "右側のイラスト領域には文字・数字・帯・吹き出しを一切置かず、左側の文字や装飾も1ピクセルも越境させない。"
            "清潔感、信頼感、親しみやすさのある配色と十分な余白を使い、素材集風、幼すぎる絵、不自然な手指、"
            "実在ロゴ、透かし、文字化けを避ける。スマートフォン表示で可読性と領域分離を検査し、問題があれば再生成する。"
        ),
    }
    filename = f"ブログ_{section.get('level', 'H2')}_{number:02d}_{_safe_filename_part(heading)}.png"
    return _add_filename_instruction(item, filename)


def _normalize_social_plan(data: dict, article: str) -> dict:
    """無料モデルの配列不足を補い、必ず表示可能な形へ整える。"""
    carousel = data.setdefault("carousel", {})
    slides = carousel.get("slides") if isinstance(carousel.get("slides"), list) else []
    article_sections = _article_sections(article)
    while len(slides) < 9:
        index = len(slides)
        source = article_sections[min(index, len(article_sections) - 1)] if article_sections else {}
        slides.append({
            "title": source.get("heading", "まとめ" if index == 8 else f"ポイント{index + 1}"),
            "body": source.get("summary", "記事の要点を分かりやすく確認しましょう。")[:80],
        })
    carousel["slides"] = slides[:9]

    prompts = data.setdefault("creative_prompts", {})
    for key, filename in MEDIA_FILENAMES.items():
        item = prompts.get(key)
        if isinstance(item, dict):
            _add_filename_instruction(item, filename)
    existing = prompts.get("instagram_carousel") if isinstance(prompts.get("instagram_carousel"), list) else []
    normalized = []
    for index, slide in enumerate(carousel["slides"], 1):
        fallback = _carousel_prompt(slide, index)
        supplied = existing[index - 1] if index <= len(existing) and isinstance(existing[index - 1], dict) else {}
        normalized.append({key: supplied.get(key) or value for key, value in fallback.items()})
        normalized[-1]["slide"] = index
        _add_filename_instruction(normalized[-1], f"Instagram_カルーセル_{index:02d}.png")
    prompts["instagram_carousel"] = normalized
    prompts["article_section_images"] = [
        _article_section_prompt(section, index)
        for index, section in enumerate(article_sections, 1)
    ] or [_article_section_prompt({"level": "H2", "heading": "記事のポイント", "summary": "記事の要点を分かりやすく伝える"}, 1)]
    return data


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
- すべての画像プロンプトの冒頭に「キャンバスをイラスト表示エリアとテキスト専用エリアの2領域へ完全分離する」と明記する
- 記事内容と読者の感情に合う人物、表情、仕草、背景、小物、光、配色、構図を具体的に指示
- 清潔感、信頼感、親しみやすさを備え、ひと目でテーマが伝わる魅力的なビジュアル
- 安価な素材集風、幼すぎる絵、単調な棒人間、過剰な誇張、不自然な手指、文字化けを避ける
- 実在ブランドのロゴ、著名キャラクター、特定作家の画風を使用しない
- 画像の中に、読者の目を止める短い日本語キャッチコピーを必ず入れる
- キャッチコピーは一目で読める大きな太字。補足文は短くし、スマートフォンでも読める文字サイズにする
- 文字と背景のコントラストを高くし、必要に応じて半透明帯、縁取り、影を使う
- テキストをイラストの主役に直接重ねず、最初から「文字専用エリア」と「メインイラストエリア」を分けて設計する
- 2つの領域は座標・比率・背景色で明確に区切り、互いの領域へ1ピクセルも侵入させない
- イラスト表示エリアには人物・商品・背景・装飾だけを置き、文字・数字・記号・帯・吹き出しを一切置かない
- テキスト専用エリアにはキャッチコピー・説明文・最小限の装飾だけを置き、人物・商品・重要なイラストを一切置かない
- テキスト専用エリアは独立した無地または淡いグラデーション背景とし、境界線または十分な余白でイラスト表示エリアと区別する
- メインイラストは画面全体の60〜70％を確保し、文字エリアは30〜40％以内に収める
- 人物の顔、表情、手、商品、重要な小物は文字・帯・吹き出し・装飾で一切隠さない
- 文字専用エリアには、無地または情報量の少ない淡い背景、独立したカード、上下の帯、左右のカラムを使う
- 半透明帯を人物の上に被せる構図は禁止。文字量に応じて余白を広げ、文字を無理に縮小しない
- キャッチコピーは原則8〜18文字、補足文は原則20〜45文字にまとめ、長文を画像内へ詰め込まない
- 横長画像は「文字35％＋イラスト65％」の左右分割、正方形は「上部文字25％＋中央イラスト55％＋下部補足20％」を基本にする
- 生成後に、文字・文字背景・装飾がイラスト表示エリアへ越境していないか必ず検査し、越境があれば配置を修正して再生成する

フォントと可読性の必須条件：
- 日本語は視認性の高い太めのゴシック体を使用し、細字、極細字、筆記体、装飾過多の書体、明朝体の小文字を避ける
- キャッチコピーはBold〜ExtraBold、説明文はMedium〜Boldを基本にする
- 1200×630・1200×675の横長画像：キャッチコピー56〜72px、補足文30〜38pxを下限とする
- 1080×1080の正方形画像：キャッチコピー64〜80px、補足文34〜44pxを下限とする
- 1200×900の画像：キャッチコピー64〜82px、補足文36〜46pxを下限とする
- 1080×1350のカルーセル：大見出し64〜80px、説明文36〜44pxを下限とする
- 1280×720のYouTubeサムネイル：キャッチコピー80〜110px、補足文40〜52pxを下限とする
- 1080×1920の縦型動画・表紙：冒頭コピー72〜96px、通常テロップ48〜60pxを下限とする
- 1920×1080のYouTube動画：見出し72〜96px、通常テロップ44〜56pxを下限とする
- 行間は文字サイズの1.25〜1.4倍、文字間隔は詰めすぎず、1行15〜18文字以内を基本にする
- 文字が領域に収まらない場合、フォントを小さくせず文章を短く要約する。上記の最小サイズを下回らない
- 背景とのコントラスト比を十分に確保し、白文字には濃色背景、濃色文字には明るい背景を使う
- 生成後にスマートフォン表示を想定して縮小確認し、読みにくい場合は文字を大きくして再生成する
- 指定した日本語を一字一句正確に描画し、誤字、文字化け、意味不明な記号、余分な文字を入れない
- 日本語が崩れた場合は、正しい文章になるまで文字部分を修正・再生成するよう明記
- カルーセル9枚は同じ人物設定・画風・カラーパレット・文字デザインで統一しつつ、構図を変えて単調さを防ぐ
- カルーセルは各イラスト内に「大見出し」と「2〜4行の短い説明文」を直接入れる
- カルーセル1枚目は強い表紙コピー、2〜8枚目は内容がすぐ分かる見出しと説明、9枚目は行動喚起を入れる
- カルーセル各枚は「上部見出し18％・中央メインイラスト57％・下部説明カード25％」を基本レイアウトにする
- 中央57％のメインイラスト領域には文字、帯、吹き出しを一切重ねず、主役が完全に見える状態にする
- 上部18％と下部25％をテキスト専用エリア、中央57％をイラスト表示エリアとして固定し、領域間の越境を禁止する
- 説明文が長い場合は内容を短く要約し、下部カードの中で最大4行に収める

動画プロンプト共通条件：
- 必ず「プロのイラストレーターと映像ディレクターが共同制作する、求心力のある高品質なイラスト動画」と明記
- すべての動画プロンプトの冒頭に「各フレームを映像表示エリアとテロップ専用エリアへ完全分離する」と明記する
- 冒頭3秒のフック、場面ごとの構図、人物の動き、カメラワーク、テンポ、転換、光、配色を具体化
- 冒頭3秒に強い日本語キャッチコピーを画面内へ大きく表示する
- 各シーンに短い日本語テロップを直接入れ、ナレーションの要点が無音でも伝わるようにする
- テロップはスマートフォンで読める大きさ、高コントラスト、字幕用の安全余白を確保する
- テロップは人物やメインイラストの上に重ねず、上部または下部の専用テロップ帯へ表示する
- 映像表示エリアには人物・商品・背景だけを表示し、文字・字幕・帯・吹き出しを一切侵入させない
- テロップ専用エリアには文字だけを表示し、人物の顔・手・商品・重要な映像を侵入させない
- 縦型動画は「上部コピー帯20％・中央メイン映像55％・下部テロップ帯10％・SNS操作UI用余白15％」を基本にする
- 縦型動画では右端12％と最下部15％に重要な文字や人物を置かない
- YouTube横型動画は、人物を左右どちらかに寄せ、反対側の文字専用エリアへテロップを配置する
- 1画面のテロップは原則2行以内・1行15文字前後とし、文章を詰め込まない
- 全フレームで領域境界を固定し、テロップや背景帯が映像表示エリアへ越境した場合は修正して再生成する
- 指定した日本語を一字一句正確に表示し、誤字や文字化けがあれば修正・再生成するよう明記
- 不自然な身体変形、激しい点滅、過剰な動き、ロゴ、透かし、意味不明な文字を避ける

制作プロンプトの独立性：
- creative_prompts内の各promptは、1件だけコピーしても成立する完全な指示文にする
- 各画像promptには「イラスト表示エリアとテキスト専用エリアの完全分離」「各領域の比率」「越境禁止」「主役を隠さない」を必ず繰り返して明記する
- 各画像promptには、その媒体の具体的なフォント種類・太さ・最低pxサイズ・行間・1行の文字数上限も必ず明記する
- 各動画promptには「映像表示エリアとテロップ専用エリアの完全分離」「全フレームで境界固定」「SNS操作UIの安全余白」「越境時の再生成」を必ず繰り返して明記する
- 各動画promptには、その媒体の具体的なテロップ最低pxサイズ・太さ・最大行数・行間も必ず明記する
- 「上記と同じ」「共通条件に従う」など、単独では意味が通じない省略表現を使わない

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
    "x_image": {{"size": "1200×675", "catch_copy": "画像内に入れる短いキャッチコピー", "sub_copy": "画像内に入れる短い補足", "layout": "文字とメインイラストを重ねない具体的な配置", "font_spec": "太めゴシック。見出し56〜72px、補足30〜38px以上など", "prompt": "レイアウトとフォント指定をすべて含む完成プロンプト"}},
    "facebook_eyecatch": {{"size": "1200×630", "catch_copy": "画像内キャッチコピー", "sub_copy": "画像内補足", "layout": "文字35％＋イラスト65％などの具体的配置", "font_spec": "太めゴシック。見出し56〜72px、補足30〜38px以上など", "prompt": "レイアウトとフォント指定をすべて含む完成プロンプト"}},
    "threads_image": {{"size": "1080×1080", "catch_copy": "画像内キャッチコピー", "sub_copy": "画像内補足", "layout": "上部文字・中央イラスト・下部補足の具体的配置", "font_spec": "太めゴシック。見出し64〜80px、補足34〜44px以上など", "prompt": "レイアウトとフォント指定をすべて含む完成プロンプト"}},
    "line_image": {{"size": "1200×900", "catch_copy": "画像内キャッチコピー", "sub_copy": "画像内補足", "layout": "文字とイラストを分離する具体的配置", "font_spec": "太めゴシック。見出し64〜82px、補足36〜46px以上など", "prompt": "レイアウトとフォント指定をすべて含む完成プロンプト"}},
    "instagram_carousel": [
      {{"slide": 1, "size": "1080×1350", "catch_copy": "イラスト内の大見出し", "body_text": "イラスト内に直接入れる2〜4行の説明文", "layout": "上部見出し18％・中央イラスト57％・下部説明カード25％。中央イラストへ文字を重ねない", "font_spec": "太めゴシック。大見出し64〜80px、説明36〜44px以上、行間1.25〜1.4倍", "prompt": "完全分離レイアウトとフォント指定を含む1枚単独で使える完成プロンプト"}}
    ],
    "reel_video": {{"size": "1080×1920", "duration": "45〜60秒", "catch_copy": "冒頭3秒に入れるキャッチコピー", "layout": "上部コピー帯20％・中央映像55％・下部テロップ帯10％・UI余白15％", "font_spec": "太めゴシック。冒頭72〜96px、通常テロップ48〜60px以上、最大2行", "prompt": "完全分離レイアウトとフォント指定を含む完成動画プロンプト"}},
    "youtube_thumbnail": {{"size": "1280×720", "catch_copy": "サムネイル内キャッチコピー", "sub_copy": "サムネイル内補足", "layout": "文字35％＋メインイラスト65％の左右分割", "font_spec": "太めゴシック。見出し80〜110px、補足40〜52px以上", "prompt": "完全分離レイアウトとフォント指定を含む完成プロンプト"}},
    "youtube_video": {{"size": "1920×1080", "duration": "3〜5分", "catch_copy": "冒頭キャッチコピー", "layout": "人物と文字を左右に分離し、字幕は下部専用帯", "font_spec": "太めゴシック。見出し72〜96px、通常テロップ44〜56px以上、最大2行", "prompt": "完全分離レイアウトとフォント指定を含む完成動画プロンプト"}},
    "tiktok_cover": {{"size": "1080×1920", "catch_copy": "表紙内キャッチコピー", "sub_copy": "表紙内補足", "layout": "上部文字20％・中央イラスト60％・下部補足5％・UI余白15％", "font_spec": "太めゴシック。見出し72〜96px、補足48〜60px以上", "prompt": "完全分離レイアウトとフォント指定を含む完成プロンプト"}},
    "tiktok_video": {{"size": "1080×1920", "duration": "45〜60秒", "catch_copy": "冒頭3秒に入れるキャッチコピー", "layout": "上部コピー帯20％・中央映像55％・下部テロップ帯10％・UI余白15％", "font_spec": "太めゴシック。冒頭72〜96px、通常テロップ48〜60px以上、最大2行", "prompt": "完全分離レイアウトとフォント指定を含む完成動画プロンプト"}}
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
            data = _normalize_social_plan(data, article)
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
            f"推奨保存ファイル名：{item.get('output_filename', '')}\n"
            f"画像・動画内キャッチコピー：{item.get('catch_copy', item.get('overlay_text', ''))}\n"
            f"画像内補足：{item.get('sub_copy', '')}\n"
            f"レイアウト：{item.get('layout', '')}\n"
            f"フォント指定：{item.get('font_spec', '')}\n{item.get('prompt', '')}"
        )
    parts.append("\n\n## Instagramカルーセル9枚")
    for item in prompts.get("instagram_carousel", []):
        parts.append(
            f"\n\n### {item.get('slide', '')}枚目\nサイズ：{item.get('size', '')}\n"
            f"推奨保存ファイル名：{item.get('output_filename', '')}\n"
            f"イラスト内の大見出し：{item.get('catch_copy', item.get('overlay_text', ''))}\n"
            f"イラスト内の説明文：{item.get('body_text', '')}\n"
            f"レイアウト：{item.get('layout', '')}\n"
            f"フォント指定：{item.get('font_spec', '')}\n{item.get('prompt', '')}"
        )
    parts.append("\n\n## ブログ記事の各セクション用イラスト")
    for item in prompts.get("article_section_images", []):
        parts.append(
            f"\n\n### セクション{item.get('section', '')}｜{item.get('heading_level', '')}：{item.get('heading', '')}\n"
            f"サイズ：{item.get('size', '')}\n推奨保存ファイル名：{item.get('output_filename', '')}\n"
            f"画像内キャッチコピー：{item.get('catch_copy', '')}\n"
            f"画像内補足：{item.get('sub_copy', '')}\nレイアウト：{item.get('layout', '')}\n"
            f"フォント指定：{item.get('font_spec', '')}\n{item.get('prompt', '')}"
        )
    return "\n".join(parts).strip()
