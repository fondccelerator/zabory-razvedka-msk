"""Медиаплан гипотез для теста с 22.10.2026 (заборы и откатные ворота, Москва и МО). Версия 4 (после проверки надзирателя, журнал qa/checks_wave2.csv).
Цепочка: бюджет → клики (бюджет / CPC) → заявки (клики × конверсия страницы) → заказы (заявки × закрытие) → цена заказа → доля рекламы в чеке.
CPC — диапазон 85–124 ₽ (прогноз Keys.so по 8 запросам — оценка Spywords по masterovit.ru), крайние 71–245 ₽ по запросам Spywords.
Чек — три сценария: консервативный (модель «длина × цена от»), по данным отзывов и прозвона (база), верхний (КП конкурента).
Вердикт по каждому сценарию чека: «≤ 11% чека» / «окупается по марже» (реклама ≤ 25% чека, валовая маржа — оценка) / «не окупается».
Бюджеты — допущение аналитика. Запуск: python3 -I mediaplan.py. Выход: data/mediaplan.csv"""
import csv, json, statistics as st

B = '/home/claude/zabory'
kq = json.load(open(f'{B}/data/keys_queries_msk.json', encoding='utf-8'))
os_rows = [r for r in csv.DictReader(open(f'{B}/data/order_sums_reviews.csv', encoding='utf-8')) if r['included'] == 'да']
OS = [int(r['sum_rub']) for r in os_rows]
OS_MED = st.median(OS); OS_Q = st.quantiles(OS, n=4, method='inclusive')

CTR = 0.05
CONV = {'поиск': 0.02, 'РСЯ': 0.01}
RSYA_K = 1.5
CLOSE, CLOSE_LO, CLOSE_HI = 0.09, 0.08, 0.10
AVITO_CLOSE = 0.023            # кейс Авито: 2 из 86 обращений дошли до оплаты (исследование ворот)
QUAL_REF = 0.65
AD_SHARE, GROSS = 0.11, 0.25
EXACT_K = round(14205 / 57377, 3)
SEASON = (round(29008 / 57377, 2), round(29008 / 41508, 2))
CPC_EXT = (71, 245)            # Spywords: «забор из профнастила» 71 ₽ … «заборы в московской области под ключ» 244,92 ₽

def wcpc(qs):
    f = sum(kq[q]['f'] for q in qs)
    return round(sum(kq[q]['f'] * kq[q]['cpc'] for q in qs) / f, 1), f
FENCE_Q = ['забор под ключ', 'установка забора', 'забор из профнастила под ключ', 'забор в московской области',
           'монтаж забора цена', 'заказать забор', 'забор из евроштакетника', 'забор жалюзи']
cpc_keys, f_fence = wcpc(FENCE_Q)
CPC = (cpc_keys, 124.0)        # Keys.so прогноз — Spywords по masterovit.ru (бюджет / переходы, включает бренд и навесы)
CPC_SRC = ('диапазон: прогноз Keys.so «Средняя ставка» по 8 запросам о заборах (85,4 ₽, 05.09–02.10.2026) — Spywords по masterovit.ru: 17 276 ₽/день × 30 / 4 164 перехода = 124 ₽ '
           '(одна точка, включает бренд и навесы); крайние 71–245 ₽ — средний CPC Spywords по запросам (data/ads_yandex.csv)')
f_pack = kq['забор с откатными воротами']['f']
GATES_Q4 = round(186600 * 0.184 / 3)
AUTO_W = round((51300 + 13600) * 0.22 / 3)

PRICE_MED = st.median([1907, 1491, 1670, 1854, 850, 2150, 1485, 1934, 1340, 1710])
GATE_AUTO = 103025
FENCE_MODEL = (round(40 * PRICE_MED), round(73 * PRICE_MED))
CHECKS = {
 'забор': [('консервативный: 40–73 м × медиана «от» 1 690 ₽', FENCE_MODEL),
           (f'база: медиана сумм заказов в отзывах (n={len(OS)})', (OS_MED, OS_MED)),
           ('верхний: третий квартиль сумм заказов в отзывах', (OS_Q[2], OS_Q[2]))],
 'пакет': [('консервативный: модель забора + ворота с автоматикой 103 025 ₽', tuple(f + GATE_AUTO for f in FENCE_MODEL)),
           ('база: прозвон 21.10 — 350–450 тыс. ₽ с воротами', (350000, 450000)),
           ('верхний: КП конкурента 730–950 тыс. ₽', (730000, 950000))],
 'привод': [('единственный: медиана 3 цен привода с монтажом', (42700, 42700))],
}

def cap(lo, hi, days):
    return round(lo * EXACT_K * CTR * days / 30), round(hi * EXACT_K * CTR * days / 30)

