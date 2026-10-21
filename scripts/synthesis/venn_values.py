"""Этап synthesis: диаграмма Венна критериев (общее / уникальное / наше) и разметка ценности
«эксплицитная / имплицитная» (методика criteria-competitor-analysis, п. 3.9 и 1.5.2).

Входы: data/criteria.csv, data/criteria_scores.csv, data/offer_vs_market.csv, data/brand_demand.csv,
notes/raw_reviews/all_reviews.json (проверка цитат), notes/venn_values_spravka.md (сверка цифр, если есть).
Выходы: data/venn_criteria.csv, data/criteria_value_type.csv, notes/venn.svg.html.
Запуск: python3 -I venn_values.py
"""
import csv, json, re, math
from collections import Counter

B = '/home/claude/zabory'
DATE = '2026-10-21'
CO = ['masterovit.ru', 'prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru',
      'zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']
GE = 3            # «закрывает критерий» — оценка 3 и выше (как в классах criteria_rules.md)
COMMON_MIN = 7    # общее: 7–10 компаний из 10
UNIQUE_MAX = 2    # уникальное: 1–2 компании из 10
EXPL_SHARE = 2.0  # эксплицитная: критерий назван не реже чем в 2% отзывов (негатив n=851 или позитив n=3 985)

def rd(path):
    return list(csv.DictReader(open(f'{B}/{path}', encoding='utf-8')))

def f1(x):
    return f'{x:.1f}'.replace('.', ',')

crit = {x['id']: x for x in rd('data/criteria.csv')}
scores = {x['id']: x for x in rd('data/criteria_scores.csv') if x['id'].startswith('C')}
offer = {x['id']: x for x in rd('data/offer_vs_market.csv') if x['id'].startswith('C')}
assert set(crit) == set(scores) == set(offer) and len(crit) == 38, (len(crit), len(scores), len(offer))
order = sorted(crit, key=lambda c: -float(crit[c]['weight']))

SHORT = {
 'C41': 'Качество монтажа', 'C28': 'Связь после оплаты', 'C18': 'Антикоррозия, покраска', 'C27': 'Гарантия',
 'C09': 'Фиксированная смета', 'C14': 'Срок до монтажа', 'C42': 'Консультация при контакте', 'C08': 'Прозрачная цена',
 'C07': 'Уровень цены', 'C29': 'Аккуратность, уборка', 'C33': 'Бесплатный замер', 'C22': 'Пакет «забор + ворота»',
 'C19': 'Фундамент и столбы', 'C31': 'География по МО', 'C15': 'Монтаж за 1 день', 'C17': 'Конструкция цифрами',
 'C16': 'Скорость ответа', 'C23': 'Сервис автоматики', 'C21': 'Цена ворот 4 м', 'C12': 'Скидки и подарки',
 'C05': 'Контроль толщины', 'C10': 'Оплата после монтажа', 'C30': 'Акт и паспорт объекта', 'C13': 'Бонус за рекомендацию',
 'C24': 'Демонтаж старого', 'C04': 'Своё производство', 'C34': 'Заявка в мессенджер', 'C26': 'Образцы, визуализация',
 'C20': 'Своя бригада', 'C25': 'Нормы СНТ и границы', 'C01': 'Отзывы и рейтинг', 'C06': 'Неустойка за срок',
 'C44': 'Письменное КП', 'C03': 'Опыт и масштаб', 'C11': 'Рассрочка', 'C35': 'Квиз со сметой',
 'C37': 'Доказательства на сайте', 'C36': 'Посадочная страница'}
STEM = {'masterovit.ru': 'masterovit', 'prof-zabory.ru': 'prof-zabory', 'zaborkin.ru': 'zaborkin', 'zavodzaborov.ru': 'zavodzaborov',
        'raduga-zaborov.ru': 'raduga', 'zaborovo.ru': 'zaborovo', 'oblzabor.ru': 'oblzabor', 'dostup-zabor.ru': 'dostup',
        'zaboroff.ru': 'zaboroff', 'pskzabor.ru': 'pskzabor'}
assert set(SHORT) == set(crit)

