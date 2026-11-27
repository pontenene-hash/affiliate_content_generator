"""Provider response usage; unknown values remain unknown, never estimated as zero."""
from contextvars import ContextVar
from contextlib import contextmanager
import time
from collections import Counter
from operation_review import error_kind
active = ContextVar('provider_metrics', default=None)
@contextmanager
def capture(events):
    token=active.set(events)
    try: yield
    finally: active.reset(token)

def measured(model, call):
    from run_controls import active_budget
    budget = active_budget.get()
    if budget is not None: budget.reserve()
    start=time.monotonic(); event={'model':model,'status':'ok','input_tokens':None,'output_tokens':None,'total_tokens':None}
    try:
        response=call()
        usage=getattr(response,'usage_metadata',None)
        for key,attr in [('input_tokens','prompt_token_count'),('output_tokens','candidates_token_count'),('total_tokens','total_token_count')]:
            value=getattr(usage,attr,None)
            if type(value) is int and value>=0: event[key]=value
        return response
    except Exception as exc:
        event['status']=error_kind(exc); raise
    finally:
        event['seconds']=time.monotonic()-start
        events=active.get()
        if events is not None: events.append(event)

def report(events):
    known = [e['total_tokens'] for e in events if type(e.get('total_tokens')) is int and e['total_tokens'] >= 0]
    return {'attempts':len(events),'events':list(events),
            'total_tokens':sum(known) if events and len(known)==len(events) else None,
            'known_total_tokens':sum(known) if known else None,
            'unknown_usage_attempts':len(events)-len(known),
            'attempts_by_model':dict(Counter(e['model'] for e in events)),
            'attempts_by_status':dict(Counter(e['status'] for e in events)),
            'actual_cost':None}
