import pytest
from partial_repair import repair_duplicates
P='購入前に自分の用途と必要な機能を整理して、選択肢を比較することが大切です。'
Q={'issues':[{'code':'duplicate','message':'重複'}]}
@pytest.mark.parametrize('prefix,suffix', [('```python\n\n','\n\n```'),('~~~\n\n','\n\n~~~'),('<!--\n\n','\n\n-->'),('', '')])
def test_protected_or_triple(prefix,suffix):
    a=prefix+'\n\n'.join([P]*3)+suffix+'\n\n'+'本文'*3000
    out,_,_=repair_duplicates(a,Q,lambda _: {'issues':[]},len)
    assert out.count(P)==(3 if prefix else 1)
@pytest.mark.parametrize('prefix',['「','口コミ：','> ','- ','1. ','    '])
def test_protected_prose(prefix):
    a='\n\n'.join([prefix+P]*2)+'\n\n'+'本文'*3000
    assert repair_duplicates(a,Q,lambda _: {'issues':[]},len)[0]==a

def test_idempotent():
    a='\n\n'.join([P]*5)+'\n\n'+'本文'*3000
    out,q,_=repair_duplicates(a,Q,lambda _: {'issues':[]},len)
    assert out==P+'\n\n'+'本文'*3000
    assert repair_duplicates(out,q,lambda _: {'issues':[]},len)[0]==out
