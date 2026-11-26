"""Advisory release checks; no network or publication authority."""
from release_review import similarity, review_quotes

def release_audit(article, previous=(), sources=(), threshold=.8):
    if not 0 < threshold <= 1: raise ValueError('threshold')
    matches=[]
    for entry in previous:
        score=similarity(article,entry['article'])
        if score>=threshold: matches.append({'id':entry['id'],'score':score})
    quotes=review_quotes(article,sources)
    return {'similar_articles':matches,'quotes':quotes,'history_compared':len(previous),'human_review_required':True,'approved':False}

def attach_release_audit(quality, audit):
    result=dict(quality)
    issues=list(result.get('issues',[]))
    if audit['similar_articles']: issues.append({'code':'similar_article_review','message':'類似記事の確認が必要'})
    if any(not q['candidate_urls'] for q in audit['quotes']): issues.append({'code':'unverified_quote_review','message':'口コミ原文の確認が必要'})
    if len(issues)>len(result.get('issues',[])):
        result.update(approved=False,status='quality_review_required',issues=issues)
    return result