# ================= 1. Венн =================
venn, Z = [], Counter()
for cid in order:
    s, o, c = scores[cid], offer[cid], crit[cid]
    ge = [k for k in CO if int(s[k]) >= GE]
    n = len(ge)
    assert n == int(c['companies_score_ge3']), (cid, n, c['companies_score_ge3'])
    dg = float(o['dom_girlyand_promise'])
    ours = dg >= GE
    if n >= COMMON_MIN:
        zone = 'общее ∩ наше: обязательный минимум' if ours else 'общее: в оффере нет'
    elif 1 <= n <= UNIQUE_MAX:
        zone = 'уникальное ∩ наше: догоняем' if ours else 'уникальное: в оффере нет'
    elif n == 0:
        zone = 'только наше: отстройка' if ours else 'ни у кого'
    else:
        zone = 'вне кругов: середина рынка (3–6), наше' if ours else 'вне кругов: середина рынка (3–6), в оффере нет'
    Z[zone] += 1
    above = ours and o['competitors_promise_at_or_above'].strip() == '0'
    notes = []
    if 1 <= n <= UNIQUE_MAX:
        notes.append('у кого ≥3: ' + ', '.join(ge))
    if above:
        notes.append('уровень обещания выше всех 10 (обещаний на уровне оффера у рынка: 0) — отстройка по уровню')
    if cid == 'C10':
        notes.append('оплата после приёмки — решение заказчика; при предоплате 50% балл 0')
    if cid == 'C36':
        notes.append('страница не сделана')
    if cid in ('C41', 'C01'):
        notes.append('оценивается только по отзывам; у нового игрока отзывов нет')
    notes.append('роль в offer_vs_market: ' + o['role'])
    status = 'обещание' if ours else f'не закрывает (обещание {o["dom_girlyand_promise"].replace(".0", "")} из 5)'
    venn.append({'criterion_id': cid, 'criterion': c['criterion'], 'weight': c['weight'], 'class': c['class'],
                 'n_companies_score_ge3': n, 'companies_ge3': '; '.join(ge), 'zone': zone,
                 'in_our_offer': 'да' if ours else 'нет', 'our_status': status,
                 'our_promise_score': o['dom_girlyand_promise'].replace('.0', ''), 'above_market_promise': 'да' if above else 'нет',
                 'note': '; '.join(notes), 'source': 'data/criteria_scores.csv; data/offer_vs_market.csv', 'date': DATE})

