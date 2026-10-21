"""«Наш оффер против рынка»: оценка целевого оффера «Дома гирлянд» по тем же критериям и рубрикам (notes/criteria_rules.md),
рядом с 10 компаниями. Оценка целевого оффера — обещание (что будет записано на сайте и в договоре), исполнения ещё нет:
по критериям, где балл рынка складывается из обещания и жалоб в отзывах, у «Дома гирлянд» стоит только обещание (отзывов нет).
Выход: data/offer_vs_market.csv. Запуск: python3 -I build_offer_vs_market.py (после build_criteria.py)"""
import csv, statistics as st
B = '/home/claude/zabory'
CO = ['masterovit.ru', 'prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru',
      'zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']
REVIEW_ONLY = {'C01', 'C41'}   # балл только по отзывам — у нового игрока 0
DG = {  # id: (балл, что обещаем; основание по рубрике)
 'C42': (5, 'скрипт квалификации из стратегии 19.10: дом, материал, метры, ворота, сроки, адрес + просьба прислать план или фото'),
 'C41': (0, 'отзывов нет; механизм — фото-акт скрытых работ и приёмка с геометрией'),
 'C28': (5, 'один координатор до конца гарантии, статус работ в мессенджере, срок ответа на обращение в договоре (рубрика 5)'),
 'C18': (4, 'порошковое покрытие каркасов и фото сварных швов в акте; гарантия покрытия 2 года (рубрика 4)'),
 'C27': (5, '2 года с даты акта + весенний осмотр + срок выезда по гарантии в договоре (рубрика 5)'),
 'C09': (5, 'итоговая сумма в договоре, доплаты на объекте 0 ₽, список исключений письменно (рубрика 5)'),
 'C08': (5, 'итог без телефона и состав сметы на странице'),
 'C14': (5, '5 дней от договора до монтажа'),
 'C07': (2, 'цена около медианы рынка 1 690 ₽/п.м. (по формуле оценки цены)'),
 'C29': (4, 'защита газона и уборка — пункты акта приёмки (рубрика 4)'),
 'C33': (4, 'бесплатный технический выезд в течение 2 дней'),
 'C22': (5, 'итоговая сумма пакета «забор + ворота + калитка» на странице (рубрика 5)'),
 'C19': (4, 'сваи или забутовка по замеру; фото основания в акте'),
 'C31': (3, 'ограниченный радиус пилота (стратегия: ограниченная география)'),
 'C15': (4, 'монтаж 1–2 дня'),
 'C17': (4, 'лист, столбы, лаги, грунт цифрами в смете'),
 'C16': (4, 'SLA ответа до 5 минут (стратегия 19.10)'),
 'C23': (5, '3 года обслуживания автоматики'),
 'C21': (5, 'ворота 4 × 2 м с автоматикой и без — рядом в таблице'),
 'C12': (4, 'неценовой бонус к пакету: подсветка въезда или закладка кабеля под неё'),
 'C05': (4, 'микрометр на приёмке + толщина в договоре'),
 'C10': (5, 'оплата после приёмки (в стратегии 19.10 — предоплата 50%: решение заказчика)'),
 'C30': (5, 'фото-акт скрытых работ + паспорт объекта (рубрика 5)'),
 'C13': (0, 'в оффер не входит'),
 'C24': (4, 'демонтаж старого забора — отдельная опция'),
 'C04': (0, 'производства нет (пилот без цеха)'),
 'C34': (5, 'WhatsApp, Telegram, MAX'),
 'C26': (4, 'визуальное согласование ворот и образцы на замере'),
 'C20': (2, 'подрядные бригады под техконтролем; бригадир известен до монтажа'),
 'C25': (4, 'консультация по нормам СНТ и границам на замере'),
 'C01': (0, 'отзывов нет'),
 'C06': (5, 'неустойка в рублях за день переноса'),
 'C03': (1, 'новое направление; опыт выездов «Дома гирлянд»'),
 'C11': (3, 'кредит через банк-партнёр'),
 'C35': (5, 'квиз со сметой в мессенджер'),
 'C44': (5, 'письменное КП: два варианта с исключениями (рубрика 5)'),
 'C37': (1, 'на старте кейсов нет; образец договора и фото-акта'),
 'C36': (5, 'цель: условие без риска на первом экране, телефон ≥ 50/100 (страница не сделана)'),
}
ADDED = {'C09': 'уровень 5', 'C22': 'уровень 5 (итоговая сумма пакета)', 'C27': 'уровень 5', 'C28': 'уровень 5', 'C30': 'уровень 5',
         'C42': 'строка добавлена 21.10', 'C44': 'строка добавлена 21.10', 'C18': 'уровень 4', 'C29': 'уровень 4'}
