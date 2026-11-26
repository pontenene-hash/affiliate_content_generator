"""Opt-in local snapshots and generation checkpoints; never caches approval."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone, timedelta


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


class ReviewStorage:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS snapshots (key TEXT PRIMARY KEY, payload TEXT NOT NULL, checksum TEXT NOT NULL, saved TEXT NOT NULL)')

    def _read(self, key, now, ttl):
        with sqlite3.connect(self.path) as db:
            row = db.execute('SELECT payload,checksum,saved FROM snapshots WHERE key=?', (key,)).fetchone()
        if not row: return None
        try:
            payload = json.loads(row[0]); age = now - datetime.fromisoformat(row[2])
            if digest(payload) != row[1] or not timedelta(0) <= age <= ttl: return None
            return payload
        except (ValueError, TypeError): return None

    def _write(self, key, payload, now):
        if now.utcoffset() is None: raise ValueError('timezone required')
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?)', (key,json.dumps(payload,ensure_ascii=False),digest(payload),now.isoformat()))

    def observe(self, product, page, now):
        # Only compare freshly fetched content; do not substitute cached evidence.
        sources = sorted([(s['url'],s['text']) for s in page.get('sources',[])])
        if not sources: return 'unavailable'
        key = 'source:' + digest([product,page['url']])
        previous = self._read(key,now,timedelta(days=30))
        payload = {'sources':sources}
        # JSON round-trip normalizes tuples.
        payload = json.loads(json.dumps(payload))
        self._write(key,payload,now)
        return 'first_or_expired' if previous is None else 'unchanged' if previous == payload else 'changed'

    def generate(self, identity, prompt, generate, now):
        key = 'generation:v1:' + digest([identity,prompt])
        cached = self._read(key,now,timedelta(hours=24))
        if isinstance(cached, str) and cached.strip(): return cached, True
        result = generate(prompt)
        if not isinstance(result,str) or not result.strip(): raise ValueError('empty generation')
        self._write(key,result,now)
        return result, False
