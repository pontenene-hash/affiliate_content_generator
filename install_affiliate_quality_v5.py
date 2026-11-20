"""Idempotent additive V5 hook installer with backup and AST checks."""
import ast
from pathlib import Path
import sys

MARK = '# AFFILIATE_QUALITY_V5_HOOK'
HOOK = '''\n\n# AFFILIATE_QUALITY_V5_HOOK\n_original_build_bundle_v5 = build_bundle\n\ndef build_bundle(article, title, product, post_id, affiliate_url, api_key, model):\n    from affiliate_quality_v5 import review_bundle\n    original = _original_build_bundle_v5(article, title, product, post_id, affiliate_url, api_key, model)\n    return review_bundle(original)\n'''

def install(target):
    path = Path(target)
    src = path.read_text(encoding='utf-8')
    if MARK in src:
        if src.rstrip().endswith(HOOK.rstrip()) and src.count(MARK) == 1:
            print('V5 hook already installed; no changes')
            return
        raise ValueError('V5 marker exists but hook differs; manual review required')
    tree = ast.parse(src)
    if sum(isinstance(n, ast.FunctionDef) and n.name == 'build_bundle' for n in tree.body) != 1:
        raise ValueError('Expected exactly one build_bundle function')
    updated = src.rstrip() + HOOK
    compile(updated, str(path), 'exec')
    backup = path.with_suffix(path.suffix + '.v5.bak')
    if backup.exists():
        raise FileExistsError('Existing backup; refusing overwrite: ' + str(backup))
    backup.write_text(src, encoding='utf-8')
    path.write_text(updated, encoding='utf-8')
    print('Installed V5 hook:', path, '| Backup:', backup)

if __name__ == '__main__':
    install(sys.argv[1] if len(sys.argv) > 1 else 'auto_creative.py')
