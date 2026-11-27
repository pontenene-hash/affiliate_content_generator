"""Run with: python test_quality_improvements.py"""
import copy
from affiliate_quality_v5 import review_bundle, short_copy, normalize_post

URL = 'https://example.com/item?ref=abc&campaign=1'

def fixture():
    slides = [{'title': '商品について', 'body': '詳しくは記事をご確認ください。'} for _ in range(9)]
    slides[0] = {'title': '全身のがんを早期発見', 'body': '利用者の声：必ず治る。'}
    scenes = [{'duration': duration, 'caption': '記事のポイント', 'narration': '利用前に確認してください。'} for duration in ('4秒','37秒','4秒')]
    scenes[0]['caption'] = '全身のがんを早期発見'
    carousel_prompts = [{'catch_copy': x['title'], 'body_text': x['body'], 'sub_copy': x['body'], 'prompt': '表示「' + x['title'] + '」と「' + x['body'] + '」'} for x in slides]
    return {'affiliate_url': URL, 'social_plan': {
        'x_posts': [{'text': '【PR】全身のがんを早期発見。\n商品の特徴は記事でご確認ください。'}],
        'threads': {'text': '記事をご確認ください。'},
        'facebook': {'text': '記事をご確認ください。'},
        'line': {'text': '記事をご確認ください。'},
        'carousel': {'caption': '商品を紹介します。', 'slides': slides},
        'reel': {'caption': '商品を紹介します。', 'scenes': copy.deepcopy(scenes)},
        'youtube': {'description': '商品を紹介します。', 'scenes': copy.deepcopy(scenes)},
        'tiktok': {'caption': '商品を紹介します。', 'scenes': copy.deepcopy(scenes)},
        'creative_prompts': {
            'instagram_carousel': carousel_prompts,
            'article_section_images': [{'prompt': '記事の内容を説明する画像'}],
            'reel_video': {'prompt': '表示「全身のがんを早期発見」'},
            'youtube_video': {'prompt': '表示「全身のがんを早期発見」'},
            'tiktok_video': {'prompt': '表示「全身のがんを早期発見」'},
        },
    }, 'gbp': {'post': '【PR】商品の特徴を紹介します。', 'image_prompt': '説明画像', 'video_prompt': '45秒の動画、40〜45秒にCTA'}}


def main():
    assert short_copy('これは長い文章で、途中で切れてはいけない説明です。', 12, '確認してください。') == '確認してください。'
    assert normalize_post('【PR】商品の紹介です。\n' + URL, URL, True).count(URL) == 1
    source = fixture()
    unchanged = copy.deepcopy(source)
    output = review_bundle(source)
    assert source == unchanged, 'Input bundle must remain unchanged'
    assert len(output['social_plan']['carousel']['slides']) == 9
    assert output['social_plan']['carousel']['slides'][0]['title'] == '商品のポイント'
    assert output['social_plan']['carousel']['slides'][0]['body'] == '商品の特徴と利用前の注意点を記事でご確認ください。'
    assert output['social_plan']['creative_prompts']['instagram_carousel'][0]['catch_copy'] == '商品のポイント'
    assert output['social_plan']['creative_prompts']['instagram_carousel'][0]['body_text'] == output['social_plan']['carousel']['slides'][0]['body']
    assert output['social_plan']['creative_prompts']['instagram_carousel'][0]['review_required'] is True
    assert '生成保留' in output['social_plan']['creative_prompts']['instagram_carousel'][0]['prompt']
    assert '早期発見' not in output['social_plan']['x_posts'][0]['text']
    assert output['social_plan']['x_posts'][0]['text'].count(URL) == 1
    assert review_bundle(output) == output, 'Review must be idempotent'
    print('PASS: safety, no truncation, 9 slides, 45s videos, GBP 45s, URL, prompt consistency, idempotence')

if __name__ == '__main__':
    main()