with open(f'{B}/data/venn_criteria.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(venn[0].keys())); w.writeheader(); w.writerows(venn)

V = {x['criterion_id']: x for x in venn}
def ids(pred):
    return [x['criterion_id'] for x in venn if pred(x)]

# ================= 2. Эксплицитная / имплицитная =================
allr = json.load(open(f'{B}/notes/raw_reviews/all_reviews.json', encoding='utf-8'))
neg_all, pos_all = [], []
for x in allr:
    if x['company'] not in CO or not (x['text'] or '').strip():
        continue
    s = int(float(x['stars'] or 0))
    if s <= 3: neg_all.append(x['text'].lower())
    elif len(x['text'].strip()) >= 15: pos_all.append(x['text'].lower())
assert len(neg_all) == 851 and len(pos_all) == 3985

# Дополнительный замер там, где позитив в criteria.csv не измерялся (pspec = None) — только для проверки порога.
SUPP = {'C06': r'неустойк|компенсац|штраф', 'C36': r'сайт.{0,40}(удобн|понятн)'}
supp = {cid: sum(1 for t in pos_all if re.search(rx, t)) for cid, rx in SUPP.items()}

# Бренд-подсказки «… отзывы» (поиск отзывов о компании до выбора) — сигнал запроса для C01.
bd = rd('data/brand_demand.csv')
brand_rev = sorted({x['domain'] for x in bd if x['domain'] in CO and 'отзыв' in x['suggest_examples']})

# Скрытые мотивы — notes/reviews_spravka.md, разд. 8 (n=851 негатива, n=3 985 позитива).
MOTIVE = {
 'M1': 'страх остаться одному после оплаты', 'M2': 'страх неподконтрольной цены', 'M3': 'проверка забора первой зимой',
 'M4': 'забор виден соседям', 'M5': 'цена потерянного дня', 'M6': 'недоверие к невидимым параметрам',
 'M7': 'кто приедет на участок'}
MOT_OF = {
 'C28': ['M1'], 'C27': ['M1', 'M3'], 'C10': ['M1'], 'C23': ['M1'],
 'C09': ['M2'], 'C08': ['M2'], 'C44': ['M2'], 'C35': ['M2'], 'C21': ['M2'], 'C22': ['M2'],
 'C18': ['M3'], 'C19': ['M3', 'M6'], 'C41': ['M3', 'M4'],
 'C13': ['M4'], 'C29': ['M4', 'M7'], 'C25': ['M4'],
 'C14': ['M5'], 'C06': ['M5'], 'C15': ['M5'],
 'C05': ['M6'], 'C17': ['M6'], 'C30': ['M6'],
 'C20': ['M7']}

QEX = {  # пример уточнения запроса (data/wordstat_tops.csv), если queries_n ≥ 1
 'C08': 'забор под ключ цена за метр с установкой', 'C07': 'заборы недорого под ключ (1 328 в мес.)',
 'C22': 'откатные ворота с калиткой под ключ цена с установкой', 'C19': 'забор на сваях под ключ',
 'C31': 'забор под ключ серпухов / солнечногорск / чехов…', 'C23': 'откатные ворота дорхан',
 'C21': 'откатные ворота цена с установкой в московской области', 'C04': 'купить забор недорого от производителя (1 342 в мес.)',
 'C25': 'установка забора на участке правила и нормативы', 'C11': 'забор под ключ в рассрочку'}

# Цитаты: (текст, площадка, компания, дата, звёзды). Имена не входят; проверяются по all_reviews.json ниже.
Q = {
 'C41': ('В декабре начались морозы и опять калитку перекосило( на замок не закрывается).', 'Яндекс Карты', 'masterovit.ru', '2024-12-17', '2'),
 'C28': ('Общее резюме: пока ты не заплатил деньги, с тобой общаются с заинтересованностью, но вот уже после оплаты - уровень эмпатии спадает.', 'Яндекс Карты', 'zaboroff.ru', '2022-08-22', '4'),
 'C18': ('Сварные швы начали ржаветь сразу же.', 'Яндекс Карты', 'zavodzaborov.ru', '2025-03-02', '1'),
 'C27': ('Обратилась в эту компанию из-за гарантии 3 года.', 'Яндекс Карты', 'masterovit.ru', '2025-10-13', '1'),
 'C09': ('После приезда замерщика цена увеличилась на 70%,это у них обычное дело.', 'Яндекс Карты', 'masterovit.ru', '2025-06-23', '1'),
 'C14': ('в течении трех раз нас просто кидали в назначенную для установки дату.', 'Яндекс Карты', 'raduga-zaborov.ru', '2024-06-16', '1'),
 'C42': ('Все оперативно замерил, проконсультировал, подсказал как сделать лучше и надежнее.', 'Яндекс Карты', 'prof-zabory.ru', '2023-07-01', '5'),
 'C08': ('Единственное, цена в онлайн калькуляторе и тут разнится в 1,5 раза, а так все супер!', 'Яндекс Карты', 'masterovit.ru', '2019-07-11', '5'),
 'C07': ('Да, дорого, но оно того стоит.', 'Яндекс Карты', 'masterovit.ru', '2019-10-03', '5'),
 'C29': ('Мастера оперативно установили забор, управились за 1,5 дня, вежливые, аккуратные, после себя не оставили мусора.', 'Яндекс Карты', 'raduga-zaborov.ru', '2024-11-19', '5'),
 'C33': ('Приехал замерщик, взял 4 тысячи.', 'Яндекс Карты', 'zaborkin.ru', '2026-09-29', '1'),
 'C22': ('Стоимость забора 30 м с калиткой и воротами 142 т р.', 'Яндекс Карты', 'dostup-zabor.ru', '2025-08-26', '5'),
 'C19': ('Ну и забор то гулять не ушёл, а ворота ушли, в феврале их выперло и столб скрутило.', 'Яндекс Карты', 'raduga-zaborov.ru', '2024-07-17', '1'),
 'C31': ('Чтобы перебдеть вызвал замерщика, за 120 км.', 'Яндекс Карты', 'zavodzaborov.ru', '2024-04-27', '5'),
 'C15': ('Поставили забор за один день.', 'Яндекс Карты', 'zavodzaborov.ru', '2025-06-07', '5'),
 'C17': ('играли высотой и кол-вом лаг, менеджер все оперативно пересчитывал и отрпалял на почту.', 'Яндекс Карты', 'masterovit.ru', '2021-08-12', '5'),
 'C16': ('На удивление среагировали быстро, перезвонили в течение пары минут, задали вопросы про размеры, тип грунта и материалы для изготовления.', 'Яндекс Карты', 'raduga-zaborov.ru', '2024-09-04', '5'),
 'C23': ('весной перестали работать пульты, мое обращение по поводу гарантийного ремонта полный игнор!', 'Яндекс Карты', 'prof-zabory.ru', '2023-05-12', '3'),
 'C21': ('Смотрела цены на откатные ворота, на сейте цена 64200, оператор мне пишет что цена 116800.', 'Яндекс Карты', 'zabory-prestige.ru', '2026-06-15', '1'),
 'C12': ('На этапе заключения договора все прекрасно и скидку сделали и скамейку привезли в подарок.', 'Яндекс Карты', 'masterovit.ru', '2021-09-13', '2'),
 'C05': ('В договоре толщина профнастила 0,4, по факту привезли 0,3.', 'Яндекс Карты', 'raduga-zaborov.ru', '2026-08-11', '1'),
 'C10': ('а главное за нормальные деньги с оплатой после установки и с гарантией 2 года, что сейчас почти не встретишь.', 'Яндекс Карты', 'raduga-zaborov.ru', '2024-11-21', '5'),
 'C30': ('Мол, вы акт приемки подписали (в тихий безветренный день), значит сами виноваты', 'Яндекс Карты', 'masterovit.ru', '2026-09-14', '1'),
 'C13': ('Обратились по рекомендации соседей.', 'Яндекс Карты', 'zaborovo.ru', '2025-04-18', '5'),
 'C24': ('за демонтаж старого и подготовку территории конечно пришлось потратиться, но у самих времени не было на это.', 'Яндекс Карты', 'masterovit.ru', '2023-11-17', '5'),
 'C04': ('Выбор был обусловлен ценой и собственным производством.', 'Яндекс Карты', 'pskzabor.ru', '2022-08-30', '5'),
 'C34': ('Подробно проконсультировались в мессенджере и в этот же день приехал замерщик.', 'Яндекс Карты', 'dostup-zabor.ru', '2026-07-01', '5'),
 'C26': ('Продемонстрировал нам  образцы забора, дал ценные советы перед установкой', 'Яндекс Карты', 'zavodzaborov.ru', '2022-07-21', '5'),
 'C20': ('Сама компания занимается только изготовлением, монтаж делает сторонняя организация.', 'Отзовик', 'masterovit.ru', '2025-07-21', '1'),
 'C25': ('решили ставить забор с обеих сторон по границе участков.', 'Яндекс Карты', 'zaboroff.ru', '2024-06-02', '5'),
 'C01': ('Компанию выбрали по отзывам в яндексе и не ошиблись!', 'Яндекс Карты', 'prof-zabory.ru', '2023-09-05', '5'),
 'C06': ('Пришлось отпрашиваться с работы на понедельник.', 'Яндекс Карты', 'raduga-zaborov.ru', '2022-06-06', '2'),
 'C44': ('на руках у меня несколько коммерческих предложений и замерщик из другой компании тоже уже выезжал.', 'Яндекс Карты', 'zavodzaborov.ru', '2026-08-08', '1'),
 'C03': ('Вроде контора давно на рынке, должна следить за имиджем, но нет.', 'Яндекс Карты', 'masterovit.ru', '2025-05-03', '2'),
 'C11': ('Удобная система оплаты: есть возможность рассрочки.', 'Яндекс Карты', 'prof-zabory.ru', '2023-08-30', '5'),
 'C35': ('Все объяснили, скинули несколько вариантов в вотсап.', 'Яндекс Карты', 'raduga-zaborov.ru', '2022-06-17', '5'),
 'C37': ('Менеджер предложил посмотреть примеры работ на фото, нам понравился евроштакетник', 'Яндекс Карты', 'zaborkin.ru', '2022-05-28', '5'),
 'C36': ('И ещё у них очень удобный сайт - всё ясно и понятно, и есть онлайн-калькулятор заборов.', 'Яндекс Карты', 'masterovit.ru', '2023-07-08', '5'),
}
assert set(Q) == set(crit)
MISS = []
norm = lambda s: re.sub(r'\s+', ' ', s).strip().lower()
for cid, (txt, pl, co, dt, st_) in Q.items():
    hit = [x for x in allr if x['platform'] == pl and x['company'] == co and x['date'] == dt
           and str(x['stars']).split('.')[0] == st_ and norm(txt) in norm(x['text'] or '')]
    if not hit: MISS.append(cid)
    assert '[' not in txt and not re.search(r'\d{3}[\s-]?\d{2}[\s-]?\d{2}', txt), f'имя или номер в цитате: {cid}'

assert not MISS, f'цитаты не найдены: {MISS}'

def fmt_date(d):
    y, m, dd = d.split('-'); return f'{dd}.{m}.{y}'

# В разметке criteria.csv часть сторон не измерялась (pspec / nspec = None в build_criteria.py) — в справке «не измерялся».
NO_POS = {'C06', 'C18', 'C19', 'C20', 'C28', 'C36'}
NO_NEG = {'C15', 'C42', 'C36'}
IMPL_HOW = {
 'C06': 'клиент описывает последствие переноса (поездка, отгул), неустойку как условие выбора не называет',
 'C44': 'клиент сравнивает несколько предложений, письменное КП как требование не называет',
 'C03': '«солидность» компании — фоновый признак доверия, в запросах его нет',
 'C35': 'смета в мессенджер работает на этапе заявки; клиент описывает удобство, сам формат не называет',
 'C37': 'доказательства на сайте снижают риск выбора, в отзывах почти не упоминаются',
 'C36': 'посадочная действует на конверсию заявки; сайт в отзывах хвалят единично'}
vt_rows = []
for cid in order:
    c = crit[cid]
    neg, pos, q = int(c['reviews_neg_n']), int(c['reviews_pos_n']), int(c['queries_n'])
    share = float(c['reviews_share_max_pct'])
    sup = supp.get(cid)
    share_eff = max(share, round(100 * sup / 3985, 1)) if sup is not None else share
    brand = cid == 'C01' and len(brand_rev) > 0
    explicit = q >= 1 or brand or share_eff >= EXPL_SHARE
    if explicit:
        conf = 'высокая' if (share_eff >= 5 or q >= 3) else 'средняя'
    else:
        conf = 'высокая' if share_eff < 0.5 else 'средняя (у порога 2%)'
    neg_s = 'не измерялся' if cid in NO_NEG else f'{neg} из 851 ({f1(100 * neg / 851)}%)'
    pos_s = 'не измерялся' if cid in NO_POS else f'{pos} из 3 985 ({f1(100 * pos / 3985)}%)'
    parts = [f'отзывы: негатив {neg_s}, позитив {pos_s}']
    if sup is not None:
        parts.append(f'доп. замер позитива «{SUPP[cid]}»: {sup} из 3 985')
    parts.append(f'уточнения запроса: {q} из 49' + (f' («{QEX[cid]}»)' if q >= 1 else ''))
    if brand:
        parts.append(f'подсказки Яндекса «<бренд> отзывы» у {len(brand_rev)} из 10 компаний (data/brand_demand.csv)')
    if explicit:
        if q >= 1 or brand:
            how = 'клиент называет сам в поисковом запросе'
            if share_eff >= EXPL_SHARE: how += ' и в отзывах'
        else:
            how = 'клиент называет сам в отзывах'
            if cid in NO_POS:
                how += ' — жалобой после покупки (позитив не измерялся)'
            elif neg / 851 > pos / 3985 * 3:
                how += ' — в основном жалобой после покупки'
        basis = how + '; ' + '; '.join(parts)
    else:
        basis = (f'в запросах нет, в отзывах реже 2% ({f1(share_eff)}%): вслух почти не называется; '
                 + IMPL_HOW[cid] + '; что критерий влияет на выбор, прямыми данными не подтверждено (оценка); ' + '; '.join(parts)
                 + f'; рынок закрывает у {V[cid]["n_companies_score_ge3"]} из 10')
    mot = MOT_OF.get(cid, [])
    txt, pl, co, dt, st_ = Q[cid]
    lead = '' if txt[0].isupper() else '…'
    vt_rows.append({'criterion_id': cid, 'criterion': c['criterion'], 'class': c['class'], 'weight': c['weight'],
                    'value_type': 'эксплицитная' if explicit else 'имплицитная', 'confidence': conf, 'basis': basis,
                    'hidden_motive': '; '.join(f'{m} {MOTIVE[m]}' for m in mot) if mot else '—',
                    'quote': f'«{lead}{txt}»', 'quote_source': f'{pl}, {co}, {fmt_date(dt)}, {st_}★',
                    'in_our_offer': V[cid]['in_our_offer'], 'our_promise_score': V[cid]['our_promise_score'],
                    'source': 'data/criteria.csv (reviews_*, queries_n); notes/raw_reviews/all_reviews.json; notes/reviews_spravka.md разд. 8',
                    'date': DATE})
with open(f'{B}/data/criteria_value_type.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(vt_rows[0].keys())); w.writeheader(); w.writerows(vt_rows)
VT = {x['criterion_id']: x for x in vt_rows}

# ================= 3. SVG =================
def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def item(cid, with_co=False):
    s = SHORT[cid] + (' ▲' if V[cid]['above_market_promise'] == 'да' else '')
    return s

CY = 330
C1 = (255, CY, 245)   # общее
C3 = (480, CY, 225)   # наше
C2 = (735, CY, 210)   # уникальное
assert math.dist(C1[:2], C2[:2]) > C1[2] + C2[2], 'круги «общее» и «уникальное» не должны пересекаться'

def inside(p, c, pad=4):
    return math.dist(p, c[:2]) < c[2] - pad

def fits(x, y, s, size, inn, out=(), anchor='middle'):
    """Проверка: оба края строки (оценка ширины 0,6 × кегль на знак) лежат в кругах inn и вне кругов out."""
    w = len(s) * size * 0.6
    xs = (x - w / 2, x + w / 2) if anchor == 'middle' else (x, x + w)
    for px in xs:
        for py in (y, y - size * 0.75):
            ok = all(inside((px, py), c) for c in inn) and not any(math.dist((px, py), c[:2]) < c[2] + 4 for c in out)
            assert ok, f'строка не помещается в зону: «{s}» ({px:.0f}, {py:.0f})'

svg = []
A = svg.append
H = 930
A(f'<svg viewBox="0 0 960 {H}" width="100%" role="img" aria-labelledby="venn-t venn-d" '
  'style="max-width:960px;height:auto;font-family:inherit;display:block" xmlns="http://www.w3.org/2000/svg">')
A('<title id="venn-t">Критерии выбора: общее у конкурентов, уникальное у отдельных, целевой оффер «Дома гирлянд»</title>')
A(f'<desc id="venn-d">38 критериев. Общее (оценка 3+ у 7–10 из 10 компаний): {len(ids(lambda x: x["n_companies_score_ge3"] >= 7))}. '
  f'Уникальное (3+ у 1–2 компаний): {len(ids(lambda x: 1 <= x["n_companies_score_ge3"] <= 2))}. '
  f'Середина рынка (3–6 компаний): {len(ids(lambda x: 3 <= x["n_companies_score_ge3"] <= 6))}. '
  f'Целевой оффер закрывает {len(ids(lambda x: x["in_our_offer"] == "да"))}, все — обещание.</desc>')
INK = 'var(--ink, #1d1d1f)'; INK2 = 'var(--ink2, #6e6e73)'
COL = {'c1': 'var(--c1, #2f6fd6)', 'c2': 'var(--c2, #d9822b)', 'c3': 'var(--c3, #2e9e6a)'}
for (x, y, r), k in ((C1, 'c1'), (C2, 'c2'), (C3, 'c3')):
    A(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{COL[k]}" fill-opacity="0.12" stroke="{COL[k]}" stroke-width="2"/>')

def text(x, y, s, size=13, fill=INK, weight=400, anchor='middle'):
    A(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{esc(s)}</text>')

def block(x, y, head, sub, items, inn, out, size=12, lh=17, sub_items=None):
    lines = [(head, 12.5, INK, 700, lh + 1 if sub else lh + 3)]
    if sub: lines.append((sub, 11, INK2, 400, lh + 2))
    for i, s in enumerate(items):
        lines.append((s, size, INK, 400, 13 if sub_items else lh))
        if sub_items: lines.append((sub_items[i], 10.5, INK2, 400, lh + 2))
    yy = y
    for s, sz, fill, wt, step in lines:
        fits(x, yy, s, sz, inn, out)
        text(x, yy, s, sz, fill, wt)
        yy += step
    return yy

# заголовки кругов (вне кругов)
text(120, 36, 'ОБЩЕЕ У КОНКУРЕНТОВ', 13, COL['c1'], 700)
text(120, 53, 'оценка 3+ у 7–10 из 10 компаний', 11.5, INK2)
text(845, 58, 'УНИКАЛЬНОЕ У ОТДЕЛЬНЫХ', 13, COL['c2'], 700)
text(845, 75, 'оценка 3+ у 1–2 из 10 компаний', 11.5, INK2)
text(480, 598, 'НАШЕ: ЦЕЛЕВОЙ ОФФЕР «ДОМА ГИРЛЯНД»', 13, COL['c3'], 700)
text(480, 615, 'обещание 3+ по той же шкале; все пункты — обещание, исполнения нет', 11.5, INK2)
for s, x, y, sz in (('ОБЩЕЕ У КОНКУРЕНТОВ', 120, 36, 13), ('УНИКАЛЬНОЕ У ОТДЕЛЬНЫХ', 845, 58, 13),
                    ('обещание 3+ по той же шкале; все пункты — обещание, исполнения нет', 480, 615, 11.5)):
    fits(x, y, s, sz, (), (C1, C2, C3))

com_only = ids(lambda x: x['zone'] == 'общее: в оффере нет')
com_our = ids(lambda x: x['zone'] == 'общее ∩ наше: обязательный минимум')
uni_only = ids(lambda x: x['zone'] == 'уникальное: в оффере нет')
uni_our = ids(lambda x: x['zone'] == 'уникальное ∩ наше: догоняем')
our_only = ids(lambda x: x['zone'] == 'только наше: отстройка')
mid_our = ids(lambda x: x['zone'] == 'вне кругов: середина рынка (3–6), наше')
mid_not = ids(lambda x: x['zone'] == 'вне кругов: середина рынка (3–6), в оффере нет')
above = ids(lambda x: x['above_market_promise'] == 'да')
stems = lambda c: 'у ' + ' · '.join(STEM[k] for k in V[c]['companies_ge3'].split('; '))

block(128, 290, f'Только у рынка: {len(com_only)}', 'в оффере нет', [item(c) for c in com_only], (C1,), (C3,))
block(378, 216, 'Обязательный минимум', f'критериев: {len(com_our)}', [item(c) for c in com_our], (C1, C3), (), 12, 17)
block(616, 262, f'Догоняем: {len(uni_our)}', None, [item(c) for c in uni_our], (C2, C3), (), 12, 17, [stems(c) for c in uni_our])
block(838, 300, f'Только у 1–2: {len(uni_only)}', 'в оффере нет', [item(c) for c in uni_only], (C2,), (C3,), 12, 17, [stems(c) for c in uni_only])
block(515, 486, f'Только наше: {len(our_only)}', 'критериев нет;', ['отстройка —', f'уровнем ▲: {len(above)}'],
      (C3,), (C1, C2), 11.5, 15)

# середина рынка — вне кругов
top = 645
A(f'<rect x="16" y="{top}" width="928" height="180" rx="10" fill="none" stroke="{INK2}" stroke-dasharray="5 4" stroke-width="1.2"/>')
text(32, top + 24, f'ВНЕ КРУГОВ: середина рынка — оценка 3+ у 3–6 из 10 компаний ({len(mid_our) + len(mid_not)})', 12.5, INK, 700, 'start')
text(32, top + 46, f'В оффере: {len(mid_our)}', 12, COL['c3'], 700, 'start')
half = math.ceil(len(mid_our) / 2)
for i, c in enumerate(mid_our):
    col, row = divmod(i, half)
    text(32 + col * 230, top + 66 + row * 17, item(c), 12, INK, 400, 'start')
text(520, top + 46, f'В оффере нет: {len(mid_not)}', 12, INK2, 700, 'start')
for i, c in enumerate(mid_not):
    text(520, top + 66 + i * 17, item(c), 12, INK, 400, 'start')
assert top + 66 + (half - 1) * 17 < top + 175 and max(len(item(c)) for c in mid_our) * 12 * 0.6 < 225

cap = [
 'Порог: критерий у компании есть, если её оценка 3 и выше из 5 (оценки 10 компаний полного разбора).',
 '«Общее» — оценка 3+ у 7–10 компаний, «уникальное» — у 1–2; эти круги не пересекаются: у критерия одно число компаний.',
 '«Наше» — обещание целевого оффера 3+ по той же шкале; исполнения и отзывов у нового игрока нет.',
 '▲ — уровень обещания, которого нет ни у одной из 10 компаний. Списки — по убыванию веса критерия. Дата: 21.10.2026.']
for i, s in enumerate(cap):
    text(16, top + 206 + i * 17, s, 11.5, INK2, 400, 'start')
    assert len(s) * 11.5 * 0.6 < 930, s
assert top + 206 + 3 * 17 < H
A('</svg>')
with open(f'{B}/notes/venn.svg.html', 'w', encoding='utf-8') as f:
    f.write('<!-- Диаграмма Венна критериев выбора. Цвета: var(--c1) общее, var(--c2) уникальное, var(--c3) наше; '
            'текст: var(--ink), var(--ink2). Источник: data/venn_criteria.csv; скрипт notes/scripts/synthesis/venn_values.py -->\n')
    f.write('<figure class="venn" style="margin:0">\n' + '\n'.join(svg) + '\n</figure>\n')

# ================= 4. Сводка и сверка справки =================
expl = ids(lambda x: VT[x['criterion_id']]['value_type'] == 'эксплицитная')
impl = [c for c in order if c not in expl]
our = ids(lambda x: x['in_our_offer'] == 'да')
w_impl = sum(float(crit[c]['weight']) for c in impl)
w_all = sum(float(crit[c]['weight']) for c in order)
mot_cov = {}
for m in MOTIVE:
    cs = [c for c in order if m in MOT_OF.get(c, [])]
    mot_cov[m] = (cs, [c for c in cs if c in our])

F = {
 'всего': len(order), 'общее': len(com_only) + len(com_our), 'общее_наше': len(com_our), 'общее_нет': len(com_only),
 'уник': len(uni_only) + len(uni_our), 'уник_наше': len(uni_our), 'уник_нет': len(uni_only), 'только_наше': len(our_only),
 'середина': len(mid_our) + len(mid_not), 'середина_наше': len(mid_our), 'середина_нет': len(mid_not),
 'наше_всего': len(our), 'выше_рынка': len(above), 'экспл': len(expl), 'импл': len(impl),
 'импл_наше': sum(1 for c in impl if c in our), 'вес_импл_pct': f1(100 * w_impl / w_all),
 'бренд_отзывы': len(brand_rev),
}
print('Зоны:', dict(Z))
print('Сводка:', F)
print('Выше рынка (▲):', above)
print('Имплицитные:', [(c, VT[c]['in_our_offer'], VT[c]['confidence']) for c in impl])
print('Доп. замер:', supp)
for m, (cs, co) in mot_cov.items():
    print(m, MOTIVE[m], 'критерии:', cs, 'закрыто оффером:', co)
for c in order:
    print(c, V[c]['n_companies_score_ge3'], V[c]['zone'], V[c]['our_status'], VT[c]['value_type'], VT[c]['confidence'])

# Сверка: каждая строка FACTS должна дословно стоять в справке.
sp = f'{B}/notes/venn_values_spravka.md'
try:
    S = open(sp, encoding='utf-8').read()
except FileNotFoundError:
    S = None
if S is not None:
    W_ = {c: float(crit[c]['weight']) for c in order}
    pct = lambda cs: f1(100 * sum(W_[c] for c in cs) / w_all)
    not_our = [c for c in order if c not in our]
    ADDED_21_10 = {'C09', 'C18', 'C22', 'C27', 'C28', 'C29', 'C30', 'C42', 'C44'}   # criteria_rules.md, уровни версии 3
    def names(cs): return ', '.join(SHORT[c].lower() if i else SHORT[c] for i, c in enumerate(cs))
    FACTS = [
     f'общее — {F["общее"]} из 38',
     f'обязательный минимум — {F["общее_наше"]}',
     f'уникальное — {F["уник"]}',
     f'догоняем — {F["уник_наше"]}',
     f'только наше — {F["только_наше"]}',
     f'середина рынка (3–6 компаний) — {F["середина"]}',
     f'целевой оффер закрывает {F["наше_всего"]} из 38',
     f'уровень обещания выше всех 10 — у {F["выше_рынка"]} критериев',
     f'эксплицитных — {F["экспл"]}, имплицитных — {F["импл"]}',
     f'{F["вес_импл_pct"]}% суммарного веса',
     f'«<бренд> отзывы» есть у {F["бренд_отзывы"]} из 10',
     f'оффер закрывает {F["импл_наше"]} из {F["импл"]}',
     f'{pct(our)}% суммарного веса; все {len(our)} — обещание',
     f'это {pct(above)}% суммарного веса. У {sum(1 for c in above if c in ADDED_21_10)} из {len(above)} этот уровень',
     f'{len(com_our)} критериев с {pct(com_our)}% суммарного веса',
     f'Вне оффера — {len(not_our)} критериев, {pct(not_our)}% суммарного веса',
     f'Из них {f1(sum(W_[c] for c in ("C41", "C07")))} из {f1(sum(W_[c] for c in not_our))} дают',
     f'полностью у {sum(1 for m in mot_cov if len(mot_cov[m][1]) == len(mot_cov[m][0]))} из 7 мотивов',
     f'M3 проверка забора первой зимой ({len(mot_cov["M3"][1])} из {len(mot_cov["M3"][0])}',
     f'M4 забор виден соседям ({len(mot_cov["M4"][1])} из {len(mot_cov["M4"][0])}',
     f'M7 кто приедет на участок ({len(mot_cov["M7"][1])} из {len(mot_cov["M7"][0])}',
     f'связь после оплаты (вес {f1(W_["C28"])}, {order.index("C28") + 1}-й по весу',
     f'квиз и доказательства на сайте — оценка 3+ у {V["C35"]["n_companies_score_ge3"]} из 10',
     f'неустойка (1,9%), письменное КП (1,4%), опыт и масштаб (1,1%)',
     ('у каждого из 38 критериев оценку 3+ имеет хотя бы 1 компания'
      if all(V[c]['n_companies_score_ge3'] >= 1 for c in order) else 'ОШИБКА: есть критерий без компаний'),
    ]
    miss = [x for x in FACTS if x.lower() not in S.lower()]
    print('Сверка справки:', 'OK' if not miss else f'НЕ НАЙДЕНО: {miss}')
    assert not miss
