"""Расчёты по выгрузкам Вордстата: бренд-спрос (год к году, тренды), рынок МО против остальной России, округа МО.
Вход: data/ws_monthly.csv, data/wordstat_regions.csv. Выход: data/brand_demand_stats.csv, data/ws_market_stats.csv,
data/wordstat_mo_districts.csv, data/regional_coef.csv, data/brand_trend.csv. Запуск: python3 -I analyze_ws.py"""
import csv, math, statistics as st
B = '/home/claude/zabory'
rd = lambda p: list(csv.DictReader(open(f'{B}/data/{p}.csv', encoding='utf-8')))
def w(p, rows):
    with open(f'{B}/data/{p}.csv', 'w', encoding='utf-8', newline='') as f:
        d = csv.DictWriter(f, fieldnames=list(rows[0].keys())); d.writeheader(); d.writerows(rows)
def fit(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs); sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx; a = my - b * mx
    sr = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys)); stt = sum((y - my) ** 2 for y in ys)
    return a, b, 1 - sr / stt
M = rd('ws_monthly')
ser = {}
for r in M:
    ser.setdefault((r['query'], r['region']), {})[r['month']] = int(r['count'])
LAST = [f'2025-{m:02d}' for m in range(10, 13)] + [f'2026-{m:02d}' for m in range(1, 10)]
PREV = [f'2024-{m:02d}' for m in range(10, 13)] + [f'2025-{m:02d}' for m in range(1, 10)]
SRC = 'Вордстат, «Динамика», по месяцам, 01.2024–09.2026, Москва и область, все устройства; выгрузка пользователя 21.10.2026'

def anomalies(s):
    med = st.median(s.values())
    return sorted(m for m, v in s.items() if v > 5 * med)

def trend_rows(name, s, mode):
    ms = sorted(s); t = list(range(1, len(ms) + 1)); y = [s[m] for m in ms]
    a, b, r2 = fit(t, y); la, lb, lr2 = fit([math.log(x) for x in t], y)
    # 12-месячная скользящая сумма убирает сезон
    roll = [sum(y[i - 11:i + 1]) for i in range(11, len(y))]
    ra, rb, rr2 = fit(list(range(1, len(roll) + 1)), roll)
    mean = sum(y) / len(y)
    return {'series': name, 'points': len(y), 'period': f'{ms[0]}…{ms[-1]}', 'mean_per_month': round(mean),
            'linear_equation': f'y = {a:.0f} + {b:.1f}·t', 'linear_slope_per_month': round(b, 1), 'linear_slope_pct_of_mean': round(100 * b / mean, 2), 'linear_r2': round(r2, 3),
            'log_equation': f'y = {la:.0f} + {lb:.1f}·ln(t)', 'log_r2': round(lr2, 3),
            'rolling12_slope_pct_per_month': round(100 * rb / (sum(roll) / len(roll)), 2), 'rolling12_r2': round(rr2, 3),
            'direction': 'не определяется (R² < 0,3)' if rr2 < 0.3 else ('рост' if rb > 0 else 'падение') + (' (устойчивый, R² ≥ 0,5)' if rr2 >= 0.5 else ' (слабый, R² 0,3–0,5)'),
            'mode': mode, 'note': 't — номер месяца, 1 = ' + ms[0] + '; по сырому ряду R² низкий из-за сезона; направление — по скользящей 12-месячной сумме (сезон убран)'}

BR = {'мастеровит': 'masterovit.ru', 'профзаборы': 'prof-zabory.ru', 'заборкин': 'zaborkin.ru', 'завод заборов': 'zavodzaborov.ru',
      'радуга заборов': 'raduga-zaborov.ru', 'заборово': 'zaborovo.ru', 'облзабор': 'oblzabor.ru', 'доступные заборы': 'dostup-zabor.ru',
      'заборофф': 'zaboroff.ru', 'пск забор': 'pskzabor.ru'}
GENERIC = {'завод заборов': 'запрос частично общий (ищут любой завод заборов), бренд-доля завышена',
           'доступные заборы': 'запрос частично общий («доступные» = недорогие), бренд-доля завышена'}
