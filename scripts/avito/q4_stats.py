"""Авито, 4-й запрос «забор из профнастила под ключ», Москва и МО (выгрузка 21.10.2026) + профили Заборкина, Заборово, ПрофЗаборов.
Вход: notes/raw_avito/q4_out/*.csv (build_avito_q4.py), notes/raw_avito/profiles_wave3_reviews.json. Выход: data/avito_q4_summary.csv, data/avito_q4_sellers.csv, data/avito_profiles_wave3.csv."""
import csv, json, re, statistics as st
from collections import Counter
B = '/home/claude/zabory'; Q = f'{B}/notes/raw_avito/q4_out'
L = list(csv.DictReader(open(f'{Q}/avito_listings.csv', encoding='utf-8')))
MASK = {'Святослав': 'компания с личным именем в названии'}
num = lambda s: float(s) if s not in ('', None) else None
def stats(rows, label):
    comp = [r for r in rows if r['seller_type'] == 'компания']; priv = [r for r in rows if r['seller_type'].startswith('частн')]
    pm = [num(r['price_rub']) for r in rows if r['product'].startswith('профнастил') and r['price_unit'].startswith('п.м') and num(r['price_rub'])]
    views = [num(r['views_total']) for r in rows if num(r['views_total']) is not None]
    return dict(scope=label, listings=len(rows), companies=len(comp), private=len(priv),
                competitors_from_brief=', '.join(sorted({r['competitor_domain'] for r in rows if r['competitor_domain']})) or '—',
                profnastil_pm_n=len(pm), profnastil_pm_median=round(st.median(pm)) if pm else '',
                profnastil_pm_q1_q3=f'{round(st.quantiles(pm, n=4, method="inclusive")[0])}–{round(st.quantiles(pm, n=4, method="inclusive")[2])}' if len(pm) >= 4 else '',
                median_views_total=round(st.median(views)) if views else '', promoted=sum(1 for r in rows if r['promotion_marks']),
                source='avito.ru, регион «Москва и МО», запрос «забор из профнастила под ключ»; Apify, датасет AcCqnMVNagcDuaFN3', date_collected='2026-10-21')
rows = [stats(L[:20], 'первые 20'), stats(L, 'все 100')]
with open(f'{B}/data/avito_q4_summary.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
cnt = Counter(MASK.get(r['seller'], r['seller']) for r in L)
sel = []
for name, n in cnt.most_common(15):
    r = next(x for x in L if MASK.get(x['seller'], x['seller']) == name)
    sel.append(dict(seller=name, seller_type=r['seller_type'], competitor_domain=r['competitor_domain'], listings_in_top100=n,
                    best_position=min(int(x['position_in_export']) for x in L if MASK.get(x['seller'], x['seller']) == name),
                    active_listings=r['seller_active_listings'], rating=r['seller_rating'], reviews=r['seller_reviews']))
with open(f'{B}/data/avito_q4_sellers.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(sel[0].keys())); w.writeheader(); w.writerows(sel)
_PS = json.load(open(f'{B}/notes/raw_avito/profiles_wave3_summary.json', encoding='utf-8'))['items']
_DOM = {'Заборкин': 'zaborkin.ru', 'ЗАБОРОВО': 'zaborovo.ru', 'Профзаборы': 'prof-zabory.ru'}
P = []
for name in ('Заборкин', 'ЗАБОРОВО', 'Профзаборы'):
    x = next(i for i in _PS if i['name'] == name)
    P.append(dict(company=name, domain=_DOM[name], active=x['activeListingCount'], closed=x['closedListingCount'], rating=x['ratingScore'], reviews=x['reviewCount'],
                  distribution='/'.join(str(x['ratingDistribution'][k]) for k in '12345'), since=x['registrationDate'].replace('На Авито с ', ''),
                  reply=x['replyTime'].replace('Отвечает ', ''), match='по названию профиля, оценка'))
rv = json.load(open(f'{B}/notes/raw_avito/profiles_wave3_reviews.json', encoding='utf-8'))
for p in P:
    mine = [r for r in rv if r['seller'].lower() == p['company'].lower()]
    p.update(reviews_loaded=len(mine), reviews_with_score=sum(1 for r in mine if r['score']), neg_1_3=sum(1 for r in mine if r['score'] and r['score'] <= 3),
             seller_replies=sum(1 for r in mine if r['reply']), source='avito.ru, профиль продавца; Apify, датасет v8bHTrMVgoLX03N9U', date_collected='2026-10-21')
with open(f'{B}/data/avito_profiles_wave3.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(P[0].keys())); w.writeheader(); w.writerows(P)
for r in rows: print(r)
for r in sel: print(r)
for p in P: print(p)
print(open(f'{Q}/avito_claims_shares.csv', encoding='utf-8').read()[:1500])
