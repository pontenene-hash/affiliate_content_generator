"""Conservative local repair of identical adjacent prose paragraphs only."""
import re
from collections import Counter

def repair_duplicates(md, quality, check, count):
    # Fail closed for complex markup: do not rewrite structured documents.
    if re.search(r'(?m)^\s*(?:`{3,}|~{3,})|<!--|-->|<[^>]+>', md):
        return md,quality,'構造保護：部分修正対象外'
    parts = re.split(r'(\n[^\S\n]*\n)', md)
    removed = 0
    previous = None
    for i in range(0,len(parts),2):
        raw=parts[i]; b=raw.strip()
        if previous==b and len(b)>=30 and not re.search(r'[#<>\[\]`|]|https?://|広告|PR|注意|相談|[「」『』]|口コミ',b,re.I) and '\n' not in b and not re.match(r'\s*(?:[-+*>]|\d+[.)]| {4}|\t)',raw):
            parts[i]=''; parts[i-1]=''; removed+=1
        else:
            previous=b
    if not removed: return md,quality,'部分修正対象なし'
    candidate=''.join(parts)
    try:
        after=check(candidate)
        def issues(q): return Counter((x.get('code'),x.get('message')) for x in q['issues'])
        if issues(after)-issues(quality) or len(after['issues'])>=len(quality['issues']) or count(candidate)<min(count(md),5000):
            return md,quality,'部分修正不採用：品質維持'
        return candidate,after,'重複段落の部分修正採用：人による確認必須'
    except Exception:
        return md,quality,'部分修正再審査失敗：原稿保持'