H = [
 dict(id='H1', ch='Яндекс Директ, поиск', kind='поиск', budget=60000, days=21, seg='забор',
      cap=cap(f_fence * SEASON[0], f_fence * SEASON[1], 21), cap_src=f'8 запросов {f_fence} (широкая) × 0,248 × сезон 0,51–0,70 × CTR 5% × 21/30'),
 dict(id='H2', ch='Яндекс Директ, поиск', kind='поиск', budget=14000, days=28, seg='пакет',
      cap=cap(f_pack * SEASON[0] + GATES_Q4, f_pack * SEASON[1] + GATES_Q4, 28), cap_src=f'«забор с откатными воротами» {f_pack} × сезон + ворота {GATES_Q4} в месяц; × 0,248 × CTR 5% × 28/30'),
 dict(id='H3', ch='Яндекс Директ, РСЯ', kind='РСЯ', budget=30000, days=28, seg='забор', cap=None, cap_src='охват РСЯ запросами не ограничен'),
 dict(id='H4', ch='VK Реклама (лид-форма или сообщения)', kind='ВК', budget=30000, days=21, seg='забор', cap=None, cap_src='—'),
 dict(id='H5', ch='Яндекс Директ, поиск', kind='поиск', budget=4500, days=28, seg='привод',
      cap=cap(AUTO_W, AUTO_W, 28), cap_src=f'«привод» + «ремонт откатных ворот» {AUTO_W} в месяц × 0,248 × CTR 5% × 28/30'),
 dict(id='H7', ch='Яндекс Карты: приоритетное размещение (Яндекс Бизнес)', kind='Карты', budget=15000, days=28, seg='пакет', cap=None, cap_src='—'),
 dict(id='H8', ch='Авито: продвижение объявлений «забор под ключ» и «откатные ворота»', kind='Авито', budget=20000, days=21, seg='забор', cap=None, cap_src='—'),
]

def pct(x): return f'{x:.1%}'.replace('.', ',')
def num(x): return f'{round(x):,}'.replace(',', ' ')
def rng(a, b, f=num):
    a, b = min(a, b), max(a, b)
    return f(a) if f(a) == f(b) else f'{f(a)}–{f(b)}'
def verdict(cpo_lo, cpo_hi, chk):
    share_hi = cpo_hi / chk[0]; share_lo = cpo_lo / chk[1]
    def one(sh): return '≤ 11% чека' if sh <= AD_SHARE else 'окупается по марже' if sh <= GROSS else 'не окупается'
    a, b = one(share_lo), one(share_hi)
    return a if a == b else f'{a} … {b}'

