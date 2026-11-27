from growth_advice import *
from datetime import datetime, timezone

def test_priority_unknown(): assert not priority({})['eligible_for_review']
def test_priority_truthy(): assert not priority({'approved':1})['eligible_for_review']
def test_priority_complete(): assert priority(dict.fromkeys(('approved','official_source_available','affiliate_link_verified','reader_fit'),True))['eligible_for_review']
def test_related(): assert related_drafts('冷え 足',[{'id':'1','article':'# 足の冷え'}])[0]['matched_terms']==2
def test_related_no_link(): assert not related_drafts('足',[{'id':'1','article':'# 足'}])[0]['link_verified']
def test_related_body_only(): assert not related_drafts('足',[{'id':'1','article':'# 別\n足'}])
def test_title(): assert title_review('足の冷え','足 冷え')['keyword_present']
def test_title_claim(): assert title_review('１００％改善','足')['absolute_claim_review']
def test_cta(): assert cta_review('広告 [商品](https://example.com/a)','https://example.com/a')['expected_url_present']
def test_cta_prefix(): assert not cta_review('https://example.com/ab','https://example.com/a')['expected_url_present']
def test_rewrite(): assert rewrite_candidates([{'id':1,'source_change':'changed'}],datetime.now(timezone.utc))[0]['reason']=='review_changed_source'
def test_advisory(): assert not advisory('本文','題','足','',[])['publication_approved']
