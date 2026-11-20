"""Run: python test_affiliate_quality_v5.py [path/to/all_prompts.json]"""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile

from affiliate_quality_v5 import review_bundle, validate_bundle


def run():
    sample = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if sample:
        original = json.loads(sample.read_text(encoding='utf-8'))
    else:
        scenes = [{'duration': '4秒', 'caption': '表紙', 'narration': '表紙'}, {'duration': '34秒', 'caption': '内容', 'narration': '内容'}, {'duration': '4秒', 'caption': 'CTA', 'narration': 'CTA'}]
        original = {'affiliate_url': 'https://example.com/a?x=1&y=2', 'social_plan': {
            'x_posts': [{'text': '【PR】\n商品紹介。\nhttps://example.com/a?x=1&y=2'}],
            'threads': {'text': '商品紹介。'}, 'facebook': {'text': '商品紹介。'}, 'line': {'text': '商品紹介。'},
            'carousel': {'caption': '商品紹介。', 'slides': [{'title': '特徴', 'body': '説明'} for _ in range(9)]},
            'reel': {'caption': '商品紹介。', 'scenes': copy.deepcopy(scenes)},
            'youtube': {'description': '商品紹介。', 'scenes': copy.deepcopy(scenes)},
            'tiktok': {'caption': '商品紹介。', 'scenes': copy.deepcopy(scenes)},
            'creative_prompts': {'instagram_carousel': [{'catch_copy': '特徴', 'body_text': '説明', 'prompt': '「特徴」「説明」'} for _ in range(9)], 'article_section_images': [{'prompt': '説明'}], 'reel_video': {'prompt': '「内容」'}, 'youtube_video': {'prompt': '「内容」'}, 'tiktok_video': {'prompt': '「内容」'}}
        }, 'gbp': {'post': '商品紹介。', 'image_prompt': '画像', 'video_prompt': '総尺45秒。40〜45秒：CTA'}}
    before = copy.deepcopy(original)
    result = review_bundle(original)
    validate_bundle(result)
    assert original == before, 'Input mutated'
    assert set(result) == set(original), 'Top-level keys changed'
    assert set(result['social_plan']['creative_prompts']) == set(original['social_plan']['creative_prompts']), 'Media inventory changed'
    assert review_bundle(result) == result, 'Review is not idempotent'
    url = original.get('affiliate_url', '')
    if url:
        for post in result['social_plan']['x_posts']:
            assert post['text'].count(url) == 1, 'Affiliate URL not exactly once'
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / 'auto_creative.py'
        path.write_text('def build_bundle(article, title, product, post_id, affiliate_url, api_key, model):\n    return {}\n', encoding='utf-8')
        installer = pathlib.Path(__file__).with_name('install_affiliate_quality_v5.py')
        subprocess.run([sys.executable, str(installer), str(path)], check=True)
        first = path.read_text(encoding='utf-8')
        subprocess.run([sys.executable, str(installer), str(path)], check=True)
        assert path.read_text(encoding='utf-8') == first, 'Installer not idempotent'
        assert path.with_suffix('.py.v5.bak').exists(), 'Backup missing'
    print('PASS: bundle structure, 9 slides, 42-second videos, 45-second GBP brief, URL, idempotence, installer backup')

if __name__ == '__main__':
    run()
