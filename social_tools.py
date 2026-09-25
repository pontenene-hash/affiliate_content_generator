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
    "reel_cover": "Instagram_リール表紙.png",
    "reel_video": "Instagram_リール動画.mp4",
    "youtube_thumbnail": "YouTube_サムネイル.png",
    "youtube_video": "YouTube_動画.mp4",
    "tiktok_cover": "TikTok_表紙.png",
    "tiktok_video": "TikTok_動画.mp4",
}

IMAGE_QUALITY = (
    "あなたは読者心理と購買行動を熟知したプロのマーケティングコンサルタントであり、"
    "広告・出版分野で経験豊富なプロのイラストレーターです。マーケティング視点で情報の優先順位と視線誘導を設計し、"
    "細部まで丁寧で求心力のある高品質な商用イラストを制作する。"
    "読者の感情が伝わる自然な表情と仕草、正確な人体、丁寧な手指、内容に合う背景と小物、柔らかな自然光、"
    "奥行きと質感、清潔感・信頼感・親しみやすさを備えた現代的な日本の雑誌広告風。"
    "安価な素材集風、幼すぎる絵、棒人間、平面的で単調な構図、不自然な手指、過剰な医療表現、"
    "実在ロゴ、著名キャラクター、特定作家の画風、透かし、意味不明な文字を使用しない。"
)

TEXT_LAYOUT_RULES = (
    "文字を描画する前に全文を日本語として読み、文節・語句・固有名詞・熟語の境界を確認して改行位置を確定する。"
    "確定した各行を分割禁止の1つのテキストオブジェクトとして配置し、制作ツールによる自動折り返しを無効にする。"
    "単語、固有名詞、商品名、施設名、熟語、数字と単位の途中では絶対に改行しない。"
    "助詞、句読点、長音、閉じ括弧を行頭に置かず、1文字だけの行や極端に短い行を作らない。"
    "改行後は各行の見た目の横幅を揃え、中央揃えを基本に、行間・字間・左右余白を再調整する。"
    "上段だけ長い、下段だけ短い、片側へ寄る構成を避け、テキストブロック全体の重心を中央に整える。"
)

PROFESSIONAL_REVIEW = (
    "納品前に、プロのイラストレーター兼アートディレクターとして100％表示とスマートフォン縮小表示の両方で最終検品する。"
    "誤字、文字化け、単語途中の改行、行頭禁則、各行の長さ、中央揃え、行間、余白、視覚的重心、"
    "文字と人物の重なり、領域越境、人物の顔・手指・身体、小物、背景、色、コントラスト、媒体サイズを確認する。"
    "1項目でも不合格なら内部で修正して再検品し、すべて合格した完成版だけを出力する。"
    "ラフ、途中経過、未検品版、複数候補は出力しない。"
)

MARKETING_REVIEW = (
    "さらに納品前に、プロのマーケティングコンサルタントとして最終確認する。"
    "想定読者の悩みとの一致、最初の3秒の訴求力、内容理解のしやすさ、媒体特性、視聴維持、商品の魅力、"
    "押し売り感のない購入導線、【PR】表記、アフィリエイト案内、事実にない誇張や効果保証がないことを確認する。"
    "見出し・イラスト・説明・CTAの優先順位が明確で、読者が次に何をすべきか自然に理解できる状態にする。"
    "1項目でも不合格ならコピー、構図、順序、CTAを修正して再確認し、マーケティング上も合格した完成版だけを出力する。"
)


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


def _as_dict(value, text_key: str = "text") -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {text_key: value}
    return {}


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _hashtags(value) -> str:
    if isinstance(value, list):
        return " ".join(str(tag) for tag in value)
    return str(value or "")


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
        "instagram_carousel", "reel_cover", "reel_video", "youtube_thumbnail",
        "youtube_video", "tiktok_cover", "tiktok_video",
    )
    if any(key not in prompts for key in prompt_keys):
        raise ValueError("画像・動画制作用プロンプトが不足しています。")
    if len(prompts.get("instagram_carousel", [])) != 9:
        raise ValueError("Instagramカルーセル用プロンプトが9枚ではありません。")
    if not prompts.get("article_section_images"):
        raise ValueError("記事各セクション用の画像プロンプトがありません。")
    for key in ("reel", "youtube", "tiktok"):
        if not _as_dict(data.get(key), "caption").get("scenes"):
            raise ValueError(f"{key}の動画構成がありません。")


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
    """保存名は管理用メタデータにだけ入れ、生成プロンプト本文には混ぜない。"""
    item["output_filename"] = filename
    prompt = str(item.get("prompt", ""))
    item["prompt"] = re.sub(
        r"\s*完成データの推奨保存ファイル名は『[^』]+』とする。?",
        "",
        prompt,
    ).strip()
    return item


