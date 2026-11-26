"""Review-only creative briefs; headings are topics, not verified claims."""
import re
from urllib.parse import urlsplit

def build_brief(article, product, article_url=None, affiliate_url=None):
    if not isinstance(article,str) or not article.strip() or not product.strip():
        raise ValueError('missing article/product')
    topics=[]
    for line in article.splitlines():
        m=re.match(r'^#{2,3}\s+(.+)$',line)
        if m:
            t=m[1].strip()
            if t not in topics and not re.search(r'https?://|[<>]|まとめ|FAQ|よくある質問',t,re.I): topics.append(t)
    if len(topics)<3: raise ValueError('insufficient article topics')
    def valid(u):
        if not u: return False
        p=urlsplit(u)
        return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password
    if article_url and (not valid(article_url) or article_url==affiliate_url): raise ValueError('invalid article destination')
    if affiliate_url and not valid(affiliate_url): raise ValueError('invalid affiliate destination')
    cta={'text':'記事を読む','url':article_url} if article_url else {'text':'公開後の記事URLを設定','url':None}
    if not article_url and affiliate_url: cta={'text':'広告リンク先の商品情報を確認','url':affiliate_url}
    def topic(i): return topics[i%len(topics)]
    slides=[{'role':'hook','topic':product+'の選び方'}]+[{'role':'question','topic':topic(i),'instruction':'断定せず確認項目として表現'} for i in range(7)]+[{'role':'cta','topic':cta['text']}]
    videos={}
    for medium,ratio,style in [('reel','9:16','短い問いと手元の切り替え'),('youtube','16:9','比較表と落ち着いた解説'),('tiktok','9:16','冒頭の疑問とテンポのよい確認項目'),('gbp','4:3','読みやすい文字と案内中心')]:
        videos[medium]={'ratio':ratio,'seconds':45,'style':style,'narration':False,'scenes':[{'seconds':9,'topic':topic(i),'instruction':'確認項目として表現。未確認の効果・価格・口コミを追加しない'} for i in range(4)]+[{'seconds':9,'topic':cta['text']} ]}
    return {'topics':topics,'slides':slides,'videos':videos,'images':[{'topic':t,'instruction':'説明用イメージ。実物・実績を捏造しない'} for t in topics[:4]],'social':{m:{'topic':topic(i),'cta':cta,'disclosure':'PR'} for i,m in enumerate(['x','threads','facebook','instagram','line','gbp'])},'hashtags':['#商品選び','#比較検討','#購入前チェック','#暮らしの情報','#PR'],'human_review_required':True,'publication_approved':False}
