from unittest.mock import Mock
import pytest
import auto_pipeline as p
import article_history as h

@pytest.mark.parametrize('failure', ['products', 'history', 'none'])
def test_batch_closes_database_on_setup_failure_or_empty_run(monkeypatch, failure):
    db = Mock()
    monkeypatch.setattr(p, 'db_connect', lambda: db)
    def fail():
        raise ValueError('invalid stored data')
    monkeypatch.setattr(p, 'load_verified_items', fail if failure == 'products' else lambda: [])
    monkeypatch.setattr(p, 'affiliate_links', lambda: {})
    monkeypatch.setattr(h, 'load_history', fail if failure == 'history' else lambda: [])
    wp = Mock(side_effect=AssertionError('unexpected WordPress write'))
    monkeypatch.setattr(p, 'wp_draft', wp)
    if failure == 'none':
        assert p._run_batch(5, dry_run=True)['batch_status'] == 'no_enabled_products'
    else:
        with pytest.raises(ValueError, match='invalid stored data'):
            p._run_batch(5, dry_run=True)
    db.close.assert_called_once_with()
    wp.assert_not_called()
