"""Conservative review triggers, not medical or legal judgments.

Matched cautions/negations may also need review. Do not replace a flagged
claim with a softer efficacy claim or treat a disclaimer as evidence.
"""
MEDICAL_RISK_PATTERN = (
    r'治る|治った|治ります|治すことができ|'
    r'(?:薬|服薬|投薬|受診|通院).{0,12}(?:やめられ|やめて|止められ|中止でき|必要ない|必要ありません|不要)|'
    r'(?:副作用|健康被害).{0,8}(?:ゼロ|[0０]|ありません|ない)|'
    r'陰性.{0,16}(?:病気ではない|病気ではありません|がんではない|異常なし|受診不要)|'
    r'(?:医師|医者).{0,12}(?:認めた|認める|推薦|推奨).{0,12}(?:効果|効き目|安全)|'
    r'(?:飲む|食べる|使う)だけで.{0,12}(?:治|痩せ|やせ|血糖|血圧)'
)
