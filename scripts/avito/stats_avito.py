# Цифры для справки avito_spravka.md (пересчёт из CSV).
import csv, statistics as st, collections, re
D = '/home/claude/zabory/data'
L = list(csv.DictReader(open(f'{D}/avito_listings.csv')))
Q = ['забор под ключ', 'откатные ворота', 'установка забора']


def num(x):
    try:
        return float(x)
    except Exception:
        return None


def q4(xs):
    xs = sorted(xs)
    if len(xs) < 4:
        return (st.median(xs) if xs else None, None, None)
    q = st.quantiles(xs, n=4)
    return (st.median(xs), q[0], q[2])


print('== 1. типы продавцов')
for q in Q:
    rows = [r for r in L if r['query'] == q]
    c = collections.Counter(r['seller_type'] for r in rows)
    acc = collections.Counter(r['avito_account_type'] for r in rows)
    us = collections.Counter(r['seller_type'] for r in {r['seller_key']: r for r in rows}.values())
    print(q, dict(c), 'уник. продавцов', dict(us), 'акк', dict(acc))
    top10 = collections.Counter(r['seller'] for r in rows).most_common(10)
    print('  top', top10)
    print('  первые 20 позиций:', dict(collections.Counter(r['seller_type'] for r in rows[:20])))
allu = {r['listing_id']: r for r in L}
print('уникальных объявлений', len(allu), 'уник продавцов', len({r['seller_key'] for r in L}))

print('== 2. просмотры')
for q in Q:
    rows = [r for r in L if r['query'] == q]
    vt = [num(r['views_total']) for r in rows if num(r['views_total']) is not None]
    vd = [num(r['views_per_day_since_posted']) for r in rows if num(r['views_per_day_since_posted']) is not None]
    td = [num(r['views_today']) or 0 for r in rows]
    days = [num(r['days_since_posted']) for r in rows if num(r['days_since_posted']) is not None]
    print(q, 'n', len(vt), 'views med/q1/q3', q4(vt), 'sum', sum(vt), 'max', max(vt), '| per day med', q4(vd), '| today>=1', sum(1 for x in td if x >= 1), 'sum today', sum(td), '| days med', st.median(days), min(days), max(days))
    for t in ('компания', 'частный мастер'):
        v = [num(r['views_total']) for r in rows if r['seller_type'] == t and num(r['views_total']) is not None]
        v2 = [num(r['views_per_day_since_posted']) for r in rows if r['seller_type'] == t and num(r['views_per_day_since_posted']) is not None]
        print('   ', t, len(v), 'med views', st.median(v) if v else '', 'med/day', st.median(v2) if v2 else '')
    # первые 20 vs остальные
    a = [num(r['views_per_day_since_posted']) for r in rows[:20] if num(r['views_per_day_since_posted']) is not None]
    b = [num(r['views_per_day_since_posted']) for r in rows[20:] if num(r['views_per_day_since_posted']) is not None]
    print('    per day first20 med', st.median(a), 'rest', st.median(b))

print('== 3. цены')
for prod in ['профнастил', 'евроштакетник', '3D-сетка', 'рабица', 'жалюзи', 'забор (материал не указан)', 'деревянный']:
    for q in Q + ['все уник']:
        rows = [r for r in (allu.values() if q == 'все уник' else [x for x in L if x['query'] == q]) if r['product'] == prod and r['price_unit'] == 'п.м.' and num(r['price_rub'])]
        if rows:
            ps = [num(r['price_rub']) for r in rows]
            stated = sum(1 for r in rows if 'указано' in r['price_unit_note'])
            print(prod, '|', q, 'n', len(ps), 'med,q1,q3', q4(ps), 'min', min(ps), 'max', max(ps), 'unit stated', stated)
print('-- ворота')
for prod in ['откатные ворота', 'распашные ворота', 'ворота (тип не указан)', 'автоматика/привод', 'ремонт ворот/автоматики']:
    rows = [r for r in allu.values() if r['product'] == prod]
    ps = [num(r['price_rub']) for r in rows if num(r['price_rub'])]
    big = [p for p in ps if p >= 15000]
    small = [p for p in ps if p < 15000]
    print(prod, 'n', len(rows), 'with price', len(ps), '>=15000', len(big), q4(big) if big else '', '| <15000', len(small), sorted(small)[:15])