def _add_video_audio_instructions(item: dict, media_key: str) -> dict:
    prompt = str(item.get("prompt", "")).rstrip()
    if media_key == "youtube_video":
        font_rule = "冒頭表紙のキャッチコピー88〜112px、通常テロップ64〜80px以上"
        cta_route = "最後は『自分に合いそうな方は、概要欄のリンクから公式サイトを確認してみてください【PR】』と自然に案内する"
    else:
        font_rule = "冒頭表紙のキャッチコピー96〜120px、通常テロップ72〜88px以上"
        cta_route = "最後は『自分に合いそうな方は、プロフィールのリンクから詳しく確認してみてください【PR】』と自然に案内する"
    instructions = (
        "画面内にはInstagram、YouTube、TikTok、X、FacebookなどのSNS名、SNSロゴ、アプリアイコン、"
        "ユーザー名、保存ファイル名、拡張子、透かしを表示しない。SNS名は制作データの管理用名称にだけ使用する。"
        "動画の0.0秒から1.5〜2秒の完成した表紙シーンを必ず表示し、黒画面・空白・待機・フェードインを入れない。記事の要点が一目で伝わる短いキャッチコピーを大きく表示する。"
        "表紙シーンはテキスト専用エリアとメインイラスト領域を完全分離し、キャッチコピーで人物や商品を隠さない。"
        f"フォントは太めの日本語ゴシック体を使い、{font_rule}とする。これより小さい文字サイズの指定があれば、この指定を優先する。"
        "テロップは原則2行以内とし、句読点や意味のまとまりで自然に改行する。助詞・助動詞・句読点を行頭に置かず、"
        "単語、固有名詞、商品名、数字と単位の途中では改行しない。1行を短くし、機械的な均等改行を禁止する。"
        "動画全編に、穏やかで温かみのある成人女性の聞き取りやすい日本語ナレーションを必ず入れる。"
        "ナレーションは台本を自然な速度より少しテンポよく読み、機械的・過度に感情的な話し方を避け、発話間の無音を最大0.3秒にする。"
        "動画全編に、穏やかで明るい著作権上利用可能なインストゥルメンタルBGMを入れる。"
        "BGMはナレーションより十分小さくし、発話中は自動的に音量を下げ、声を明瞭に聞かせる。"
        "BGMは0.0秒から開始し、終了時だけ自然にフェードアウトさせる。場面転換は0.2〜0.4秒、同一静止画は3秒以内にする。"
        "ナレーション、BGM、テロップの内容とタイミングを一致させる。無音、音切れ、声がBGMに埋もれる状態は禁止し、"
        "音声が入っていない場合は必ず音声付きで再生成する。"
        "動画の最後に3〜4秒の商品案内シーンを設け、記事で確認できた事実だけを使い、商品が向く人へ押し売りにならない言葉で勧める。"
        f"{cta_route}。最後の商品案内でも、人物・商品とテキストの表示領域を完全分離する。"
    )
    if "音声が入っていない場合は必ず音声付きで再生成する" not in prompt:
        item["prompt"] = f"{prompt} {instructions}".strip()
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


def _article_title(article: str) -> str:
    for raw in article.splitlines():
        match = re.match(r"^#\s+(.+)$", raw.strip())
        if match:
            return _plain_text(match.group(1), 22)
    return "悩みを解決するヒント"


def _ensure_video_scenes(item: dict, media_key: str, article: str) -> dict:
    scenes = [_as_dict(scene, "narration") for scene in _as_list(item.get("scenes"))]
    catch_copy = _plain_text(item.get("title") or item.get("caption") or _article_title(article), 22)
    if not scenes or scenes[0].get("scene_type") != "opening_cover":
        scenes.insert(0, {
            "scene_type": "opening_cover",
            "duration": "1.5〜2秒",
            "caption": catch_copy,
            "narration": catch_copy,
            "direction": "最初の表紙。大きなキャッチコピーとメインイラストを完全分離して表示する。",
        })

    if media_key == "youtube":
        cta_caption = "公式サイトで詳しく確認"
        cta_narration = "自分に合いそうだと感じた方は、概要欄のリンクから公式サイトを確認してみてください。"
    else:
        cta_caption = "詳しくはプロフィールへ"
        cta_narration = "自分に合いそうだと感じた方は、プロフィールのリンクから詳しく確認してみてください。"
    last_text = " ".join(str(value) for value in scenes[-1].values()) if scenes else ""
    if not any(word in last_text for word in ("プロフィール", "概要欄", "公式サイト", "詳しく確認")):
        scenes.append({
            "scene_type": "affiliate_cta",
            "duration": "3〜4秒",
            "caption": f"{cta_caption}【PR】",
            "narration": cta_narration,
            "direction": "最後の商品案内。向いている人へ自然に勧め、押し売り表現は使わない。",
        })
    else:
        scenes[-1].setdefault("scene_type", "affiliate_cta")
        scenes[-1].setdefault("duration", "3〜4秒")
    item["scenes"] = scenes
    return item


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
            "句読点や意味のまとまりで自然に改行し、助詞・助動詞・句読点を行頭に置かない。"
            "単語、固有名詞、商品名、数字と単位の途中では改行せず、機械的な均等改行を禁止する。"
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
            "句読点や意味のまとまりで自然に改行し、助詞・助動詞・句読点を行頭に置かない。"
            "単語、固有名詞、商品名、数字と単位の途中では改行せず、機械的な均等改行を禁止する。"
            "右側にはセクション内容を一目で理解できる人物・表情・仕草・背景・小物を具体的かつ自然に描く。"
            "右側のイラスト領域には文字・数字・帯・吹き出しを一切置かず、左側の文字や装飾も1ピクセルも越境させない。"
            "清潔感、信頼感、親しみやすさのある配色と十分な余白を使い、素材集風、幼すぎる絵、不自然な手指、"
            "実在ロゴ、透かし、文字化けを避ける。スマートフォン表示で可読性と領域分離を検査し、問題があれば再生成する。"
        ),
    }
    filename = f"ブログ_{section.get('level', 'H2')}_{number:02d}_{_safe_filename_part(heading)}.png"
    return _add_filename_instruction(item, filename)


def _image_prompt_item(
    title: str,
    body: str,
    size: str,
    layout: str,
    font_spec: str,
    filename: str,
    scene: str = "",
) -> dict:
    title = _plain_text(title, 22) or "記事のポイント"
    body = _plain_text(body, 55)
    visual_direction = _plain_text(scene or f"{title}。{body}", 180)
    prompt = (
        "キャンバスをイラスト表示エリアとテキスト専用エリアの2領域へ完全分離する。"
        f"{IMAGE_QUALITY} 出力サイズは{size}。テーマは『{visual_direction}』。"
        f"レイアウトは{layout}。テキスト専用エリアへ見出し『{title}』"
        + (f"、補足『{body}』" if body else "")
        + "を一字一句正確に入れる。イラスト領域には人物・背景・小物だけを描き、文字・数字・帯・吹き出しを置かない。"
        "テキスト領域には人物や重要なイラストを置かず、両領域を1ピクセルも越境させない。人物の顔、手、商品、重要な小物を文字で隠さない。"
        f"フォントは{font_spec}。{TEXT_LAYOUT_RULES}"
        "補足のフォントサイズは見出しの約80％にする。文字が収まらない場合はフォントを小さくせず文章を短くする。"
        "高コントラストと十分な安全余白を確保する。"
        f"{PROFESSIONAL_REVIEW}{MARKETING_REVIEW}"
    )
    return {
        "size": size,
        "catch_copy": title,
        "sub_copy": body,
        "layout": layout,
        "font_spec": font_spec,
        "output_filename": filename,
        "prompt": prompt,
    }


