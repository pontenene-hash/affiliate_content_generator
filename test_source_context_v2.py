from stage4_metadata import source_issues

def codes(article, source):
    return {i['code'] for i in source_issues(article, source)}

def test_wrong_charge():
    assert 'source_numeric_context_review' in codes('送料は500円。','商品価格500円。送料800円。')

def test_correct_charge():
    assert 'source_numeric_context_review' not in codes('送料は500円。','送料：500円。')

def test_missing_number():
    assert 'source_numeric_unmatched' in codes('送料500円。','送料800円。')

def test_no_cross_sentence():
    assert 'source_numeric_context_review' in codes('送料500円。','送料は別途。商品価格500円。')
