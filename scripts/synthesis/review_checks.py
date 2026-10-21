"""Оценка чека и длины забора по текстам отзывов (data/reviews.csv).
Регулярные выражения: сумма рядом со словами договор/смета/стоимость/заплатил/обош; длина — число + «м/метр/п.м.».
Результат — оценка (шумные данные), печатается и пишется в notes/scripts/synthesis/review_checks.txt"""
import csv, re, statistics as st, os
BASE = '/home/claude/zabory'
rows = list(csv.DictReader(open(f'{BASE}/data/reviews.csv', encoding='utf-8')))
money_ctx = re.compile(r'(договор|смет|стоимост|заплатил|оплатил|обош|сумм|цена|итог)')
L, S = [], []
for x in rows:
    t = x['text'].lower()
    for sent in re.split(r'[.!?\n]', t):
        for m in re.finditer(r'(\d{2,3})\s?(?:м\b|метр|п\.?\s?м|пог)', sent):
            v = int(m.group(1))
            if 10 <= v <= 400 and 'забор' in sent:
                L.append(v)
        if money_ctx.search(sent):
            for m in re.finditer(r'(\d{2,3}(?:[  .]?\d{3})?)\s?(?:тыс|т\.\s?р|тр\b|000\s?р|руб|₽)', sent):
                s = re.sub(r'[  .]', '', m.group(1)); v = int(s)
                if v < 1000: v *= 1000
                if 50000 <= v <= 2000000:
                    S.append(v)
def q(a, p): a = sorted(a); return a[int(p*(len(a)-1))]
out = []
out.append(f'длина забора, м: n={len(L)}, медиана={st.median(L)}, Q1={q(L,.25)}, Q3={q(L,.75)}')
out.append(f'сумма заказа, ₽: n={len(S)}, медиана={st.median(S):.0f}, Q1={q(S,.25)}, Q3={q(S,.75)}')
print('\n'.join(out))
open(os.path.join(os.path.dirname(__file__), 'review_checks.txt'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
