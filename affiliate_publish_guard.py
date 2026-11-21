"""Conservative post-generation guard for affiliate creative bundles.

No external services, WordPress writes, or article generation. Works on a deep copy.
Requires human approval before publishing health/medical test promotions.
"""
import copy
import json
import re
from pathlib import Path

MEDICAL = re.compile(r'がん|癌|検査|診断|疾患|医療|病気|人間ドック|スクリーニング', re.I)
UNSAFE = re.compile(r'通院不要|通院や痛みが一切なし|自宅で完結|医療機関.*不要|病院.*不要|がんリスク(?:が分かる|を調べ|チェック)|早期発見|必ず治る|絶対に改善|検診の代わり|検査の代わり|検査キットを見る|検査キットの案内', re.I)
HOLD = '【要確認・生成保留】'
SAFE_TEXT = '商品の特徴、利用条件、注意点を記事と公式情報でご確認ください。医療機関での診断や検査に代わるものではありません。'
SAFE_HEAD = '商品情報を確認'
SAFE_SUB = '特徴と注意点は記事でご確認ください'
SAFE_VISUAL = '明るい自然光の日本の生活場面。実物の商品、検査キット、結果、認証、ロゴ、医療効果は創作しない。'
DISCLAIMER = '【PR】'


def _safe_caption(url='', include_url=False):
    result = DISCLAIMER + '\n' + SAFE_TEXT
    if include_url and url:
        result += '\n' + url
    return result


def _brief(item, medical, max_chars):
    if not isinstance(item, dict):
        return
    prompt = item.get('prompt')
    if not isinstance(prompt, str):
        return
    if not medical and len(prompt) <= max_chars and not UNSAFE.search(prompt):
        return
    size = str(item.get('size', ''))[:70]
    layout = str(item.get('layout', ''))[:180]
    duration = str(item.get('duration', ''))[:70]
    parts = [HOLD, '医療・健康関連広告の事実確認と承認が完了するまで生成・公開しない。'] if medical else []
    parts += [
        '日本語の商用クリエイティブ。広告表示【PR】を明確にする。',
        SAFE_VISUAL,
        '見出し：「' + SAFE_HEAD + '」',
        '補足：「' + SAFE_SUB + '」',
    ]
    if size:
        parts.append('サイズ：' + size)
    if layout:
        parts.append('配置：' + layout)
    if duration:
        parts.append('尺：' + duration)
    if 'video' in str(item.get('output_filename', '')).lower() or duration:
        parts.append('既存のシーン構成と秒数を維持する。字幕・映像は未確認の効能や検査結果を表現しない。')
    item['prompt'] = '\n'.join(parts)[:max_chars]
    if medical:
        item['review_required'] = True
    if 'catch_copy' in item:
        item['catch_copy'] = SAFE_HEAD
    if 'sub_copy' in item:
        item['sub_copy'] = SAFE_SUB
    if 'body_text' in item:
        item['body_text'] = SAFE_TEXT


def guard_bundle(bundle, max_prompt_chars=1100):
    """Return (cleaned bundle, report). Do not change top-level key set."""
    data = copy.deepcopy(bundle)
    original_keys = set(data)
    medical = bool(MEDICAL.search(str(data.get('title', '')) + str(data.get('product_name', ''))))
    url = data.get('affiliate_url', '')
    plan = data.get('social_plan', {})
    if not isinstance(plan, dict):
        raise ValueError('social_plan must be an object')
    report = {'medical_review_required': medical, 'hold_items': [], 'max_prompt_chars': max_prompt_chars}

    if medical:
        for post in plan.get('x_posts', []):
            if isinstance(post, dict):
                post['text'] = _safe_caption(url, True)
        for channel in ('threads', 'facebook', 'line'):
            entry = plan.get(channel)
            if isinstance(entry, dict):
                entry['text'] = _safe_caption(url, True)
                for field in ('image_title', 'image_body', 'visual'):
                    if field in entry:
                        entry[field] = SAFE_HEAD if field == 'image_title' else SAFE_VISUAL if field == 'visual' else SAFE_SUB
        for field in ('x_image',):
            entry = plan.get(field)
            if isinstance(entry, dict):
                for key in ('title', 'body', 'visual'):
                    if key in entry:
                        entry[key] = SAFE_HEAD if key == 'title' else SAFE_VISUAL if key == 'visual' else SAFE_SUB
        carousel = plan.get('carousel', {})
        if isinstance(carousel, dict):
            carousel['caption'] = _safe_caption(url, True)
            for slide in carousel.get('slides', []):
                if isinstance(slide, dict):
                    if 'title' in slide:
                        slide['title'] = SAFE_HEAD
                    if 'body' in slide:
                        slide['body'] = SAFE_TEXT
        for channel in ('reel', 'youtube', 'tiktok'):
            entry = plan.get(channel)
            if not isinstance(entry, dict):
                continue
            for key in ('caption', 'description'):
                if key in entry:
                    entry[key] = _safe_caption(url, key == 'caption')
            for key in ('title', 'cover_title', 'thumbnail_title'):
                if key in entry:
                    entry[key] = SAFE_HEAD
            for key in ('cover_body', 'thumbnail_body'):
                if key in entry:
                    entry[key] = SAFE_SUB
            for scene in entry.get('scenes', []):
                if isinstance(scene, dict):
                    for key in ('caption', 'narration', 'text', 'visual'):
                        if key in scene:
                            scene[key] = SAFE_VISUAL if key == 'visual' else SAFE_TEXT
        gbp = data.get('gbp')
        if isinstance(gbp, dict):
            if 'post' in gbp:
                gbp['post'] = _safe_caption() + '\n詳しくはブログ記事をご確認ください。'
            if 'image_prompt' in gbp:
                gbp['image_prompt'] = HOLD + '\n1:1の説明画像。' + SAFE_VISUAL + '\n' + SAFE_SUB
            if 'video_prompt' in gbp:
                gbp['video_prompt'] = (
                    HOLD + '\nGBP用縦型9:16、総尺45秒。ナレーションなし、穏やかなBGM、PR表示。\n'
                    '0〜5秒：導入。5〜13秒：概要。13〜23秒：確認事項。'
                    '23〜33秒：注意点。33〜40秒：記事紹介。40〜45秒：記事への案内。\n'
                    + SAFE_VISUAL
                )
        for item in data.get('blog_images', []):
            if isinstance(item, dict) and 'prompt' in item:
                item['prompt'] = HOLD + '\n横長16:9。' + SAFE_VISUAL + '\n' + SAFE_SUB

    prompts = plan.get('creative_prompts', {})
    if isinstance(prompts, dict):
        for category, value in prompts.items():
            entries = value if isinstance(value, list) else [value]
            for index, item in enumerate(entries):
                if isinstance(item, dict):
                    _brief(item, medical, max_prompt_chars)
                    if item.get('review_required'):
                        report['hold_items'].append(f'{category}[{index}]')
    if set(data) != original_keys:
        raise AssertionError('Top-level keys changed')
    return data, report


def guard_file(input_path, output_path, report_path):
    original = json.loads(Path(input_path).read_text(encoding='utf-8'))
    guarded, report = guard_bundle(original)
    Path(output_path).write_text(json.dumps(guarded, ensure_ascii=False, indent=2), encoding='utf-8')
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('report')
    args = parser.parse_args()
    print(json.dumps(guard_file(args.input, args.output, args.report), ensure_ascii=False))
