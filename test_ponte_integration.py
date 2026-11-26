import ast
from pathlib import Path
from unittest.mock import Mock
from search_intent import editorial_plan

def test_brave_description_mapping():
    rows=[{'url':'https://example.com','title':'商品','description':'送料'}, {'url':'https://example.org','title':'商品','description':'送料'}]
    result=editorial_plan('商品','暮らし','商品',[dict(x,snippet=x['description']) for x in rows])
    assert 'cost' in result['analysis']['intents']
    assert sum(s['target'] for s in result['sections'])==6000

def test_creative_bridge(monkeypatch):
    auto_creative = load_creative(monkeypatch)
    monkeypatch.setattr(auto_creative.genai,'Client',Mock())
    generate=Mock(return_value={})
    monkeypatch.setattr(auto_creative,'generate_social_plan',generate)
    import affiliate_quality_v5
    monkeypatch.setattr(affiliate_quality_v5,'review_bundle',lambda x:x)
    article='# 商品\n## 比較\n本文\n## 送料\n本文\n## 選び方\n本文'
    bundle=auto_creative.build_bundle(article,'商品','商品',0,'https://example.com/ad','fake','fake')
    assert len(bundle['grounded_brief']['slides'])==9
    assert len(bundle['grounded_brief']['videos'])==4
    assert not bundle['grounded_brief']['publication_approved']
    assert '記事連動' in generate.call_args.kwargs['promotion_context']

def test_short_creative_preserves_legacy(monkeypatch):
    auto_creative = load_creative(monkeypatch)
    monkeypatch.setattr(auto_creative.genai,'Client',Mock())
    monkeypatch.setattr(auto_creative,'generate_social_plan',Mock(return_value={}))
    import affiliate_quality_v5
    monkeypatch.setattr(affiliate_quality_v5,'review_bundle',lambda x:x)
    bundle=auto_creative.build_bundle('# 商品\n本文','商品','商品',0,'https://example.com/ad','fake','fake')
    assert 'grounded_brief' not in bundle
    assert len(bundle['blog_images'])==4

def load_creative(monkeypatch):
    import sys, types, importlib
    google=types.ModuleType('google'); genai=types.ModuleType('google.genai'); genai.Client=Mock(); genai.types=types.ModuleType('google.genai.types'); google.genai=genai
    for name, module in [('google',google),('google.genai',genai),('google.genai.types',genai.types)]:
        monkeypatch.setitem(sys.modules,name,module)
    return importlib.import_module('auto_creative')
