"""Safely patch two functions in an existing social_tools.py.

Usage: python social_tools_safe_patch.py path/to/social_tools.py
Creates a .bak copy and validates syntax before replacing the original.
"""
from pathlib import Path
import ast
import sys

NEW_MARK = '''def _mark_text(value, context):
    """Show the appropriate disclosure exactly once, at the beginning."""
    value = str(value or '').strip()
    mark = _disclosure(context)
    # Remove only disclosure labels, never product names or supplied links.
    value = re.sub(r'【(?:PR|商品案内)】', '', value)
    value = re.sub(r'\\n[ \\t]*\\n[ \\t]*\\n+', '\\n\\n', value).strip()
    return mark + ('\\n' + value if value else '')
'''

NEW_VIDEO = '''def _ensure_video_scenes(item, media_key, article, promotion_context='アフィリエイト販売'):
    """Keep article-grounded scenes, avoid repeated points, and total 42 seconds."""
    scenes = [_as_dict(scene, 'narration') for scene in _as_list(item.get('scenes'))]
    title = _plain_text(item.get('title') or item.get('caption') or _article_title(article), 28)
    if not scenes or scenes[0].get('scene_type') != 'opening_cover':
        scenes.insert(0, {'scene_type': 'opening_cover', 'caption': title,
                          'narration': title, 'visual': '記事のテーマが伝わる明るい表紙。人物と文字を分離'})
    else:
        scenes[0]['scene_type'] = 'opening_cover'

    if _store_only(promotion_context):
        caption, narration = '院内でご相談ください', '気になる方は、ご来店時にスタッフへお気軽にご相談ください。'
    elif media_key == 'youtube':
        caption, narration = '概要欄から詳しく確認', '気になる方は、概要欄のリンクから詳しくご確認ください。'
    else:
        caption, narration = '詳しくはプロフィールへ', '気になる方は、プロフィールのリンクから詳しくご確認ください。'

    cta = {'scene_type': 'affiliate_cta', 'caption': caption, 'narration': narration,
           'visual': '明るく自然な商品案内。人物と文字の領域を分離'}
    # Discard any Gemini-generated intermediate CTA; use a single final CTA.
    middle = [scene for scene in scenes[1:] if scene.get('scene_type') != 'affiliate_cta']
    article_points = _fallback_video_points(article)
    seen_headings, seen_bodies = set(), set()
    selected = []
    for scene in middle + article_points:
        heading = _plain_text(scene.get('caption'), 40)
        body = _plain_text(scene.get('narration'), 45)
        if not heading and not body:
            continue
        # Ignore identical or near-identical points after whitespace/punctuation normalization.
        heading_key = re.sub(r'[\\W_]+', '', heading).lower()
        body_key = re.sub(r'[\\W_]+', '', body).lower()
        if (heading_key and heading_key in seen_headings) or (body_key and body_key in seen_bodies):
            continue
        if heading_key:
            seen_headings.add(heading_key)
        if body_key:
            seen_bodies.add(body_key)
        scene = dict(scene)
        scene.update({'scene_type': 'content', 'caption': heading, 'narration': body})
        selected.append(scene)
        if len(selected) == 6:
            break
    if not selected:
        selected = [{'scene_type': 'content', 'caption': '記事のポイント',
                     'narration': '商品の特徴や注意点を記事で確認できます。',
                     'visual': '記事の要点を示す生活場面'}]
    scenes = [scenes[0]] + selected + [cta]
    for scene in scenes:
        scene['narration'] = _plain_text(scene.get('narration'), 45)
        scene['caption'] = _plain_text(scene.get('caption'), 40)
    item['scenes'] = scenes
    _fix_video_timing(item)
    return item
'''

def replace_function(source, name, replacement):
    tree = ast.parse(source)
    matches = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one {name}; found {len(matches)}')
    node = matches[0]
    lines = source.splitlines(keepends=True)
    lines[node.lineno - 1:node.end_lineno] = [replacement.rstrip() + '\n']
    return ''.join(lines)

def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python social_tools_safe_patch.py social_tools.py')
    path = Path(sys.argv[1])
    original = path.read_text(encoding='utf-8')
    result = replace_function(original, '_mark_text', NEW_MARK)
    result = replace_function(result, '_ensure_video_scenes', NEW_VIDEO)
    compile(result, str(path), 'exec')
    backup = path.with_suffix(path.suffix + '.bak')
    if backup.exists():
        raise SystemExit(f'Backup already exists: {backup}. No files changed.')
    backup.write_text(original, encoding='utf-8')
    path.write_text(result, encoding='utf-8')
    print(f'Patched: {path}; backup: {backup}')

if __name__ == '__main__':
    main()
