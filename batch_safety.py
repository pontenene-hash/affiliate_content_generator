"""Local process coordination and advisory release diagnostics."""
from contextlib import contextmanager
from pathlib import Path
import fcntl
import json
import os
import tempfile

@contextmanager
def exclusive_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another local operation is running') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)

def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, indent=2, allow_nan=False)
            out.write('\n'); out.flush(); os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def atomic_text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(value)
            out.flush(); os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def review_queue(rows):
    """Conservative, advisory queue; never treats a draft as approved."""
    result=[]
    for index, row in enumerate(rows, 1):
        status=row.get('status') if isinstance(row,dict) else None
        result.append({'index':index, 'action':'inspect_preview' if status=='preview_only' else 'inspect_draft' if status in ('draft','held_wp_draft') else 'review_quality' if status=='quality_review_required' else 'research_sources' if status=='research_required' else 'supply_link' if status=='manual_link_required' else 'investigate_status', 'publication_approved':False})
    return result
