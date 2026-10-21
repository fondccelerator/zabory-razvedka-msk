"""Ключи, рефералы, соцсети, медийка этапа traffic (из notes/raw_traffic, Similarweb Pro, 20.10.2026)."""
import csv
import os

DATA = '/home/claude/zabory/data'
DATE = '20.10.2026'
import json
SH = json.load(open('/home/claude/zabory/notes/raw_traffic/shares.json', encoding='utf-8'))
CV = lambda d, ch: SH[d]['visits'] * SH[d]['shares'][ch]  # визиты за 3 мес × доля канала
S_KW1 = 'Similarweb Pro, Website performance (один домен masterovit.ru), Search: топ-5 ключей за сентябрь 2026'
S_KW3 = 'Similarweb Pro, Search → Search overview (masterovit.ru), Top keywords за июль–сентябрь 2026'
S_KWF = 'Similarweb Pro, Search → Find keywords (website-keyword-v2, masterovit.ru), июль–сентябрь 2026'
S_KWG = 'Similarweb Pro, Website performance, сравнение группы 2 (zaborovo, oblzabor, dostup-zabor, zaboroff, pskzabor): топ-5 ключей группы за сентябрь 2026'


def w(name, rows):
    with open(os.path.join(DATA, name), 'w', encoding='utf-8', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print(name, len(rows))


def kw(domain, keyword, ktype, branded, share, visits, volume, cpc, period, source, note=''):
    return {'domain': domain, 'keyword': keyword, 'type': ktype, 'branded': branded,
            'share_pct': share, 'visits': visits, 'volume_month': volume, 'cpc_usd': cpc,
            'period': period, 'source': source, 'note': note, 'date': DATE}


K = []
# masterovit.ru, сентябрь: топ-5 органических (доля от органических визитов сайта из поиска за месяц)
for t, sh, v, cpc, vol in [
    ('чем зашить ворота в гараже изнутри', '8,9', 430, '0', '0'),
    ('монтаж секционного забора', '8,1', 390, '0', '267'),
    ('навес для автомобиля', '8,1', 390, '0', '938'),
    ('отделка внешней стиороны ворот гаража', '7,7', 370, '0', '90'),
    ('через какое растояние ставится металлический штакетник', '6,9', 330, '0', '0'),
]:
    K.append(kw('masterovit.ru', t, 'органический', 'нет', sh, v, vol, cpc, 'сентябрь 2026', S_KW1,
                'написание запроса — как в Similarweb'))
for t, sh, v, cpc, vol in [
    ('калькулятор забора из  профлиста', '20,5', 230, '0', '0'),
    ('блолк прямоугольный для установки забора', '18,8', 210, '0', '0'),
    ('забор из профнастила', '17,0', 190, '0,24', '2555'),
    ('забор купить с установкой под ключ', '13,4', 150, '0', '0'),
    ('забор', '11,6', 130, '0,24', '25484'),
]:
    K.append(kw('masterovit.ru', t, 'платный', 'нет', sh, v, vol, cpc, 'сентябрь 2026', S_KW1,
                'доля от платных визитов из поиска за месяц; частотность — мировая оценка Similarweb'))
# masterovit.ru, 3 месяца: Top keywords (клики, доля от кликов топа)
for t, ty, sh, v in [
    ('сетка 3d 7004', 'платный', '4,2', 1340),
    ('как правильно ставить раскосы на распашных воротах', 'органический', '3,3', 1060),
    ('расчёт забора из профнастила калькулятор', 'органический', '3,2', 1020),
    ('сколько стоит установка забора', 'органический', '3,2', 1010),
]:
    K.append(kw('masterovit.ru', t, ty, 'нет', sh, v, '', '', 'июль–сентябрь 2026', S_KW3))
K.append(kw('masterovit.ru', 'навес для машины на дачу цена с установкой московская область', 'органический', 'нет',
            '', '', '', '', 'июль–сентябрь 2026', S_KW3, '5-й ключ топа; число кликов не снято (вывод обрезан)'))
K.append(kw('masterovit.ru', 'мастеровит', 'органический', 'да', '11,1', 2830, '1580', '0', 'июль–сентябрь 2026', S_KWF,
            '1-е место из 599 ключей; всего 25 570 кликов по списку; полный список не снят — дневной лимит'))
# группа 2, сентябрь: доля — от поисковых визитов всей группы данного типа; домен — по SiteOrigins
for t, dom, sh, v, vol, br in [
    ('навес для машины на дачу 4*6 с плоским поликарбонатом в москве', 'oblzabor.ru; zaboroff.ru (поровну)', '14,3', 640, '0', 'нет'),
    ('профнастил честный знак', 'zaborovo.ru', '10,7', 480, '0', 'нет'),
    ('вадский муниципальный округ правила строительства забора между соседями', 'zaboroff.ru', '8,9', 400, '179', 'нет'),
    ('ворота в частный дом из серого профнастила высотой 3 м', 'oblzabor.ru', '8,3', 370, '180', 'нет'),
    ('своими руками устройство на откатные ворота с верхним подвесом', 'zaborovo.ru', '7,4', 330, '0', 'нет'),
]:
    K.append(kw(dom, t, 'органический', br, sh, v, vol, '0', 'сентябрь 2026', S_KWG,
                f'доля от органических визитов группы; оценка: модель Similarweb, малая база ({v} визитов за сентябрь)'))
for t, dom, sh, v, vol, br, note in [
    ('калькулятор забор из профнастила', 'oblzabor.ru', '43,2', 190, '0', 'нет', ''),
    ('расчёт забора из профнастила', 'oblzabor.ru', '29,5', 130, '0', 'нет', ''),
    ('калькулятор забора мастеровит', 'zaborovo.ru', '13,6', 60, '0', 'чужой бренд (Мастеровит)',
     'zaborovo.ru получает платный трафик по запросу с брендом конкурента'),
    ('заборово', 'zaborovo.ru', '11,4', 50, '59', 'да', ''),
    ('заборы под ключ москва', 'zaborovo.ru; zaboroff.ru (поровну)', '4,5', 20, '0', 'нет', ''),
]:
    K.append(kw(dom, t, 'платный', br, sh, v, vol, '0', 'сентябрь 2026', S_KWG,
                (f'доля от платных визитов группы; оценка: модель Similarweb, малая база ({v} визитов за сентябрь). ' + note).strip()))
w('traffic_keywords.csv', K)

# Сводка поиска по доменам: органика/платный/бренд
SR = [
    {'domain': 'masterovit.ru', 'search_visits_3m': 72815, 'organic_visits_3m': 68893, 'paid_visits_3m': 3922,
     'organic_share_of_search_pct': '94,6', 'paid_share_of_search_pct': '5,4', 'branded_share_pct': '19,4',
     'nonbranded_share_pct': '80,6', 'branded_by_month': 'июль 21,5; август 18,5; сентябрь 19,2',
     'keywords_count': 599, 'ppc_spend_usd': '0 (Similarweb не оценивает бюджет Директа)',
     'source': 'Similarweb Pro, Search → Search overview (masterovit.ru), июль–сентябрь 2026', 'date': DATE},
]
w('traffic_search_summary.csv', SR)

# Рефералы
REF_TOT_M = CV('masterovit.ru', 'Referrals')  # визиты канала за 3 мес × доля
R = []
for dom, f_, sh in [('yandex.ru', 0.4682, '46,8'), ('dzen.ru', 0.2669, '26,7'), ('без атрибуции («Referral»)', 0.178, '17,8'),
                    ('ya.ru', 0.048, '4,8'), ('ivi.ru', 0.010, '1,0')]:
    vis = round(REF_TOT_M * f_)
    note = f'оценка: визиты канала переходов ({round(REF_TOT_M)}) × доля источника {f_}'
    R.append({'domain': 'masterovit.ru', 'referrer': dom, 'visits_3m': vis, 'share_of_referrals_pct': sh,
              'referrers_total': 18, 'aggregator_or_catalog': 'нет', 'note': note,
              'source': 'Similarweb Pro, Referral (masterovit.ru) и Website performance → Top referrals, июль–сентябрь 2026, весь мир',
              'date': DATE})
# группа 2: доля источника в рефералах группы × распределение по доменам
G2_REF = {d: CV(d, 'Referrals') for d in ['zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']}
G2_TOT = sum(G2_REF.values())
order = ['zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']
for ref, sh, split in [
    ('без атрибуции («Referral»)', 0.615, [0.445, 0.001, 0.316, 0.203, 0.036]),
    ('yandex.ru', 0.149, [0, 0.114, 0.886, 0, 0]),
    ('avatars.mds.yandex.net', 0.094, [0, 0, 1, 0, 0]),
    ('dzen.ru', 0.083, [0, 1, 0, 0, 0]),
    ('ya.ru', 0.034, [0, 1, 0, 0, 0]),
]:
    for d, s in zip(order, split):
        if s == 0:
            continue
        v = G2_TOT * sh * s
        R.append({'domain': d, 'referrer': ref, 'visits_3m': round(v),
                  'share_of_referrals_pct': f'{min(v / G2_REF[d] * 100, 100):.1f}'.replace('.', ','),
                  'referrers_total': '', 'aggregator_or_catalog': 'нет',
                  'note': f'оценка: {round(G2_TOT)} визитов переходов группы (Σ визиты × доля) × доля источника {sh} × доля домена {s}',
                  'source': 'Similarweb Pro, Website performance, сравнение группы 2 → Top referrals (топ-5 по группе), июль–сентябрь 2026',
                  'date': DATE})
w('traffic_referrals.csv', R)

# Соцсети
SOC = []
socdata = {
    'masterovit.ru': (1274, 8, 'YouTube 100%'), 'prof-zabory.ru': (202, 14676, 'ВКонтакте 100%'),
    'zaborkin.ru': (2001, 96, 'Telegram (веб-приложение) 100%'), 'zavodzaborov.ru': (1076, 239, 'разбивки нет'),
    'raduga-zaborov.ru': (417, 83, 'разбивки нет'), 'zaborovo.ru': (1183, 247, 'разбивки нет'),
    'oblzabor.ru': (1, 343, 'Одноклассники 100%'), 'dostup-zabor.ru': (897, 167, 'разбивки нет'),
    'zaboroff.ru': (578, 130, 'разбивки нет'), 'pskzabor.ru': (197, 40, 'разбивки нет'),
}
visits = {'masterovit.ru': 388817, 'prof-zabory.ru': 366903, 'zaborkin.ru': 113654, 'zavodzaborov.ru': 96670,
          'raduga-zaborov.ru': 13860, 'zaborovo.ru': 37928, 'oblzabor.ru': 50242, 'dostup-zabor.ru': 43758,
          'zaboroff.ru': 21842, 'pskzabor.ru': 7316}
for d, (_o, _p, nets) in socdata.items():
    org, paid = round(CV(d, 'Social - Organic')), round(CV(d, 'Social - Paid'))
    SOC.append({'domain': d, 'social_organic_visits_3m': org, 'social_paid_visits_3m': paid,
                'social_total_visits_3m': org + paid,
                'social_share_of_site_pct': f'{(org + paid) / visits[d] * 100:.2f}'.replace('.', ','),
                'networks': nets,
                'source': 'Similarweb Pro, Website performance (сравнение групп 1 и 2): Marketing channels и Social; визиты = визиты за 3 мес × доля; весь мир',
                'period': 'июль–сентябрь 2026', 'date': DATE})
w('traffic_social.csv', SOC)

# Медийная реклама
DSP = [
    {'domain': 'prof-zabory.ru', 'display_visits_3m_channels': round(CV('prof-zabory.ru', 'Display Ads')), 'publisher': 'web.max.ru (единственная площадка)',
     'publisher_category_similarweb': 'Computers_Electronics_and_Technology~Email',
     'impressions_3m': 1214370910, 'spend_usd_model': 118520, 'ad_visits_3m': 167325, 'campaigns': 0, 'creatives': 0,
     'note': 'модельная оценка Similarweb; показы и бюджет несопоставимы с визитами (CTR 0,014%) — как бюджет не использовать',
     'source': 'Similarweb Pro, Display → Advertiser overview (prof-zabory.ru)'},
    {'domain': 'masterovit.ru', 'display_visits_3m_channels': round(CV('masterovit.ru', 'Display Ads')), 'publisher': 'yandex.ru',
     'publisher_category_similarweb': 'Computers_Electronics_and_Technology~Search_Engines',
     'impressions_3m': 150142437, 'spend_usd_model': 15431, 'ad_visits_3m': '', 'campaigns': '', 'creatives': '',
     'note': 'модельная оценка Similarweb', 'source': 'Similarweb Pro, Website performance (masterovit.ru) → Top publishers'},
    {'domain': 'zaborovo.ru', 'display_visits_3m_channels': round(CV('zaborovo.ru', 'Display Ads')), 'publisher': 'ya.ru',
     'publisher_category_similarweb': 'Computers_Electronics_and_Technology~Search_Engines',
     'impressions_3m': 2781998, 'spend_usd_model': 632, 'ad_visits_3m': '', 'campaigns': '', 'creatives': '',
     'note': 'модельная оценка Similarweb', 'source': 'Similarweb Pro, Website performance, сравнение группы 2 → Top publishers'},
    {'domain': 'oblzabor.ru', 'display_visits_3m_channels': round(CV('oblzabor.ru', 'Display Ads')), 'publisher': 'не снято (в сравнении группы 2 видны только ya.ru и yandex.ru)',
     'publisher_category_similarweb': '', 'impressions_3m': '', 'spend_usd_model': '', 'ad_visits_3m': '', 'campaigns': '', 'creatives': '',
     'note': 'Advertiser overview не открыт — дневной лимит', 'source': 'Similarweb Pro, Website performance, сравнение группы 2'},
    {'domain': 'zavodzaborov.ru', 'display_visits_3m_channels': round(CV('zavodzaborov.ru', 'Display Ads')), 'publisher': 'не снято (в сравнении группы 1 видны web.max.ru и yandex.ru)',
     'publisher_category_similarweb': '', 'impressions_3m': '', 'spend_usd_model': '', 'ad_visits_3m': '', 'campaigns': '', 'creatives': '',
     'note': 'Advertiser overview не открыт — дневной лимит', 'source': 'Similarweb Pro, Website performance, сравнение группы 1'},
]
for r in DSP:
    r['note'] += '; площадки yandex.ru / ya.ru — вероятно, Директ и РСЯ; деление с платным поиском уточнится в волне 2; визиты канала = визиты за 3 мес × доля'
    r['region'] = 'весь мир'
    r['period'] = 'июль–сентябрь 2026'
    r['date'] = DATE
w('traffic_display.csv', DSP)
