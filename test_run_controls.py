from datetime import datetime, timezone, timedelta
import pytest
from run_controls import AttemptBudget, BudgetExhausted, budget_scope, freshness, batch_overview, active_budget
from provider_metrics import measured

def test_cap_blocks_before_call():
    b=AttemptBudget(1); calls=[]
    with budget_scope(b):
        measured('m', lambda: calls.append(1))
        with pytest.raises(BudgetExhausted): measured('m', lambda: calls.append(2))
    assert calls==[1] and b.report()['remaining']==0
    assert active_budget.get() is None

def test_failure_counts():
    b=AttemptBudget(1)
    with budget_scope(b):
        with pytest.raises(TimeoutError): measured('m', lambda: (_ for _ in ()).throw(TimeoutError()))
    assert b.attempts==1

@pytest.mark.parametrize('limit',[0,-1,True,1.5])
def test_invalid(limit):
    with pytest.raises(ValueError): AttemptBudget(limit)

def test_unlimited():
    b=AttemptBudget(); b.reserve(); assert b.report()['remaining'] is None

@pytest.mark.parametrize('age,change,expected',[(0,'changed','review_changed_source'),(0,'unavailable','review_unavailable_source'),(30,'unchanged','review_due'),(29,'unchanged','recent_check_not_verified'),(-1,'unchanged','review_unknown_date')])
def test_freshness(age,change,expected):
    now=datetime.now(timezone.utc)
    assert freshness((now-timedelta(days=age)).isoformat(),now,change)==expected

def test_missing_date():
    assert freshness(None,datetime.now(timezone.utc),'unchanged')=='review_unknown_date'

def test_overview():
    assert batch_overview([{'status':'draft'},{'status':'error'},{'status':'draft'}])=={'status_counts':{'draft':2,'error':1},'record_count':3,'publication_verified':False}
