"""Стоимость рекламного трафика конкурентов (методика 1.4.8): платные визиты Similarweb × цена клика.
Поиск: визиты из платного поиска × 85–124 ₽ (диапазон медиаплана: прогноз Keys.so — Spywords по masterovit.ru).
Медийная реклама и платные соцсети: цена клика не измерена — в рубли не переводятся, показаны визитами.
Выход: data/paid_traffic_cost.csv. Запуск: python3 -I paid_traffic_cost.py"""
import csv
B = '/home/claude/zabory'
num = lambda s: float(str(s).replace(' ', '').replace(',', '.')) if str(s).strip() else 0.0
bud = {}
for r in csv.DictReader(open(f'{B}/data/ad_budgets.csv', encoding='utf-8')):
    v = (r.get('budget_month') or '').split(' (')[0]
    if v and v.replace(' ', '').isdigit():
        per = '' if 'Spywords' in r['source'] else ' (период не указан)'
        bud.setdefault(r['domain'].replace('sales.', ''), []).append(f"{r['source'].split(',')[0]}: {round(num(v)):,} ₽{per}".replace(',', ' '))
rows = []
for r in csv.DictReader(open(f'{B}/data/traffic_channels_wide.csv', encoding='utf-8')):
    sp = num(r['search_paid_visits']) / 3; pt = num(r['paid_total_visits']) / 3
    rows.append(dict(domain=r['domain'], paid_search_visits_month=round(sp), other_paid_visits_month=round(pt - sp),
                     paid_share_pct=r['paid_total_pct'], search_cost_month_rub_low=round(sp * 85), search_cost_month_rub_high=round(sp * 124),
                     other_budgets_seen='; '.join(bud.get(r['domain'], [])) or '—', reliability=r['reliability'],
                     note='оценка: Similarweb (весь мир, июль–сентябрь 2026) × CPC 85–124 ₽; медийная и соцсети без цены клика',
                     source='data/traffic_channels_wide.csv; data/mediaplan.csv (CPC); data/ad_budgets.csv', date_collected='2026-10-21'))
with open(f'{B}/data/paid_traffic_cost.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows: print(r['domain'], r['paid_search_visits_month'], r['other_paid_visits_month'], r['search_cost_month_rub_low'], r['search_cost_month_rub_high'], r['other_budgets_seen'], r['reliability'])
