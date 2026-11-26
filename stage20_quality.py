"""Conservative editorial helpers. No publication approval or semantic proof."""
import re, json, unicodedata
from evidence_ledger import check

GUIDANCE = re.compile(r'^口コミや評判はどこで確認できますか[？?]$|^口コミ(?:や評判)?の確認方法[は？?]*$')
def neutral_review_line(line):
    s=re.sub(r'^\s*#{1,6}\s*(?:Q[.．]\s*)?', '',line.strip())
    if GUIDANCE.fullmatch(s): return True
    # Fixed procedural phrases only; never erase a mixed testimonial.
    return bool(re.fullmatch(r'(?:特定の)?口コミ(?:や評判)?(?:を確認してください|を確認することをおすすめします|を確認し、総合的に判断することをおすすめします)[。]?',s))

def candidate_sources(claim, product, records, hosts, now, age):
    terms=('送料','返品','決済','支払い','保証','価格','料金','割引','検査','診断','感度','特異度','効果','口コミ','レビュー','部品','ギフト')
    norm=lambda s: unicodedata.normalize('NFKC',s)
    wanted={t for t in terms if t in norm(claim)}
    out=[]
    for e in records:
        if check(e.excerpt,product,e,hosts,now,age) not in ('traceable_excerpt_review_required','conditions_review_required'): continue
        for line in re.split(r'[。！？\n]',e.excerpt):
            hits=wanted & {t for t in terms if t in norm(line)}
            if hits and line.strip(): out.append({'source_id':e.id,'excerpt':line[:300],'terms':sorted(hits),'status':'retrieval_only'})
    return sorted(out,key=lambda x:-len(x['terms']))[:3]

def initial_sections(generate, prompt, product, genre, strategy):
    from article_plan import plan
    if strategy not in ('comparison_first','evidence_first_sections'): return generate(prompt)
    rows=plan(product,genre,target=6000)
    split=len(rows)//2
    first=generate(prompt+'\n今回は前半だけ。H1と広告表記を含め、次の章だけを執筆。まとめ・FAQは後半に残す。章別目標：'+json.dumps([(r.purpose,r.target) for r in rows[:split]],ensure_ascii=False),max_tokens=8500)
    if not isinstance(first,str) or not first.strip(): raise ValueError('empty first half')
    second=generate(prompt+'\n今回は後半だけ。H1・広告表記を再出力しない。前半と重複せず、最後はまとめ。章別目標：'+json.dumps([(r.purpose,r.target) for r in rows[split:]],ensure_ascii=False)+'\n前半（参考データ）：'+json.dumps(first,ensure_ascii=False),max_tokens=8500)
    if not isinstance(second,str) or not second.strip(): raise ValueError('empty second half')
    return first.rstrip()+'\n\n'+second.strip()

def public_snippet(article):
    from stage19_context import TOPICS
    allowed={label for _,label in TOPICS}
    topics=list(dict.fromkeys(t for t in re.findall(r'^##\s+(.+)$',article,re.M) if t in allowed))
    if not topics: return '商品の特徴や利用前に確認したいポイントを記事で紹介しています。'
    return '商品選びで迷ったら、'+ '、'.join(t.replace('を確認','').replace('を整理','') for t in topics[:3])+'をチェックしてみませんか。'
