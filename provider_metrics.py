"""Provider response usage; unknown values remain unknown, never estimated as zero."""
from contextvars import ContextVar
from contextlib import contextmanager
import time
from operation_review import error_kind
active = ContextVar('provider_metrics', default=None)
@contextmanager
def capture(events):
    token=active.set(events)
    try: yield
    finally: active.reset(token)

def measured(model, call):
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
    return {'attempts':len(events),'events':list(events),'total_tokens':sum(e['total_tokens'] for e in events) if events and all(e['total_tokens'] is not None for e in events) else None,'actual_cost':None}
