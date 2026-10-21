"""Региональный коэффициент (методика 1.4): коэффициент = частотность в городе / частотность в Москве;
оценка трафика аналогичного конкурента в городе = коэффициент × трафик московского конкурента.
Вход (когда появится): data/wordstat_regions.csv со столбцами query, region, frequency (Вордстат «Регионы» или помесячная частотность по городам),
строка region = «Москва» обязательна. Трафик московского конкурента — data/traffic_overview.csv (avg_month_visits), по умолчанию masterovit.ru.
Сейчас частотности по городам нет — скрипт печатает пример методики из курса и проверку формулы.
Выход: data/regional_coef.csv. Запуск: python3 -I regional_coef.py [домен-эталон]"""
import csv, sys

B = '/home/claude/zabory'
REF = sys.argv[1] if len(sys.argv) > 1 else 'masterovit.ru'
vis = {r['domain']: float(r['avg_month_visits']) for r in csv.DictReader(open(f'{B}/data/traffic_overview.csv', encoding='utf-8')) if r.get('avg_month_visits')}

rows = []
src = list(csv.DictReader(open(f'{B}/data/wordstat_regions.csv', encoding='utf-8')))
freq = [r for r in src if r.get('frequency')]
if freq:
    by_q = {}
    for r in freq:
        by_q.setdefault(r['query'], {})[r['region']] = float(str(r['frequency']).replace(' ', '').replace(' ', ''))
    for q, regs in by_q.items():
        msk = regs.get('Москва')
        if not msk: continue
        for reg, f in regs.items():
            if reg == 'Москва': continue
            k = f / msk
            rows.append({'query': q, 'region': reg, 'frequency': f, 'moscow_frequency': msk, 'coef': round(k, 4),
                         'reference_domain': REF, 'reference_visits_month': round(vis.get(REF, 0)), 'est_visits_month': round(k * vis.get(REF, 0)),
                         'mode': 'Вордстат', 'note': 'оценка: трафик аналогичного конкурента в городе'})
else:
    k = 22690 / 278215
    rows.append({'query': 'купить велосипед (пример курса)', 'region': 'Челябинск', 'frequency': 22690, 'moscow_frequency': 278215, 'coef': round(k, 4),
                 'reference_domain': 'пример курса', 'reference_visits_month': 100000, 'est_visits_month': round(k * 100000),
                 'mode': 'демонстрация формулы (методика, раздел 1.4)', 'note': 'частотность по городам МО не снята: Вордстат требует вход, браузер заблокирован 21.10.2026'})
    rows.append({'query': 'забор под ключ', 'region': 'города МО из подсказок (Серпухов, Солнечногорск, Чехов, Истра, Дмитров и др.)', 'frequency': 'не снято', 'moscow_frequency': 57377,
                 'coef': 'не считается', 'reference_domain': REF, 'reference_visits_month': round(vis.get(REF, 0)), 'est_visits_month': 'не считается',
                 'mode': 'ожидает data/wordstat_regions.csv со столбцом frequency', 'note': 'Москва — широкая частотность Keys.so, сентябрь 2026'})
with open(f'{B}/data/regional_coef.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for r in rows: print(r)
