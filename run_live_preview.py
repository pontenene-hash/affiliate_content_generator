"""One to five real articles, no WordPress or persistent history writes."""
import json
import os
from pathlib import Path
from unittest.mock import patch


def main():
    if os.environ.get('GITHUB_REF') != 'refs/heads/feature-affiliate-v2-validation':
        raise RuntimeError('Validation branch required')
    for key in ('WP_SITE_URL', 'WP_URL', 'WP_USERNAME', 'WP_APP_PASSWORD', 'WP_SAVE_HELD_DRAFTS'):
        os.environ.pop(key, None)
    for key in ('GEMINI_API_KEY', 'BRAVE_API_KEY', 'GH_HISTORY_TOKEN', 'GITHUB_TOKEN'):
        if not os.environ.get(key):
            raise RuntimeError(f'Missing required credential: {key}')
    from stage31_45 import preview_limit, validate_preview, validate_preview_identity
    limit = preview_limit(os.environ.get('PREVIEW_LIMIT', '1'))
    import auto_pipeline as pipeline
    import article_history
    import product_registry
    dest = Path('preview_outputs')
    if dest.exists() or Path('creative_outputs').exists():
        raise RuntimeError('Preview output already exists; use a clean workspace')
    dest.mkdir(exist_ok=False)
    def forbidden(*args, **kwargs):
        raise AssertionError('Persistent write forbidden in preview')
    # Registry is read from main using the read-only workflow token; history is read from validation branch.
    with patch.object(pipeline, 'wp_draft', forbidden), \
         patch.object(pipeline, 'wp_review_gate_check', forbidden), \
         patch.object(pipeline, 'record_saved_draft', forbidden), \
         patch.object(article_history, 'save_article', forbidden), \
         patch.object(product_registry, 'write_items', forbidden):
        result = pipeline.run_batch(limit=limit, preview=True, preview_product=os.environ.get("PREVIEW_PRODUCT", "").strip())
    (dest / 'run_report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    validate_preview(result, limit)
    validate_preview_identity(result, limit)
    from stage44_operations import preview_manifest, verify_manifest
    manifest = preview_manifest(Path("."), result, limit)
    verify_manifest(Path("."), manifest)
    (dest / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == '__main__':
    main()
