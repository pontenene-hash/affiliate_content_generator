from stage19_context import creative_context, expansion_prompt

def test_topics_are_questions_not_claims():
    text='## 送料無料\n## ギフト無料\n## スペアパーツ全品在庫あり'
    result=creative_context(text,'HARIO','fallback')
    assert '送料無料' not in result and '全品在庫' not in result
    assert result.count('## ')==3

def test_sparse_fallback():
    assert creative_context('## 送料','HARIO','fallback')=='fallback'

def test_expansion_context():
    p=expansion_prompt('HARIO','暮らし','送料','確認','## 比較\n秘密の長文',[], '送料条件\n'+'無関係'*9000,1000)
    assert '秘密の長文' not in p and len(p)<8000 and '無関係な医療' in p

def test_medical_retained():
    assert '検査の限界' in expansion_prompt('尿がん検査','健康','目的','','',[],'資料',1000)
