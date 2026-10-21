# Сводит сырые данные площадок в один набор (без имён авторов)
import json, glob, os
B='/home/claude/zabory/notes/raw_reviews'
rows=[]; cards=[]
for f in glob.glob(B+'/yandex/*.json'):
    o=json.load(open(f))
    url=f"https://yandex.ru/maps/org/{o['id']}/reviews/"
    cards.append(dict(platform='Яндекс Карты',company=o['company'],card_id=o['id'],url=url,title=o.get('title',''),address=o.get('addr',''),rating=o.get('rating'),ratings_count=o.get('cnt'),text_reviews=o.get('rev'),collected=o.get('got',0),cats=o.get('cats','')))
    for r in o['reviews']:
        rows.append(dict(platform='Яндекс Карты',company=o['company'],card_id=o['id'],address=o.get('addr',''),url=url,rid=r['id'],date=r['date'],stars=r['stars'],text=r['text'],reply=r['reply'],reply_date=r['reply_date'],author_meta=r['author_level'],author_reviews=None,photos=r['photos']))
g=json.load(open(B+'/2gis/2gis_reviews_raw.json'))
for fid,m in g['meta'].items():
    cards.append(dict(platform='2ГИС',company=m['d'],card_id=fid,url=f'https://2gis.ru/moscow/firm/{fid}/tab/reviews',title='',address='',rating=m['rating'],ratings_count=m['cnt'],text_reviews=m['total'],collected=m['got'],cats=''))
for r in g['reviews']:
    rows.append(dict(platform='2ГИС' if r['pr']=='2gis' else '2ГИС (Флamp)'.replace('Флamp','Флэмп'),company=r['d'],card_id=r['f'],address='',url=f"https://2gis.ru/moscow/firm/{r['f']}/tab/reviews",rid=r['id'],date=r['dt'],stars=r['s'],text=r['x'],reply=r['a'],reply_date=r['ad'],author_meta='',author_reviews=r['ur'],photos=r['ph']))
for f in glob.glob(B+'/otzovik/*.json'):
    o=json.load(open(f))
    for r in o['reviews']:
        txt=' '.join(x for x in [r['title']+'.',r['teaser'],('Достоинства: '+r['plus']) if r['plus'] else '',('Недостатки: '+r['minus']) if r['minus'] else ''] if x)
        rows.append(dict(platform='Отзовик',company=o['company'],card_id=o['slug'],address='',url=f"https://otzovik.com/review_{r['id']}.html",rid=r['id'],date=r['date'],stars=r['stars'],text=txt,reply='',reply_date='',author_meta='',author_reviews=None,photos=0))
json.dump(rows,open(B+'/all_reviews.json','w'),ensure_ascii=False)
json.dump(cards,open(B+'/all_cards_yandex_2gis.json','w'),ensure_ascii=False)
import collections
print(len(rows), collections.Counter((r['platform']) for r in rows))
print('neg', collections.Counter(r['platform'] for r in rows if r['stars'] and r['stars']<=3))
