"""Offline release safeguards. No network, publication or automatic approval."""
import re, unicodedata, time
from operation_review import error_kind
from cross_review import revision_review

def recover(call, *, attempts=2, sleep=time.sleep):
    if type(attempts) is not int or not 1 <= attempts <= 3: raise ValueError('attempts')
    for i in range(attempts):
        try: return call()
        except Exception as e:
            if error_kind(e) != 'transient' or i+1 == attempts: raise
            sleep(2**i)

def normalized(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC',s)).casefold()

def similarity(a,b):
    def grams(s):
        s=normalized(s); return {s[i:i+5] for i in range(max(0,len(s)-4))}
    x,y=grams(a),grams(b)
    return len(x&y)/len(x|y) if x and y else float(bool(normalized(a) and normalized(a)==normalized(b)))

def review_quotes(article, sources):
    # Only explicitly attributed testimonial quotations; source existence is not authenticity.
    quotes=[]
    pattern=r'(?:口コミ|レビュー|体験談)[^。！？]{0,40}?[「『]([^」』]+)[」』]'
    end=-1
    for match in re.finditer(pattern,article):
        if match.start()<end: continue
        quotes.append(match.group(1))
        end=match.end()
        while True:
            continuation=re.match(r'[ \t\n>＊*・\-、]{0,20}[「『]([^」』]+)[」』]',article[end:])
            if not continuation: break
            quotes.append(continuation.group(1)); end+=continuation.end()
    return [{'quote':q,'candidate_urls':[s['url'] for s in sources if s.get('verified_by_human') is True and s.get('url','').startswith('https://') and q in s.get('text','')], 'human_review_required':True} for q in quotes]

def partial_patch(article, old, new, quality):
    if not old or article.count(old)!=1 or not new: return article, {'accepted':False,'reason':'ambiguous'}
    candidate=article.replace(old,new,1)
    try: audit=revision_review(article,candidate,quality)
    except Exception: return article, {'accepted':False,'reason':'review_error'}
    accepted=not audit['new_issues'] and not audit['remaining_issues']
    return (candidate if accepted else article),dict(audit,accepted=accepted)

def model_compare(models, cases, judge):
    results=[]
    for name,call in models.items():
        for case in cases:
            start=time.monotonic()
            try: result=judge(case,call(case)); status='ok'
            except Exception: result=None; status='error'
            results.append(dict(model=name,case=case['id'],result=result,status=status,seconds=time.monotonic()-start))
    return results

def batch_preview(items, generate, review):
    results=[]
    for item in items:
        try: result=review(generate(item)); status='held'
        except Exception: result=None; status='error'
        results.append(dict(id=item['id'],status=status,review=result,approved=False))
    return results