CLIENT_DECISION = {'C10': (0, 'вариант с предоплатой 50% по модели стратегии 19.10 — 0 по рубрике (≥ 50%)')}
rows = list(csv.DictReader(open(f'{B}/data/criteria_scores.csv', encoding='utf-8')))
prom = {r['id']: r for r in csv.DictReader(open(f'{B}/data/criteria_scores_promise.csv', encoding='utf-8'))}
crit = [r for r in rows if r['id'].startswith('C')]
assert set(r['id'] for r in crit) == set(DG), set(r['id'] for r in crit) ^ set(DG)
W = {r['id']: float(r['weight']) for r in crit}
out = []
for r in crit:
    i = r['id']; sc = [int(r[c]) for c in CO]; mx = max(sc); med = st.median(sc); d = DG[i][0]
    p = prom[i]; psc = [int(p[c]) for c in CO] if p['combined_with_reviews'] != 'только отзывы' else None
    pmx = max(psc) if psc else 'н/п'
    if r['class'] == 'свободный':
        role = 'обещание закрывает свободный критерий' if d >= 4 else 'свободный критерий не закрыт'
    elif d > (pmx if psc else mx):
        role = 'обещание, которого нет ни у кого из 10'
    elif d == (pmx if psc else mx):
        role = 'на уровне лучших обещаний рынка'
    else:
        role = 'не можем конкурировать на старте' if i in ('C01', 'C41', 'C04', 'C03', 'C37', 'C20') else 'ниже лучших обещаний рынка'
    row = {'id': i, 'criterion': r['criterion'], 'class': r['class'], 'weight': r['weight'],
           'market_basis': {'да': 'исполнено: обещание + жалобы в отзывах', 'только отзывы': 'исполнено: только отзывы', 'нет': 'проверено на сайтах и в рекламе'}[p['combined_with_reviews']]}
    row.update({c: r[c] for c in CO})
    row.update({'market_best_executed': mx, 'market_median_executed': med,
                'market_best_promise_only': pmx, 'market_promise_scores': ' '.join(p[c] for c in CO),
                'dom_girlyand_promise': d, 'dom_girlyand_basis': DG[i][1],
                'scale_level_added_21_10': ADDED.get(i, 'нет'),
                'client_decision_variant': f'{CLIENT_DECISION[i][0]}: {CLIENT_DECISION[i][1]}' if i in CLIENT_DECISION else '—',
                'competitors_promise_at_or_above': (sum(1 for x in psc if x >= d) if psc else 'н/п') if d > 0 else '— (у нас 0)',
                'role': role})
    out.append(row)
def wavg(get, ids): return round(sum(get(i) * W[i] for i in ids) / sum(W[i] for i in ids), 2)
ids = [r['id'] for r in crit]; ids_p = [i for i in ids if i not in REVIEW_ONLY]
tot = {'id': 'СВОДКА', 'criterion': 'взвешенный балл обещаний 0–5 без C01, C41; шкала дополнена 21.10 под целевой оффер; исполнение не оценивается — победой не считать',
       'class': '—', 'weight': '—', 'market_basis': 'только обещания (data/criteria_scores_promise.csv)'}
for c in CO: tot[c] = wavg(lambda i: int(prom[i][c]), ids_p)
dg_pay_after = wavg(lambda i: DG[i][0], ids_p)
dg_prepay = wavg(lambda i: CLIENT_DECISION[i][0] if i in CLIENT_DECISION else DG[i][0], ids_p)
roles = {}
for o in out: roles.setdefault(o['role'], []).append(o['id'])
tot.update({'market_best_executed': '—', 'market_median_executed': '—', 'market_best_promise_only': '—', 'market_promise_scores': '—',
            'dom_girlyand_promise': dg_pay_after, 'dom_girlyand_basis': f'с оплатой после приёмки {dg_pay_after}; с предоплатой 50% {dg_prepay}',
            'scale_level_added_21_10': f"{len(ADDED)} критериев с уровнями, добавленными 21.10", 'client_decision_variant': 'C10: оплата после приёмки или предоплата 50% — решение заказчика',
            'competitors_promise_at_or_above': '—', 'role': '; '.join(f'{k}: {", ".join(v)}' for k, v in roles.items())})
out.append(tot)
with open(f'{B}/data/offer_vs_market.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print({c[:8]: tot[c] for c in CO}, 'DG', dg_pay_after, dg_prepay)
for k, v in roles.items(): print(k, v)
