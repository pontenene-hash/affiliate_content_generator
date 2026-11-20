
"""Safety tests for the additive Affiliate V5 creative quality review.

Run with:
    python test_affiliate_quality_v5.py

No WordPress writes, article generation, or external API calls.
"""

import copy
import json
import pathlib
import subprocess
import sys
import tempfile

from affiliate_quality_v5 import review_bundle, validate_bundle


REVIEW_MARKER = "[V5_REVIEWED]"


def make_sample():
    """Create a local test bundle without external API calls."""
    scenes = [
        {
            "duration": "4秒",
            "caption": "表紙",
            "narration": "表紙",
        },
        {
            "duration": "34秒",
            "caption": "内容",
            "narration": "内容",
        },
        {
            "duration": "4秒",
            "caption": "CTA",
            "narration": "CTA",
        },
    ]

    slides = [
        {
            "title": "特徴",
            "body": "説明",
        }
        for _ in range(9)
    ]

    carousel_prompts = [
        {
            "catch_copy": "特徴",
            "body_text": "説明",
            "prompt": "「特徴」「説明」",
        }
        for _ in range(9)
    ]

    return {
        "affiliate_url": "https://example.com/a?x=1&y=2",
        "social_plan": {
            "x_posts": [
                {
                    "text": (
                        "【PR】\n"
                        "商品紹介。\n"
                        "https://example.com/a?x=1&y=2"
                    )
                }
            ],
            "threads": {
                "text": "商品紹介。",
            },
            "facebook": {
                "text": "商品紹介。",
            },
            "line": {
                "text": "商品紹介。",
            },
            "carousel": {
                "caption": "商品紹介。",
                "slides": slides,
            },
            "reel": {
                "caption": "商品紹介。",
                "scenes": copy.deepcopy(scenes),
            },
            "youtube": {
                "description": "商品紹介。",
                "scenes": copy.deepcopy(scenes),
            },
            "tiktok": {
                "caption": "商品紹介。",
                "scenes": copy.deepcopy(scenes),
            },
            "creative_prompts": {
                "instagram_carousel": carousel_prompts,
                "article_section_images": [
                    {
                        "prompt": "説明",
                    }
                ],
                "reel_video": {
                    "prompt": "「内容」",
                },
                "youtube_video": {
                    "prompt": "「内容」",
                },
                "tiktok_video": {
                    "prompt": "「内容」",
                },
            },
        },
        "gbp": {
            "post": "商品紹介。",
            "image_prompt": "画像",
            "video_prompt": "総尺45秒。40〜45秒：CTA",
        },
    }


def check_bundle(original):
    """Check structure, safety, and repeatability."""
    before = copy.deepcopy(original)

    result = review_bundle(original)

    # Validate the generated creative bundle.
    assert validate_bundle(result) is True

    # Original input must remain unchanged.
    assert original == before, "Input mutated"

    # V5 may add only its own review marker.
    expected_keys = set(original) | {REVIEW_MARKER}

    assert set(result) == expected_keys, (
        "Unexpected top-level keys"
    )

    assert result[REVIEW_MARKER] is True, (
        "V5 review marker missing"
    )

    # Preserve all existing social and creative categories.
    assert set(result["social_plan"]) == set(
        original["social_plan"]
    ), "Social plan structure changed"

    assert set(
        result["social_plan"]["creative_prompts"]
    ) == set(
        original["social_plan"]["creative_prompts"]
    ), "Media inventory changed"

    # Instagram carousel must retain nine slides.
    assert len(
        result["social_plan"]["carousel"]["slides"]
    ) == 9, "Instagram carousel count changed"

    # Three video formats must retain their original scenes.
    for platform in ("reel", "youtube", "tiktok"):
        original_scenes = original["social_plan"][platform]["scenes"]
        result_scenes = result["social_plan"][platform]["scenes"]

        assert len(result_scenes) == len(original_scenes), (
            platform + " scene count changed"
        )

        assert [
            scene["duration"] for scene in result_scenes
        ] == [
            scene["duration"] for scene in original_scenes
        ], platform + " durations changed"

    # Review must not change the bundle when called again.
    second = review_bundle(result)

    assert second == result, (
        "Review is not idempotent"
    )

    # Affiliate URL must appear exactly once in X posts.
    url = original.get("affiliate_url", "")

    if url:
        for post in result["social_plan"]["x_posts"]:
            assert post["text"].count(url) == 1, (
                "Affiliate URL not exactly once"
            )

    return result


def check_installer():
    """Test the installer on a temporary file only."""
    installer = pathlib.Path(__file__).with_name(
        "install_affiliate_quality_v5.py"
    )

    assert installer.exists(), (
        "V5 installer file is missing"
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "auto_creative.py"

        source = (
            "def build_bundle("
            "article, title, product, post_id, "
            "affiliate_url, api_key, model):\n"
            "    return {}\n"
        )

        path.write_text(
            source,
            encoding="utf-8",
        )

        # First installation.
        subprocess.run(
            [
                sys.executable,
                str(installer),
                str(path),
            ],
            check=True,
        )

        first = path.read_text(
            encoding="utf-8"
        )

        assert "AFFILIATE_QUALITY_V5_HOOK" in first, (
            "V5 hook was not installed"
        )

        backup = path.with_suffix(
            ".py.v5.bak"
        )

        assert backup.exists(), (
            "Installer backup missing"
        )

        assert backup.read_text(
            encoding="utf-8"
        ) == source, "Installer backup differs from original"

        # Second installation must not duplicate the hook.
        subprocess.run(
            [
                sys.executable,
                str(installer),
                str(path),
            ],
            check=True,
        )

        second = path.read_text(
            encoding="utf-8"
        )

        assert first == second, (
            "Installer is not idempotent"
        )

        assert second.count(
            "# AFFILIATE_QUALITY_V5_HOOK"
        ) == 1, "V5 hook was duplicated"


def run():
    """Run all safety checks."""
    sample = (
        pathlib.Path(sys.argv[1])
        if len(sys.argv) > 1
        else None
    )

    if sample:
        original = json.loads(
            sample.read_text(
                encoding="utf-8"
            )
        )
    else:
        original = make_sample()

    check_bundle(original)

    check_installer()

    print(
        "PASS: bundle structure, "
        "9 Instagram slides, "
        "42-second videos, "
        "45-second GBP brief, "
        "affiliate URL, "
        "V5 review marker, "
        "idempotence, "
        "installer backup"
    )


if __name__ == "__main__":
    run()
