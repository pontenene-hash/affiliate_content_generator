"""Operational diagnostics: no credentials, no publication approval."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit


def status_code(exc):
    for value in (getattr(exc, 'status_code', None), getattr(exc, 'code', None),
                  getattr(getattr(exc, 'response', None), 'status_code', None)):
        if not isinstance(value, bool) and str(value).isdigit():
            return int(value)
    return None


def safe_error(exc):
    # Never export arbitrary provider messages, URLs, headers or tokens.
    from operation_review import error_kind
    return f'{error_kind(exc)} (HTTP {status_code(exc)})' if status_code(exc) else error_kind(exc)


def wordpress_endpoint(base, suffix):
    parsed = urlsplit(base)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError('WordPress requires a clean HTTPS base URL')
    return base.rstrip('/') + suffix


def reject_redirect(response):
    if 300 <= response.status_code < 400:
        raise RuntimeError('WordPress redirect rejected; configure canonical HTTPS URL')
    response.raise_for_status()


def creative_flags(bundle):
    from stage31_45 import audit_export
    try:
        if not isinstance(bundle, dict):
            raise TypeError('Expected object')
        return audit_export(bundle)['flags']
    except (AttributeError, TypeError, ValueError, KeyError):
        return ['invalid_creative_schema']


def preview_manifest(root, result, limit):
    from stage31_45 import validate_preview, preview_paths
    root = Path(root)
    validate_preview(result, limit, root)
    entries = []
    for i in range(limit):
        dest, post = preview_paths(limit, i)
        files = [dest / f'article.{ext}' for ext in ('md','html','json')]
        bundle = Path('creative_outputs') / f'post_{post}' / 'all_prompts.json'
        files.append(bundle)
        flags = creative_flags(json.loads((root / bundle).read_text(encoding='utf-8')))
        entries.append({'index': i+1, 'creative_flags': flags,
                        'files': [{'path': p.as_posix(), 'sha256': hashlib.sha256((root/p).read_bytes()).hexdigest(), 'bytes': (root/p).stat().st_size} for p in files]})
    return {'schema': 1, 'articles': entries, 'human_review_required': True, 'publication_approved': False}


def verify_manifest(root, manifest):
    """Check expected paths and content; does not authenticate the manifest itself."""
    from stage31_45 import preview_paths, preview_limit
    root = Path(root).resolve()
    entries = manifest['articles']
    limit = preview_limit(len(entries))
    if manifest.get('schema') != 1:
        raise ValueError('Unsupported manifest schema')
    for i, entry in enumerate(entries):
        dest, post = preview_paths(limit, i)
        expected = {str(dest / f'article.{ext}') for ext in ('md','html','json')}
        expected.add(f'creative_outputs/post_{post}/all_prompts.json')
        files = entry['files']
        if entry['index'] != i+1 or len(files) != 4 or {f['path'] for f in files} != expected:
            raise ValueError('Unexpected manifest paths or index')
        for f in files:
            p = root / f['path']
            if (any(q.is_symlink() for q in (p, *p.parents) if q != root and q.is_relative_to(root))
                    or not p.resolve().is_relative_to(root) or not p.is_file()):
                raise ValueError('Missing or unsafe artifact')
            data = p.read_bytes()
            if len(data) != f['bytes'] or hashlib.sha256(data).hexdigest() != f['sha256']:
                raise ValueError('Artifact content mismatch')
    return True
