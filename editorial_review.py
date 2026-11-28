"""Offline editorial findings; evidence records are supplied, never verified online."""
import re
from datetime import date
from urllib.parse import urlsplit
from growth_advice import norm


def evidence_status(row, article, today=None):
    today = today or date.today()
    if not isinstance(row, dict):
        return 'invalid_record'
    fields = ('claim', 'source_url', 'checked_on', 'quote')
    if any(not isinstance(row.get(k), str) or not row[k].strip() for k in fields):
        return 'incomplete'
    try:
        parsed = urlsplit(row['source_url'])
        checked = date.fromisoformat(row['checked_on'])
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            return 'invalid_source'
        if checked > today:
            return 'future_date'
    except ValueError:
        return 'invalid_record'
    if row['claim'] not in article:
        return 'claim_changed'
    if row['claim'] not in row['quote']:
        return 'quote_mismatch'
    if (today - checked).days > 30:
        return 'stale'
    return 'supplied_unverified'


def editorial_review(article, evidence=(), today=None):
    if not isinstance(article, str) or not isinstance(evidence, (list, tuple)):
        raise ValueError('本文と根拠一覧の形式が不正です')
    # Exclude fenced code from prose structure checks.
    prose = re.sub(r'```.*?```', '', article, flags=re.S)
    headings = re.findall(r'^#{2,3}\s+(.+)$', prose, re.M)
    seen, duplicates = set(), []
    for heading in headings:
        key = norm(heading)
        if key in seen:
            duplicates.append(heading)
        seen.add(key)
    faq = [h for h in headings if re.search(r'FAQ|よくある質問', h, re.I)]
    findings = []
    if duplicates:
        findings.append({'code': 'duplicate_heading', 'detail': duplicates, 'action': '同じ見出しの内容を比較し、条件を残して統合してください'})
    if len(faq) > 1:
        findings.append({'code': 'fragmented_faq', 'detail': faq, 'action': 'FAQを1か所にまとめ、同じ質問を整理してください'})
    records = [{'claim': r.get('claim', '') if isinstance(r, dict) else '',
                'status': evidence_status(r, article, today)} for r in evidence]
    invalid_evidence = [r for r in records if r['status'] != 'supplied_unverified']
    if invalid_evidence:
        findings.append({'code': 'invalid_evidence', 'detail': invalid_evidence,
                         'action': '根拠記録の未入力・日付・本文と引用の一致を見直してください'})
    claims = [line.strip() for line in prose.splitlines()
              if re.search(r'\d[\d,]*\s*円|送料|返品|解約|口コミ|体験談', line) and line.strip()]
    uncovered = [line for line in claims if not any(r['status'] == 'supplied_unverified' and
                 r['claim'] == line for r in records)]
    if uncovered:
        findings.append({'code': 'evidence_review', 'detail': uncovered,
                         'action': '記述ごとに出典URL・確認日・引用を記録し、人が適用条件を照合してください'})
    return {'findings': findings, 'evidence': records, 'faq_sections': len(faq),
            'publication_approved': False, 'facts_verified': False,
            'limitations': '根拠の文字一致は真偽の証明ではありません。検出対象外の主張も人の確認が必要です。'}
