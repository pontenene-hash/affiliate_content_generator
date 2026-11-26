from stage23_creative import audit_bundle

def test_duplicates():
    b={'social_plan':{'carousel':{'slides':[{'body':'購入前に送料を確認しましょう。'},{'body':'購入前に送料を確認しましょう！'}]}}}
    assert audit_bundle(b)['flags'][0]['kind']=='repeated_slide_body'

def test_videos():
    v={'scenes':[{'scene_type':'content','caption':'送料を確認'}]}
    assert audit_bundle({'social_plan':{'reel':v,'youtube':v}})['flags'][0]['kind']=='repeated_video_content'

def test_link():
    b={'affiliate_url':'https://example.org/ad','social_plan':{'line':{'text':'記事はこちら https://example.org/ad'}}}
    assert audit_bundle(b)['flags'][0]['kind']=='ambiguous_article_destination'

def test_safe():
    r=audit_bundle({'affiliate_url':'https://example.org/ad','social_plan':{'line':{'text':'広告リンク先の商品情報を確認 https://example.org/ad'}}})
    assert not r['flags'] and not r['publication_approved'] and r['human_review_required']
