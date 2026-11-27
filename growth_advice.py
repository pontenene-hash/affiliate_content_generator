"""Deterministic editorial suggestions; no ranking, conversion or publication guarantees."""
import re
import unicodedata
from datetime import datetime
from run_controls import freshness

def norm(s):
    return unicodedata.normalize('NFKC', s).casefold().strip() if isinstance(s,str) else ''

def priority(item):
    fields = ('approved', 'official_source_available', 'affiliate_link_verified', 'reader_fit')
    missing = [f for f in fields if item.get(f) is not True]
    return {'eligible_for_review': not missing, 'missing': missing, 'score': len(fields)-len(missing), 'basis': 'explicit supplied flags only'}

def related_drafts(keyword, previous, limit=3):
    terms = set(norm(keyword).split())
    if not terms or type(limit) is not int or limit < 1: return []
    matches = []
    seen = set()
    for row in previous:
        if not isinstance(row,dict): continue
        body = row.get('article', '')
        if not isinstance(body,str): continue
        title = next((s[2:].strip() for s in body.splitlines() if s.startswith('# ')), '')
        score = sum(t in norm(title) for t in terms)
        if score and title and row.get('id') is not None:
            if str(row['id']) in seen: continue
            seen.add(str(row['id']))
            matches.append({'draft_id':str(row['id']), 'title':title, 'matched_terms':score, 'link_verified':False})
    return sorted(matches,key=lambda r:(-r['matched_terms'],r['draft_id']))[:limit]

def title_review(title, keyword):
    t, k = norm(title), norm(keyword)
    return {'length':len(title), 'keyword_present':bool(k and all(x in t for x in k.split())), 'absolute_claim_review':any(x in t for x in ('絶対','必ず','100%','完全に')), 'conversion_verified':False}

def cta_review(article, affiliate_url):
    return {'expected_url_present':bool(affiliate_url and affiliate_url in re.findall(r'https?://[^\s<>\)\]"\']+', article)), 'disclosure_present':bool(re.search(r'広告|PR|プロモーション',article,re.I)), 'conversion_verified':False}

def rewrite_candidates(records, now, days=30):
    result=[]
    for r in records:
        state=freshness(r.get('last_checked'),now,r.get('source_change'),days)
        if state!='recent_check_not_verified': result.append({'id':r.get('id'),'reason':state})
    return result

def advisory(article,title,keyword,affiliate_url,previous):
    return {'title':title_review(title,keyword),'cta':cta_review(article,affiliate_url),'related_drafts':related_drafts(keyword,previous),'publication_approved':False}

def ranked_candidates(items):
    """Advisory only: unknown flags never become verified facts."""
    return sorted([{'id': str(r['id']), **priority(r)} for r in items
                   if isinstance(r,dict) and r.get('id') is not None],
                  key=lambda r:(not r['eligible_for_review'],-r['score'],r['id']))

def compare_titles(titles, keyword):
    rows = [{'title': t, **title_review(t,keyword)} for t in dict.fromkeys(titles)
            if isinstance(t,str) and t.strip()]
    return sorted(rows,key=lambda r:(r['absolute_claim_review'],not r['keyword_present'],abs(r['length']-32)))

def performance_summary(records):
    """Only aggregate explicitly supplied, valid counts; no attribution inference."""
    totals = dict(impressions=0, clicks=0, conversions=0)
    accepted = 0
    for r in records:
        if not isinstance(r,dict): continue
        values = [r.get(k) for k in totals]
        if any(type(v) is not int or v<0 for v in values): continue
        if not values[0]>=values[1]>=values[2]: continue
        for k,v in zip(totals,values): totals[k]+=v
        accepted+=1
    return {**totals,'accepted':accepted,'ctr':totals['clicks']/totals['impressions'] if totals['impressions'] else None,
            'conversion_rate':totals['conversions']/totals['clicks'] if totals['clicks'] else None,
            'attribution_verified':False}
