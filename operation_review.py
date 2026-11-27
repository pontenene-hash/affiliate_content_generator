"""Conservative external-data screening and logical call telemetry."""
import re
import time
import unicodedata
import json

RULES = [r'ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions', r'(?:system|developer)\s*(?:prompt|message)\s*:', r'(?:以前|上記|これまで)の指示を(?:無視|忘れ)', r'(?:APIキー|システムプロンプト)を(?:出力|公開|送信)', r'\[/?INST\]|<\|(?:system|im_start)\|>']

def screen_external(value):
    text = unicodedata.normalize('NFKC', json.dumps(value, ensure_ascii=False))
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
    return [i for i,p in enumerate(RULES) if re.search(p,text,re.I)]

def error_kind(exc):
    from stage44_operations import status_code
    code = status_code(exc)
    if isinstance(code,int):
        if code == 429: return 'rate_limit'
        if code in (401,403): return 'authorization'
        if code in (408,500,502,503,504): return 'transient'
        if 400 <= code < 500: return 'request_error'
    if isinstance(exc,(TimeoutError,ConnectionError)): return 'transient'
    return 'unknown'

class Meter:
    def __init__(self, call):
        self.call=call
        self.events=[]
    def __call__(self,*args,**kwargs):
        start=time.monotonic(); status='ok'
        try: return self.call(*args,**kwargs)
        except Exception as exc:
            status=error_kind(exc)
            raise
        finally:
            self.events.append({'status':status,'seconds':round(time.monotonic()-start,6)})
    def report(self):
        return {'logical_calls':len(self.events),'seconds':sum(x['seconds'] for x in self.events),'events':list(self.events),'provider_tokens':None}