def _video_prompt_item(
    plan_item: dict,
    size: str,
    duration: str,
    filename: str,
    vertical: bool,
) -> dict:
    scene_lines = []
    for index, raw_scene in enumerate(_as_list(plan_item.get("scenes")), 1):
        scene = _as_dict(raw_scene, "narration")
        heading = _plain_text(scene.get("caption", ""), 22)
        narration = _plain_text(scene.get("narration", ""), 240)
        visual = _plain_text(scene.get("visual") or scene.get("direction", ""), 120)
        scene_lines.append(
            f"シーン{index}（4〜6秒を目安）：上部見出し『{heading}』。"
            "下部補足は上部見出しを繰り返さず、ナレーションの要点を短く言い換える。"
            f"ナレーション『{narration}』。映像は『{visual or narration}』を表す人物・表情・動作・背景・小物。"
        )
    scene_script = " ".join(scene_lines)
    if vertical:
        layout = "上部コピー帯20％・中央メイン映像55％・下部テロップ帯10％・右端と最下部の操作UI用安全余白15％"
        font_spec = "太めの日本語ゴシック体。表紙メイン96〜120px、表紙サブはメインの約80％、場面見出し72〜88px、下部補足は見出しの約80％、最大2行、行間1.25〜1.4倍"
        cta = "最後の3〜4秒は【PR】を示し、商品が向く人へ自然に勧め、プロフィールのアフィリエイトリンクへ案内する"
    else:
        layout = "人物・映像と文字を左右に完全分離し、下部に独立した字幕帯を設け、重要要素を画面端から十分に離す"
        font_spec = "太めの日本語ゴシック体。表紙メイン88〜112px、表紙サブはメインの約80％、場面見出し64〜80px、下部補足は見出しの約80％、最大2行、行間1.25〜1.4倍"
        cta = "最後の3〜4秒は【PR】を示し、商品が向く人へ自然に勧め、概要欄のアフィリエイトリンクへ案内する"
    prompt = (
        "各フレームを映像表示エリアとテロップ専用エリアへ完全分離する。"
        "あなたは読者心理、購買行動、視聴維持を熟知したプロのマーケティングコンサルタントであり、"
        "プロのイラストレーター兼映像ディレクターである。情報の優先順位と視線誘導を設計した高品質なイラスト動画を制作する。"
        f"出力は{size}、長さは{duration}。{layout}。全フレームで境界を固定し、文字・帯・字幕を映像領域へ越境させない。"
        "再生開始0.0秒の最初のフレームから、完成した表紙イラストと短いキャッチコピーを明るく鮮明に表示する。"
        "冒頭の黒画面、空白画面、無地背景、読み込み待ち、暗転、黒からのフェードインを一切入れない。"
        "表紙は1.5〜2秒間表示し、要点が一目で伝わった時点ですぐ本編へ進む。"
        f"{font_spec}。上部は場面見出し、下部は具体的な補足説明とし、同じ文章を上下へ重複表示しない。"
        f"すべての画面テキストは日本語にする。{TEXT_LAYOUT_RULES}"
        f"場面構成：{scene_script} "
        "動画全編のナレーションは日本語だけに統一し、外国語の発話や不自然な英語読みを混ぜない。"
        "声は穏やかで温かみのある成人女性に固定し、自然な発音と抑揚を保ちながら通常より少しテンポよく読む。"
        "不要な間、長い息継ぎ、語尾を長く伸ばす読み方を避け、ナレーション間の無音は最大0.3秒とする。"
        "ナレーション終了を待って映像を止めず、次のテロップと映像を直ちに開始する。場面転換は0.2〜0.4秒とし、静止画が3秒以上変化しない状態を作らない。"
        "明るく穏やかで前向きな、著作権上利用可能なインストゥルメンタルBGMを0.0秒から入れる。"
        "柔らかなピアノ、アコースティック、軽いパーカッションを中心にし、暗い、不安、悲しい、重い、激しい曲調は禁止する。"
        "発話中はBGMを自動的に下げ、ナレーションを常に明瞭にする。BGMは場面転換中も途切れさせず、終了時だけ自然にフェードアウトする。"
        "映像・テロップ・ナレーションを完全に同期し、0.5秒を超える無音、意味のない静止、音切れ、声がBGMに埋もれる状態を禁止する。"
        f"{cta}。Instagram、YouTube、TikTok、X、FacebookなどのSNS名、SNSロゴ、アプリアイコン、"
        "ユーザー名、保存ファイル名、拡張子、透かしを画面に表示しない。不自然な身体変形、激しい点滅、過剰な動きを避ける。"
        "検品では、上下テキストの重複、ナレーションと映像の同期、音声の有無、BGM音量、テンポも確認する。"
        f"{PROFESSIONAL_REVIEW}{MARKETING_REVIEW}"
    )
    return {
        "size": size,
        "duration": duration,
        "layout": layout,
        "font_spec": font_spec,
        "output_filename": filename,
        "prompt": prompt,
    }


