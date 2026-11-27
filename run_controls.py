"""Optional per-process generation attempt cap and advisory maintenance summaries."""
from contextvars import ContextVar
from contextlib import contextmanager
from collections import Counter
from datetime import datetime, timedelta

active_budget = ContextVar('active_budget', default=None)

class BudgetExhausted(RuntimeError):
    pass

class AttemptBudget:
    def __init__(self, limit=None):
        if limit is not None and (type(limit) is not int or limit < 1):
            raise ValueError('positive attempt limit required')
        self.limit, self.attempts = limit, 0
    def reserve(self):
        if self.limit is not None and self.attempts >= self.limit:
            raise BudgetExhausted('Generation attempt budget exhausted')
        self.attempts += 1
    def report(self):
        return {'limit': self.limit, 'attempts': self.attempts,
                'remaining': None if self.limit is None else self.limit-self.attempts,
                'scope': 'measured generation calls in this batch only'}

@contextmanager
def budget_scope(budget):
    token = active_budget.set(budget)
    try: yield
    finally: active_budget.reset(token)

def freshness(last_checked, now, source_change, days=30):
    if now.utcoffset() is None or type(days) is not int or days < 1:
        raise ValueError('aware time and positive interval required')
    if source_change == 'changed': return 'review_changed_source'
    if source_change == 'unavailable': return 'review_unavailable_source'
    try:
        age = now - datetime.fromisoformat(last_checked)
    except (TypeError, ValueError, OverflowError): return 'review_unknown_date'
    if age < timedelta(0): return 'review_unknown_date'
    return 'review_due' if age >= timedelta(days=days) else 'recent_check_not_verified'

def batch_overview(results):
    counts = Counter(r.get('status', 'unknown') for r in results)
    return {'status_counts': dict(counts), 'record_count': len(results),
            'publication_verified': False}
