"""Local draft body index; no remote reads or publication authority."""
import sqlite3
from review_storage import digest

class DraftIndex:
    def __init__(self,path):
        self.path=path
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS draft_index (scope TEXT, id TEXT, body TEXT, checksum TEXT, PRIMARY KEY(scope,id))')
    def save(self,scope,id,body):
        if not scope or not str(id) or not body.strip(): raise ValueError('missing draft identity')
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT OR REPLACE INTO draft_index VALUES (?,?,?,?)',(scope,str(id),body,digest(body)))
    def previous(self,scope,exclude):
        with sqlite3.connect(self.path) as db:
            rows=db.execute('SELECT id,body,checksum FROM draft_index WHERE scope=? AND id<>? ORDER BY id',(scope,str(exclude))).fetchall()
        if any(digest(body)!=checksum for _,body,checksum in rows): raise ValueError('draft index integrity failure')
        return [{'id':id,'article':body} for id,body,_ in rows]
