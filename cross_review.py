"""Advisory cross-channel and revision checks; never grants approval."""
import re
import unicodedata
from claim_countercheck import amounts
from claim_review import PATTERNS
from difflib import SequenceMatcher

EXTRA = re.compile(r'必ず|絶対|100\s*%|副作用なし|リスクなし|完全に|誰でも|全員|最安|No\.?1',re.I)

def normalize(s):
    return unicodedata.normalize('NFKC',s).strip()

def sentences(s):
    return [normalize(x) for x in re.split(r'(?<=[。！？])|\n',s) if x.strip()]

def strings(value,path=''):
    if isinstance(value,str): yield path,value
    elif isinstance(value,dict):
        for k,v in value.items():
            if k not in ('affiliate_url','post_id','cross_review'): yield from strings(v,path+'/'+str(k))
    elif isinstance(value,list):
        for i,v in enumerate(value): yield from strings(v,path+'/'+str(i))

def cross_review(article,bundle):
    original=set(sentences(article)); flags=[]
    for path,text in strings(bundle):
        for sentence in sentences(text):
            if sentence in original: continue
            kinds=[k for k,p in PATTERNS.items() if re.search(p,sentence)]
            if EXTRA.search(sentence): kinds.append('absolute_or_superlative')
            if kinds: flags.append(dict(path=path,claim=sentence,kinds=kinds,status='new_wording_review'))
    return dict(flags=flags,approved=False,human_review_required=True,limitations='Exact sentence comparison; instructions and negations may be flagged; paraphrases not verified.')

def source_changes(old,new):
    a=sentences(old); b=sentences(new); changes=[]
    for op,i,j,k,l in SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if op=='equal': continue
        before=a[i:j]; after=b[k:l]; text=' '.join(before+after)
        kinds=[key for key,p in PATTERNS.items() if re.search(p,text)]
        if amounts(text): kinds.append('money')
        changes.append(dict(operation=op,before=before,after=after,kinds=kinds or ['other']))
    return changes

def revision_review(before,after,quality_check):
    old=quality_check(before); new=quality_check(after)
    # Never infer approval from a successful comparison.
    def keys(result):
        return {str(x) for x in result.get('issues',[])}
    return dict(new_issues=sorted(keys(new)-keys(old)),remaining_issues=sorted(keys(new)),changes=source_changes(before,after),approved=False,human_review_required=True)
