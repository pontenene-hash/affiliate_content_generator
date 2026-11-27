"""Conservative validation-only recovery and operational safeguards."""
import copy
import re
from stage23_creative import audit_bundle


def repair_cta(bundle):
    result=copy.deepcopy(bundle)
    plan=result.get('social_plan',{})
    link=result.get('affiliate_url','')
    changes=[]
    entries=[(f'x/{i+1}',p,'text') for i,p in enumerate(plan.get('x_posts',[]))]
    entries += [(k,plan.get(k,{}),'description' if k=='youtube' else 'text') for k in ('threads','facebook','line','youtube')]
    for path,obj,key in entries:
        value=obj.get(key,'')
        # Only replace a standalone CTA line with an exact destination; leave ambiguous prose for review.
        if link and isinstance(value,str):
            pattern=r'(?m)^(?:記事はこちら|記事を読む|ブログはこちら|ブログを読む)[：:]?[ \t]*'+re.escape(link)+r'[ \t]*$'
            revised=re.sub(pattern,lambda _: '【PR】広告主の商品ページ：'+link,value)
            if revised!=value:
                obj[key]=revised; changes.append(path)
    return result,changes


def retry_kind(exc):
    from operation_review import error_kind
    from stage44_operations import status_code
    code=str(status_code(exc) or '')
    if code=='404': return 'model_missing'
    if code in ('401','403','429'): return 'stop_batch'
    if code in ('408','500','502','503','504'): return 'retry'
    if code: return 'stop_request'
    return 'retry' if error_kind(exc)=='transient' else 'stop_request'


def valid_draft_response(data):
    if not isinstance(data,dict) or data.get('status')!='draft' or data.get('review') not in ('needs_review','approved'):
        raise RuntimeError('WordPress draft status not verified')
    value=data.get('id')
    if isinstance(value,bool) or not re.fullmatch(r'[1-9][0-9]*',str(value)):
        raise RuntimeError('WordPress draft ID not verified')
    return int(value)
