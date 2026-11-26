"""Advisory exact-text evidence retrieval, never semantic approval."""
import re
from evidence_ledger import check
from claim_countercheck import countercheck
from source_review import source_review, followup_plan
from review_report import build_review_report

PATTERNS = {'medical': r'治る|治療|予防|診断|感度|特異度|改善|副作用|効果', 'commercial': r'円|送料|無料|返品|解約|保証|割引|税込', 'comparison': r'最安|最高|唯一|No\.1|より優れ', 'testimonial': r'口コミ|体験談|利用者の声'}

def audit_claims(article, product, records, hosts, now):
    results = []
    for line in article.splitlines():
        if line.lstrip().startswith('#'): continue
        for sentence in re.split(r'(?<=。)|(?<=！)|(?<=？)', line):
            sentence = sentence.strip()
            kinds = [k for k,p in PATTERNS.items() if re.search(p,sentence)]
            if not kinds: continue
            age = 1 if 'commercial' in kinds else 7
            matches = [e for e in records if check(sentence,product,e,hosts,now,age)=='traceable_excerpt_review_required']
            results.append({'claim': sentence, 'kinds': kinds, 'source_ids': [e.id for e in matches], 'status': 'exact_candidate' if matches else 'unverified', 'human_review_required': True, 'counter_candidates': countercheck(sentence, product, records, hosts, now), 'source_review': source_review(sentence, product, records, hosts, now, age)})
    audit = {'claims': results, 'followup_queries': followup_plan(product, results), 'approved': False, 'limitations': 'Keyword extraction and exact matching only; numeric counter-candidates only; no semantic entailment or definitive contradiction detection.'}
    audit['review_report'] = build_review_report(audit, product, records, hosts, now)
    return audit