def _build_creative_prompts(plan: dict, article: str) -> dict:
    x_data = _as_dict(plan.get("x_image"))
    facebook = _as_dict(plan.get("facebook"))
    threads = _as_dict(plan.get("threads"))
    line = _as_dict(plan.get("line"))
    reel = _as_dict(plan.get("reel"), "caption")
    youtube = _as_dict(plan.get("youtube"), "description")
    tiktok = _as_dict(plan.get("tiktok"), "caption")
    horizontal = "左側35％をテキスト専用、右側65％をイラスト専用とする左右分割。背景色と余白で境界を明確にする"
    square = "上部25％を見出し、中央55％をイラスト、下部20％を補足専用カードとして3領域を完全分離する"
    vertical = "上部20％を見出し、中央60％をイラスト、下部5％を補足、残り15％を操作UI用安全余白として固定する"
    prompts = {
        "x_image": _image_prompt_item(x_data.get("title", ""), x_data.get("body", ""), "1200×675", horizontal, "太めゴシック。見出し56〜72px、補足は見出しの約80％、行間1.25〜1.4倍", MEDIA_FILENAMES["x_image"], x_data.get("visual", "")),
        "facebook_eyecatch": _image_prompt_item(facebook.get("image_title", ""), facebook.get("image_body", ""), "1200×630", horizontal, "太めゴシック。見出し56〜72px、補足は見出しの約80％、行間1.25〜1.4倍", MEDIA_FILENAMES["facebook_eyecatch"], facebook.get("visual", "")),
        "threads_image": _image_prompt_item(threads.get("image_title", ""), threads.get("image_body", ""), "1080×1080", square, "太めゴシック。見出し64〜80px、補足は見出しの約80％、行間1.25〜1.4倍", MEDIA_FILENAMES["threads_image"], threads.get("visual", "")),
        "line_image": _image_prompt_item(line.get("image_title", ""), line.get("image_body", ""), "1200×900", horizontal, "太めゴシック。見出し64〜82px、補足は見出しの約80％、行間1.25〜1.4倍", MEDIA_FILENAMES["line_image"], line.get("visual", "")),
        "reel_cover": _image_prompt_item(reel.get("cover_title", ""), reel.get("cover_body", ""), "1080×1920", vertical, "太めゴシック。見出し96〜120px、補足は見出しの約80％、最大2行", MEDIA_FILENAMES["reel_cover"]),
        "youtube_thumbnail": _image_prompt_item(youtube.get("thumbnail_title", ""), youtube.get("thumbnail_body", ""), "1280×720", horizontal, "太めゴシック。見出し88〜112px、補足は見出しの約80％、最大2行", MEDIA_FILENAMES["youtube_thumbnail"]),
        "tiktok_cover": _image_prompt_item(tiktok.get("cover_title", ""), tiktok.get("cover_body", ""), "1080×1920", vertical, "太めゴシック。見出し96〜120px、補足は見出しの約80％、最大2行", MEDIA_FILENAMES["tiktok_cover"]),
        "reel_video": _video_prompt_item(reel, "1080×1920", "40〜45秒", MEDIA_FILENAMES["reel_video"], True),
        "youtube_video": _video_prompt_item(youtube, "1920×1080", "40〜45秒", MEDIA_FILENAMES["youtube_video"], False),
        "tiktok_video": _video_prompt_item(tiktok, "1080×1920", "40〜45秒", MEDIA_FILENAMES["tiktok_video"], True),
    }
    prompts["instagram_carousel"] = []
    carousel = _as_dict(plan.get("carousel"), "caption")
    for index, raw_slide in enumerate(_as_list(carousel.get("slides"))[:9], 1):
        slide = _as_dict(raw_slide, "body")
        item = _image_prompt_item(
            slide.get("title", ""), slide.get("body", ""), "1080×1350",
            "上部18％を見出し、中央57％をイラスト、下部25％を説明カードとして固定し、3領域を完全分離する",
            "太めゴシック。大見出し64〜80px、説明は大見出しの約80％、最大4行、行間1.25〜1.4倍",
            f"Instagram_カルーセル_{index:02d}.png", slide.get("visual", ""),
        )
        item.update({"slide": index, "body_text": item.get("sub_copy", "")})
        prompts["instagram_carousel"].append(item)
    sections = _article_sections(article) or [{
        "level": "H2", "heading": "記事のポイント",
        "summary": _plain_text(article, 140) or "記事の要点を視覚的に分かりやすく表現する",
    }]
    prompts["article_section_images"] = []
    for index, section in enumerate(sections, 1):
        item = _image_prompt_item(
            section.get("heading", ""), section.get("summary", ""), "1200×675", horizontal,
            "太めゴシック。見出し56〜72px、補足は見出しの約80％、1行15〜18文字以内、行間1.25〜1.4倍",
            f"ブログ_{section.get('level', 'H2')}_{index:02d}_{_safe_filename_part(section.get('heading', ''))}.png",
            f"記事の{section.get('level', 'H2')}『{section.get('heading', '')}』。要点：{section.get('summary', '')}",
        )
        item.update({"section": index, "heading_level": section.get("level", "H2"), "heading": section.get("heading", "")})
        prompts["article_section_images"].append(item)
    return prompts


