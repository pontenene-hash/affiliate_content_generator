import base64
import json
from unittest.mock import Mock
import pytest
import article_history as h

@pytest.mark.parametrize('payload', [{}, {'articles': None}, {'articles': {}}, {'articles': [None]}, {'articles': [{}]}, {'articles': [{'key': ''}]}, {'articles': [{'key': 'a'}, {'key': 'a'}]}])
def test_corrupt_local_history_never_overwritten(payload, tmp_path, monkeypatch):
    path = tmp_path / 'history.json'
    original = json.dumps(payload)
    path.write_text(original)
    monkeypatch.setattr(h, 'HISTORY_PATH', str(path))
    monkeypatch.setattr(h, '_config', lambda: None)
    with pytest.raises(ValueError): h.load_history()
    with pytest.raises(ValueError): h.save_article({'key': 'new'})
    assert path.read_text() == original

def test_corrupt_remote_history_never_written(monkeypatch):
    monkeypatch.setattr(h, '_config', lambda: ('fake', 'owner/repo', 'v2'))
    get = Mock(return_value=Mock(status_code=200, json=lambda: {'content': base64.b64encode(b'{}').decode(), 'sha': 'old'}))
    put = Mock()
    monkeypatch.setattr(h.requests, 'get', get)
    monkeypatch.setattr(h.requests, 'put', put)
    with pytest.raises(ValueError): h.load_history()
    with pytest.raises(ValueError): h.save_article({'key': 'new'})
    put.assert_not_called()

def test_missing_history_initializes_and_rerun_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(h, 'HISTORY_PATH', str(tmp_path / 'history.json'))
    monkeypatch.setattr(h, '_config', lambda: None)
    assert h.load_history() == []
    h.save_article({'key': 'a'})
    h.save_article({'key': 'a'})
    assert h.load_history() == [{'key': 'a'}]
