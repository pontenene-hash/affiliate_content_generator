"""Offline prototype: bounded section completion, no publishing or network access."""
import re
from collections import Counter


def complete_sections(article, generate, check, count, minimum=5000, maximum=8000, attempts=3, contextual_generate=None):
    audit=[]
    attempted=Counter()
    def norm(s): return re.sub(r"[\s\W_]+", "", s).casefold()
    quality=check(article)
    for _ in range(attempts):
        if count(article)>=minimum: break
        sections=list(re.finditer(r'^##\s+(.+)$',article,re.M))
        eligible=[(m,sections[i+1].start() if i+1<len(sections) else len(article)) for i,m in enumerate(sections) if not re.search(r'まとめ|FAQ|よくある質問|結論',m.group(1),re.I)]
        if not eligible: break
        eligible.sort(key=lambda p:(attempted[p[0].group(1)],count(article[p[0].end():p[1]])))
        m,end=eligible[0]
        attempted[m.group(1)] += 1
        try:
            extra=(contextual_generate(m.group(1), article[m.end():end], minimum-count(article), article, tuple(audit)) if contextual_generate else generate(m.group(1),article[m.end():end],minimum-count(article)))
            if not isinstance(extra,str) or not extra.strip() or re.search(r'^\s*#|https?://|<[^>]+>',extra,re.M):
                audit.append('invalid output'); continue
            extra=extra.strip()
            parts=[norm(p) for p in re.split(r'\n\s*\n|(?<=[。！？])',extra) if norm(p)]
            if not parts or len(parts)!=len(set(parts)) or any(p in norm(article) for p in parts):
                audit.append('duplicate output'); continue
            candidate=article[:end].rstrip()+'\n\n'+extra+'\n\n'+article[end:]
            if not count(article)<count(candidate)<=maximum:
                audit.append('invalid length'); continue
            new=check(candidate)
            issues=lambda q:Counter((i['code'],str(i.get('message',''))) for i in q.get('issues',[]) if i['code']!='article_too_short')
            if issues(new)-issues(quality):
                audit.append('new quality issue: '+', '.join(sorted({k[0] for k in issues(new)-issues(quality)}))); continue
            article,quality=candidate,new
            audit.append('accepted section: '+m.group(1))
        except Exception as exc:
            audit.append('retained original: '+type(exc).__name__)
    if count(article)<minimum:
        audit.append("minimum not reached; human review required")
    return article,quality,audit
