"""Тип участка в текстах отзывов: дача / дом (доля «не указано»). База — все тексты 10 компаний полного разбора (all_reviews.json).
Регулярные выражения записаны ниже; «дом» даёт ложные совпадения («дома», «домой»), поэтому показаны строгий и широкий вариант.
Выход: печать и notes/scripts/synthesis/persona_counts.txt. Запуск: python3 -I persona_counts.py"""
import json, re, os
B = '/home/claude/zabory'
CO = ['masterovit.ru', 'prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru',
      'zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']
RX = {
    'дача (дач, СНТ, садовый участок)': r'дач|\bснт\b|садов\w* участ',
    'дом, строго (коттедж, ИЖС, частный/загородный дом)': r'коттедж|\bижс\b|частн\w* дом|загородн\w* дом|жил\w* дом|дом для постоянн',
    'дом, широко (+ слово «дом/дома/дому»)': r'коттедж|\bижс\b|частн\w* дом|загородн\w* дом|\bдом\b|\bдома\b|\bдому\b',
}
texts = [x['text'].lower() for x in json.load(open(f'{B}/notes/raw_reviews/all_reviews.json', encoding='utf-8'))
         if x['company'] in CO and (x['text'] or '').strip()]
n = len(texts)
out = [f'база: {n} текстов (все площадки, все оценки)']
hit = {}
for k, rx in RX.items():
    r = re.compile(rx); hit[k] = [bool(r.search(t)) for t in texts]
    c = sum(hit[k]); out.append(f'{k}: {c} ({100 * c / n:.1f}%)')
dacha, dom_s, dom_w = (hit[k] for k in RX)
none_s = sum(1 for a, b in zip(dacha, dom_s) if not a and not b)
none_w = sum(1 for a, b in zip(dacha, dom_w) if not a and not b)
out.append(f'тип участка не назван (дача и дом строго): {none_s} ({100 * none_s / n:.1f}%)')
out.append(f'тип участка не назван (дача и дом широко): {none_w} ({100 * none_w / n:.1f}%)')
print('\n'.join(out))
open(os.path.join(os.path.dirname(__file__), 'persona_counts.txt'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
