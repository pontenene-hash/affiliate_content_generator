from partial_repair import repair_duplicates
P='購入前に自分の用途と必要な機能を整理して、選択肢を比較することが大切です。'
A=P+'\n\n'+P+'\n\n'+'本文'*3000
Q={'issues':[{'code':'duplicate','message':'重複'}]}
def test_accept():
    out,q,_=repair_duplicates(A,Q,lambda _: {'issues':[]},len)
    assert out.count(P)==1 and not q['issues']
def test_new_issue():
    assert repair_duplicates(A,Q,lambda _: {'issues':[{'code':'new'}]},len)[0]==A
def test_error():
    def fail(_): raise RuntimeError()
    assert repair_duplicates(A,Q,fail,len)[0]==A
def test_short():
    a=P+'\n\n'+P
    assert repair_duplicates(a,Q,lambda _: {'issues':[]},len)[0]==a
def test_warning():
    a=('注意'+P+'\n\n')*2+'本文'*3000
    assert repair_duplicates(a,Q,lambda _: {'issues':[]},len)[0]==a
