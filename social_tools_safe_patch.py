"""Idempotent, AST-checked URL cleanup patch for social_tools.py.

Upload this file to the repository root as social_tools_safe_patch.py,
then run the existing safe_patch_check + apply_safe_patch GitHub workflow.
Only two existing functions are modified. A .bak backup is created.
"""
import ast
from pathlib import Path
import sys

NEW_ENSURE_LINK = '''def _ensure_link(value, url):
    """Output one complete affiliate URL; remove broken/duplicate versions."""
    value = str(value or '').strip()
    url = str(url or '').strip()
    if not url:
        return value
    # A Gemini response can split a query string after '?' or '&'.
    # Match only the supplied affiliate URL, with optional whitespace at
    # those boundaries, rather than deleting unrelated external links.
    pieces = re.split(r'([?&=])', url)
    flexible = ''.join(r'\\s*' + re.escape(p) + r'\\s*' if p in '?&=' else re.escape(p)
                       for p in pieces if p)
    value = re.sub(flexible, '', value, flags=re.I)
    # Also strip a partial link emitted on a separate line, such as
    # https://px.a8.net/svt/ejp? followed by a8mat=... on the next line.
    base = url.split('?', 1)[0]
    if base:
        value = re.sub(re.escape(base) + r'\\s*\\?\\s*(?:\\n|$)', '', value, flags=re.I)
    # Remove a stray query line only if it exactly matches the known query.
    if '?' in url:
        query = url.split('?', 1)[1]
        value = re.sub(r'(?m)^\\s*' + re.escape(query) + r'\\s*$', '', value)
    value = re.sub(r'\\n{3,}', '\\n\\n', value).strip()
    return value + '\\n' + url
'''

NEW_STRIP_LINK = '''def _strip_affiliate_link(value, url):
    """Remove the supplied affiliate URL from profile-link-only platforms."""
    value = str(value or '').strip()
    url = str(url or '').strip()
    if not url:
        return value
    pieces = re.split(r'([?&=])', url)
    flexible = ''.join(r'\\s*' + re.escape(p) + r'\\s*' if p in '?&=' else re.escape(p)
                       for p in pieces if p)
    value = re.sub(flexible, '', value, flags=re.I)
    base = url.split('?', 1)[0]
    if base:
        value = re.sub(re.escape(base) + r'\\s*\\?\\s*(?:\\n|$)', '', value, flags=re.I)
    if '?' in url:
        query = url.split('?', 1)[1]
        value = re.sub(r'(?m)^\\s*' + re.escape(query) + r'\\s*$', '', value)
    return re.sub(r'\\n{3,}', '\\n\\n', value).strip()
'''

# Inserted immediately before building creative prompts, preserving all
# existing normalization and all creative/image/video generation functions.
EXTRA_NORMALIZATION = '''    # Profile-only platforms: do not print raw affiliate links in captions.
    carousel['caption'] = _mark_text(_strip_affiliate_link(carousel.get('caption'), affiliate_url), promotion_context)
    for media_key in ('reel', 'tiktok'):
        media = _as_dict(data.get(media_key), 'caption')
        media['caption'] = _mark_text(_strip_affiliate_link(media.get('caption'), affiliate_url), promotion_context)
        data[media_key] = media
'''


def function_names(source):
    return [node.name for node in ast.parse(source).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def replace_function(source, name, replacement):
    tree = ast.parse(source)
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise ValueError(f'Expected one function {name}, found {len(matches)}')
    node = matches[0]
    lines = source.splitlines(keepends=True)
    return ''.join(lines[:node.lineno - 1]) + replacement.rstrip() + '\n' + ''.join(lines[node.end_lineno:])


def main(path):
    target = Path(path)
    original = target.read_text(encoding='utf-8')
    before = function_names(original)
    updated = replace_function(original, '_ensure_link', NEW_ENSURE_LINK)
    if 'def _strip_affiliate_link(' not in updated:
        anchor = 'def _ensure_link('
        updated = updated.replace(anchor, NEW_STRIP_LINK + '\n\n' + anchor, 1)
    # Locate the end of _normalize_social_plan using AST, not an ambiguous
    # global text replacement. Do not insert twice on subsequent runs.
    tree = ast.parse(updated)
    normalize = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name == '_normalize_social_plan')
    lines = updated.splitlines(keepends=True)
    start, end = normalize.lineno - 1, normalize.end_lineno
    block = ''.join(lines[start:end])
    if '# Profile-only platforms: do not print raw affiliate links' not in block:
        needle = "    data['creative_prompts'] = _build_creative_prompts(data, article)"
        if block.count(needle) != 1:
            raise ValueError('Cannot find unique creative prompt assignment; refusing to patch')
        block = block.replace(needle, EXTRA_NORMALIZATION + needle)
        updated = ''.join(lines[:start]) + block + ''.join(lines[end:])
    ast.parse(updated)
    after = function_names(updated)
    if after != before[:before.index('_ensure_link')] + ['_strip_affiliate_link'] + before[before.index('_ensure_link'):] and after != before:
        raise ValueError('Unexpected change in existing function inventory')
    if updated == original:
        print('No changes to commit. URL cleanup is already installed.')
        return
    backup = target.with_suffix(target.suffix + '.bak')
    backup.write_text(original, encoding='utf-8')
    target.write_text(updated, encoding='utf-8')
    print(f'Patched: {target}; backup: {backup}')
    print('All existing function names preserved. Python AST syntax valid.')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'social_tools.py')