print('продукты в выдаче:')
for q in Q:
    print(q, collections.Counter(r['product'] for r in L if r['query'] == q).most_common())
print('единица указана в цене:', sum(1 for r in allu.values() if 'указано' in r['price_unit_note']), 'из', len(allu), '; цена договорная/не указана:', sum(1 for r in allu.values() if not num(r['price_rub'])))

print('== 4. прочее')
mixed = [r for r in allu.values() if int(r['mixed_script_words']) >= 3]
print('латинские двойники >=3 слов', len(mixed), 'из', len(allu), collections.Counter(r['seller_type'] for r in mixed))
fake = re.compile(r'Красная пл|Воскресенские Ворота|Охотный Ряд|ул\. Арбат|Манежная|Тверская')
fk = [r for r in allu.values() if fake.search(r['address'])]
print('адрес в центре (Красная пл., Воскресенские Ворота, Охотный Ряд, Арбат...)', len(fk), collections.Counter(r['seller'] for r in fk).most_common(10))
print('Зеленоград', sum(1 for r in allu.values() if 'Зеленоград' in r['address']))
for q in Q:
    rows = [r for r in L if r['query'] == q]
    rt = [num(r['seller_rating']) for r in rows if num(r['seller_rating'])]
    rv = [num(r['seller_reviews']) for r in rows if num(r['seller_reviews']) is not None]
    yrs = collections.Counter((re.search(r'\d{4}', r['seller_on_avito_since']) or [None])[0] for r in {r['seller_key']: r for r in rows}.values())
    print(q, 'rating med', st.median(rt), 'n', len(rt), '| reviews med', st.median(rv), 'max', max(rv), '| years', sorted(yrs.items(), key=lambda x: str(x[0])))
    print('   reply', collections.Counter(r['seller_reply_time'] for r in rows))
    print('   video', sum(1 for r in rows if r['has_video'] == 'да'), 'img med', st.median([num(r['image_count']) for r in rows]))

print('== 5. сверка со снимком 21.10 (avito_serp.csv, стр. 1)')
old = list(csv.DictReader(open(f'{D}/avito_serp.csv')))
oldt = [(r['title'].strip().lower(), r['price_from_rub']) for r in old if r['title']]
newt = [(r['title'].strip().lower(), str(int(num(r['price_rub']))) if num(r['price_rub']) else '') for r in L if r['query'] == 'забор под ключ']
s_old = set(oldt)
print('из 50 старых найдено в новых 100 (заголовок+цена):', sum(1 for x in oldt if x in set(newt)), '; только по заголовку', sum(1 for x in oldt if x[0] in {n[0] for n in newt}))
print('promo old', collections.Counter(r['promotion_mark'] for r in old))

print('== 6. продавцы: у кого больше всего объявлений')
S = list(csv.DictReader(open(f'{D}/avito_sellers.csv')))
for s in S[:25]:
    print(s['seller'], '|', s['seller_type'], '|', s['unique_listings_in_3_queries'], s['in_top100_zabor_pod_klyuch_msk'], s['in_top100_otkatnye_vorota_msk'], s['in_top100_ustanovka_zabora_mo'], '| active', s['active_listings_in_profile'], '| r', s['rating'], s['reviews'], '|', s['on_avito_since'], '|', s['reply_time'], '| views med', s['median_views_total'], s['median_views_per_day'])
big = sorted(S, key=lambda s: -(num(s['active_listings_in_profile']) or 0))[:15]
print('-- по числу активных объявлений в профиле')
for s in big:
    print(s['seller'], s['seller_type'], s['active_listings_in_profile'], s['rating'], s['reviews'], s['on_avito_since'])
la = [num(s['active_listings_in_profile']) for s in S if num(s['active_listings_in_profile']) is not None]
for t in ('компания', 'частный мастер'):
    x = [num(s['active_listings_in_profile']) for s in S if s['seller_type'] == t and num(s['active_listings_in_profile']) is not None]
    print(t, 'продавцов', len(x), 'медиана активных объявлений', st.median(x), 'доля >=50', sum(1 for v in x if v >= 50))
