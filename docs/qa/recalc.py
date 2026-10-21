#!/usr/bin/env python3
"""Надзиратель: волна 1, волна 2 (реклама Яндекса, Авито, Карты, площадки, пересъёмка сайтов) и synthesis v3 (критерии, оффер против рынка, медиаплан, гипотезы, ответы) — пересчёт производных цифр из data/*.csv.
Запуск: python3 -I qa/recalc.py  (из любой папки; пути абсолютные от корня проекта).
Печатает таблицу проверок: id | что | заявлено | пересчитано | статус.
"""
import csv, json, re, statistics as st, os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda f: os.path.join(ROOT, 'data', f)
N = lambda f: os.path.join(ROOT, 'notes', f)
rows = lambda f: list(csv.DictReader(open(D(f), encoding='utf-8')))
num = lambda s: float(str(s).replace(' ', '').replace(' ', '').replace(',', '.')) if str(s).strip() not in ('', 'не снято') else None

OUT = []
def check(cid, what, claimed, got, tol=0.0, rel=False):
    if isinstance(claimed, (int, float)) and isinstance(got, (int, float)):
        diff = abs(got - claimed)
        ok = diff <= (abs(claimed) * tol if rel else tol)
    else:
        ok = str(claimed) == str(got)
    OUT.append((cid, what, claimed, round(got, 2) if isinstance(got, float) else got, 'OK' if ok else 'РАСХОЖДЕНИЕ'))

def note(cid, what, value):
    OUT.append((cid, what, '—', value, 'ИНФО'))

# ---------- 1. sites: цены ----------
pr = rows('sites_prices.csv')
main10 = ['masterovit.ru', 'prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru',
          'zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']
pn = {x['domain']: num(x['price_from_rub']) for x in pr if x['product'] == 'профнастил' and x['domain'] in main10}
check('R01', 'профнастил «от», n', 10, len(pn))
check('R02', 'профнастил «от», медиана ₽/п.м.', 1690, st.median(pn.values()))
check('R03', 'профнастил «от», минимум', 850, min(pn.values()))
check('R04', 'профнастил «от», максимум', 2150, max(pn.values()))

g = rows('sites_gates.csv')
mech = {x['domain']: num(x['price_mech_4m_rub']) for x in g if x['price_mech_4m_rub'] and x['domain'] != 'dostup-zabor.ru'}
auto = {x['domain']: num(x['price_auto_4m_rub']) for x in g if x['price_auto_4m_rub'] and x['domain'] != 'oblzabor.ru'}
check('R05', 'ворота 4 м механика, n', 14, len(mech))
check('R06', 'ворота 4 м механика, медиана', 72025, st.median(mech.values()))
check('R07', 'ворота 4 м механика, мин/макс', '47150-101400', f'{min(mech.values()):.0f}-{max(mech.values()):.0f}')
check('R08', 'ворота 4 м автоматика, n', 8, len(auto))
check('R09', 'ворота 4 м автоматика, медиана', 106625, st.median(auto.values()))
check('R10', 'ворота 4 м автоматика, мин/макс', '80500-144100', f'{min(auto.values()):.0f}-{max(auto.values()):.0f}')
pairs = {d: auto[d] - mech[d] for d in auto if d in mech}
check('R11', 'надбавка за автоматику, n', 8, len(pairs))
check('R12', 'надбавка за автоматику, медиана', 33500, st.median(pairs.values()))
check('R13', 'надбавка, мин/макс', '18000-48850', f'{min(pairs.values()):.0f}-{max(pairs.values()):.0f}')
# чувствительность: без конфигураций с другим составом (masterovit без наполнения; zaborovo авто без наполнения; otkatnie-vorota 1,8 м)
mech_s = {k: v for k, v in mech.items() if k not in ('masterovit.ru', 'otkatnie-vorota.com')}
note('R14', 'медиана механики без masterovit (без наполнения) и otkatnie-vorota (1,8 м)', st.median(mech_s.values()))
pairs_s = {k: v for k, v in pairs.items() if k not in ('zaborovo.ru', 'otkatnie-vorota.com')}
note('R15', 'медиана надбавки без zaborovo и otkatnie-vorota', st.median(pairs_s.values()))
obl = [x for x in pr if x['domain'] == 'oblzabor.ru' and 'ворот' in x['product']]
note('R16', 'oblzabor ворота с автоматикой, ₽ / отношение к медиане авто', f"{obl[0]['price_from_rub']} / {num(obl[0]['price_from_rub'])/st.median(auto.values()):.2f}")

# ---------- 2. reviews ----------
rv = rows('reviews.csv')
ts = lambda x: {t.strip() for t in x['themes'].split(';') if t.strip()}
neg = [x for x in rv if int(x['stars']) <= 3]
fen = [x for x in neg if x['group'] != 'откатные ворота']
check('V01', 'негатив 1–3★, всего', 886, len(neg))
check('V02', 'негатив заборных компаний', 851, len(fen))
plat = Counter(x['platform'] for x in fen)
check('V03', 'негатив Яндекс', 772, plat['Яндекс Карты'])
check('V04', 'негатив Отзовик', 48, plat['Отзовик'])
check('V05', 'негатив 2ГИС+Флэмп', 31, plat['2ГИС'] + plat['2ГИС (Флэмп)'])
th = Counter(t for x in fen for t in ts(x))
for cid, t, claimed in [('V06', 'качество_монтажа', 31.4), ('V07', 'связь_менеджер', 28.4), ('V08', 'материал', 27.7),
                        ('V09', 'гарантия', 27.6), ('V10', 'смета_замер', 18.0), ('V11', 'сроки', 10.3)]:
    check(cid, f'доля темы «{t}», %', claimed, th[t] / len(fen) * 100, 0.05)
rec = [x for x in fen if x['date'] >= '2024-10-20']
check('V12', 'негатив за 24 мес., n', 407, len(rec))
G = {'изделие': {'качество_монтажа', 'материал', 'фундамент_столбы', 'ворота_автоматика'},
     'после продажи': {'гарантия', 'связь_менеджер'}, 'цена': {'смета_замер', 'ошибка_замера', 'цена_высокая'}}
for cid, (k, claimed) in zip(('V13', 'V14', 'V15'), [('изделие', 55.0), ('после продажи', 47.4), ('цена', 28.1)]):
    check(cid, f'группа «{k}», %', claimed, sum(1 for x in fen if ts(x) & G[k]) / len(fen) * 100, 0.05)
check('V16', 'материал+гарантия вместе', 113, sum(1 for x in fen if {'материал', 'гарантия'} <= ts(x)))
mast = [x for x in fen if x['company'] == 'masterovit.ru']
check('V17', 'Мастеровит, негатив n', 478, len(mast))
check('V18', 'Мастеровит, доля в негативе 10 компаний, %', 56, len(mast) / len(fen) * 100, 0.5)
# нормировка на объём собранных текстов
cards = rows('reviews_cards.csv')
texts = Counter()
for c in cards:
    if c['group'] == 'полный разбор' and c['platform'] in ('Яндекс Карты', '2ГИС', 'Отзовик'):
        texts[c['company']] += int(c['collected'] or 0)
tot = sum(texts.values())
note('V19', 'Мастеровит: доля в собранных текстах (Яндекс+2ГИС+Отзовик), %', round(texts['masterovit.ru'] / tot * 100, 1))
note('V20', 'Мастеровит: доля 1–3★ в своих текстах, % / остальные 9 компаний, %',
     f"{len(mast)/texts['masterovit.ru']*100:.1f} / {(len(fen)-len(mast))/(tot-texts['masterovit.ru'])*100:.1f}")
yfen = [x for x in fen if x['platform'] == 'Яндекс Карты']
ym = [x for x in yfen if x['company'] == 'masterovit.ru']
note('V21', 'Мастеровит: доля в негативе только Яндекс (Отзовик собран только у Мастеровита), %', round(len(ym) / len(yfen) * 100, 1))
yrep = sum(1 for x in ym if x['has_reply'] == 'да')
check('V22', 'Мастеровит: ответы на негатив Яндекс, %', 95, yrep / len(ym) * 100, 0.5)
gates = [x for x in neg if x['group'] == 'откатные ворота']
gth = Counter(t for x in gates for t in ts(x))
check('V23', 'ворота-специалисты: n негатива', 35, len(gates))
check('V24', 'ворота-специалисты: связь, %', 54.3, gth['связь_менеджер'] / len(gates) * 100, 0.05)
check('V25', 'отзывы с признаками накрутки (is_suspicious)', 38, sum(1 for x in rv if x['is_suspicious'] == 'да'))

# ---------- 3. finance ----------
fin = rows('finance.csv')
rev = {(x['company'], x['year']): float(x['revenue_th_rub']) for x in fin if x['revenue_th_rub']}
lst = ['ООО «Мастеровит»', 'ООО «Первый строительный»', 'ООО «Мособлстрой»', 'ООО «Заборово»', 'ООО «ЗАБОРОФФ»',
       'ООО «Строймонтаж 2015»', 'ООО «ПРО-СТРОЙ»', 'ООО «СТРОЙ-ЦЕНТР»', 'ООО «СВ Компани»', 'ООО «Строй Модуль»',
       'ООО «ПК АЛЮСИС»', 'ООО «Металлические системы»', 'ООО «СУ-8»']
s = lambda names, y: sum(rev.get((n, y), 0) for n in names) / 1000
a, b = s(lst, '2024'), s(lst, '2025')
check('F01', 'сумма 13 ООО 2024, млн ₽', 4572, a, 1)
check('F02', 'сумма 13 ООО 2025, млн ₽', 3688, b, 1)
check('F03', 'динамика 13 ООО, %', -19, (b / a - 1) * 100, 0.5)
nm = [n for n in lst if 'Мастеровит' not in n]
check('F04', 'динамика без Мастеровита, %', -33, (s(nm, '2025') / s(nm, '2024') - 1) * 100, 0.5)
both = [n for n in lst if (n, '2024') in rev and (n, '2025') in rev]
check('F05', 'ООО с отчётностью за оба года (справка исправлена: «12 из 13», I2)', 12, len(both))
check('F06', 'из них выручка 2025 ниже', 10, sum(1 for n in both if rev[(n, '2025')] < rev[(n, '2024')]))
withruf = lst + ['ООО «Мастеровит Руф»']
note('F07', 'динамика 13 ООО + «Мастеровит Руф» (оборот группы), %', round((s(withruf, '2025') / s(withruf, '2024') - 1) * 100, 1))
check('F08', 'группа Мастеровит 2025, млн ₽', 3295, (rev[('ООО «Мастеровит»', '2025')] + rev[('ООО «Мастеровит Руф»', '2025')]) / 1000, 1)
check('F09', 'группа / Мособлстрой, раз', 6.9, (rev[('ООО «Мастеровит»', '2025')] + rev[('ООО «Мастеровит Руф»', '2025')]) / rev[('ООО «Мособлстрой»', '2025')], 0.05)
bad = []
for x in fin:
    r_, p_ = x['revenue_th_rub'], x['net_profit_th_rub']
    if r_ and p_ and float(r_) > 0 and x['net_margin_pct']:
        if abs(float(p_) / float(r_) * 100 - float(x['net_margin_pct'])) > 0.06: bad.append(x['company'] + x['year'])
check('F10', 'формула чистой маржи в строках finance.csv: ошибок', 0, len(bad))
m = defaultdict(list)
for x in fin:
    if x['net_margin_pct'] and 'расчёт' not in x['role']: m[x['company']].append(float(x['net_margin_pct']))
m15 = [st.mean(m[c]) for c in withruf + ['ООО «М-ЗАБОР»'] if m[c]]
check('F11', 'медиана средней чистой маржи, %, n=15', 3.8, st.median(m15), 0.05)
d25 = [float(x['receivable_days']) for x in fin if x['year'] == '2025' and x['receivable_days'] and x['company'] in withruf]
check('F12', 'медиана дней дебиторки 2025, n=13', 40, st.median(d25), 0.5)

