from section_engine import complete_sections

def test_retry_uses_current_article_and_feedback():
    original='# 商品\n\n## 比較\n\n用途を確認。\n\n## 準備\n\n候補を整理。\n\n## まとめ\n\n確認する。'
    calls=[]
    def generate(h,s,m,current,feedback):
        calls.append((current,feedback))
        return ['送料無料です。','収納場所の寸法を測り、置き場所を検討します。','購入前に使用場面を整理して候補を比較します。'][len(calls)-1]
    def check(a): return {'issues':[{'code':'unsupported','message':'送料'}] if '送料無料' in a else []}
    a,q,log=complete_sections(original,None,check,len,len(original)+35,500,3,contextual_generate=generate)
    assert len(calls)==3
    assert 'unsupported' in calls[1][1][-1]
    assert '収納場所' in calls[2][0]
    assert '送料無料' not in a
    assert len(a)>=len(original)+35
    assert a.endswith('確認する。')
