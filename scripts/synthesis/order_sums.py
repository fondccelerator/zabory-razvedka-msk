"""Суммы заказов в отзывах (база чека). Берутся предложения с суммой рядом со словами «договор, смета, стоимость, заплатил, обошёлся, цена, итог»
(как в review_checks.py), затем каждая сумма размечена вручную: входит ли это итоговая сумма заказа забора (в т. ч. с воротами).
Исключены: предоплата, разница между КП, цена за метр или замер, доставка, суммы специалистов по воротам без забора, неясные предложения, дубли.
Выход: data/order_sums_reviews.csv и печать медианы и квартилей. Запуск: python3 -I order_sums.py"""
import csv, re, statistics as st
B = '/home/claude/zabory'
rows = list(csv.DictReader(open(f'{B}/data/reviews.csv', encoding='utf-8')))
money = re.compile(r'(договор|смет|стоимост|заплатил|оплатил|обош|сумм|цена|итог)')
found = []
for x in rows:
    t = x['text'].lower()
    for sent in re.split(r'[.!?\n]', t):
        if money.search(sent):
            for m in re.finditer(r'(\d{2,3}(?:[  .]?\d{3})?)\s?(?:тыс|т\.\s?р|тр\b|000\s?р|руб|₽)', sent):
                s = re.sub(r'[  .]', '', m.group(1)); v = int(s)
                if v < 1000: v *= 1000
                if 50000 <= v <= 2000000:
                    found.append((v, x['company'], x['stars'], sent.strip(), (x['company'], x['date'], x['card_id'], x['text'][:40])))
# ручная разметка: (сумма, компания, начало предложения) → (входит, причина)
EXCLUDE = {
 (50000, 'masterovit.ru'): 'предоплата, не сумма заказа',
 (80000, 'prof-zabory.ru'): '80 руб — не сумма заказа',
 (80000, 'zaborovo.ru'): 'разница между КП',
 (100000, 'masterovit.ru', 'цена вопроса'): '1 100 ₽ — не сумма заказа',
 (102500, 'alusys.ru'): 'специалист по воротам, ворота без забора',
 (130000, 'alusys.ru'): 'специалист по воротам, ворота без забора',
 (260000, 'masterovit.ru'): 'первая из двух смет того же заказа; взята итоговая 445 000',
 (400000, 'masterovit.ru'): 'сумма не названа в предложении (доплата за столбы)',
 (400000, 'zavodzaborov.ru'): 'неясно: отказ на этапе замеров',
 (500000, 'masterovit.ru'): '500 ₽ / 1 500 ₽ — замер или выезд',
 (650000, 'zavodzaborov.ru'): 'цена демонтажа за кв. м',
 (750000, 'masterovit.ru', 'и вишенкой'): '2 750 ₽ — выезд замерщика',
 (800000, 'masterovit.ru', 'причём'): 'доставка 800 ₽',
 (300000, 'masterovit.ru', 'в августе 2024'): 'тот же заказ, что и 430 000 (два отзыва автора на Отзовике 03.07.2025: «забор» и «забор + монтаж»); взято 430 000',
}
out, seen = [], set()
for v, comp, stars, sent, rk in sorted(found):
    key3 = next((k for k in EXCLUDE if len(k) == 3 and k[0] == v and k[1] == comp and sent.startswith(k[2])), None)
    key2 = (v, comp) if (v, comp) in EXCLUDE else None
    reason = EXCLUDE.get(key3) if key3 else (EXCLUDE.get(key2) if key2 and not any(len(k) == 3 and k[0] == v and k[1] == comp for k in EXCLUDE) else None)
    dup = (v, rk) in seen
    if dup and not reason: reason = 'дубль того же отзыва'
    seen.add((v, rk))
    out.append({'sum_rub': v, 'company': comp, 'stars': stars, 'with_gates_in_text': 'да' if 'ворот' in sent else 'не указано в предложении',
                'included': 'нет' if reason else 'да', 'reason': reason or 'итоговая сумма заказа забора', 'sentence': sent[:160]})
inc = [o['sum_rub'] for o in out if o['included'] == 'да']
q = st.quantiles(inc, n=4, method='inclusive')
with open(f'{B}/data/order_sums_reviews.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f'всего сумм {len(out)}, вошло {len(inc)}; медиана {st.median(inc):.0f}; Q1 {q[0]:.0f}; Q3 {q[2]:.0f}; мин {min(inc)}; макс {max(inc)}')
print('негатив 1–3★ среди вошедших:', sum(1 for o in out if o['included'] == 'да' and int(o['stars']) <= 3))
