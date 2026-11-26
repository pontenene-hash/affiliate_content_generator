"""Conservative local repair of identical adjacent prose paragraphs only."""
import re
from collections import Counter

def repair_duplicates(md, quality, check, count):
    parts = re.split(r'(\n\s*\n)', md)
    removed = 0
    for i in range(2,len(parts),2):
        a,b=parts[i-2].strip(),parts[i].strip()
        if a==b and len(b)>=30 and not re.search(r'[#<>\[\]`|]|https?://|広告|PR|注意|相談',b,re.I) and '\n' not in b:
            parts[i]=''; removed+=1
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
