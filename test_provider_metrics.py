from types import SimpleNamespace as S
import pytest
from provider_metrics import capture, measured, report

def test_usage():
    events=[]
    with capture(events):
        measured('lite',lambda:S(usage_metadata=S(prompt_token_count=5,candidates_token_count=7,total_token_count=12)))
    assert report(events)['total_tokens']==12
    assert report(events)['actual_cost'] is None

def test_unknown():
    events=[]
    with capture(events): measured('lite',lambda:S())
    assert report(events)['total_tokens'] is None

def test_error():
    events=[]
    with capture(events), pytest.raises(TimeoutError):
        measured('lite',lambda: (_ for _ in ()).throw(TimeoutError()))
    assert events[0]['status']=='transient'
    assert report(events)['total_tokens'] is None

def test_isolation():
    a=[]; b=[]
    with capture(a):
        with capture(b): measured('lite',lambda:S())
        measured('other',lambda:S())
    assert a[0]['model']=='other' and b[0]['model']=='lite'