# ---------- 4. traffic ----------
tw = {x['domain']: x for x in rows('traffic_channels_wide.csv')}
for cid, d, claimed in [('T01', 'prof-zabory.ru', 64.1), ('T02', 'oblzabor.ru', 67.9), ('T03', 'zavodzaborov.ru', 27.3), ('T04', 'masterovit.ru', 15.1)]:
    x = tw[d]
    check(cid, f'{d}: доля платных каналов, %', claimed, num(x['search_paid_pct']) + num(x['display_ads_pct']) + num(x['social_paid_pct']), 0.06)
v = lambda d: num(tw[d]['visits_3m'])
check('T05', 'prof-zabory медийная, визитов (визиты × доля)', 170931, v('prof-zabory.ru') * num(tw['prof-zabory.ru']['display_ads_pct']) / 100, 0.005, True)
check('T06', 'prof-zabory платный поиск, визитов', 49600, v('prof-zabory.ru') * num(tw['prof-zabory.ru']['search_paid_pct']) / 100, 0.005, True)
check('T07', 'masterovit прямые, визитов', 248525, v('masterovit.ru') * num(tw['masterovit.ru']['direct_pct']) / 100, 0.005, True)
ch = rows('traffic_channels.csv')
# I6 (повторная проверка 20.10): одна формула «визиты × доля» во всех строках traffic_channels.csv
badf = [f"{x['domain']}/{x['channel']}" for x in ch
        if abs(num(x["site_visits_3m"]) * num(x["share_pct"]) / 100 - num(x["channel_visits_3m"])) > num(x["site_visits_3m"]) * 0.00005 + 1]
check('T08', 'traffic_channels.csv: строк, где визиты канала ≠ визиты × доля', '[]', str(badf[:5]))
check('T08b', 'zaborkin.ru органика, визитов за 3 мес (= SEO-справка 74,9 тыс.)', 74894,
      num([x for x in ch if x['domain'] == 'zaborkin.ru' and x['channel'] == 'Поиск органический'][0]['channel_visits_3m']), 1)
ov = {x['domain']: x for x in rows('traffic_overview.csv')}
comp = {x['domain']: x for x in rows('competitors.csv')}
miss = [d for d in main10 if d not in comp]
check('T09', 'полный разбор без строки в competitors.csv', '[]', str(miss))
diff = [d for d in main10 if d in comp and num(comp[d]['visits_jul_sep_2026']) != num(ov[d]['visits_3m'])]
check('T10', 'визиты competitors.csv ≠ traffic_overview', '[]', str(diff))

# ---------- 5. SEO: индекс видимости ----------
kq = json.load(open(D('keys_queries_msk.json'), encoding='utf-8'))
ctr = [.28, .15, .10, .07, .05, .04, .03, .025, .02, .018]
vis, hits = Counter(), Counter()
for q, val in kq.items():
    for i, dom in enumerate(val['org']):
        vis[dom] += val['f'] * ctr[i]; hits[dom] += 1
seo = {x['domain']: x for x in rows('seo_sites.csv')}
for d, x in seo.items():
    if x['keys_visibility_index_estimate']:
        check('S01', f'индекс видимости {d}', num(x['keys_visibility_index_estimate']), vis.get(d, 0), 1)
light = ['zabormo.ru', 'pro-zabor.ru', 'moscow.kupitzabor.ru', '33zabora.ru', 'zabor-vam.ru', 'good-zabor.ru',
         'moskovskie-zabory.ru', 'ligazaborov.ru', 'zabory-deshevo.ru', 'gorodzaborov.ru']
check('S02', 'облегчённые домены вне seo_sites.csv', '[]', str([d for d in light if d not in seo]))
top = sorted(((round(vv), d) for d, vv in vis.items() if d in main10 + light), reverse=True)[:7]
note('S03', 'топ-7 по индексу видимости среди 20 доменов брифа', top)
check('S04', 'мест в топ-10 по 9 запросам', 89, sum(len(val['org']) for val in kq.values()))

# ---------- 6. спрос ----------
wd = [x for x in rows('wordstat_dynamics.csv') if x['query'] == 'забор под ключ' and x['frequency_broad'] and 'повторяет' not in x['note']]
ms = [(int(x['month'][:4]) * 12 + int(x['month'][5:7]), float(x['frequency_broad'])) for x in wd]
xs, ys = zip(*ms)
mx, my = st.mean(xs), st.mean(ys)
slope = sum((a - mx) * (b - my) for a, b in ms) / sum((a - mx) ** 2 for a in xs)
check('W01', 'точек без повторов', 11, len(ms))
check('W02', 'тренд «забор под ключ», запросов/мес', 913, slope, 2)
check('W03', 'среднее по 11 точкам', 51437, my, 2)
fm = {x['month']: float(x['frequency_broad']) for x in rows('wordstat_dynamics.csv') if x['query'] == 'забор под ключ' and x['frequency_broad']}
check('W04', 'май 2026 / январь 2026, раз', 10.2, fm['2026-05'] / fm['2026-01'], 0.05)
for cid, mth, claimed in [('W05', '05', 31), ('W06', '07', -34), ('W07', '09', 38)]:
    check(cid, f'год к году, месяц {mth}, %', claimed, (fm[f'2026-{mth}'] / fm[f'2025-{mth}'] - 1) * 100, 0.5)