stats, trends = [], []
tot_last = sum(sum(ser[(q, 'Москва и область')][m] for m in LAST) for q in BR)
for q, d in BR.items():
    s = ser[(q, 'Москва и область')]
    an = anomalies(s)
    s_clean = {m: v for m, v in s.items() if m not in an}
    last = sum(s[m] for m in LAST); prev = sum(s[m] for m in PREV)
    pairs = [(a, b) for a, b in zip(LAST, PREV) if a not in an and b not in an]
    last_c = sum(s[a] for a, _ in pairs); prev_c = sum(s[b] for _, b in pairs)
    pk = max(s, key=s.get)
    note = []
    if an: note.append('всплески ' + ', '.join(an) + ' (больше 5 медиан) исключены из «год к году без всплесков» и тренда')
    if q in GENERIC: note.append(GENERIC[q])
    stats.append(dict(domain=d, query=q, sum_last12=last, avg_month_last12=round(last / 12), sep_2026=s['2026-09'],
                      sum_prev12=prev, yoy_pct=round(100 * (last / prev - 1), 1),
                      yoy_clean_pct=('без всплесков направление не определяется: по 7 парам месяцев знак зависит от января 2025 года') if an else '',
                      share_of_10_brands_pct=round(100 * last / tot_last, 1), peak_month=pk, peak_value=s[pk],
                      anomaly_months=';'.join(an), note='; '.join(note), source=SRC, date_collected='2026-10-21'))
    tr = trend_rows(f'бренд «{q}» ({d})', s_clean if not an else s, 'Вордстат')
    if an:
        tr['direction'] = 'не определяется (всплески 2025 года)'
    elif not tr['direction'].startswith('не') and (tr['direction'].startswith('рост')) != (last > prev):
        tr['direction'] += '; за последние 12 мес. к предыдущим — обратный знак'
    trends.append(tr)
stats.sort(key=lambda r: -r['sum_last12'])
w('brand_demand_stats', stats)

MK = ['забор под ключ', 'установка забора', 'забор из профнастила', 'откатные ворота']
mk = []
for q in MK:
    s = ser[(q, 'Москва и область')]; rest = ser.get((q, 'Россия, кроме Москва и область'))
    last = sum(s[m] for m in LAST); prev = sum(s[m] for m in PREV)
    row = dict(query=q, sum_last12_mo=last, avg_month_last12_mo=round(last / 12), sep_2026_mo=s['2026-09'],
               yoy_pct_mo=round(100 * (last / prev - 1), 1), jan_2026=s['2026-01'], may_2026=s['2026-05'],
               may_to_jan=round(s['2026-05'] / s['2026-01'], 1), nov_2025=s['2025-11'], dec_2025=s['2025-12'],
               nov_to_sep_2025=round(s['2025-11'] / s['2025-09'], 2), peak_month=max(s, key=s.get), peak_value=max(s.values()))
    J = lambda y: sum(s[f'{y}-{m:02d}'] for m in range(1, 10))
    row.update(may_to_jan_2024=round(s['2024-05'] / s['2024-01'], 1), may_to_jan_2025=round(s['2025-05'] / s['2025-01'], 1),
               nov_to_sep_2024=round(s['2024-11'] / s['2024-09'], 2), dec_to_sep_2024=round(s['2024-12'] / s['2024-09'], 2), dec_to_sep_2025=round(s['2025-12'] / s['2025-09'], 2),
               jan_sep_2025_vs_2024_pct=round(100 * (J(2025) / J(2024) - 1), 1))
    row.update(jan_sep_2024=J(2024), jan_sep_2025=J(2025), jan_sep_2026=J(2026),
               jan_sep_2026_vs_2024_pct=round(100 * (J(2026) / J(2024) - 1), 1), jan_sep_2026_vs_2025_pct=round(100 * (J(2026) / J(2025) - 1), 1))
    if rest:
        JR = lambda y: sum(rest[f'{y}-{m:02d}'] for m in range(1, 10))
        lr_p = sum(rest[m] for m in PREV)
        row.update(rest_jan_sep_2026_vs_2024_pct=round(100 * (JR(2026) / JR(2024) - 1), 1), rest_jan_sep_2026_vs_2025_pct=round(100 * (JR(2026) / JR(2025) - 1), 1),
                   rest_jan_sep_2025_vs_2024_pct=round(100 * (JR(2025) / JR(2024) - 1), 1), mo_share_of_rf_prev12_pct=round(100 * prev / (prev + lr_p), 1))
    else:
        row.update(rest_jan_sep_2026_vs_2024_pct='', rest_jan_sep_2026_vs_2025_pct='', rest_jan_sep_2025_vs_2024_pct='', mo_share_of_rf_prev12_pct='')
    if rest:
        lr = sum(rest[m] for m in LAST); pr = sum(rest[m] for m in PREV)
        row.update(sum_last12_rest_rf=lr, yoy_pct_rest_rf=round(100 * (lr / pr - 1), 1), mo_share_of_rf_pct=round(100 * last / (last + lr), 1))
    else:
        row.update(sum_last12_rest_rf='не снято', yoy_pct_rest_rf='', mo_share_of_rf_pct='')
    row.update(source=SRC.replace('Москва и область', 'Москва и область; Россия, кроме Москвы и области'), date_collected='2026-10-21')
    mk.append(row)
    trends.append(trend_rows(f'рынок «{q}», Москва и МО', s, 'Вордстат'))
