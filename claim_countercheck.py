"""Conservative counter-evidence retrieval; flags candidates, never approves."""
import re
import unicodedata
from evidence_ledger import check

MONEY = re.compile(r'(送料|手数料|価格|料金|定価)(?:は|が|：|:)?\s*(無料|[0-9,]+円)')
CONDITION = re.compile(r'以上|未満|場合|限定|一部|除く|対象|条件|初回|地域|別途|税込|税別|から|まで|通常|キャンペーン')

def amounts(text):
    return [(m[1], 0 if m[2]=='無料' else int(m[2][:-1].replace(',',''))) for m in MONEY.finditer(unicodedata.normalize('NFKC',text))]

def countercheck(claim, product, records, hosts, now):
    flags=[]
    wanted=amounts(claim)
    for e in records:
        # Validate provenance independently of whether the claim matches.
        if not isinstance(e.excerpt,str) or not e.excerpt.strip(): continue
        state=check(e.excerpt,product,e,hosts,now,1)
        if state not in ('traceable_excerpt_review_required','conditions_review_required'): continue
        for sentence in re.split(r'[。！？\n]',e.excerpt):
            for key,value in amounts(sentence):
                for k,v in wanted:
                    if k==key and v!=value:
                        flags.append({'source_id':e.id,'field':key,'article_yen':v,'source_yen':value,'status':'scope_review' if e.conditions or CONDITION.search(sentence) or CONDITION.search(claim) else 'possible_conflict'})
    return flags