# ---------- 7. реквизиты: контрольные суммы ИНН/ОГРН ----------
def inn_ok(inn):
    d = [int(c) for c in inn]
    if len(d) == 10:
        return sum(a * b for a, b in zip([2, 4, 10, 3, 5, 9, 4, 6, 8], d)) % 11 % 10 == d[9]
    w1, w2 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8], [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    return sum(a * b for a, b in zip(w1, d)) % 11 % 10 == d[10] and sum(a * b for a, b in zip(w2, d)) % 11 % 10 == d[11]
bad = [x['domain'] for x in rows('legal.csv') if x['inn'].isdigit() and not inn_ok(x['inn'])]
check('L01', 'ИНН с неверной контрольной суммой (legal.csv)', '[]', str(bad))
pz = [x for x in rows('legal.csv') if x['domain'].startswith('prof-zabory')][0]
check('L02', 'prof-zabory: ОГРНИП как в брифе', '319762700025982', pz['ogrn'])
check('L03', 'prof-zabory: ИНН (подвал сайта)', '112103967667', pz['inn'])
check('L04', 'prof-zabory: ИНН в competitors.csv', '112103967667', comp['prof-zabory.ru']['inn'])

# ---------- 8. персональные данные ----------
patr = re.compile(r'[А-ЯЁ][а-яё]+(?:вич|вна|вичу|вне|вича|вны)\b')
phone = re.compile(r'(?:\+7|\b8)[\s\-\(]*9\d{2}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}')
cnt = Counter()
for x in rv:
    for k in ('text', 'reply_summary'):
        cnt['отчества'] += len(patr.findall(x[k])); cnt['телефоны'] += len(phone.findall(x[k]))
        cnt['номера договоров'] += len(re.findall(r'договор[а-я]*\s*(?:№|N)?\s*\d[\d/\-]{2,}', x[k], re.I))
check('P01', 'reviews.csv: отчества / телефоны / номера договоров', '0/0/0', f"{cnt['отчества']}/{cnt['телефоны']}/{cnt['номера договоров']}")
raw = json.load(open(N('raw_reviews/all_reviews.json'), encoding='utf-8'))
rt = ' '.join(str(x.get('text', '')) + ' ' + str(x.get('reply', '')) for x in raw)
check('P02', 'raw all_reviews.json: телефоны / отчества', '0/0', f'{len(phone.findall(rt))}/{len(patr.findall(rt))}')

# ---------- 7b. sites_gates: медианы по сопоставимым (повторная проверка I8) ----------
mc = [num(x['mech_4m_for_median_rub']) for x in g if x['comparable_mech'] == 'да' and x['mech_4m_for_median_rub']]
ac = {x['domain']: num(x['auto_4m_for_median_rub']) for x in g if x['comparable_auto'] == 'да' and x['auto_4m_for_median_rub']}
mcd = {x['domain']: num(x['mech_4m_for_median_rub']) for x in g if x['comparable_mech'] == 'да' and x['mech_4m_for_median_rub']}
check('R17', 'механика 4 м по сопоставимым: n / медиана', '12 / 71086.5', f'{len(mc)} / {st.median(mc)}')
check('R18', 'автоматика 4 м по сопоставимым: n / медиана', '6 / 103025.0', f'{len(ac)} / {st.median(ac.values())}')
sur = [ac[d] - mcd[d] for d in ac if d in mcd]
check('R19', 'надбавка по сопоставимым парам: n / медиана', '6 / 39000.0', f'{len(sur)} / {st.median(sur)}')


# =====================================================================
# ЭТАП SYNTHESIS v3 (надзиратель, 2-й круг, 21.10.2026): критерии, оценки, оффер против рынка, медиаплан, гипотезы, ответы
# Версия синтеза 1–2 и прежние проверки Y/MP/A — qa/backup/recalc_before_wave2.py
# =====================================================================
import subprocess, tempfile, shutil, math
CO = main10
crit = rows('criteria.csv'); ctext = {x['id']: x for x in rows('criteria_text.csv')}
cs = rows('criteria_scores.csv'); csc = {x['id']: x for x in cs}
CID = [x['id'] for x in crit]
CB = {x['id']: x for x in crit}
COMBO = {'C09': 'смета_замер', 'C14': 'сроки', 'C18': 'материал', 'C19': 'фундамент_столбы', 'C27': 'гарантия', 'C28': 'связь_менеджер', 'C29': 'бригада_поведение'}
KEYS = dict(zip(['M', 'PZ', 'ZK', 'ZZ', 'RZ', 'ZV', 'OZ', 'DZ', 'ZF', 'PSK'], CO))

# --- Y01 воспроизводимость build_criteria.py в песочнице + выгрузка оценок обещаний комбинированных критериев ---
tmp = tempfile.mkdtemp()
os.makedirs(f'{tmp}/data'); os.makedirs(f'{tmp}/notes/raw_reviews')
for f in os.listdir(os.path.join(ROOT, 'data')):
    shutil.copy(D(f), f'{tmp}/data/')
for f in ('all_reviews.json', 'neg_coded.json'):
    shutil.copy(N('raw_reviews/' + f), f'{tmp}/notes/raw_reviews/')
src = open(N('scripts/synthesis/build_criteria.py'), encoding='utf-8').read().replace("B = '/home/claude/zabory'", f"B = '{tmp}'")
src += "\nimport json as _j\n_j.dump({k: {K[kk]: v[0] for kk, v in S[k].items()} for k in COMBO}, open(f'{B}/promise_combo.json', 'w'))\n"
open(f'{tmp}/bc.py', 'w', encoding='utf-8').write(src)
subprocess.run(['python3', '-I', f'{tmp}/bc.py'], capture_output=True, cwd=tmp)
same = [f for f in ('criteria.csv', 'criteria_text.csv', 'criteria_scores.csv')
        if open(f'{tmp}/data/{f}', encoding='utf-8').read() == open(D(f), encoding='utf-8').read()]
check('Y01', 'build_criteria.py воспроизводит criteria*.csv (совпало файлов из 3)', 3, len(same))
PROM = json.load(open(f'{tmp}/promise_combo.json', encoding='utf-8')) if os.path.exists(f'{tmp}/promise_combo.json') else {}
shutil.rmtree(tmp)

# --- Y02 вес v3: 100 × (0,7 × r / r_max + 0,3 × q / q_max), r = max(негатив / 851, позитив / 3 985) ---
rr_ = {x['id']: max(int(x['reviews_neg_n']) / 851, int(x['reviews_pos_n']) / 3985) for x in crit}
rmax = max(rr_.values()); qmax = max(int(x['queries_n']) for x in crit)
badw = [x['id'] for x in crit if abs(round(100 * (0.7 * rr_[x['id']] / rmax + 0.3 * int(x['queries_n']) / qmax), 1) - float(x['weight'])) > 0.051]
check('Y02', 'вес критерия ≠ формуле v3 (criteria_rules.md п.1)', '[]', str(badw))
check('Y02b', 'r_max (C41 после W2-K1) / q_max (C08)', '31.4 / 18', f'{rmax*100:.1f} / {qmax}')

# --- Y03 класс v3: вес < 10 → второстепенный; охват (оценок ≥3) 8–10 обяз., 4–7 ключ., 0–3 своб. ---
badc = []
for x in crit:
    cov = sum(1 for c in CO if int(csc[x['id']][c]) >= 3)
    w_ = float(x['weight'])
    cls = 'второстепенный' if w_ < 10 else 'обязательный' if cov >= 8 else 'ключевой' if cov >= 4 else 'свободный'
    if cov != int(x['companies_score_ge3']) or cls != x['class']: badc.append(x['id'])
check('Y03', 'класс / охват ≠ правилу v3 (criteria_rules.md п.2)', '[]', str(badc))
check('Y04', 'критериев / C02, C38, C39, C40 вне суммы', '38 / вынесены', f"{len(crit)} / {'вынесены' if not {'C02','C38','C39','C40'} & set(CID) else 'остались'}")
cnt_cls = Counter(x['class'] for x in crit)
note('Y04b', 'классы v3: ключевой / обязательный / свободный / второстепенный', f"{cnt_cls['ключевой']} / {cnt_cls['обязательный']} / {cnt_cls['свободный']} / {cnt_cls['второстепенный']}")

# --- Y05 C42 «Квалификация и консультация»: голос клиента измерен темой «консультация», где часть слов — общая похвала ---
raw_ = json.load(open(N('raw_reviews/all_reviews.json'), encoding='utf-8'))
pos_t = [x['text'].lower() for x in raw_ if x['company'] in CO and (x['text'] or '').strip() and int(float(x['stars'] or 0)) >= 4 and len(x['text'].strip()) >= 15]
FULL = re.compile(r'консульт\w*|подробно (рассказ|объясн|ответ|проконсульт)|объяснил\w*|все (рассказал|объяснил|разъяснил)|помог\w* (выбрать|определит|подобрать)|подсказал\w*|посоветовал\w*|грамотн\w*|компетентн\w*|профессионал\w*|вежлив\w*|внимательн\w*|отзывчив\w*|на связи|всегда на связи|оперативно отвеча|менеджер\w*.{0,40}(отличн|молодец|помог|вежлив|грамотн|внимат|приятн)|замерщик\w*.{0,40}(отличн|молодец|помог|вежлив|грамотн|подробн|профессион)')
NARROW = re.compile(r'консульт\w*|подробно (рассказ|объясн|ответ|проконсульт)|объяснил\w*|все (рассказал|объяснил|разъяснил)|помог\w* (выбрать|определит|подобрать)|подсказал\w*|посоветовал\w*|менеджер\w*.{0,40}(отличн|молодец|помог|вежлив|грамотн|внимат|приятн)|замерщик\w*.{0,40}(отличн|молодец|помог|вежлив|грамотн|подробн|профессион)')
f_ = sum(1 for t in pos_t if FULL.search(t)); n_ = sum(1 for t in pos_t if NARROW.search(t))
gen = sum(1 for t in pos_t if FULL.search(t) and not NARROW.search(t) and not re.search(r'на связи|оперативно отвеча', t))
note('Y05', 'C42: позитив с темой «консультация» / только общая похвала («профессионалы», «грамотные», «вежливые», «внимательные») / консультация, менеджер, замерщик', f'{f_} / {gen} ({gen/f_*100:.0f}%) / {n_} ({n_/len(pos_t)*100:.1f}% из {len(pos_t)})')
r42n = n_ / len(pos_t); rmax2 = max(v for k, v in rr_.items() if k != 'C42'); rmax2 = max(rmax2, r42n)
w2 = {x['id']: round(100 * (0.7 * (r42n if x['id'] == 'C42' else rr_[x['id']]) / rmax2 + 0.3 * int(x['queries_n']) / qmax), 1) for x in crit}
top5 = sorted(w2, key=lambda k: -w2[k])[:5]
note('Y06', 'если голос C42 = консультация/менеджер/замерщик: вес C42, ранг; первые 5 критериев', f"{w2['C42']}, ранг {sorted(w2, key=lambda k: -w2[k]).index('C42') + 1}; {', '.join(f'{k} {w2[k]}' for k in top5)}")
check('Y07', 'первые 5 по весу (synthesis_spravka разд.1 и «Главные наблюдения» п.1)', 'C41, C28, C18, C27, C09', ', '.join(CID[:5]))
check('Y07b', 'W2-K1: C42 — ранг / вес / позитив консультации', '7 / 35.6 / 636 из 3985', f"{CID.index('C42')+1} / {CB['C42']['weight']} / {CB['C42']['reviews_pos_n']} из {CB['C42']['reviews_pos_base']}")

# --- Y10 суммы и взвешенные суммы ---
W = {x['id']: float(x['weight']) for x in crit}
kk = [x['id'] for x in crit if x['class'] in ('ключевой', 'свободный')]
bad = []
for c in CO:
    s = sum(int(csc[i][c]) for i in CID)
    wv = round(sum(int(csc[i][c]) * W[i] for i in CID) / sum(W.values()), 2)
    kv = round(sum(int(csc[i][c]) * W[i] for i in kk) / sum(W[i] for i in kk), 2)
    if s != int(csc['ИТОГ'][c]) or abs(wv - float(csc['ИТОГ_ВЗВ'][c])) > 0.005 or abs(kv - float(csc['ИТОГ_КЛЮЧ'][c])) > 0.005:
        bad.append(c)
check('Y10', 'ИТОГ / ИТОГ_ВЗВ / ИТОГ_КЛЮЧ ≠ пересчёту', '[]', str(bad))
check('Y11', 'Σ весов (строка ИТОГ_ВЗВ)', float(csc['ИТОГ_ВЗВ']['weight']), round(sum(W.values()), 1), 0.05)
empty = [(i, c) for i in CID for c in CO if csc[i][c].strip() == '' or ctext[i][c].strip() == '']
check('Y12', 'пустые клетки в criteria_scores / criteria_text', '[]', str(empty))

# --- Y13 вычисляемые клетки C01, C07, C41 ---
allr = [x for x in raw if x['company'] in CO and (x['text'] or '').strip()]
yt, yn, yr = Counter(), Counter(), Counter()
for x in allr:
    if x['platform'] == 'Яндекс Карты':
        yt[x['company']] += 1
        if float(x['stars']) <= 3: yn[x['company']] += 1
        if (x.get('reply') or '').strip(): yr[x['company']] += 1
cod = json.load(open(N('raw_reviews/neg_coded.json'), encoding='utf-8'))['neg']
thy = defaultdict(Counter)
for x in cod:
    if x['company'] in CO and x['platform'] == 'Яндекс Карты':
        for t in x['themes']: thy[x['company']][t] += 1
def rs(r):
    for lim, sc in [(1, 5), (2, 4), (4, 3), (7, 2), (10, 1)]:
        if r <= lim: return sc
    return 0
pmn, pmx = min(pn.values()), max(pn.values())
bad = []
for c in CO:
    sh = round(100 * yn[c] / yt[c], 1)
    exp = {'C01': 5 if sh <= 5 else 4 if sh <= 8 else 3 if sh <= 13 else 2 if sh <= 20 else 1 if sh <= 28 else 0,
           'C07': round(5 * (pmx - pn[c]) / (pmx - pmn)),
           'C41': rs(round(100 * thy[c]['качество_монтажа'] / yt[c], 1))}
    for k, e in exp.items():
        if int(csc[k][c]) != e: bad.append(f'{k}/{c}: {csc[k][c]}≠{e}')
check('Y13', 'вычисляемые клетки C01 C07 C41 ≠ источникам', '[]', str(bad))

# --- Y14 комбинированные клетки ---
bad = []
for i, th in COMBO.items():
    for c in CO:
        m = re.search(r'жалоб по теме: ([\d,]+) на 100 отзывов \((\d+) из (\d+)\)', ctext[i][c])
        k_, n_c = thy[c][th], yt[c]
        if not m or int(m.group(2)) != k_ or int(m.group(3)) != n_c:
            bad.append(f'{i}/{c}'); continue
        r_ = rs(round(100 * k_ / n_c, 1)); s_ = int(csc[i][c])
        p_ = PROM.get(i, {}).get(c)
        if p_ is not None and int((p_ + r_) / 2 + 0.5) != s_: bad.append(f'{i}/{c} балл')
check('Y14', 'комбинированные клетки: счёт жалоб или итог (обещание + жалобы) не сходятся', '[]', str(bad))

# --- Y15 SM1, SM2, SM7 (2-й круг) и баллы по прозвону ---
fix = {('C12', 'pskzabor.ru'): 3, ('C27', 'masterovit.ru'): 1, ('C15', 'oblzabor.ru'): 0, ('C20', 'oblzabor.ru'): 1, ('C20', 'dostup-zabor.ru'): 1,
       ('C33', 'zavodzaborov.ru'): 3, ('C42', 'zavodzaborov.ru'): 5, ('C44', 'zavodzaborov.ru'): 3, ('C42', 'prof-zabory.ru'): 4, ('C44', 'prof-zabory.ru'): 4}
check('Y15', 'SM1 и баллы по прозвону (criteria_rules.md п.3, 99): отклонения', '[]', str([f'{i}/{c}={csc[i][c]}≠{v}' for (i, c), v in fix.items() if int(csc[i][c]) != v]))
t21 = ctext['C21']['zavodzaborov.ru']
check('Y16', 'SM2: C21 zavodzaborov — сваи и бетон в ячейке', 'да', 'да' if all(s in t21.replace('\xa0', ' ') for s in ('80 760', '123 460', '101 400', '144 100')) else 'нет')
check('Y17', 'SM7: C10 zaboroff — оговорка об исследовании 13.10', 'да', 'да' if '13.10' in ctext['C10']['zaboroff.ru'] else 'нет')

# --- OV оффер против рынка (offer_vs_market.csv, структура W2-V2: исполнено / обещание / роль) ---
ovm = [x for x in rows('offer_vs_market.csv') if x['id'].startswith('C')]
prom_csv = {x['id']: x for x in rows('criteria_scores_promise.csv')}
bad = []
for x in ovm:
    sc = [int(x[c]) for c in CO]
    if any(x[c] != csc[x['id']][c] for c in CO) or int(x['market_best_executed']) != max(sc) or float(x['market_median_executed']) != st.median(sc): bad.append(x['id'] + ' исполнено')
    p_ = prom_csv[x['id']]
    psc = None if p_['combined_with_reviews'] == 'только отзывы' else [int(p_[c]) for c in CO]
    if (str(max(psc)) if psc else 'н/п') != x['market_best_promise_only']: bad.append(x['id'] + ' лучшее обещание')
    d_ = int(x['dom_girlyand_promise'])
    exp_n = ('— (у нас 0)' if d_ == 0 else (str(sum(1 for v in psc if v >= d_)) if psc else 'н/п'))
    if exp_n != x['competitors_promise_at_or_above']: bad.append(x['id'] + ' не ниже')
    ref = max(psc) if psc else max(sc)
    if x['class'] == 'свободный':
        role = 'обещание закрывает свободный критерий' if d_ >= 4 else 'свободный критерий не закрыт'
    elif d_ > ref: role = 'обещание, которого нет ни у кого из 10'
    elif d_ == ref: role = 'на уровне лучших обещаний рынка'
    else: role = 'не можем конкурировать на старте' if x['id'] in ('C01', 'C41', 'C04', 'C03', 'C37', 'C20') else 'ниже лучших обещаний рынка'
    if role != x['role']: bad.append(x['id'] + ' роль')
check('OV01', 'offer_vs_market: исполнено = criteria_scores (макс., медиана), лучшее обещание = criteria_scores_promise, «не ниже», роль', '[]', str(bad))
rc = Counter(x['role'] for x in ovm)
check('OV02', 'роли: закрывает свободный / нет ни у кого / на уровне / ниже / не конкурирует', '3 / 6 / 13 / 10 / 6',
      ' / '.join(str(rc[k]) for k in ('обещание закрывает свободный критерий', 'обещание, которого нет ни у кого из 10', 'на уровне лучших обещаний рынка', 'ниже лучших обещаний рынка', 'не можем конкурировать на старте')))
added = [x['id'] for x in ovm if x['scale_level_added_21_10'] != 'нет']
check('OV03', 'критериев со шкалой, дополненной 21.10 (страница: 5 уровней 5, 2 уровня 4, 2 новые строки)', '9: C09 C18 C22 C27 C28 C29 C30 C42 C44', f"{len(added)}: {' '.join(sorted(added))}")
nobody = [x['id'] for x in ovm if x['role'] == 'обещание, которого нет ни у кого из 10']
check('OV04', '«нет ни у кого из 10» — все со шкалой, дополненной 21.10, кроме C06 (неустойка)', '[]', str([i for i in nobody if i not in added and i != 'C06']))
ids_p = [x['id'] for x in ovm if x['id'] not in ('C01', 'C41')]
WVp = lambda get: round(sum(get(i) * W[i] for i in ids_p) / sum(W[i] for i in ids_p), 2)
svod = [x for x in rows('offer_vs_market.csv') if x['id'] == 'СВОДКА'][0]
got = ' / '.join(f"{WVp(lambda i, c=c: int(prom_csv[i][c])):.2f}" for c in CO[:3]) + f" / ДГ {WVp(lambda i: int(next(y for y in ovm if y['id']==i)['dom_girlyand_promise'])):.2f}"
check('OV05', 'СВОДКА (обещания без C01, C41): masterovit / prof-zabory / zaborkin / Дом гирлянд', f"{float(svod['masterovit.ru']):.2f} / {float(svod['prof-zabory.ru']):.2f} / {float(svod['zaborkin.ru']):.2f} / ДГ {float(svod['dom_girlyand_promise']):.2f}", got)

# --- MP медиаплан v3 ---
bud = {x['domain'] + '|' + x['source'].split(',')[0]: x for x in rows('ad_budgets.csv')}
spm = bud['masterovit.ru|Spywords']
cpc_sp = num(spm['budget_day']) * 30 / num(spm['traffic_from_ads'])
check('MP01', 'CPC Spywords masterovit.ru = 17 276 × 30 / 4 164', 124, cpc_sp, 0.5)
FQ = ['забор под ключ', 'установка забора', 'забор из профнастила под ключ', 'забор в московской области',
      'монтаж забора цена', 'заказать забор', 'забор из евроштакетника', 'забор жалюзи']
ff = sum(kq[q_]['f'] for q_ in FQ)
check('MP02', 'прогноз Keys.so по 8 запросам, ₽ / Σ частотности', '85.4 / 235979', f"{sum(kq[q_]['f'] * kq[q_]['cpc'] for q_ in FQ) / ff:.1f} / {ff}")
rc = open(N('scripts/synthesis/review_checks.txt'), encoding='utf-8').read()
medl = int(re.search(r'медиана=(\d+)', rc).group(1)); q3 = int(re.search(r'Q3=(\d+)', rc).group(1))
pm = st.median(pn.values())
fence = (round(medl * pm), round(q3 * pm)); pack = tuple(f + 103025 for f in fence)
check('MP03', 'чек забора / пакета (40 и 73 м × медиана «от»; + ворота 103 025)', '67600-123370 / 170625-226395', f'{fence[0]}-{fence[1]} / {pack[0]}-{pack[1]}')
mp = rows('mediaplan.csv')
NB = lambda s: str(s).replace('\xa0', '').replace(' ', '')
P = lambda s: float(NB(s).replace('%', '').replace(',', '.'))
def RNG(s):
    s = NB(s).replace('%', '').replace(',', '.')
    parts = [x for x in s.split('–') if x]
    v = [float(x) for x in parts]
    return (v[0], v[-1])
# --- MP04 медиаплан в трёх сценариях чека (W2-K2): клики, заявки, заказы, цена заказа, доля рекламы в чеке, безубыточная заявка ---
bad = []
for x in mp:
    if x['cpl_rub'] in ('не считается',) or x['hypothesis_id'] in ('H6', 'H7'): continue
    hid = x['hypothesis_id'] + ' / ' + x['scenario'][:12]
    b_ = P(x['budget_rub_assumption']); cl = RNG(x['cpl_rub']); close = 0.023 if x['close_rate'].startswith('2,3') else 0.09
    if x['cpc_rub'] != 'не применяется':
        cpc = RNG(x['cpc_rub']); clk = RNG(x['clicks'])
        if abs(b_ / cpc[1] - clk[0]) > 0.6 or abs(b_ / cpc[0] - clk[1]) > 0.6: bad.append(hid + ' клики')
        if x['scenario'].startswith('база'):
            conv = P(x['page_conversion']) / 100
            if abs(cpc[0] / conv - cl[0]) > 0.002 * cl[0] or abs(cpc[1] / conv - cl[1]) > 0.002 * cl[1]: bad.append(hid + ' цена заявки')
    leads = RNG(x['leads'])
    if abs(b_ / cl[-1] - leads[0]) > 0.06: bad.append(hid + ' заявки')
    orders = RNG(x['orders']); cpo = RNG(x['cpo_rub'])
    if abs(leads[0] * close - orders[0]) > 0.011: bad.append(hid + ' заказы')
    if abs(cl[0] / close - cpo[0]) > 0.001 * cpo[0] or abs(cl[-1] / close - cpo[-1]) > 0.001 * cpo[-1]: bad.append(hid + ' цена заказа')  # CPL на странице округлён до рубля
    for k in ('check1', 'check2', 'check3'):
        if x[f'{k}_rub'] in ('', '—', 'не считается'): continue
        ch = RNG(x[f'{k}_rub']); sh = RNG(x[f'{k}_ad_share'])
        exp = (cpo[0] / ch[-1] * 100, cpo[-1] / ch[0] * 100)
        if abs(exp[0] - sh[0]) > 0.06 or abs(exp[1] - sh[-1]) > 0.06: bad.append(f'{hid} {k} доля {exp[0]:.1f}–{exp[1]:.1f}')
        be_ = RNG(x[f'{k}_breakeven_cpl_rub'])
        if abs(0.25 * ch[0] * close - be_[0]) > 1 or abs(0.25 * ch[-1] * close - be_[-1]) > 1: bad.append(f'{hid} {k} безубыточная')
        v_ = x[f'{k}_verdict']; lo_, hi_ = sh[0], sh[-1]
        cls_ = lambda v: '≤ 11% чека' if v <= 11 else 'окупается по марже' if v <= 25 else 'не окупается'
        exp_v = cls_(lo_) if cls_(lo_) == cls_(hi_) else f'{cls_(lo_)} … {cls_(hi_)}'
        if exp_v != v_: bad.append(f'{hid} {k} вердикт «{v_}» ≠ «{exp_v}»')
check('MP04', 'медиаплан (3 сценария чека): клики, заявки, заказы, цена заказа, доля в чеке, безубыточная, вердикт ≠ формулам', '[]', str(sorted(set(bad))))
EXK = round(14205 / 57377, 3); S1, S2 = round(29008 / 57377, 2), round(29008 / 41508, 2)
check('MP06', 'ёмкость H1 за 21 день (широкая × 0,248 × сезон × 5% × 21/30)', '1045-1434', f'{round(ff*EXK*S1*0.05*21/30)}-{round(ff*EXK*S2*0.05*21/30)}')
hy = {x['hypothesis_id']: x for x in rows('hypotheses.csv')}
check('MP07', 'бюджет теста H1–H8, ₽ (допущение; страница: 183 500)', 183500, sum(int(h['budget_rub_assumption']) for h in hy.values()))
bad = []
for hid, h in hy.items():
    base = ([x for x in mp if x['hypothesis_id'] == hid] or [None])[0]
    bc = NB(h['base_check_rub'])
    if base and bc not in (NB(base['check2_rub']), NB(base['check1_rub'])): bad.append(hid + ' базовый чек')
    if h['threshold_cpl_ad11pct_rub'] not in ('', '—'):
        thr = RNG(h['threshold_cpl_ad11pct_rub']); ch = RNG(h['base_check_rub']); close = 0.023 if hid == 'H8' else 0.09
        if abs(0.11 * ch[0] * close - thr[0]) > 1 or abs(0.11 * ch[-1] * close - thr[-1]) > 1: bad.append(hid + ' порог 11%')
        m = re.search(r'цена заявки выше ([\d\s\xa0]+) ₽ \(2 ×', h['stop_rule'])
        if m and abs(P(m.group(1)) - 2 * 0.11 * ch[-1] * close) > 1: bad.append(hid + ' стоп 2× порог')
check('MP08', 'hypotheses.csv: базовый чек = сценарию базы медиаплана; порог 11% и стоп-правило = формуле', '[]', str(sorted(set(bad))))
ok_ = [x for x in rows('order_sums_reviews.csv') if x['included'] == 'да']
vals = sorted(int(x['sum_rub']) for x in ok_)
q = st.quantiles(vals, n=4, method='inclusive')
check('MP09', 'суммы заказов в отзывах: размечено / вошло / медиана / Q1 / Q3 / негатив', '38 / 20 / 259825 / 165000 / 407500 / 19',
      f"{len(rows('order_sums_reviews.csv'))} / {len(vals)} / {st.median(vals):.0f} / {q[0]:.0f} / {q[2]:.0f} / {sum(1 for x in ok_ if int(x['stars']) <= 3)}")
note('MP09b', 'квартили сумм методом exclusive (справочно)', ' / '.join(f'{v:.0f}' for v in st.quantiles(vals, n=4)))
h8 = [x for x in mp if x['hypothesis_id'] == 'H8' and x['scenario'].startswith('база')][0]
check('MP12', 'H8 база: обращение 230 ₽, закрытие 2,3% → заказ / порог 11% при 259 825 и 67 600 ₽', '10000 / 657 / 171',
      f"{230/0.023:.0f} / {0.11*259825*0.023:.0f} / {0.11*67600*0.023:.0f}")
h2 = [x for x in mp if x['hypothesis_id'] == 'H2' and x['scenario'].startswith('база')][0]
check('MP13', 'H2: 14 000 ₽ → клики при 124 / 85,4 ₽; ёмкость', '113-164 / 161–172', f"{14000/124:.0f}-{14000/85.4:.0f} / {h2['capacity_clicks_test_period']}")
check('MP14', '«Коротко»: реклама в чеке пакета при 350–450 тыс. ₽ / при 170–226 тыс. ₽ (H2)', '10,5%–19,7% / 21,0%–40,4%', f"{h2['check2_ad_share']} / {h2['check1_ad_share']}")

# --- TR бренд-тренд и региональный коэффициент ---
bt = rows('brand_trend.csv')[0]
xs_ = [x_ - xs[0] + 1 for x_ in xs]; mx_ = st.mean(xs_)
sl = sum((a - mx_) * (b - my) for a, b in zip(xs_, ys)) / sum((a - mx_) ** 2 for a in xs_); ic = my - sl * mx_
r2 = 1 - sum((b - (ic + sl * a)) ** 2 for a, b in zip(xs_, ys)) / sum((b - my) ** 2 for b in ys)
lx = [math.log(a) for a in xs_]; ml = st.mean(lx)
sl2 = sum((a - ml) * (b - my) for a, b in zip(lx, ys)) / sum((a - ml) ** 2 for a in lx); ic2 = my - sl2 * ml
r2l = 1 - sum((b - (ic2 + sl2 * a)) ** 2 for a, b in zip(lx, ys)) / sum((b - my) ** 2 for b in ys)
check('TR01', 'тренд: y = a + b·t, R²; лог: R²', '39904 / 912.7 / 0.079 / 0.117', f'{ic:.0f} / {sl:.1f} / {r2:.3f} / {r2l:.3f}')
bt_ms = [r for r in rows('brand_trend.csv') if r['series'].startswith('бренд «мастеровит»')][0]
_m = raw_dyn('dyn_мастеровит_msk_mo.csv') if 'raw_dyn' in globals() else None
check('TR02', 'brand_trend.csv: 14 рядов Вордстата (10 брендов + 4 запроса рынка)', 14, len(rows('brand_trend.csv')))
note('TR02b', 'Мастеровит: линейный тренд и направление по скользящей сумме 12 мес.', f"{bt_ms['linear_equation']}; R² {bt_ms['linear_r2']}; {bt_ms['direction']}")
rc_ = rows('regional_coef.csv')[0]
check('TR03', 'региональный коэффициент примера курса / переходов', '0.0816 / 8156', f'{22690/278215:.4f} / {round(22690/278215*100000)}')

# --- AD реклама Яндекса волны 2 (ad_budgets.csv, ads_yandex.csv) ---
for key, cid in (('masterovit.ru|Spywords', 'AD01'), ('sales.prof-zabory.ru|Spywords', 'AD02'), ('prof-zabory.ru|Spywords', 'AD03')):
    x = bud[key]; bd = num(x['budget_day']); tr = num(x['traffic_from_ads'])
    claimed = f"{x['budget_month'].split(' ')[0]} / {x['cpc_calc'].split(' ')[0]} / {x['cost_per_order_est'].split(' ')[0]}"
    check(cid, f"{x['domain']}: бюджет в месяц / клик / заявка при 1% (без округления заявок)", claimed, f'{bd*30:.0f} / {bd*30/tr:.0f} / {bd*30/(tr*0.01):.0f}')
km = bud['masterovit.ru|Keys.so']
check('AD04', 'masterovit.ru: Keys.so / Spywords — бюджет, запросов, раз', '3.8 / 3.6', f"{1972900/num(spm['budget_month'].split(' ')[0]):.1f} / {num(km['queries_count'])/num(spm['queries_count']):.1f}")
spraw = open(N('raw_ads/spy_masterovit.ru.txt'), encoding='utf-8').read()
cpcs = [int(l.split('|')[-2]) for l in spraw.splitlines() if l.startswith('Q|')]
check('AD05', 'Spywords masterovit.ru: средние CPC по 5 видимым запросам, мин–макс (справка 71–173)', '71-173', f'{min(cpcs)}-{max(cpcs)}')
note('AD05b', 'из 5 видимых запросов Spywords masterovit.ru: бренд и навес', [l.split('|')[1] for l in spraw.splitlines() if l.startswith('Q|')])
ady = rows('ads_yandex.csv')
check('AD06', 'ads_yandex.csv: строк / доменов с текстами', '98 / 5', f"{len(ady)} / {len(set(x['domain'] for x in ady))}")
dir8 = [d for d in CO if d in {x['domain'] for x in rows('ad_budgets.csv')} or (d == 'prof-zabory.ru')]
check('AD07', 'Директ у компаний полного разбора (Keys.so или Spywords)', 8, len(dir8))

# --- MAP Яндекс Карты (ads_maps.csv) ---
am = rows('ads_maps.csv'); ym = [x for x in am if x['source'] == 'Яндекс Карты']
isad = lambda x: x['ad_mark'].startswith('реклам')
byq = defaultdict(list)
for x in ym: byq[x['query']].append(x)
check('MAP01', 'у всех 10 первых карточек по 4 запросам — реклама', '4 из 4', f"{sum(1 for v in byq.values() if all(isad(x) for x in sorted(v, key=lambda x: int(x['rank']))[:10]))} из {len(byq)}")
check('MAP02', 'рекламных карточек: заборы / установка / откатные / под ключ', '28/74 20/75 29/95 26/68',
      ' '.join(f"{sum(map(isad, byq[q_]))}/{len(byq[q_])}" for q_ in ('заборы', 'установка заборов', 'откатные ворота', 'забор под ключ')))
paid = sorted({x['competitor'] for x in ym if x['competitor'] in CO and isad(x)})
check('MAP03', 'компаний полного разбора с рекламой на Картах', 6, len(paid))
mst = [x for x in ym if x['competitor'] == 'masterovit.ru']
check('MAP04', 'masterovit.ru: реклама в появлениях', '17 из 20', f'{sum(map(isad, mst))} из {len(mst)}')

# --- AV Авито (avito_serp.csv) ---
av = [x for x in rows('avito_serp.csv') if x['rank'].strip().isdigit()]
prm = [x for x in av if 'Продвинуто' in x['promotion_mark']]
check('AV01', 'Авито «забор под ключ», стр. 1: «Продвинуто»', '44 из 50 (88%)', f'{len(prm)} из {len(av)} ({len(prm)/len(av)*100:.0f}%)')
apr = [num(x['price_from_rub']) for x in av if x['price_from_rub'].strip()]
check('AV02', 'цена «от»: n / медиана / Q1–Q3 / мин–макс', '49 / 850 / 650–1315 / 200–2300',
      f"{len(apr)} / {st.median(apr):.0f} / {st.quantiles(apr, n=4)[0]:.0f}–{st.quantiles(apr, n=4)[2]:.0f} / {min(apr):.0f}–{max(apr):.0f}")
check('AV03', 'единица цены указана', '9 из 49', f"{sum(1 for x in av if 'указано' in x['price_unit'])} из {len(apr)}")
check('AV04', 'Облзабор / Мастеровит: объявлений в первых 50', '4 / 1', f"{sum(1 for x in av if x['competitor']=='oblzabor.ru')} / {sum(1 for x in av if x['competitor']=='masterovit.ru')}")
check('AV05', 'answers п.2 сводит 88% («забор под ключ», 21.10) и 48 из 50 («откатные ворота», исследование ворот 19.10)', 'да', 'да' if '48 из 50 (96%' in open(N('answers.md'), encoding='utf-8').read() else 'нет')

# --- PD персональные данные волны 2 ---
legal_ = [x['advertiser_legal'] for x in am if x['advertiser_legal'] and x['advertiser_inn'] and not re.search(r'ООО|ИП|АО|ЗАО|ПАО|ОАО|ОБЩЕСТВО|Индивидуальный|АКЦИОНЕРН|[A-Z]{3}', x['advertiser_legal'])]
check('PD01', 'ads_maps.csv: рекламодатель — физлицо (ФИО без ИП/ООО) с ИНН', 0, len(legal_))
ph_all = 0
for f in ('avito_serp.csv', 'avito_profiles.csv', 'ads_platforms.csv', 'ads_vk.csv', 'ads_telegram.csv', 'mystery_shopper.csv'):
    ph_all += len(phone.findall(open(D(f), encoding='utf-8').read()))
check('PD02', 'мобильные телефоны в avito_*, ads_platforms, ads_vk, ads_telegram, mystery_shopper', 0, ph_all)
check('PD03', 'avito_serp: продавцы-частники заменены («частный мастер»), отчеств в файле', '0', str(len(patr.findall(open(D('avito_serp.csv'), encoding='utf-8').read()))))

# --- SS пересъёмка сайтов ---
sl_ = rows('sites_screenshots_log.csv')
miss = [x[k] for x in sl_ for k in ('screenshot_desktop', 'screenshot_mobile', 'screenshot_full') if x[k] and not os.path.exists(os.path.join(ROOT, x[k]))]
check('SS01', 'скриншоты из журнала отсутствуют на диске', '[]', str(miss))
note('SS02', 'страниц в журнале / принят баннер cookies / закрыт попап', f"{len(sl_)} / {sum(1 for x in sl_ if x['consent_accepted'] != 'нет')} / {sum(1 for x in sl_ if x['popups_closed'] != 'нет')}")

# --- A answers.md (v3) ---
ans = open(N('answers.md'), encoding='utf-8').read()
check('A01', 'потолок 5 бригад, млн ₽: мин / макс', '14.2 / 90.6', f'{5*6*7*fence[0]/1e6:.1f} / {5*10*8*pack[1]/1e6:.1f}')
check('A02', 'доля от 20 млрд, %: мин / макс', '0.07 / 0.45', f'{5*6*7*fence[0]/2e10*100:.2f} / {5*10*8*pack[1]/2e10*100:.2f}')
fm_ = {(x['company'], x['year']): x for x in fin}
cshare = [num(fm_[('ООО «Мастеровит»', y)]['cost_share_pct']) for y in ('2024', '2025')]
check('A03', 'закупка до оплаты, тыс. ₽: забор / пакет при 76,6–76,8%', '52-95 / 131-174',
      f'{fence[0]*min(cshare)/1e5:.0f}-{fence[1]*max(cshare)/1e5:.0f} / {pack[0]*min(cshare)/1e5:.0f}-{pack[1]*max(cshare)/1e5:.0f}')
my_ = [x for x in raw if x['company'] == 'masterovit.ru' and x['platform'] == 'Яндекс Карты']
yy = {y: (sum(1 for x in my_ if x['date'][:4] == y), sum(1 for x in my_ if x['date'][:4] == y and float(x['stars']) <= 3)) for y in ('2021', '2024', '2025', '2026')}
check('A04', 'Мастеровит Яндекс: доля 1–3★ 2021 / 2024 / 2025 / 2026, %', '27 / 43 / 47 / 24', ' / '.join(f'{yy[y][1]/yy[y][0]*100:.0f}' for y in ('2021', '2024', '2025', '2026')))
check('A05', 'Мастеровит Яндекс: негативных 2026 из / 2025 из', '77 из 315 / 108 из 229', f"{yy['2026'][1]} из {yy['2026'][0]} / {yy['2025'][1]} из {yy['2025'][0]}")
sub = sum(1 for x in cod if x['company'] in CO and 'субподряд_монтаж' in x['themes'])
subm = sum(1 for x in cod if x['company'] == 'masterovit.ru' and 'субподряд_монтаж' in x['themes'])
check('A06', '«сторонний монтаж» (ручная разметка): всего / у Мастеровита', '19 / 14', f'{sub} / {subm}')
check('A07', 'answers п.2: метка «n=3 против n=1» при двух платных сайтах в тексте', 'n=2 против n=1', 'n=2 против n=1' if 'n=2 против n=1' in ans else ('n=3 против n=1' if 'n=3 против n=1' in ans else '?'))
check('A08', 'answers п.6: «Тренд спроса слабый» при R² 0,079 (справка: вывод не делается)', 'вывода нет', 'вывод есть' if 'Тренд спроса «забор под ключ» слабый' in ans else 'вывода нет')
pc = open(N('scripts/synthesis/persona_counts.txt'), encoding='utf-8').read()
check('A09', 'персонаж: дача / дом строго / дом широко, %', '8.0 / 1.0 / 3.1', ' / '.join(re.search(p, pc).group(1) for p in (r'дача.*\(([\d.]+)%', r'дом, строго.*\(([\d.]+)%', r'дом, широко.*\(([\d.]+)%')))
mo = {d: [num(ov[d][f'visits_2026_0{m}']) / 1000 for m in (7, 8, 9)] for d in ('prof-zabory.ru', 'zaborkin.ru', 'oblzabor.ru')}
check('A10', 'помесячно prof-zabory / oblzabor / zaborkin, тыс.', '111.9/181.1/73.8 | 10.2/23.9/16.1 | 42.8/44.0/26.8',
      ' | '.join('/'.join(f'{v_:.1f}' for v_ in mo[d]) for d in ('prof-zabory.ru', 'oblzabor.ru', 'zaborkin.ru')))
tw = {x['domain']: x for x in rows('traffic_channels_wide.csv')}
check('A11', 'доли платных: oblzabor / prof / zavod / masterovit / dostup / zaborkin, %', '67.9 / 64.1 / 27.3 / 15.1 / 8.1 / 4.8',
      ' / '.join(f"{num(tw[d]['paid_total_pct']):.1f}" for d in ('oblzabor.ru', 'prof-zabory.ru', 'zavodzaborov.ru', 'masterovit.ru', 'dostup-zabor.ru', 'zaborkin.ru')))

# --- SP synthesis_spravka.md v3 ---
negsh = {c: round(100 * yn[c] / yt[c], 1) for c in CO}
check('SP01', 'доля 1–3★ Яндекс: zaborovo / dostup / zavodzaborov / raduga / pskzabor / masterovit / zaborkin',
      '7.5 / 7.1 / 29.2 / 15.3 / 4.3 / 31.9 / 26.9',
      ' / '.join(str(negsh[c]) for c in ('zaborovo.ru', 'dostup-zabor.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru', 'pskzabor.ru', 'masterovit.ru', 'zaborkin.ru')))
order = sorted(CO, key=lambda c: -float(csc['ИТОГ_ВЗВ'][c]))
check('SP02', 'топ-3 по взвешенному баллу', 'zaborovo.ru, dostup-zabor.ru, prof-zabory.ru', ', '.join(order[:3]))
check('SP03', 'masterovit.ru: место по взвешенному баллу (страница: 10-й, 2,07)', 10, order.index('masterovit.ru') + 1)
spr = open(N('synthesis_spravka.md'), encoding='utf-8').read()
check('SP04', 'synthesis_spravka: в таблице «Сила конкурента» бюджет masterovit.ru с меткой «оценка»', 'да', 'да' if re.search(r'\| masterovit\.ru \| 129 606 \|[^\n]*518 тыс\. ₽ в месяц \(Spywords, оценка', spr) else 'нет')
cs_ = {x['domain']: x for x in rows('competitor_strength.csv')}
check('SP05', 'competitor_strength: визиты в месяц masterovit / prof (= визиты 3 мес / 3)', '129606 / 122301',
      f"{round(num(tw['masterovit.ru']['visits_3m'])/3)} / {round(num(tw['prof-zabory.ru']['visits_3m'])/3)}" if 'visits_3m' in tw['masterovit.ru'] else f"{cs_['masterovit.ru']['visits_month_similarweb']} / {cs_['prof-zabory.ru']['visits_month_similarweb']}")


# =====================================================================
# ПРОВЕРКА ПЕРЕД ПУБЛИКАЦИЕЙ (надзиратель, 21.10.2026): Авито волны 2, бюджеты Директа, финансы-динамика, сверка страницы
# =====================================================================
# --- AVF Авито: avito_listings / avito_sellers / avito_claims / avito_reviews / avito_profiles ---
AL = rows('avito_listings.csv')
AU = {}
for x in AL: AU.setdefault(x['listing_id'], x)
AU = list(AU.values())
tc = Counter(x['seller_type'] for x in AU)
check('AVF01', 'уникальных объявлений / компании / частные / не отдано', '249 / 109 / 137 / 3', f"{len(AU)} / {tc['компания']} / {tc['частный мастер']} / {tc['не отдано актором']}")
check('AVF01b', 'доли по 249: частные / компании, %', '55 / 44', f"{tc['частный мастер']/len(AU)*100:.0f} / {tc['компания']/len(AU)*100:.0f}")
got = []
for q_ in ('забор под ключ', 'откатные ворота', 'установка забора'):
    rr = sorted([x for x in AL if x['query'] == q_], key=lambda x: int(x['position_in_export']))
    a = Counter(x['seller_type'] for x in rr); b = Counter(x['seller_type'] for x in rr[:20])
    got.append(f"{a['компания']}/{a['частный мастер']} {b['компания']}/{b['частный мастер']}")
check('AVF02', 'компании/частные: все 100 и первые 20 — забор под ключ | откатные ворота | установка забора', '65/35 17/3 | 54/46 14/6 | 24/73 3/17', ' | '.join(got))
AS = rows('avito_sellers.csv')
ma = lambda t: [num(x['active_listings_in_profile']) for x in AS if x['seller_type'] == t and num(x['active_listings_in_profile']) is not None]
check('AVF03', 'медиана активных объявлений: компании (n) / частные (n)', '88 (n=55) / 36 (n=47)', f"{st.median(ma('компания')):.0f} (n={len(ma('компания'))}) / {st.median(ma('частный мастер')):.0f} (n={len(ma('частный мастер'))})")
APf = {x['company']: x for x in rows('avito_profiles.csv') if x['company']}
mp_ = APf['МАСТЕРОВИТ']
check('AVF04', 'МАСТЕРОВИТ: активных / закрытых / медиана просмотров / в выдаче 3 запросов (уник.)', '655 / 1071 / 105 / 15',
      f"{mp_['active_listings']} / {mp_['closed_listings']} / {mp_['median_views_total_in_3_queries']} / {len({x['listing_id'] for x in AL if x['seller'] == 'МАСТЕРОВИТ'})}")
def pstat(prod):
    v = sorted(float(x['price_rub']) for x in AU if x['product'] == prod and x['price_unit'] == 'п.м.' and x['price_rub'] and float(x['price_rub']) > 10)
    q_ = st.quantiles(v, n=4)
    return f"{len(v)} {st.median(v):.0f} {q_[0]:.0f}–{q_[2]:.0f} {min(v):.0f}–{max(v):.0f}"
check('AVF05', 'профнастил ₽/п.м.: n, медиана, Q1–Q3, мин–макс (страница: 33, 700, 650–1 210, 350–2 900)', '33 700 650–1210 350–2900', pstat('профнастил'))
check('AVF05b', 'евроштакетник / 3D-сетка / без материала: n медиана', '9 1050 | 6 1554 | 108 650', ' | '.join(' '.join(pstat(p_).split()[:2]) for p_ in ('евроштакетник', '3D-сетка', 'забор (материал не указан)')))
check('AVF05c', 'профнастил Авито против сайтов: 700 / 1 690 − 1, %', -59, (700 / 1690 - 1) * 100, 0.5)
gv = [x for x in AL if x['query'] == 'откатные ворота' and x['product'] in ('откатные ворота', 'ворота (тип не указан)')]
gp = [float(x['price_rub']) for x in gv if x['price_rub']]
gvd = [float(x['views_per_day_since_posted']) for x in gv if x['views_per_day_since_posted']]
check('AVF06', 'установка ворот: объявлений (комп./част.) / ≥15 000 ₽ n, медиана / <15 000 ₽ / просмотров медиана, в день / продавцов в выдаче', '34 (21/13) / 13, 41000 / 17 / 125, 11.3 / 74',
      f"{len(gv)} ({sum(1 for x in gv if x['seller_type']=='компания')}/{sum(1 for x in gv if x['seller_type']=='частный мастер')}) / {sum(1 for p_ in gp if p_>=15000)}, {st.median([p_ for p_ in gp if p_>=15000]):.0f} / {sum(1 for p_ in gp if p_<15000)} / {st.median([float(x['views_total']) for x in gv if x['views_total']]):.0f}, {st.median(gvd):.1f} / {len({x['seller_key'] for x in AL if x['query']=='откатные ворота'})}")
check('AVF07', 'единица цены указана / цены 1–10 ₽ / поднято ≤ 7 дней', '16 из 249 / 4 / 84 из 246',
      f"{sum(1 for x in AU if 'указано в цене' in x['price_unit_note'])} из {len(AU)} / {sum(1 for x in AU if x['price_rub'] and float(x['price_rub']) <= 10)} / {sum(1 for x in AU if x['days_since_posted'] and float(x['days_since_posted']) <= 7)} из {sum(1 for x in AU if x['days_since_posted'])}")
ACl = {x['listing_id']: x for x in rows('avito_claims.csv') if x['source_type'] == 'объявление' and x['duplicate_of_other_query'] == 'нет'}
shr = lambda k, t=None: (lambda g: f"{sum(int(x[k]) for x in g)/len(g)*100:.0f}")([x for x in ACl.values() if t is None or x['seller_type'] == t])
check('AVF08', 'обещания, % всех / компаний / частных: гарантия, толщина, рассрочка, цена за п.м., оплата после',
      '83/82/85 21/34/12 8/15/4 6/12/2 19/22/17', ' '.join('/'.join(shr(k, t) for t in (None, 'компания', 'частный мастер')) for k in ('гарантия', 'толщина_металла', 'рассрочка', 'цена_за_пм', 'оплата_после_монтажа')))
ARv = rows('avito_reviews.csv'); ARs = [x for x in ARv if x['score'].isdigit()]; ARn = [x for x in ARs if int(x['score']) <= 3]
check('AVF09', 'отзывы Авито: всего / компаний / с оценкой / 1–3★ / % / ответ продавца', '368 / 11 / 335 / 19 / 5.7 / 256',
      f"{len(ARv)} / {len({x['company'] for x in ARv})} / {len(ARs)} / {len(ARn)} / {len(ARn)/len(ARs)*100:.1f} / {sum(1 for x in ARv if x['has_seller_reply']=='да')}")
tn_ = Counter(t.strip() for x in ARn for t in x['themes_negative'].split(';') if t.strip())
ARp = [x for x in ARs if int(x['score']) >= 4]; tp_ = Counter(t.strip() for x in ARp for t in x['themes_positive'].split(';') if t.strip())
check('AVF10', 'темы негатива: договор / смета / гарантия / связь / монтаж; позитив: скорость / качество / консультация из n', '7/6/5/5/5; 154/109/67 из 316',
      f"{tn_['договор_документы']}/{tn_['смета_замер']}/{tn_['гарантия']}/{tn_['связь_менеджер']}/{tn_['качество_монтажа']}; {tp_['скорость_монтажа']}/{tp_['качество_позитив']}/{tp_['консультация']} из {len(ARp)}")
mrv = [x for x in ARs if x['company'] == 'МАСТЕРОВИТ']
rd = [int(v) for v in mp_['rating_distribution_1_to_5'].split(' / ')]
check('AVF11', 'МАСТЕРОВИТ 1–3★: последние 75 / всё распределение профиля', '7 из 75 (9%) / 11 из 157 (7%)',
      f"{sum(1 for x in mrv if int(x['score'])<=3)} из {len(mrv)} ({sum(1 for x in mrv if int(x['score'])<=3)/len(mrv)*100:.0f}%) / {sum(rd[:3])} из {sum(rd)} ({sum(rd[:3])/sum(rd)*100:.0f}%)")
AVS = {(x['company'], x['product']): x for x in rows('avito_vs_sites.csv')}
check('AVF12', 'Авито к сайту по минимуму: Облзабор профнастил / Заборкин профнастил / Мастеровит профнастил, %', '-46 / 74 / 5',
      ' / '.join(str(round(float(AVS[k]['avito_min_vs_site_pct']))) for k in (('Облзабор', 'профнастил'), ('Заборкин', 'профнастил'), ('МАСТЕРОВИТ', 'профнастил'))))

# --- ADF бюджеты Директа: 518 тыс. ₽ — оценка, нижняя граница ---
bud_ = {x['domain'] + '|' + x['source'].split(',')[0]: x for x in rows('ad_budgets.csv')}
km_ = [x for x in rows('ad_budgets.csv') if x['domain'] == 'masterovit.ru' and 'Keys.so' in x['source'] and 'прогноз' in (x['budget_month'] + x['note'] + x['source']).lower()]
check('ADF01', 'masterovit.ru: Spywords 17 276 × 30 / Keys.so прогноз / раз', '518280 / 1972900 / 3.8',
      f"{num(spm['budget_day'])*30:.0f} / {num(km['budget_month'].split(' ')[0]) if num(km['budget_month'].split(' ')[0]) else km['budget_month']:.0f} / {1972900/(num(spm['budget_day'])*30):.1f}")

# --- FIN динамика 2023–2025 (вкладка «Финансы»): выручка, маржа, дни дебиторки по каждому ООО ---
fin = rows('finance.csv')
FR = {(x['company'], x['year']): x for x in fin}
def fv(c, y, k):
    v = FR.get((c, y), {}).get(k)
    return num(v) if v not in (None, '', 'нет') else None
chg = lambda c: (fv(c, '2025', 'revenue_th_rub') / fv(c, '2024', 'revenue_th_rub') - 1) * 100
check('FIN01', 'падение 2025/2024: ЗАБОРОФФ / Первый строительный / Мособлстрой / Металлич. системы / СТРОЙ-ЦЕНТР, %', '-61 / -44 / -36 / -50 / -40',
      ' / '.join(f"{chg(c):.0f}" for c in ('ООО «ЗАБОРОФФ»', 'ООО «Первый строительный»', 'ООО «Мособлстрой»', 'ООО «Металлические системы»', 'ООО «СТРОЙ-ЦЕНТР»')))
check('FIN02', 'рост: Мастеровит Руф / Строймонтаж 2015 / ПРО-СТРОЙ, %; Мастеровит, %', '176 / 54 / 56; -12',
      f"{chg('ООО «Мастеровит Руф»'):.0f} / {chg('ООО «Строймонтаж 2015»'):.0f} / {chg('ООО «ПРО-СТРОЙ»'):.0f}; {chg('ООО «Мастеровит»'):.0f}")
grp = lambda y: (fv('ООО «Мастеровит»', y, 'revenue_th_rub') + fv('ООО «Мастеровит Руф»', y, 'revenue_th_rub')) / 1000
check('FIN03', 'группа Мастеровит 2024 → 2025, млн ₽; %', '3199 → 3295; 3', f"{grp('2024'):.0f} → {grp('2025'):.0f}; {(grp('2025')/grp('2024')-1)*100:.0f}")
bad = []
for x in fin:
    r_, n_, rec = num(x['revenue_th_rub']), num(x['net_profit_th_rub']), num(x['receivables_th_rub'])
    if r_ and n_ is not None and x['net_margin_pct'] not in ('', 'нет') and abs(n_ / r_ * 100 - num(x['net_margin_pct'])) > 0.06: bad.append(f"{x['company']} {x['year']} маржа")
    if r_ and rec is not None and x['receivable_days'] not in ('', 'нет') and abs(rec / r_ * 365 - num(x['receivable_days'])) > 1: bad.append(f"{x['company']} {x['year']} дни")
check('FIN04', 'finance.csv: маржа = прибыль / выручка, дни = дебиторка / выручка × 365', '[]', str(bad[:8]))
from html.parser import HTMLParser
class _TX(HTMLParser):
    def __init__(s_): super().__init__(); s_.cur = None; s_.depth = 0; s_.txt = {}; s_.skip = 0
    def handle_starttag(s_, t, a):
        a = dict(a)
        if t in ('script', 'style'): s_.skip += 1
        if t == 'section' and a.get('class', '').startswith('panel'): s_.cur = a.get('id'); s_.txt[s_.cur] = []
    def handle_endtag(s_, t):
        if t in ('script', 'style'): s_.skip -= 1
    def handle_data(s_, d):
        if s_.cur and not s_.skip: s_.txt[s_.cur].append(d)
_p = _TX(); _p.feed(open(os.path.join(ROOT, 'site', 'index.html'), encoding='utf-8').read())
TAB = {k: re.sub(r'\s+', ' ', ' '.join(v)).replace('\xa0', ' ') for k, v in _p.txt.items()}
fin_page = TAB.get('finansy', '')
bad = []
for c, short_ in (('ООО «Мособлстрой»', 'ООО «Мособлстрой»'), ('ООО «Заборово»', 'ООО «Заборово»'), ('ООО «ЗАБОРОФФ»', 'ООО «ЗАБОРОФФ»'), ('ООО «Строймонтаж 2015»', 'ООО «Строймонтаж 2015»'), ('ООО «Первый строительный»', 'ООО «Первый строительный»')):
    i = fin_page.find(short_ + ' ')
    seg = fin_page[i:i + 400]
    for y in ('2023', '2024', '2025'):
        v = fv(c, y, 'revenue_th_rub') / 1000
        txt = (f'{v:,.0f}' if v >= 100 else f'{v:,.1f}').replace(',', ' ').replace('.', ',')
        if f'{y[2:]} {txt} ' not in seg + ' ': bad.append(f'{c} {y} {txt}')
check('FIN05', 'вкладка «Финансы»: выручка 2023–2025 пяти ООО = finance.csv', '[]', str(bad))

# --- PG одна цифра — одно значение: вкладки страницы против данных и друг друга ---
def has(tab, s_): return s_.replace('\xa0', ' ') in TAB.get(tab, '')
PG = [
    ('PG01', 'korotko', '13 560'),
    ('PG02', 'korotko', '85–124 ₽'), ('PG02', 'gipotezy', '85–124 ₽'), ('PG02', 'predlozhenie', '85–124 ₽'),
    ('PG03', 'korotko', '4 270–6 200 ₽'), ('PG03', 'gipotezy', '4 270–6 200 ₽'),
    ('PG04', 'korotko', '518 тыс. ₽'), ('PG04', 'reklama', '518 280 ₽'), ('PG04', 'predlozhenie', '518 тыс. ₽'),
    ('PG05', 'korotko', '1,97 млн ₽'), ('PG05', 'reklama', '1 972 900 ₽'),
    ('PG06', 'korotko', '259 825 ₽'), ('PG06', 'gipotezy', '259 825 ₽'),
    ('PG07', 'korotko', '10,5–19,7%'), ('PG07', 'gipotezy', '10,5%–19,7%'), ('PG07', 'predlozhenie', '10,5–19,7%'),
    ('PG08', 'korotko', '183 500 ₽'), ('PG08', 'gipotezy', '183 500 ₽'),
    ('PG09', 'korotko', '161–172'), ('PG09', 'gipotezy', '161–172'),
    ('PG10', 'korotko', '19 из 335'), ('PG10', 'avito', '1–3★ — 19 (5,7%)'),
    ('PG11', 'korotko', '700 ₽/п.м. (n=33'), ('PG11', 'avito', '700 ₽ за п.м. (n=33)'),
    ('PG12', 'korotko', 'МАСТЕРОВИТ — 655'), ('PG12', 'avito', '655 активных'),
    ('PG13', 'korotko', '44 из первых 50'), ('PG13', 'reklama', '17 из 20'), ('PG13', 'korotko', '6 из 10 компаний'),
    ('PG14', 'korotko', '3 295 млн ₽'), ('PG14', 'finansy', '3 295'),
    ('PG15', 'korotko', '10 из 12 ООО'), ('PG15', 'finansy', '10 из 12 ООО'),
    ('PG16', 'korotko', '31,4%'), ('PG16', 'korotko', '28,4%'),
    ('PG17', 'korotko', '64,1%'), ('PG17', 'korotko', '67,9%'),
    ('PG18', 'gipotezy', 'до 657 ₽'), ('PG18', 'gipotezy', '171 ₽'),
    ('PG19', 'korotko', '2,0 млн ₽'), ('PG19', 'predlozhenie', '2,0 млн ₽'),
    ('PG20', 'korotko', '12 447') if False else ('PG20', 'reklama', '12 447 ₽'),
]
miss = [f'{c}:{t}:«{s_}»' for c, t, s_ in PG if not has(t, s_)]
check('PG', f'{len(PG)} ключевых значений на своих вкладках (Коротко, Реклама, Авито, Гипотезы, Финансы, Предложение)', '[]', str(miss))
STALE = ['191 500', '269 825', '3,93', '33,6%', '669 ₽', '«n=3', '(по формуле )', '1 591 по Keys']
found = [f'{t}:«{s_}»' for s_ in STALE for t in TAB if s_ in TAB[t]]
check('PG-STALE', 'устаревшие значения прежних версий на странице', '[]', str(found))
m75 = re.findall(r'МАСТЕРОВИТ[^.]{0,60}?1–3★ — (\d+%)', TAB.get('korotko', '') + ' ' + TAB.get('avito', ''))
m75 += re.findall(r'у Мастеровита 1–3★ — (\d+%)', TAB.get('avito', ''))
note('PG-M', 'доля 1–3★ МАСТЕРОВИТ на Авито в тексте страницы (должна быть одна база)', m75)

# ---------- Вордстат 21.10: пересчёт из сырых выгрузок (notes/raw_wordstat), независимо от analyze_ws.py ----------
import glob
MON_RU = {m: i for i, m in enumerate('январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь'.split(), 1)}
def raw_dyn(fname):
    t = open(os.path.join(ROOT, 'notes', 'raw_wordstat', fname), encoding='utf-8-sig').read().replace('\r', '\n')
    out = {}
    for mn, y, c in re.findall(r'(январь|февраль|март|апрель|май|июнь|июль|август|сентябрь|октябрь|ноябрь|декабрь) (\d{4});([\d\s ]+);', t):
        out[f'{y}-{MON_RU[mn]:02d}'] = int(re.sub(r'\D', '', c))
    return out
def raw_reg(fname):
    t = open(os.path.join(ROOT, 'notes', 'raw_wordstat', fname), encoding='utf-8-sig').read().replace('\r', '\n')
    body = t.split('все устройства', 1)[1]
    tok = [x for x in body.replace('\n', ';').split(';') if x.strip()]
    return [(tok[k], tok[k + 1], tok[k + 3]) for k in range(0, len(tok) - 3, 4)]
z = raw_dyn('dyn_забор_под_ключ_msk_mo.csv'); zr = raw_dyn('dyn_забор_под_ключ_rf_bez_msk.csv'); g = raw_dyn('dyn_откатные_ворота_msk_mo.csv')
check('WS1', 'Вордстат: «забор под ключ», МО, сентябрь 2026 (плитка «Коротко»)', 13560, z['2026-09'])
check('WS2', 'май / январь 2026 = ×6,0', 6.0, round(z['2026-05'] / z['2026-01'], 1))
check('WS3', 'ноябрь 2025 / сентябрь 2025 = 50%; декабрь = 24%', '50/24', f'{round(100*z["2025-11"]/z["2025-09"])}/{round(100*z["2025-12"]/z["2025-09"])}')
J = lambda s_, y: sum(s_[f'{y}-{m:02d}'] for m in range(1, 10))
check('WS4', 'янв–сен 2026 к 2025: −43,0%; к 2024: +5,2%', '-43.0/5.2', f'{round(100*(J(z,2026)/J(z,2025)-1),1)}/{round(100*(J(z,2026)/J(z,2024)-1),1)}')
check('WS5', 'остальная Россия янв–сен 2026 к 2025: +17,3%', 17.3, round(100 * (J(zr, 2026) / J(zr, 2025) - 1), 1))
check('WS6', 'ворота: май/январь ×1,8; ноябрь 61% сентября; пик август 2026 116 442', '1.8/61/116442',
      f'{round(g["2026-05"]/g["2026-01"],1)}/{round(100*g["2025-11"]/g["2025-09"])}/{max(g.values())}')
LAST = [f'2025-{m:02d}' for m in (10, 11, 12)] + [f'2026-{m:02d}' for m in range(1, 10)]
PREV = [f'2024-{m:02d}' for m in (10, 11, 12)] + [f'2025-{m:02d}' for m in range(1, 10)]
bfiles = {q: raw_dyn(f'dyn_{q.replace(" ", "_")}_msk_mo.csv') for q in ['мастеровит', 'профзаборы', 'заборкин', 'завод_заборов', 'радуга_заборов', 'заборово', 'облзабор', 'доступные_заборы', 'заборофф', 'пск_забор']}
tot = sum(sum(v[m] for m in LAST) for v in bfiles.values())
ms = bfiles['мастеровит']
check('WS7', 'Мастеровит: 13 701 в месяц, 70,3% суммы 10 брендов, +4,0% за год', '13701/70.3/4.0',
      f'{round(sum(ms[m] for m in LAST)/12)}/{round(100*sum(ms[m] for m in LAST)/tot,1)}/{round(100*(sum(ms[m] for m in LAST)/sum(ms[m] for m in PREV)-1),1)}')
zb = bfiles['заборово']
check('WS8', 'Заборово: 1 112 в месяц, +38,6% за год', '1112/38.6', f'{round(sum(zb[m] for m in LAST)/12)}/{round(100*(sum(zb[m] for m in LAST)/sum(zb[m] for m in PREV)-1),1)}')
small = [round(sum(v[m] for m in LAST) / 12) for q, v in bfiles.items() if q not in ('мастеровит', 'завод_заборов', 'заборово')]
check('WS9', 'остальные семь брендов: 132–579 в месяц', '132–579', f'{min(small)}–{max(small)}')
rz = {r[0]: (int(re.sub(r'\D', '', r[1])), r[2]) for r in raw_reg('reg_забор_под_ключ_regiony.csv')}
rg = {r[0]: (int(re.sub(r'\D', '', r[1])), r[2]) for r in raw_reg('reg_откатные_ворота_regiony.csv')}
check('WS10', 'доля Москвы и МО в России: 32,3% (заборы), 20,7% (ворота)', '32.3/20.7',
      f'{round(100*rz["Москва и область"][0]/rz["Россия"][0],1)}/{round(100*rg["Москва и область"][0]/rg["Россия"][0],1)}')
check('WS11', 'Раменский: 541 запрос, индекс 448% (заборы); 3 186 (ворота); Чехов ворота индекс 370%', '541/448/3186/370',
      f'{rz["Раменский район"][0]}/{round(num(rz["Раменский район"][1]))}/{rg["Раменский район"][0]}/{round(num(rg["Чехов (городской округ)"][1]))}')
fin = {(r['domain'], r['year']): r for r in rows('finance.csv')}
Y25 = [f'2025-{m:02d}' for m in range(1, 13)]
rat = {'заборкин': ('zaborkin.ru', 33944), 'заборово': ('zaborovo.ru + p-z-z.ru', 15730), 'пск_забор': ('pskzabor.ru', 12850), 'заборофф': ('zaboroff.ru', 13047)}
got = {q: round(num(fin[(k, '2025')]['revenue_th_rub']) * 1000 / sum(bfiles[q][m] for m in Y25)) for q, (k, _) in rat.items()}
check('WS12', 'выручка на брендовый запрос 2025: Заборкин 33 944, Заборово 15 730, ПСК 12 850, Заборофф 13 047 ₽', str({q: v for q, (_, v) in rat.items()}), str(got))
pz = sum(bfiles['профзаборы'][m] for m in Y25)
s_all = open(os.path.join(ROOT, 'site', 'index.html'), encoding='utf-8').read()
import html as _h
_t = re.sub(r'\s+', ' ', _h.unescape(re.sub('<[^>]+>', ' ', s_all)))
stale_ws = [x for x in ('10,2 раза', '51 437', 'в 10 раз', 'демонстрация, R²', 'бренд-спрос Вордстата не снят', '×10,2', '10% мая', '10% от майского', '8 376', '85 336',
                        'в других регионах не повторился', 'приоритетны юг и запад') if x in _t]
J2 = lambda s_, y: sum(s_[f'{y}-{m:02d}'] for m in range(1, 10))
check('WS14', '2025 к 2024 (янв–сен): МО +84,5%, остальная Россия +30,2%', '84.5/30.2', f'{round(100*(J2(z,2025)/J2(z,2024)-1),1)}/{round(100*(J2(zr,2025)/J2(zr,2024)-1),1)}')
_l = lambda s_, ms_: sum(s_[m] for m in ms_)
check('WS15', 'доля МО в России по «забор под ключ», 12 мес.: 30,4% и годом раньше 45,4%', '30.4/45.4',
      f'{round(100*_l(z,LAST)/(_l(z,LAST)+_l(zr,LAST)),1)}/{round(100*_l(z,PREV)/(_l(z,PREV)+_l(zr,PREV)),1)}')
check('WS16', 'май / январь «забор под ключ»: 2024 ×3,4, 2025 ×2,7; январь — 17–38% мая', '3.4/2.7/17–38',
      f'{round(z["2024-05"]/z["2024-01"],1)}/{round(z["2025-05"]/z["2025-01"],1)}/{round(100*min(z[f"{y}-01"]/z[f"{y}-05"] for y in (2024,2025,2026)))}–{round(100*max(z[f"{y}-01"]/z[f"{y}-05"] for y in (2024,2025,2026)))}')
pmax = round(pz * 33944 / 1e6)
check('WS17', 'оценка выручки ПрофЗаборов по полному диапазону: 49–131 млн ₽', '49–131', f'{round(pz*12850/1e6)}–{pmax}')
check('WS-STALE', 'устаревшие цифры Keys.so о сезоне на странице', '[]', str(stale_ws))


# ---------- Топы запросов и стоимость рекламного трафика ----------
def raw_top(fname):
    t = open(os.path.join(ROOT, 'notes', 'raw_wordstat', fname), encoding='utf-8-sig').read().replace('\r', '\n')
    tok = [x.strip() for x in t.split('все устройства', 1)[1].replace('\n', ';').split(';') if x.strip()]
    return [(tok[i], int(tok[i + 1])) for i in range(0, len(tok) - 1, 2)]
tg = raw_top('top_откатные_ворота_rf_bez_msk.csv'); tz = raw_top('top_установка_забора_rf_bez_msk.csv')
check('TP1', '«Топы»: откатные ворота 286 570, установка забора 42 295 (главный запрос)', '286570/42295', f'{tg[0][1]}/{tz[0][1]}')
diy = sum(c for p_, c in tg[1:] if re.search(r'своими руками|как сделать|чертеж|пошагов|инструкц|схем', p_))
note('TP2', 'ворота: грубая доля фраз «своими руками / чертёж / инструкция» (страница: 25,3% по полному словарю)', f'{100*diy/sum(c for _, c in tg[1:]):.1f}%')
pr = sum(c for p_, c in tz[1:] if re.search(r'цен|стоим|сколько|прайс|расцен|под ключ|заказ|купить|с установк', p_))
note('TP3', 'забор: грубая доля фраз о цене и заказе (страница: 36,1% по полному словарю)', f'{100*pr/sum(c for _, c in tz[1:]):.1f}%')
tw = {r['domain']: r for r in rows('traffic_channels_wide.csv')}
check('PT1', 'Мастеровит: платный поиск 1 308 визитов/мес × 85–124 ₽ = 111–162 тыс. ₽', '111/162',
      f"{round(num(tw['masterovit.ru']['search_paid_visits'])/3*85/1000)}/{round(num(tw['masterovit.ru']['search_paid_visits'])/3*124/1000)}")
check('PT2', 'ПрофЗаборы: 1,4–2,0 млн ₽ в месяц', '1.4/2.0', f"{round(num(tw['prof-zabory.ru']['search_paid_visits'])/3*85/1e6,1)}/{round(num(tw['prof-zabory.ru']['search_paid_visits'])/3*124/1e6,1)}")
_ti2 = {(x['query'], x['value']): x['share_pct'] for x in rows('ws_tops_intents.csv')}
check('TP4', 'страница: цена работы без материала 2,9%, соседи и нормы 7,0%, цена и заказ 36,1%', '2.9/7.0/36.1',
      f"{_ti2[('установка забора','цена работы отдельно от материала')]}/{_ti2[('установка забора','правовой вопрос')]}/{_ti2[('установка забора','цена и заказ')]}")
_sp = {'masterovit.ru': 518280, 'prof-zabory.ru': 41545}
_lo = 518280 / (num(tw['masterovit.ru']['search_paid_visits']) / 3 * 124); _hi = num(tw['prof-zabory.ru']['search_paid_visits']) / 3 * 124 / 41545
check('PT3', 'расхождение источников «3–50 раз»: Мастеровит Spywords/Similarweb-верх, ПрофЗаборы Similarweb-верх/Spywords', '3–50', f'{_lo:.0f}–{round(_hi, -1):.0f}')
pii = [r['phrase'] for r in rows('ws_tops.csv') if re.search(r'\d{7,}', r['phrase'])]
check('TP-PII', 'в опубликованных «Топах» нет номеров телефонов', '[]', str(pii))

# ---------- волна 3 (Apify 21.10, вечер): выдача МО, Similarweb, Авито 4-й запрос, профили ----------
_S = json.load(open(os.path.join(ROOT, 'notes', 'raw_serp', 'yandex_serp_apify_21-10.json'), encoding='utf-8'))['items']
_mv = len({x['searchQuery'] for x in _S if x.get('type') == 'organic' and (x.get('organicPosition') or 99) <= 10 and 'masterovit.ru' in (x.get('url') or '')})
check('W3-1', 'выдача Яндекса МО: Мастеровит в топ-10 по 9 из 15 запросов', 9, _mv)
_SW = {x['name']: x for x in json.load(open(os.path.join(ROOT, 'notes', 'raw_similarweb', 'similarweb_apify_21-10.json'), encoding='utf-8'))['items']}
_to = {r['domain']: r for r in rows('traffic_overview.csv')}
check('W3-2', 'Similarweb сентябрь: публичная страница = Pro (Мастеровит, ПрофЗаборы)', f"{_to['masterovit.ru']['visits_2026_09']}/{_to['prof-zabory.ru']['visits_2026_09']}",
      f"{_SW['masterovit.ru']['totalVisits']}/{_SW['prof-zabory.ru']['totalVisits']}")
_q4 = json.load(open(os.path.join(ROOT, 'notes', 'raw_avito', 'zabor_iz_profnastila_pod_klyuch_mo.json'), encoding='utf-8'))['items']
check('W3-3', 'Авито 4-й запрос: 100 объявлений', 100, len(_q4))
_ps = json.load(open(os.path.join(ROOT, 'notes', 'raw_avito', 'profiles_wave3_summary.json'), encoding='utf-8'))['items']
check('W3-4', 'профили: Заборкин 317/24 089, Заборово 95/2 051, ПрофЗаборы 87/17, оценки 1–2★ у ПрофЗаборов 4', '317/24089 95/2051 87/17 4',
      ' '.join(f"{x['activeListingCount']}/{x['closedListingCount']}" for x in sorted(_ps, key=lambda x: ['Заборкин', 'ЗАБОРОВО', 'Профзаборы'].index(x['name']))) + f" {sum(x['ratingDistribution']['1'] + x['ratingDistribution']['2'] for x in _ps)}")
_pii = [f for f in os.listdir(os.path.join(ROOT, 'site', 'data')) if re.search(r'Святослав|Алексе[йя]', open(os.path.join(ROOT, 'site', 'data', f), encoding='utf-8').read())]
check('W3-PII', 'имена частных лиц в опубликованных CSV', '[]', str(_pii))

w = max(len(o[1]) for o in OUT)
for o in OUT:
    print(f'{o[0]:5} | {o[1]:<{w}} | {o[2]} | {o[3]} | {o[4]}')
print('\nИтого:', Counter(o[4] for o in OUT))
