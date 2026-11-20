"""Safely patch social_tools.py without duplicating existing functions.

Usage: python social_tools_safe_patch.py social_tools.py
Does not touch WordPress, schedules, or article generation.
"""
import ast
import re
import sys
from collections import Counter
from pathlib import Path

PATCH_MARKER = '# SAFE_SOCIAL_QUALITY_PATCH_V4'


def names(source):
    return [node.name for node in ast.parse(source).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def replace_function(source, name, replacement):
    tree = ast.parse(source)
    matches = [node for node in tree.body
               if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one {name}; found {len(matches)}')
    node = matches[0]
    lines = source.splitlines(keepends=True)
    lines[node.lineno - 1:node.end_lineno] = [replacement.strip() + '\n']
    return ''.join(lines)


NEW_REVIEW_SAFE_COPY = r'''
def _review_safe_copy(value):
    """Remove unsupported claim sentences without leaving fragments."""
    text = str(value or '')
    parts = re.split(r'(?<=[。！？!?])|\n', text)
    return '\n'.join(part.strip() for part in parts
                     if part.strip() and not _REVIEW_CLAIM.search(part)).strip()
'''

NEW_FALLBACK_LINE = r'''
def _fallback_line(article):
    """Create a neutral, complete LINE message."""
    title = _article_title(article)
    return (f'{title}について、商品の特徴や利用前に'
            '確認したいポイントを記事にまとめました。'
            '\n詳しくは記事でご確認ください。')
'''

NEW_ENSURE_VIDEO = r'''
def _ensure_video_scenes(item, media_key, article,
                         promotion_context='アフィリエイト販売'):
    """Build 42-second scenes with an opening and a final CTA."""
    scenes = [_as_dict(scene, 'narration')
              for scene in _as_list(item.get('scenes'))]
    title = _plain_text(item.get('title') or _article_title(article), 28)
    opening = {'scene_type': 'opening_cover', 'caption': title,
               'narration': title, 'visual': '明るい表紙。文字と人物を分離する。'}
    if _store_only(promotion_context):
        caption, narration = ('院内でご相談ください',
                              'ご来店時にスタッフへお気軽にご相談ください。')
    elif media_key == 'youtube':
        caption, narration = ('概要欄から詳しく確認',
                              '詳しくは概要欄のリンクをご確認ください。')
    else:
        caption, narration = ('詳しくはプロフィールへ',
                              '詳しくはプロフィールのリンクをご確認ください。')
    cta = {'scene_type': 'affiliate_cta', 'caption': caption,
           'narration': narration,
           'visual': '自然な商品案内。文字の安全余白を確保する。'}
    candidates = [scene for scene in scenes
                  if scene.get('scene_type') not in
                  ('opening_cover', 'affiliate_cta')]
    candidates += _fallback_video_points(article)
    selected, seen = [], set()
    for scene in candidates:
        heading = _review_safe_copy(_plain_text(scene.get('caption'), 40))
        body = _review_safe_copy(_plain_text(scene.get('narration'), 45))
        if not heading or not body:
            continue
        key = re.sub(r'[\W_]+', '', heading).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        selected.append({'scene_type': 'content', 'caption': heading,
                         'narration': body,
                         'visual': _review_safe_copy(scene.get('visual'))
                         or '記事に沿った明るい生活場面'})
        if len(selected) == 6:
            break
    if not selected:
        selected.append({'scene_type': 'content', 'caption': '記事のポイント',
                         'narration': '商品の特徴や注意点を記事でご確認ください。',
                         'visual': '記事の内容を表す明るい生活場面'})
    item['scenes'] = [opening] + selected + [cta]
    _fix_video_timing(item)
    return item
'''

NEW_BUILD_CREATIVE = r'''
def _build_creative_prompts(plan, article):
    """Preserve the original builder and sanitize its output."""
    prompts = _build_creative_prompts_original(plan, article)
    def clean_item(item):
        if isinstance(item, list):
            return [clean_item(x) for x in item]
        if not isinstance(item, dict):
            return item
        result = dict(item)
        for key in ('catch_copy', 'sub_copy', 'body_text', 'heading', 'prompt'):
            if key in result:
                result[key] = _review_safe_copy(result[key])
        return result
    return {key: clean_item(value) for key, value in prompts.items()}
'''


def patch(source):
    before = names(source)
    duplicates = [name for name, count in Counter(before).items() if count > 1]
    if duplicates:
        raise ValueError('Existing duplicate functions: ' + ', '.join(duplicates))

    # V4 already contains the original builder and its safe wrapper.
    if PATCH_MARKER in source:
        if not {'_build_creative_prompts_original', '_build_creative_prompts'} <= set(before):
            raise ValueError('V4 marker exists but creative builder functions are missing')
        return source

    updated = source
    for name, replacement in (
        ('_review_safe_copy', NEW_REVIEW_SAFE_COPY),
        ('_fallback_line', NEW_FALLBACK_LINE),
        ('_ensure_video_scenes', NEW_ENSURE_VIDEO),
    ):
        updated = replace_function(updated, name, replacement)

    current = set(names(updated))
    if '_build_creative_prompts_original' in current:
        # Existing original builder must never be renamed again.
        updated = replace_function(updated, '_build_creative_prompts', NEW_BUILD_CREATIVE)
    else:
        tree = ast.parse(updated)
        matches = [node for node in tree.body
                   if isinstance(node, ast.FunctionDef)
                   and node.name == '_build_creative_prompts']
        if len(matches) != 1:
            raise ValueError('Creative builder not found exactly once')
        node = matches[0]
        lines = updated.splitlines(keepends=True)
        original = ''.join(lines[node.lineno - 1:node.end_lineno])
        renamed = original.replace('def _build_creative_prompts(',
                                   'def _build_creative_prompts_original(', 1)
        if renamed == original:
            raise ValueError('Could not rename original creative builder')
        lines[node.lineno - 1:node.end_lineno] = [
            renamed.rstrip() + '\n\n' + NEW_BUILD_CREATIVE.strip() + '\n'
        ]
        updated = ''.join(lines)

    updated = PATCH_MARKER + '\n' + updated
    compile(updated, '<patched social_tools>', 'exec')
    after = names(updated)
    duplicates = [name for name, count in Counter(after).items() if count > 1]
    if duplicates:
        raise ValueError('Duplicate functions after patch: ' + ', '.join(duplicates))
    expected = set(before) | {'_build_creative_prompts_original'}
    if set(after) != expected:
        raise ValueError('Unexpected function inventory change')
    return updated


def main():
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'social_tools.py')
    original = target.read_text(encoding='utf-8')
    updated = patch(original)
    if patch(updated) != updated:
        raise ValueError('Idempotence check failed')
    if updated == original:
        print('Already patched (V4). No changes required.')
        print('Syntax and duplicate-function checks passed.')
        return
    backup = target.with_suffix(target.suffix + '.bak')
    if backup.exists():
        raise SystemExit(f'Backup already exists: {backup}. No files changed.')
    backup.write_text(original, encoding='utf-8')
    target.write_text(updated, encoding='utf-8')
    print(f'Patched: {target}')
    print(f'Backup: {backup}')
    print('Syntax, function inventory, and idempotence checks passed.')


if __name__ == '__main__':
    main()
