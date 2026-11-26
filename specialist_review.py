"""Offline advisory screening; never authorizes publication or establishes facts."""
import re
RULES = {
 'medical': r'がん|癌|医療|診断|検査キット|尿検査|治療|疾患',
 'nutrition': r'健康食品|サプリ|機能性表示食品|栄養補助',
 'cosmetic': r'化粧品|美容液|スキンケア|美容クリーム',
 'contract': r'定期購入|サブスク|保険|ローン|月額|解約',
 'food': r'宅配食|弁当|食品|アレルギー',
}
CLAIMS = {
 'medical': r'陰性.{0,12}(?:安心|心配ない)|(?:受診|検診|診察).{0,8}不要|見逃さない',
 'nutrition': r'病気.{0,8}(?:治る|予防できる)|必ず痩せる',
 'cosmetic': r'シミが消える|永久に|肌が再生する',
 'contract': r'いつでも無料で解約|絶対に損しない',
 'food': r'アレルギー.{0,8}(?:絶対安全|心配ない)',
}
def classify(name='', genre='', article=''):
    context='\n'.join((name,genre,article))
    tags={k for k,v in RULES.items() if re.search(v,context)}
    if '健康' in genre and not tags.intersection({'medical','nutrition'}): tags.add('health_unknown')
    return sorted(tags or {'general'})

def specialist_review(name, genre, article):
    tags=classify(name,genre,article)
    issues=[]
    for tag in tags:
        if tag in {'medical','nutrition','cosmetic','health_unknown'}:
            issues.append({'code':'specialist_'+tag+'_review','message':'専門分野の根拠・広告表現を人が確認してください','severity':'block'})
        if tag in CLAIMS and re.search(CLAIMS[tag],article):
            issues.append({'code':'specialist_'+tag+'_claim','message':'専門分野の断定表現を文脈と根拠から確認してください','severity':'block'})
    return {'categories':tags,'issues':issues}
