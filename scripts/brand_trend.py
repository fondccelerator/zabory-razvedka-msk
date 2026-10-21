"""Бренд-спрос и тренды: линейный (y = a + b·t) и логарифмический (y = a + b·ln t) тренд по месяцам, R², наклон.
Вход (когда появится): data/brand_demand_ws.csv — столбцы brand, month (ГГГГ-ММ), frequency (Вордстат «Динамика», помесячно, регион).
Сейчас (демонстрация): ряд Keys.so «забор под ключ», Москва, из data/wordstat_dynamics.csv; месяцы с повтором значения без перепроверки исключаются.
Выход: data/brand_trend.csv. Запуск: python3 -I brand_trend.py [путь к CSV]"""
import csv, math, os, sys

B = '/home/claude/zabory'
SRC = sys.argv[1] if len(sys.argv) > 1 else f'{B}/data/brand_demand_ws.csv'

def month_index(m0, m):
    y0, mm0 = map(int, m0.split('-')); y, mm = map(int, m.split('-'))
    return (y - y0) * 12 + (mm - mm0) + 1          # t = 1, 2, … (для ln нужен t ≥ 1)

def fit(xs, ys):
    n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs); sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx; a = my - b * mx
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys)); ss_tot = sum((y - my) ** 2 for y in ys)
    return a, b, (1 - ss_res / ss_tot) if ss_tot else float('nan')

series = {}
if os.path.exists(SRC):
    mode = 'Вордстат, ' + os.path.basename(SRC)
    for r in csv.DictReader(open(SRC, encoding='utf-8')):
        if r.get('frequency'):
            series.setdefault(r['brand'], []).append((r['month'][:7], float(str(r['frequency']).replace(' ', '').replace(' ', ''))))
else:
    mode = 'демонстрация: Keys.so «забор под ключ», Москва (data/wordstat_dynamics.csv); бренд-спрос Вордстата не снят'
    for r in csv.DictReader(open(f'{B}/data/wordstat_dynamics.csv', encoding='utf-8')):
        if r['query'] == 'забор под ключ' and r['frequency_broad'] and len(r['month']) == 7 and 'повторяет' not in r['note']:
            series.setdefault('забор под ключ (широкая, Keys.so)', []).append((r['month'], float(r['frequency_broad'])))

rows = []
for brand, pts in series.items():
    pts.sort(); m0 = pts[0][0]
    t = [month_index(m0, m) for m, _ in pts]; y = [v for _, v in pts]
    a, b, r2 = fit(t, y)
    la, lb, lr2 = fit([math.log(x) for x in t], y)
    mean = sum(y) / len(y)
    rows.append({'series': brand, 'points': len(pts), 'period': f'{pts[0][0]}…{pts[-1][0]}', 'mean_per_month': round(mean),
                 'linear_equation': f'y = {a:.0f} + {b:.1f}·t', 'linear_slope_per_month': round(b, 1), 'linear_slope_pct_of_mean': round(100 * b / mean, 2), 'linear_r2': round(r2, 3),
                 'log_equation': f'y = {la:.0f} + {lb:.1f}·ln(t)', 'log_r2': round(lr2, 3),
                 'direction': ('рост' if b > 0 else 'падение') if r2 >= 0.5 else f'не определён (R² {r2:.3f}: сезонность не убрана)', 'mode': mode,
                 'note': 't — номер месяца от первого в ряду (1 = ' + m0 + '); сезонность не убрана, R² показывает долю вариации, объяснённую трендом'})
out = f'{B}/data/brand_trend.csv'
with open(out, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows: print(r)