def _normalize_social_plan(data: dict, article: str) -> dict:
    """無料モデルの配列不足を補い、必ず表示可能な形へ整える。"""
    if not isinstance(data, dict):
        raise ValueError("SNS構成が正しい形式ではありません。")

    data["x_posts"] = [_as_dict(item) for item in _as_list(data.get("x_posts"))]
    data["x_image"] = _as_dict(data.get("x_image"))
    for key in ("threads", "facebook", "line"):
        data[key] = _as_dict(data.get(key))
    for key in ("reel", "youtube", "tiktok"):
        item = _as_dict(data.get(key), "caption")
        item["scenes"] = [_as_dict(scene, "narration") for scene in _as_list(item.get("scenes"))]
        data[key] = _ensure_video_scenes(item, key, article)

    carousel = _as_dict(data.get("carousel"), "caption")
    data["carousel"] = carousel
    slides = [_as_dict(slide, "body") for slide in _as_list(carousel.get("slides"))]
    article_sections = _article_sections(article)
    while len(slides) < 9:
        index = len(slides)
        source = article_sections[min(index, len(article_sections) - 1)] if article_sections else {}
        slides.append({
            "title": source.get("heading", "まとめ" if index == 8 else f"ポイント{index + 1}"),
            "body": source.get("summary", "記事の要点を分かりやすく確認しましょう。")[:80],
        })
    carousel["slides"] = slides[:9]
    last_slide = carousel["slides"][8]
    last_text = f"{last_slide.get('title', '')} {last_slide.get('body', '')}"
    if not any(word in last_text for word in ("プロフィール", "公式サイト", "アフィリエイトリンク", "購入")):
        last_slide["title"] = "自分に合うか確認しよう"
        last_slide["body"] = "商品が自分の悩みや希望に合いそうな方は、プロフィールのリンクから公式サイトを確認してみてください。【PR】"

    data["creative_prompts"] = _build_creative_prompts(data, article)
    return data


def _generate_social_plan_legacy(client, model: str, article: str, call_llm, affiliate_url: str = "") -> dict:
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
- Instagramカルーセルは必ず9枚。1枚目は表紙、9枚目は商品が向く人に自然に勧め、プロフィールのリンクへ案内する行動喚起
- リール、TikTok、YouTubeはいずれも40〜45秒を目安にする
- 動画台本の最初は0.0秒から表示する1.5〜2秒の表紙シーン、最後は3〜4秒の商品案内と購入導線のシーンにする
- 記事で確認できた事実だけを使い、商品が向く人へ押し売りにならない自然な言葉で購入検討を促す

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
- 日本語は句読点または意味のまとまりで自然に改行し、助詞・助動詞・句読点を行頭に置かない
- 単語、固有名詞、商品名、数字と単位の途中で改行せず、文字数だけを基準にした機械的な均等改行をしない
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
- 1080×1920の縦型動画・表紙：冒頭コピー96〜120px、通常テロップ72〜88pxを下限とする
- 1920×1080のYouTube動画：見出し88〜112px、通常テロップ64〜80pxを下限とする
- 行間は文字サイズの1.25〜1.4倍、文字間隔は詰めすぎず、1行15〜18文字以内を基本にする
- 文字が領域に収まらない場合、フォントを小さくせず文章を短く要約する。上記の最小サイズを下回らない
- 背景とのコントラスト比を十分に確保し、白文字には濃色背景、濃色文字には明るい背景を使う
- 生成後にスマートフォン表示を想定して縮小確認し、読みにくい場合は文字を大きくして再生成する
- 指定した日本語を一字一句正確に描画し、誤字、文字化け、意味不明な記号、余分な文字を入れない
- 日本語が崩れた場合は、正しい文章になるまで文字部分を修正・再生成するよう明記
- カルーセル9枚は同じ人物設定・画風・カラーパレット・文字デザインで統一しつつ、構図を変えて単調さを防ぐ
- カルーセルは各イラスト内に「大見出し」と「2〜4行の短い説明文」を直接入れる
- カルーセル1枚目は強い表紙コピー、2〜8枚目は内容がすぐ分かる見出しと説明、9枚目は商品が向く人に自然に勧め「プロフィールのリンクから公式サイトを確認」と案内する
- カルーセル各枚は「上部見出し18％・中央メインイラスト57％・下部説明カード25％」を基本レイアウトにする
- 中央57％のメインイラスト領域には文字、帯、吹き出しを一切重ねず、主役が完全に見える状態にする
- 上部18％と下部25％をテキスト専用エリア、中央57％をイラスト表示エリアとして固定し、領域間の越境を禁止する
- 説明文が長い場合は内容を短く要約し、下部カードの中で最大4行に収める

動画プロンプト共通条件：
- 必ず「プロのイラストレーターと映像ディレクターが共同制作する、求心力のある高品質なイラスト動画」と明記
- すべての動画プロンプトの冒頭に「各フレームを映像表示エリアとテロップ専用エリアへ完全分離する」と明記する
- Instagram、YouTube、TikTokなどのSNS名、SNSロゴ、アプリアイコン、ユーザー名、保存ファイル名、拡張子を動画内に表示しない
- SNS名は管理用の推奨保存ファイル名だけに使い、映像、背景、テロップ、字幕、エンドカードには入れない
- 最初に1.5〜2秒の独立した表紙シーンを必ず設け、0.0秒から完成した表紙を表示し、黒画面・空白・待機・フェードインを入れない。場面ごとの構図、人物の動き、カメラワーク、テンポ、転換、光、配色を具体化
- 表紙シーンに短く強い日本語キャッチコピーを大きく表示し、人物・商品と重ならない専用エリアへ配置する
- 各シーンに短い日本語テロップを直接入れ、ナレーションの要点が無音でも伝わるようにする
- テロップはスマートフォンで読める大きさ、高コントラスト、字幕用の安全余白を確保する
- テロップは人物やメインイラストの上に重ねず、上部または下部の専用テロップ帯へ表示する
- 映像表示エリアには人物・商品・背景だけを表示し、文字・字幕・帯・吹き出しを一切侵入させない
- テロップ専用エリアには文字だけを表示し、人物の顔・手・商品・重要な映像を侵入させない
- 縦型動画は「上部コピー帯20％・中央メイン映像55％・下部テロップ帯10％・SNS操作UI用余白15％」を基本にする
- 縦型動画では右端12％と最下部15％に重要な文字や人物を置かない
- YouTube横型動画は、人物を左右どちらかに寄せ、反対側の文字専用エリアへテロップを配置する
- 1画面のテロップは原則2行以内・1行15文字前後とし、文章を詰め込まない
- テロップは句読点または意味のまとまりで自然に改行し、助詞・助動詞・句読点を行頭に置かない
- 単語、固有名詞、商品名、数字と単位の途中で改行せず、機械的な均等改行を禁止する
- 全フレームで領域境界を固定し、テロップや背景帯が映像表示エリアへ越境した場合は修正して再生成する
- 指定した日本語を一字一句正確に表示し、誤字や文字化けがあれば修正・再生成するよう明記
- 不自然な身体変形、激しい点滅、過剰な動き、ロゴ、透かし、意味不明な文字を避ける
- 動画全編に、落ち着きと温かみのある聞き取りやすい日本語ナレーションを必ず入れる
- ナレーションは穏やかで温かみのある成人女性の日本語音声に固定し、自然な速度より少しテンポよく読む。ナレーション間の無音は最大0.3秒とする
- 穏やかで明るい、著作権上利用可能なインストゥルメンタルBGMを動画全編に入れる
- BGMはナレーションより十分小さくし、発話中は自動的に音量を下げて声を明瞭にする
- BGMは0.0秒から明るく穏やかに開始し、場面転換は0.2〜0.4秒、同一静止画は3秒以内とする。終了時のみ自然にフェードアウトし、ナレーション・BGM・テロップのタイミングを合わせる
- 無音、音切れ、BGMで声が聞こえない状態は禁止。音声が生成されなかった場合は、必ず音声付きで再生成する
- 最後に3〜4秒の商品案内シーンを必ず設け、向いている人へ自然に勧める。リール・TikTokはプロフィールのリンク、YouTubeは概要欄のリンクへ案内する
- 最後の案内は【PR】を明示し、過度な煽り、効果保証、架空の限定性、強引な購入表現を使わない