w('ws_market_stats', mk)
w('brand_trend', trends)

# округа МО
MO = ['Волоколамский район', 'Воскресенский район', 'Дмитровский городской округ', 'Егорьевск (городской округ)', 'Зарайск (городской округ)',
      'Истра (городской округ)', 'Кашира (городской округ)', 'Клин (городской округ)', 'Красногорск (городской округ)', 'Ленинский район',
      'Луховицы (городской округ)', 'Люберцы (городской округ)', 'Можайский (городской округ)', 'Мытищи (городской округ)',
      'Наро-Фоминский городской округ', 'Богородский (городской округ)', 'Одинцовский район', 'Павловский Посад (городской округ)',
      'Пушкинский район', 'Раменский район', 'Рузский городской округ', 'Ступино (городской округ)', 'Сергиево-Посадский район',
      'Солнечногорский район', 'Чехов (городской округ)', 'Шатура (городской округ)', 'Щёлковский район']
R = rd('wordstat_regions')
dist, rc = [], []
REF_D, REF_V = 'masterovit.ru', 129606
for q in ('забор под ключ', 'откатные ворота'):
    rows = [r for r in R if r['query'] == q]
    tot = int(next(r['frequency'] for r in rows if r['region'] == 'Москва и область'))
    rus = int(next(r['frequency'] for r in rows if r['region'] == 'Россия'))
    aff_mo = float(next(r['affinity_pct'] for r in rows if r['region'] == 'Москва и область'))
    # «Ленинский район» встречается дважды; округ МО идёт в блоке после «Красногорск» — берём последнее вхождение в блоке МО
    seen, sel = set(), []
    start = next(i for i, r in enumerate(rows) if r['region'] == 'Волоколамский район')
    for r in rows[start:]:
        if r['region'] in MO and r['region'] not in seen:
            seen.add(r['region']); sel.append(r)
        if len(seen) == len(MO): break
    ssum = sum(int(r['frequency']) for r in sel)
    for r in sorted(sel, key=lambda r: -int(r['frequency'])):
        f = int(r['frequency']); k = f / tot
        dist.append(dict(query=q, district=r['region'], frequency=f, share_of_msk_mo_pct=round(100 * k, 2), affinity_pct=r['affinity_pct'],
                         period=r['period'], source=r['source'], date_collected=r['date_collected']))
        rc.append(dict(query=q, region=r['region'], frequency=f, moscow_frequency=tot, coef=round(k, 4), reference_domain=REF_D,
                       reference_visits_month=REF_V, est_visits_month=round(k * REF_V), mode='Вордстат «Регионы», 20.09–20.10.2026',
                       note='база — «Москва и область» целиком (Москва отдельно Вордстат не выдаёт); индекс интереса ' + r['affinity_pct'] + '%; визиты masterovit.ru — Similarweb, весь мир и все регионы компании (в т. ч. СПб), поэтому оценка визитов завышена для МО'))
    rem = tot - ssum
    dist.append(dict(query=q, district='Москва и округа без строки в выгрузке (остаток: Подольск, Балашиха, Химки, Домодедово, Серпухов, Коломна и др.)', frequency=rem, share_of_msk_mo_pct=round(100 * rem / tot, 2),
                     affinity_pct='', period=sel[0]['period'], source='расчёт: «Москва и область» − сумма 27 округов; оценка', date_collected='2026-10-21'))
    dist.append(dict(query=q, district='ИТОГО Москва и область', frequency=tot, share_of_msk_mo_pct=100, affinity_pct=aff_mo,
                     period=sel[0]['period'], source=sel[0]['source'], date_collected='2026-10-21'))
    dist.append(dict(query=q, district=f'Россия (Москва и область — {round(100 * tot / rus, 1)}%)', frequency=rus, share_of_msk_mo_pct='', affinity_pct='',
                     period=sel[0]['period'], source=sel[0]['source'], date_collected='2026-10-21'))
