"""One real article, no WordPress or persistent history writes."""
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
    import auto_pipeline as pipeline
    import article_history
    import product_registry
    dest = Path('preview_outputs')
    dest.mkdir(exist_ok=True)
    def forbidden(*args, **kwargs):
        raise AssertionError('Persistent write forbidden in preview')
    # Registry is read from main using the read-only workflow token; history is read from validation branch.
    with patch.object(pipeline, 'wp_draft', forbidden), \
         patch.object(pipeline, 'wp_review_gate_check', forbidden), \
         patch.object(pipeline, 'record_saved_draft', forbidden), \
         patch.object(article_history, 'save_article', forbidden), \
         patch.object(product_registry, 'write_items', forbidden):
        result = pipeline.run_batch(limit=1, preview=True, preview_product=os.environ.get("PREVIEW_PRODUCT", "").strip())
    (dest / 'run_report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = result.get('results', [])
    if len(rows) != 1 or rows[0].get('status') != 'preview_only' or rows[0].get('creative') != 'saved':
        raise RuntimeError('Preview incomplete; inspect artifact report')
    if not (dest / 'article.md').is_file() or not Path('creative_outputs/post_0/all_prompts.json').is_file():
        raise RuntimeError('Preview artifacts missing')


if __name__ == '__main__':
    main()
