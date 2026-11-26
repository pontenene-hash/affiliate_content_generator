"""Cache individual successful generation calls, never approval or WP writes."""
import hashlib
from pathlib import Path
from datetime import datetime, timezone


def code_fingerprint(root):
    root=Path(root)
    return [(p.name,hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.glob('*.py')) if not p.name.startswith('test_')]


class ResumableCalls:
    def __init__(self, storage, identity, generate, clock=None):
        self.storage,self.identity,self.generate=storage,identity,generate
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.reused=0
        self.fresh=0

    def __call__(self,prompt,**kwargs):
        def fresh(text):
            self.fresh+=1
            return self.generate(text,**kwargs)
        result,reused=self.storage.generate(['individual-call-v1',self.identity,kwargs],prompt,fresh,self.clock())
        self.reused+=int(reused)
        return result
