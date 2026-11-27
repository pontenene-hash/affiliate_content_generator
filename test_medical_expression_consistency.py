import pytest
from affiliate_article_guard import review_article
from affiliate_quality_v5 import safe_sentences
from test_affiliate_article_guard import article, URL

@pytest.mark.parametrize('claim', [
    '腰痛が治る。', '体験談：飲んだら治った。個人の感想です。',
    '薬をやめられる。', '服薬を中止できます。',
    '副作用はゼロ。', '副作用がありません。',
    '陰性なら病気ではありません。', '陰性であればがんではない。',
    '医師が認めた効果。', '飲むだけで血糖値が下がります。',
])
def test_medical_claims_held_in_article_and_removed_from_social(claim):
    result = review_article(article(body=claim), '生活用品', '暮らし', URL, claim)
    assert not result['approved']
    assert 'high_risk_claim' in {i['code'] for i in result['issues']}
    assert claim not in safe_sentences(claim)

@pytest.mark.parametrize('sentence', ['素材とサイズを確認してください。', '服薬中の方は医師や薬剤師に相談してください。'])
def test_neutral_guidance_remains_in_social(sentence):
    assert safe_sentences(sentence) == sentence
