"""Summarize actual batch outcomes without treating held drafts as approved."""
from collections import Counter

def summarize(rows, requested):
    counts=Counter(r.get('status','unknown') for r in rows)
    ids=[r['wp_id'] for r in rows if r.get('wp_id') is not None]
    duplicate_ids=sorted(k for k,v in Counter(ids).items() if v>1)
    return {'requested':requested,'attempted':len(rows),'statuses':dict(counts),'saved_drafts':counts['draft']+counts['held_wp_draft'],'preview_only':counts['preview_only'],'errors':counts['error'],'duplicate_wp_ids':duplicate_ids,'creative_failures':sum(str(r.get('creative','')).startswith('error') for r in rows),'human_review_required':True,'publication_approved':False}