制作プロンプトの独立性：
- creative_prompts内の各promptは、1件だけコピーしても成立する完全な指示文にする
- 各画像promptには「イラスト表示エリアとテキスト専用エリアの完全分離」「各領域の比率」「越境禁止」「主役を隠さない」を必ず繰り返して明記する
- 各画像promptには、その媒体の具体的なフォント種類・太さ・最低pxサイズ・行間・1行の文字数上限も必ず明記する
- 各動画promptには「映像表示エリアとテロップ専用エリアの完全分離」「全フレームで境界固定」「SNS操作UIの安全余白」「越境時の再生成」を必ず繰り返して明記する
- 各動画promptには、その媒体の拡大後の具体的なテロップ最低pxサイズ・太さ・最大行数・行間も必ず明記する
- 各動画promptには「0.0秒から始まる1.5〜2秒の表紙シーンと大きなキャッチコピー」「自然な日本語改行」「3〜4秒の商品案内と購入導線」を必ず明記する
- 各動画promptには「SNS名・ロゴ・保存ファイル名を画面に表示しない」「穏やかな日本語ナレーション」「穏やかなBGM」「ナレーション優先の音量調整」「無音時の再生成」を必ず明記する
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
    "scenes": [{{"scene_type": "opening_cover/content/affiliate_cta", "duration": "秒数", "caption": "字幕", "narration": "読み上げ文", "direction": "画面指示"}}]
  }},
  "youtube": {{
    "title": "タイトル", "description": "URLを含む概要欄", "hashtags": ["#タグ"],
    "scenes": [{{"scene_type": "opening_cover/content/affiliate_cta", "duration": "秒数", "caption": "字幕", "narration": "読み上げ文", "direction": "画面指示"}}]
  }},
  "tiktok": {{
    "caption": "投稿文", "hashtags": ["#タグ"],
    "scenes": [{{"scene_type": "opening_cover/content/affiliate_cta", "duration": "秒数", "caption": "字幕", "narration": "読み上げ文", "direction": "画面指示"}}]
  }},
  "creative_prompts": {{
    "x_image": {{"size": "1200×675", "catch_copy": "画像内に入れる短いキャッチコピー", "sub_copy": "画像内に入れる短い補足", "layout": "文字とメインイラストを重ねない具体的な配置", "font_spec": "太めゴシック。見出し56〜72px、補足30〜38px以上など", "prompt": "レイアウトとフォント指定をすべて含む完成プロンプト"}},
    "facebook_eyecatch": {{"size": "1200×630", "catch_copy": "画像内キャッチコピー", "sub_copy": "画像内補足", "layout": "文字35％＋イラスト65％などの具体的配置", "font_spec": "太めゴシック。見出し56〜72px、補足30〜38px以上など", "prompt": "レイアウトとフォント指定をすべて含む完成プロンプト"}},
    "threads_image": {{"size": "1080×1080", "catch_copy": "画像内キャッチコピー", "sub_copy": "画像内補足", "layout": "上部文字・中央イラスト・下部補足の具体的配置", "font_spec": "太めゴシック。見出し64〜80px、補足34〜44px以上など", "prompt": "レイアウトとフォント指定をすべて含む完成プロンプト"}},
    "line_image": {{"size": "1200×900", "catch_copy": "画像内キャッチコピー", "sub_copy": "画像内補足", "layout": "文字とイラストを分離する具体的配置", "font_spec": "太めゴシック。見出し64〜82px、補足36〜46px以上など", "prompt": "レイアウトとフォント指定をすべて含む完成プロンプト"}},
    "instagram_carousel": [
      {{"slide": 1, "size": "1080×1350", "catch_copy": "イラスト内の大見出し", "body_text": "イラスト内に直接入れる2〜4行の説明文", "layout": "上部見出し18％・中央イラスト57％・下部説明カード25％。中央イラストへ文字を重ねない", "font_spec": "太めゴシック。大見出し64〜80px、説明36〜44px以上、行間1.25〜1.4倍", "prompt": "完全分離レイアウトとフォント指定を含む1枚単独で使える完成プロンプト"}}
    ],
    "reel_video": {{"size": "1080×1920", "duration": "40〜45秒", "catch_copy": "最初の表紙に入れるキャッチコピー", "layout": "上部コピー帯20％・中央映像55％・下部テロップ帯10％・UI余白15％", "font_spec": "太めゴシック。表紙96〜120px、通常テロップ72〜88px、最大2行", "prompt": "表紙・自然な改行・成人女性ナレーション・明るく穏やかなBGM・最後の商品案内まで含む完成動画プロンプト"}},
    "youtube_thumbnail": {{"size": "1280×720", "catch_copy": "サムネイル内キャッチコピー", "sub_copy": "サムネイル内補足", "layout": "文字35％＋メインイラスト65％の左右分割", "font_spec": "太めゴシック。見出し80〜110px、補足40〜52px以上", "prompt": "完全分離レイアウトとフォント指定を含む完成プロンプト"}},
    "youtube_video": {{"size": "1920×1080", "duration": "40〜45秒", "catch_copy": "最初の表紙に入れるキャッチコピー", "layout": "人物と文字を左右に分離し、字幕は下部専用帯", "font_spec": "太めゴシック。表紙88〜112px、通常テロップ64〜80px、最大2行", "prompt": "表紙・自然な改行・成人女性ナレーション・明るく穏やかなBGM・最後の商品案内まで含む完成動画プロンプト"}},
    "tiktok_cover": {{"size": "1080×1920", "catch_copy": "表紙内キャッチコピー", "sub_copy": "表紙内補足", "layout": "上部文字20％・中央イラスト60％・下部補足5％・UI余白15％", "font_spec": "太めゴシック。見出し72〜96px、補足48〜60px以上", "prompt": "完全分離レイアウトとフォント指定を含む完成プロンプト"}},
    "tiktok_video": {{"size": "1080×1920", "duration": "40〜45秒", "catch_copy": "最初の表紙に入れるキャッチコピー", "layout": "上部コピー帯20％・中央映像55％・下部テロップ帯10％・UI余白15％", "font_spec": "太めゴシック。表紙96〜120px、通常テロップ72〜88px、最大2行", "prompt": "表紙・自然な改行・成人女性ナレーション・明るく穏やかなBGM・最後の商品案内まで含む完成動画プロンプト"}}
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


def generate_social_plan(client, model: str, article: str, call_llm, affiliate_url: str = "") -> dict:
    prompt = f"""【完成記事からSNS投稿文・動画台本を作成】
あなたは、読者心理・購買行動・媒体特性を熟知したプロのマーケティングコンサルタントであり、
広告・出版分野で経験豊富なプロのイラストレーター兼映像ディレクターです。
以下の完成記事だけを情報源として、各SNS向けコンテンツをJSONで作成してください。

完成記事：
---
{article}
---

購入・詳細確認用アフィリエイトURL：
{affiliate_url}

厳格な条件：
- 記事にない数値、実績、料金、資格、口コミ、効果、人物、店舗情報、研究結果を追加しない
- 医療・健康・美容情報を断定せず、過度な煽り、効果保証、架空の限定性を使わない
- すべての投稿の冒頭または目立つ位置に「【PR】」を入れる
- X、Facebook、Threads、LINE、YouTube概要欄にはアフィリエイトURLを省略せず1回入れる
- Instagram、リール、TikTokは「プロフィールのリンクから確認」と自然に案内する
- 同じ文章を使い回さず、媒体ごとの閲覧行動に最適化する
- ハッシュタグは文字列配列にする
- カルーセルは必ず9枚。1枚目は表紙、9枚目は商品が向く人への自然な案内とプロフィールリンクへの行動喚起
- リール、TikTok、YouTubeはいずれも40〜45秒程度、5〜7シーンとする
- 動画の最初は1.5〜2秒の表紙、最後は3〜4秒の商品案内。中間シーンは4〜6秒を目安にする
- ナレーションは日本語だけで、穏やかで温かみのある成人女性の声を想定し、通常より少しテンポよい短文にする
- 各ナレーション間を最大0.3秒にできる構成とし、不要な間や長い余韻を作らない
- captionは上部に表示する短い場面見出し、narrationは読み上げる自然な文章、visualは人物・表情・動作・背景・小物が分かる場面説明
- 上部見出しと下部テロップに同じ文章を重複させない。下部はナレーションの要点を具体的に言い換える
- 画面テキストは日本語の文節と意味のまとまりで自然に改行できる長さにする。単語途中の分割、助詞・句読点の行頭、1文字だけの行を避ける
- 改行後は各行の見た目の長さを近づけ、中央揃えで視覚的な重心が偏らない短文にする
- 最後にプロのマーケティングコンサルタントとして、訴求力、媒体適合、広告表記、自然な購入導線、事実性を確認する
- 最後にプロのイラストレーターとして、場面の具体性、人物・表情・小物、文字量、自然な改行、構図の作りやすさを確認する
- 1項目でも不十分なら内部で修正し、検品済みのJSONだけを出力する
- JSONを途中で省略せず、次の形式以外は出力しない

{{
  "x_posts": [
    {{"text": "投稿文", "hashtags": ["#タグ"]}},
    {{"text": "別角度の投稿文", "hashtags": ["#タグ"]}},
    {{"text": "別角度の投稿文", "hashtags": ["#タグ"]}}
  ],
  "x_image": {{"title": "短い見出し", "body": "60文字以内の説明", "visual": "具体的な場面"}},
  "threads": {{"text": "投稿文", "hashtags": ["#タグ"], "image_title": "短い見出し", "image_body": "60文字以内", "visual": "具体的な場面"}},
  "facebook": {{"text": "詳しい投稿文", "hashtags": ["#タグ"], "image_title": "短い見出し", "image_body": "60文字以内", "visual": "具体的な場面"}},
  "line": {{"text": "LINE配信用文", "image_title": "短い見出し", "image_body": "80文字以内", "visual": "具体的な場面"}},
  "carousel": {{"caption": "Instagramキャプション", "hashtags": ["#タグ"], "slides": [{{"title": "短い見出し", "body": "80文字以内", "visual": "具体的な場面"}}]}},
  "reel": {{"caption": "リール投稿文", "hashtags": ["#タグ"], "cover_title": "表紙見出し", "cover_body": "短い補足", "scenes": [{{"scene_type": "opening_cover/content/affiliate_cta", "duration": "秒数", "caption": "上部見出し", "narration": "読み上げ文", "visual": "具体的な場面"}}]}},
  "youtube": {{"title": "タイトル", "description": "URLを含む概要欄", "hashtags": ["#タグ"], "thumbnail_title": "サムネイル見出し", "thumbnail_body": "短い補足", "scenes": [{{"scene_type": "opening_cover/content/affiliate_cta", "duration": "秒数", "caption": "上部見出し", "narration": "読み上げ文", "visual": "具体的な場面"}}]}},
  "tiktok": {{"caption": "投稿文", "hashtags": ["#タグ"], "cover_title": "表紙見出し", "cover_body": "短い補足", "scenes": [{{"scene_type": "opening_cover/content/affiliate_cta", "duration": "秒数", "caption": "上部見出し", "narration": "読み上げ文", "visual": "具体的な場面"}}]}}
}}"""
    last_error = None
    for attempt in range(2):
        retry = "" if not attempt else "\n前回はJSONが不完全でした。文章量を調整し、必ず最後まで有効なJSONで出力してください。"
        raw = call_llm(
            client, model, prompt + retry, 16_000,
            response_mime_type="application/json", temperature=0.35,
        )
        try:
            data = _normalize_social_plan(_load_json_response(raw), article)
            _validate_social_plan(data)
            return data
        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
    raise ValueError(f"SNS投稿文と制作プロンプトを完成できませんでした：{last_error}")


def social_text(plan: dict) -> str:
    plan = _as_dict(plan)
    parts = ["X（旧Twitter）投稿案"]
    for index, raw_post in enumerate(_as_list(plan.get("x_posts")), 1):
        post = _as_dict(raw_post)
        parts.append(f"\n【パターン{index}】\n{post.get('text', '')}\n{_hashtags(post.get('hashtags'))}")
    for key, label in (("threads", "Threads"), ("facebook", "Facebook")):
        item = _as_dict(plan.get(key))
        parts.append(f"\n\n{label}投稿\n{item.get('text', '')}\n{_hashtags(item.get('hashtags'))}")
    parts.append(f"\n\nLINE配信文\n{_as_dict(plan.get('line')).get('text', '')}")
    carousel = _as_dict(plan.get("carousel"), "caption")
    parts.append(f"\n\nInstagram投稿\n{carousel.get('caption', '')}\n{_hashtags(carousel.get('hashtags'))}")
    for key, label in (("reel", "Instagramリール"), ("youtube", "YouTube"), ("tiktok", "TikTok")):
        item = _as_dict(plan.get(key), "caption")
        parts.append(f"\n\n{label}\n{item.get('title', '')}\n{item.get('caption', item.get('description', ''))}\n{_hashtags(item.get('hashtags'))}")
    return "\n".join(parts).strip()


def creative_prompt_text(plan: dict) -> str:
    plan = _as_dict(plan)
    prompts = _as_dict(plan.get("creative_prompts"))
    labels = (
        ("x_image", "X投稿画像"),
        ("facebook_eyecatch", "Facebookアイキャッチ"),
        ("threads_image", "Threads投稿画像"),
        ("line_image", "LINE配信用画像"),
        ("reel_cover", "Instagramリール表紙"),
        ("reel_video", "Instagramリール動画"),
        ("youtube_thumbnail", "YouTubeサムネイル"),
        ("youtube_video", "YouTube動画"),
        ("tiktok_cover", "TikTok表紙"),
        ("tiktok_video", "TikTok動画"),
    )
    parts = ["画像・動画制作用プロンプト"]
    for key, label in labels:
        item = _as_dict(prompts.get(key), "prompt")
        parts.append(
            f"\n\n## {label}\nサイズ：{item.get('size', '')}\n"
            f"推奨保存ファイル名：{item.get('output_filename', '')}\n"
            f"画像・動画内キャッチコピー：{item.get('catch_copy', item.get('overlay_text', ''))}\n"
            f"画像内補足：{item.get('sub_copy', '')}\n"
            f"レイアウト：{item.get('layout', '')}\n"
            f"フォント指定：{item.get('font_spec', '')}\n{item.get('prompt', '')}"
        )
    parts.append("\n\n## Instagramカルーセル9枚")
    for raw_item in _as_list(prompts.get("instagram_carousel")):
        item = _as_dict(raw_item, "prompt")
        parts.append(
            f"\n\n### {item.get('slide', '')}枚目\nサイズ：{item.get('size', '')}\n"
            f"推奨保存ファイル名：{item.get('output_filename', '')}\n"
            f"イラスト内の大見出し：{item.get('catch_copy', item.get('overlay_text', ''))}\n"
            f"イラスト内の説明文：{item.get('body_text', '')}\n"
            f"レイアウト：{item.get('layout', '')}\n"
            f"フォント指定：{item.get('font_spec', '')}\n{item.get('prompt', '')}"
        )
    parts.append("\n\n## ブログ記事の各セクション用イラスト")
    for raw_item in _as_list(prompts.get("article_section_images")):
        item = _as_dict(raw_item, "prompt")
        parts.append(
            f"\n\n### セクション{item.get('section', '')}｜{item.get('heading_level', '')}：{item.get('heading', '')}\n"
            f"サイズ：{item.get('size', '')}\n推奨保存ファイル名：{item.get('output_filename', '')}\n"
            f"画像内キャッチコピー：{item.get('catch_copy', '')}\n"
            f"画像内補足：{item.get('sub_copy', '')}\nレイアウト：{item.get('layout', '')}\n"
            f"フォント指定：{item.get('font_spec', '')}\n{item.get('prompt', '')}"
        )
    return "\n".join(parts).strip()