rows = []
for h in H:
    K_ = RSYA_K if h['kind'] == 'РСЯ' else 1
    cpc = (CPC[0] / K_, CPC[1] / K_) if h['kind'] in ('поиск', 'РСЯ') else None
    scen = []
    if cpc:
        scen.append(('база: конверсия страницы ' + pct(CONV[h['kind']]), CONV[h['kind']], None, CLOSE))
        if h['seg'] != 'привод':
            scen.append(('сверка: цена заявки кейсов ' + ('741' if h['kind'] == 'РСЯ' else '1 300') + ' ₽', None, 741 if h['kind'] == 'РСЯ' else 1300, CLOSE))
    if h['kind'] == 'ВК':
        scen.append(('по кейсам: заявка 1 300 ₽ (1 257–1 373 ₽, eLama)', None, 1300, CLOSE))
    if h['kind'] == 'Авито':
        scen.append(('база: кейс Авито — обращение 230 ₽ (120–339 ₽) и закрытие 2,3%', None, 230, AVITO_CLOSE))
        scen.append(('оптимистичный: обращение 230 ₽, закрытие 9% (как у квалифицированных заявок Директа)', None, 230, CLOSE))
        scen.append(('справочно, ворота: заявка 550 ₽ (авитолог, 400–700 ₽), закрытие 9%', None, 550, CLOSE))
    if h['kind'] == 'Карты':
        scen.append(('не считается: цена обращения с карт не найдена', None, None, None))
    for name, conv, cpl_fixed, close in scen:
        base = {'hypothesis_id': h['id'], 'channel': h['ch'], 'segment_check': h['seg'], 'scenario': name, 'budget_rub_assumption': h['budget'], 'test_days': h['days'],
                'cpc_rub': rng(*cpc, f=lambda v: f'{v:.1f}'.replace('.', ',')) if cpc else 'не применяется',
                'cpc_source': (CPC_SRC + (' / 1,5' if K_ > 1 else '')) if cpc else ('цена клика ВК не снята' if h['kind'] == 'ВК' else 'Авито: цена обращения из кейсов (исследование ворот) и данных авитолога' if h['kind'] == 'Авито' else 'тариф Яндекс Бизнес от 3 000 ₽ в месяц; у всех 10 первых карточек по 4 запросам есть реклама (data/ads_maps.csv)'),
                'capacity_clicks_test_period': rng(*h['cap']) if h['cap'] else '—', 'capacity_source': h['cap_src']}
        if conv is None and cpl_fixed is None:
            base.update({k: 'не считается' for k in ['clicks', 'page_conversion', 'page_conversion_note', 'leads', 'cpl_rub', 'cpl_at_cpc_extremes_rub', 'qualified_leads_ref_65pct', 'close_rate', 'orders', 'cpo_rub']})
            for i, (cn, chk) in enumerate(CHECKS[h['seg']], 1):
                base[f'check{i}_name'] = cn; base[f'check{i}_rub'] = rng(*chk); base[f'check{i}_ad_share'] = 'не считается'
                base[f'check{i}_breakeven_cpl_rub'] = rng(GROSS * chk[0] * CLOSE, GROSS * chk[1] * CLOSE); base[f'check{i}_verdict'] = 'не считается'
            rows.append(base); continue
        if cpl_fixed:
            leads = (h['budget'] / cpl_fixed,) * 2
            clicks = (h['budget'] / cpc[1], h['budget'] / cpc[0]) if cpc else None
            conv_eff = (cpc[0] / cpl_fixed, cpc[1] / cpl_fixed) if cpc else None
            cpl = (cpl_fixed, cpl_fixed)
        else:
            clicks = (h['budget'] / cpc[1], h['budget'] / cpc[0]); leads = (clicks[0] * conv, clicks[1] * conv)
            cpl = (cpc[0] / conv, cpc[1] / conv); conv_eff = (conv, conv)
        orders = (leads[0] * close, leads[1] * close); cpo = (h['budget'] / orders[1], h['budget'] / orders[0])
        base.update({
            'clicks': rng(*clicks) if clicks else 'не считается',
            'page_conversion': rng(*conv_eff, f=pct) if conv_eff else 'не считается',
            'page_conversion_note': 'задана сценарием' if conv else ('неявная: CPC ÷ цена заявки кейса' if cpc else 'не считается'),
            'leads': rng(*leads, f=lambda v: f'{v:.1f}'.replace('.', ',')), 'cpl_rub': rng(*cpl),
            'cpl_at_cpc_extremes_rub': (rng(CPC_EXT[0] / K_ / conv, CPC_EXT[1] / K_ / conv) + f' (CPC {CPC_EXT[0]}–{CPC_EXT[1]} ₽' + (' / 1,5' if K_ > 1 else '') + ')') if (conv and cpc) else 'не считается',
            'qualified_leads_ref_65pct': rng(leads[0] * QUAL_REF, leads[1] * QUAL_REF, f=lambda v: f'{v:.1f}'.replace('.', ',')) + ' (справочно)',
            'close_rate': pct(close) if close != CLOSE else '9% (8–10%)', 'orders': rng(*orders, f=lambda v: f'{v:.2f}'.replace('.', ',')), 'cpo_rub': rng(*cpo)})
        for i, (cn, chk) in enumerate(CHECKS[h['seg']], 1):
            base[f'check{i}_name'] = cn; base[f'check{i}_rub'] = rng(*chk)
            base[f'check{i}_ad_share'] = rng(cpo[0] / chk[1], cpo[1] / chk[0], pct)
            base[f'check{i}_breakeven_cpl_rub'] = rng(GROSS * chk[0] * close, GROSS * chk[1] * close)
            base[f'check{i}_verdict'] = verdict(cpo[0], cpo[1], chk)
        rows.append(base)
for r in rows:
    for i in (2, 3):
        for k in ('name', 'rub', 'ad_share', 'breakeven_cpl_rub', 'verdict'):
            r.setdefault(f'check{i}_{k}', '—')
    r['note'] = 'бюджет — допущение; конверсии, закрытие, маржа — оценки; ноябрь — спад спроса; суммы в отзывах: 19 из 20 — из негативных отзывов (смещение)'
fields = list(rows[0].keys())
for r in rows:
    for k in fields: r.setdefault(k, '—')
with open(f'{B}/data/mediaplan.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
print('CPC', CPC, 'orders sums median', OS_MED, 'Q', OS_Q, 'budget', sum(h['budget'] for h in H))
for r in rows:
    print(r['hypothesis_id'], r['scenario'][:40].ljust(40), 'clk', r['clicks'], 'cap', r['capacity_clicks_test_period'], 'cpl', r['cpl_rub'], 'cpo', r['cpo_rub'])
    for i in (1, 2, 3):
        if r[f'check{i}_name'] != '—': print('     ', r[f'check{i}_name'][:45].ljust(45), r[f'check{i}_rub'], r[f'check{i}_ad_share'], '|', r[f'check{i}_verdict'])