w('wordstat_mo_districts', dist)
w('regional_coef', rc)
for r in stats: print(r['query'], r['sum_last12'], r['avg_month_last12'], r['yoy_pct'], r['yoy_clean_pct'], r['share_of_10_brands_pct'], r['anomaly_months'])
for r in mk: print(r)
for r in trends: print(r['series'], r['linear_r2'], r['rolling12_slope_pct_per_month'], r['rolling12_r2'], r['direction'])
for r in dist: 
    if r['district'].startswith(('Москва и окр', 'ИТОГО', 'Россия')) or float(r['share_of_msk_mo_pct'])>2: print(r['query'], r['district'], r['frequency'], r['share_of_msk_mo_pct'], r['affinity_pct'])

# выручка на брендовый запрос (методика 1.4): выручка ООО за 2025 / бренд-запросы за 2025 (Москва и МО)
FIN = {'masterovit.ru': ('ООО «Мастеровит»', 'masterovit.ru'), 'zaborkin.ru': ('ООО «Первый строительный»', 'zaborkin.ru'),
       'zavodzaborov.ru': ('ООО «Мособлстрой»', 'zavodzaborov.ru + zabor-dlya-vseh.site'), 'zaborovo.ru': ('ООО «Заборово»', 'zaborovo.ru + p-z-z.ru'),
       'zaboroff.ru': ('ООО «ЗАБОРОФФ»', 'zaboroff.ru'), 'pskzabor.ru': ('ООО «Строймонтаж 2015»', 'pskzabor.ru')}
fin = {(r['domain'], r['year']): r for r in rd('finance')}
Y25 = [f'2025-{m:02d}' for m in range(1, 13)]
ratio_rows, ratios = [], []
for q, d in BR.items():
    s = ser[(q, 'Москва и область')]
    an = set(anomalies(s))
    bq = sum(s[m] for m in Y25)
    bq_clean = sum(s[m] for m in Y25 if m not in an) + (round(st.median([s[m] for m in Y25 if m not in an])) * len(an & set(Y25)) if an & set(Y25) else 0)
    row = dict(domain=d, query=q, brand_queries_2025=bq, brand_queries_2025_used=bq_clean)
    if d in FIN:
        comp, fkey = FIN[d]; rev = float(fin[(fkey, '2025')]['revenue_th_rub']) * 1000
        k = rev / bq_clean
        row.update(company=comp, revenue_2025_rub=round(rev), revenue_per_brand_query_rub=round(k), revenue_est_rub='', basis='факт ГИР БО')
        if d != 'masterovit.ru':      # Мастеровит — другой масштаб и ассортимент, в медиану не берётся
            ratios.append(k)
    else:
        row.update(company='ИП (отчётности в ГИР БО нет)', revenue_2025_rub='', revenue_per_brand_query_rub='', revenue_est_rub='', basis='')
    row['note'] = '; '.join(x for x in (('всплески ' + ', '.join(sorted(an & set(Y25))) + ' заменены медианой года') if an & set(Y25) else '', GENERIC.get(q, '')) if x)
    ratio_rows.append(row)
sp = lambda x: f'{round(x):,}'.replace(',', ' ')
q1, med, q3 = st.quantiles(ratios, n=4, method='inclusive')[0], st.median(ratios), st.quantiles(ratios, n=4, method='inclusive')[2]
for row in ratio_rows:
    if not row['revenue_2025_rub']:
        b = row['brand_queries_2025_used']
        flag = {'prof-zabory.ru': 'нижняя граница: 64,1% визитов из платных каналов (Similarweb)', 'oblzabor.ru': 'нижняя граница: 67,9% визитов из платных каналов (Similarweb)',
                }.get(row['domain'], '')
        row.update(revenue_est_rub=f'{round(b * min(ratios) / 1e6)}–{round(b * max(ratios) / 1e6)} млн ₽ (медиана {round(b * med / 1e6)} млн ₽)',
                   basis=f'оценка: бренд-запросы 2025 × выручка на запрос у 5 ООО (n=5, {sp(min(ratios))}–{sp(max(ratios))} ₽, медиана {sp(med)} ₽ — ЗаводЗаборов с частично общим запросом; Мастеровит не входит — другой масштаб и ассортимент)',
                   note='; '.join(x for x in (row['note'], flag) if x))
w('brand_revenue_ratio', ratio_rows)
for r in ratio_rows: print(r)
