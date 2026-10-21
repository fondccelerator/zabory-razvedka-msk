# Сборка CSV этапа ads_social из сырых данных (Авито — notes/raw_ads, Карты/2ГИС/Услуги — scratchpad raw)
import csv, re, sys, os, statistics
ROOT = '/home/claude/zabory'
RAW = sys.argv[1]
D = '2026-10-21'
COMP = {'masterovit': 'masterovit.ru', 'prof-zabory': 'prof-zabory.ru', 'zaborkin': 'zaborkin.ru', 'zavodzaborov': 'zavodzaborov.ru',
        'zabor-dlya-vseh': 'zavodzaborov.ru', 'raduga-zaborov': 'raduga-zaborov.ru', 'zaborovo': 'zaborovo.ru', 'p-z-z': 'zaborovo.ru',
        'oblzabor': 'oblzabor.ru', 'dostup-zabor': 'dostup-zabor.ru', 'zaboroff': 'zaboroff.ru', 'pskzabor': 'pskzabor.ru',
        'zabormo': 'zabormo.ru', 'pro-zabor': 'pro-zabor.ru', 'kupitzabor': 'moscow.kupitzabor.ru', '33zabora': '33zabora.ru',
        'zabor-vam': 'zabor-vam.ru', 'good-zabor': 'good-zabor.ru', 'moskovskie-zabory': 'moskovskie-zabory.ru', 'ligazaborov': 'ligazaborov.ru',
        'zabory-deshevo': 'zabory-deshevo.ru', 'gorodzaborov': 'gorodzaborov.ru', 'alusys': 'alusys.ru', 'vorota750': 'vorota750.ru',
        'naves-pod-avto': 'naves-pod-avto-msk.ru', 'otkatnie-vorota.com': 'otkatnie-vorota.com', 'gruppa-masterov': 'gruppa-masterov.ru',
        'metalsystems': 'metalsystems.ru', 'zabory-prestige': 'zabory-prestige.ru', 'atlantzabor': 'atlantzabor.ru'}
FULL = {'masterovit.ru', 'prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru', 'zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru'}
GATES = {'alusys.ru', 'vorota750.ru', 'naves-pod-avto-msk.ru', 'otkatnie-vorota.com', 'gruppa-masterov.ru', 'metalsystems.ru', 'zabory-prestige.ru', 'atlantzabor.ru'}
def comp_of(site):
    s = (site or '').lower()
    for k, v in COMP.items():
        if k in s: return v
    return ''
def group_of(dom):
    if not dom: return ''
    return 'полный' if dom in FULL else ('ворота' if dom in GATES else 'облегчённый')
def write(path, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(path, len(rows))

# ---------- Авито: выдача ----------
FLAGS = {'дг': 'договор', 'бз': 'бесплатный замер/выезд', 'оп': 'оплата после монтажа / без предоплаты', 'пр': 'своё производство',
         'рс': 'рассрочка', 'ск': 'скидка', '1д': 'монтаж за 1–2 дня', 'бп': 'без посредников', 'ав': 'автоматика/привод'}
BADGES = {'Н': 'Надёжный исполнитель', 'Р': 'Реквизиты проверены', 'Д': 'Документы проверены', 'Я': 'яПомогаю', 'П': 'Есть портфолио'}
AV_COMP = {'МАСТЕРОВИТ': ('masterovit.ru', 'по названию и цене 3D-сетки 1 658 ₽, совпадающей с /price/ сайта'),
           'Облзабор': ('oblzabor.ru', 'по названию; в описании «Компания Oblzabor»'),
           'Профзаборы': ('prof-zabory.ru', 'только по названию — оценка, не подтверждено'),
           'Купить забор': ('moscow.kupitzabor.ru', 'только по названию — оценка, не подтверждено'),
           'Забор Престиж': ('zabory-prestige.ru', 'только по названию — оценка, не подтверждено')}
def decode_flags(f):
    out = []
    for x in [x for x in f.split(',') if x]:
        m = re.match(r'г(\d+[,.]?\d*)([лгм])', x)
        if m: out.append('гарантия %s %s' % (m.group(1), {'л': 'г.', 'г': 'г.', 'м': 'мес.'}[m.group(2).lower()]))
        elif x == 'г': out.append('гарантия (срок не указан в фрагменте)')
        else: out.append(FLAGS.get(x, x))
    return '; '.join(out)
def decode_badges(b):
    parts = []; rest = b
    extra = [x for x in re.split(r',', b) if len(x) > 1 and not set(x) <= set(BADGES)]
    letters = b.split(',')[0] if b else ''
    for ch in letters:
        if ch in BADGES: parts.append(BADGES[ch])
    for x in b.split(','):
        x = x.strip()
        if x and not set(x) <= set(BADGES): parts.append(x)
    return '; '.join(dict.fromkeys(parts))
def price_num(p):
    m = re.search(r'(\d[\d\s]*)\s*₽', p.replace(' ', ' '))
    return int(re.sub(r'\D', '', m.group(1))) if m else ''
def price_unit(p):
    if '/м' in p and 'м²' not in p: return 'за метр (указано)'
    if 'м²' in p: return 'за м² (указано)'
    if 'договор' in p.lower(): return 'договорная'
    return 'единица не указана в карточке'
rows = []
q = page = total = None
for line in open(f'{ROOT}/notes/raw_ads/avito_serp_raw.txt', encoding='utf-8'):
    line = line.rstrip('\n')
    if line.startswith('## '):
        m = re.match(r'## Q=(.*?); P=(\d+); всего объявлений (.*)', line); q, page, total = m.group(1), int(m.group(2)), m.group(3)
        continue
    if not line or line.startswith('#'): continue
    p = line.split(';')
    rank, title, price, seller, rating, revs, badges, promo, flags, height = p[:10]
    bl = decode_badges(badges)
    if seller == 'частный мастер': stype = 'частный мастер (имя не сохраняется)'
    elif not seller: stype = 'продавец не показан в карточке'
    elif 'Реквизиты проверены' in bl: stype = 'компания или ИП (значок «Реквизиты проверены»)'
    else: stype = 'бренд-название без проверенных реквизитов (оценка: компания или частный мастер)'
    dom, why = AV_COMP.get(seller, ('', ''))
    rows.append(dict(query=q, region='Москва и Московская область', page=page, total_ads_in_search=total, rank=int(rank),
                     title=title, price_text=price, price_from_rub=price_num(price), price_unit=price_unit(price),
                     seller=seller or 'не указан', seller_type=stype, rating=rating, reviews=revs,
                     badges=bl, reliable_partner='да' if 'Надёжный исполнитель' in bl else 'нет',
                     promotion_mark='«Продвинуто» (платное продвижение)' if promo == '1' else 'нет пометки',
                     xl_or_highlight='не определяется по карточке: размеры карточек 236–342 px различаются из-за блока прайса',
                     key_promises=decode_flags(flags) or 'в видимом фрагменте описания не найдено',
                     competitor=dom, competitor_match=why, card_height_px=height,
                     source=f'avito.ru/moskva_i_mo/predlozheniya_uslug?q={q}' + (f'&p={page}' if page > 1 else ''),
                     date_collected=D))
for qq, reason in [('забор под ключ', 'страница 2: после перехода браузер ответил «This site is blocked by your site permissions» (настройки разрешений расширения), съём остановлен'),
                   ('установка забора', 'страницы 1–2 не сняты: avito.ru заблокирован в настройках разрешений браузера; из облака — HTTP 429 «Доступ ограничен: проблема с IP» с кнопкой капчи, капча не проходилась'),
                   ('откатные ворота', 'страницы 1–2 не сняты: те же причины, что у «установка забора»')]:
    rows.append(dict({k: '' for k in rows[0]}, query=qq, region='Москва и Московская область', page='2' if qq == 'забор под ключ' else '1–2',
                     title='не снято', key_promises=reason, source='avito.ru', date_collected=D))
write(f'{ROOT}/data/avito_serp.csv', rows)
av = [r for r in rows if r['title'] != 'не снято']

# ---------- Авито: профили ----------
prof = []
for seller, (dom, why) in AV_COMP.items():
    rs = [r for r in av if r['seller'] == seller]
    prices = [r['price_from_rub'] for r in rs if r['price_from_rub'] != '']
    prof.append(dict(company=seller, domain=dom, group=group_of(dom), match_basis=why,
                     ads_in_first_page=len(rs), ranks=', '.join(str(r['rank']) for r in rs),
                     rating=rs[0]['rating'] if rs else '', reviews=rs[0]['reviews'] if rs else '',
                     badges=rs[0]['badges'] if rs else '', promoted_ads=sum(1 for r in rs if r['promotion_mark'].startswith('«')),
                     titles_examples=' | '.join(dict.fromkeys(r['title'] for r in rs)),
                     prices_in_serp_rub=', '.join(str(p) for p in prices),
                     ads_total_in_profile='не снято', on_avito_since='не снято',
                     note='профиль не открывался: avito.ru заблокирован в настройках разрешений браузера после 1-й страницы выдачи; из облака — капча (HTTP 429)',
                     source='avito.ru, выдача «забор под ключ», стр. 1', date_collected=D))
for dom in sorted(FULL - {v[0] for v in AV_COMP.values()}):
    prof.append(dict({k: '' for k in prof[0]}, domain=dom, group='полный', company='',
                     ads_in_first_page=0, ads_total_in_profile='не снято', on_avito_since='не снято',
                     note='в первых 50 объявлениях «забор под ключ» не найден; поиск профиля по названию не выполнен (avito.ru заблокирован в браузере, из облака капча)',
                     source='avito.ru, выдача «забор под ключ», стр. 1', date_collected=D))
write(f'{ROOT}/data/avito_profiles.csv', prof)

# ---------- Карты: Яндекс + 2ГИС ----------
# надзиратель 21.10.2026: рекламодатель-физлицо (ФИО без ИП/ООО) — ФИО и ИНН не сохраняются
def mask_person(name, inn):
    if name and not re.search(r'ООО|ИП|АО|ЗАО|ПАО|ОАО|ОБЩЕСТВО|Индивидуальный|АКЦИОНЕРН|[A-Z]{3}', name):
        return 'физлицо (ФИО и ИНН не сохраняются)', ''
    return name, inn
maps = []
BANNERS = ('ЦПЛ', 'Платформа', 'Флаувау')
for r in csv.DictReader(open(f'{RAW}/ymaps_rows.csv', encoding='utf-8')):
    dom = comp_of(r['site'])
    maps.append(dict(source='Яндекс Карты', query=r['query'], region='Москва', page='список (25 + подгрузка прокруткой)', rank=r['rank'],
                     company=r['company'], site=r['site'], competitor=dom, competitor_group=group_of(dom), address=r['address'],
                     rating=round(float(r['rating']), 1) if r['rating'] else '', ratings_count=r['ratings_count'],
                     ad_mark='рекламное размещение (в данных карточки — блок advert с маркировкой ОРД)' if r['ad_label'] else 'нет',
                     priority_placement=r['priority_placement'], geo_direct=r['is_direct'], highlighted=r['highlighted'],
                     advertiser_legal=mask_person(r['advertiser'], r['advertiser_inn'])[0], advertiser_inn=mask_person(r['advertiser'], r['advertiser_inn'])[1],
                     ad_text=r['ad_title'] or r['ad_text'], ad_products_prices=r['ad_products'], cta=r['ad_buttons'],
                     promo_action=r['promo_action'].replace('\n', ' '), has_stories=r['has_stories'],
                     source_url=r['source_url'], date_collected=D))
for r in csv.DictReader(open(f'{RAW}/gis2_rows.csv', encoding='utf-8')):
    is_banner = any(b in r['advertiser_legal'] for b in BANNERS)
    maps.append(dict(source='2ГИС', query=r['query'], region='Москва', page=r['page'], rank=r['rank'],
                     company=r['company'], site='', competitor='', competitor_group='', address='',
                     rating=r['rating'], ratings_count=r['ratings_count'],
                     ad_mark=('баннер площадки между карточками (не относится к организации)' if is_banner else ('рекламная карточка (пометка «Реклама»)' if r['ad_label'] else 'нет')),
                     priority_placement='', geo_direct='', highlighted='',
                     advertiser_legal=r['advertiser_legal'], advertiser_inn='',
                     ad_text=r['ad_text'], ad_products_prices='', cta=r['cta'], promo_action='', has_stories='',
                     source_url=r['source_url'], date_collected=D))
write(f'{ROOT}/data/ads_maps.csv', maps)

# ---------- Платформы: Яндекс Услуги + Профи ----------
pl = []
for r in csv.DictReader(open(f'{RAW}/uslugi_rows.csv', encoding='utf-8')):
    dom = comp_of(r['domain'] or r['site'] or r['name'])
    if r['block'] == 'исполнитель':
        kind = 'исполнитель (выдача Услуг)'
        name = r['name']
    else:
        kind = 'объявление Яндекс Директа на странице Услуг' + (' (блок «гарантия»)' if r['block'] == 'direct-guarantee' else '')
        name = r['name']
        if re.match(r'^[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+$', name):  # ФИО рекламодателя-ИП
            name = 'ИП ' + name
    pl.append(dict(platform='Яндекс Услуги', query=r['query'], region='Москва', page=r['page'], position=r['position'], block=kind,
                   name=name, inn=r['inn'], competitor=dom, competitor_group=group_of(dom), account_type={'person': 'частное лицо', 'org': 'организация'}.get(r['account_type'], r['account_type']),
                   promoted='да (продвижение в Услугах)' if r['advertised'] == 'да' else ('нет' if r['block'] == 'исполнитель' else 'реклама Директа'),
                   rating=r['rating'] if r['rating'] not in ('0', '') else ('нет рейтинга в профиле' if r['block'] == 'исполнитель' else ''),
                   reviews=r['reviews'], finished_orders=r['finished_orders'],
                   ad_title=r['title'], ad_text=r['text'] if r['block'] != 'исполнитель' or r['account_type'] != 'person' else '',
                   ad_domain=r['domain'], callouts=r['callouts'], price_from=r['price_from'], site=r['site'],
                   source_url=r['url'], date_collected=D))
pl.append(dict({k: '' for k in pl[0]}, platform='Профи.ру', query='заборы (раздел /remont/zabory/)', region='Москва',
               block='не снято', name='', promoted='', ad_text='из облака HTTP 418 «Не смогли открыть страницу. Возможно, у вас включён VPN» (curl и Playwright); браузер пользователя недоступен (расширение отключилось)',
               source_url='https://profi.ru/remont/zabory/', date_collected=D))
write(f'{ROOT}/data/ads_platforms.csv', pl)

# ---------- 2ГИС: поиск по названиям конкурентов (дописывается к ads_maps.csv) ----------
names = [
    ('заборкин', 'Заборкин', 'zaborkin.ru', '5', '190', 'нет', 'карточка «Компания», Москва'),
    ('заборово', 'Заборово', 'zaborovo.ru', '5', '23', 'нет', 'Пушкино, ул. Тургенева, 15а'),
    ('заборофф', 'Zaboroff', 'zaboroff.ru', '4.8', '12', 'нет', '2 филиала (ул. Яблочкова, 21 к3; Марксистская, 22 ст1)'),
    ('завод заборов', 'ЗаводЗаборов.ру', 'zavodzaborov.ru', '4.6', '73', 'нет', '5 филиалов; лучшая карточка — Ленинградский пр., 63 (4.6, 73 оценки); Люберцы 4.5, 21 оценка'),
    ('пск забор', 'ПСК Забор', 'pskzabor.ru', '4.8', '32', 'нет', '13 филиалов; карточки на рынках и в ТК (МКАД 25 км; Новорижское ш.; Каширский двор)'),
    ('радуга заборов', 'Радуга заборов', 'raduga-zaborov.ru', '2.6', '5', 'нет', 'Выборгская ул., 16 ст1'),
    ('облзабор', '', 'oblzabor.ru', '', '', '', 'карточка компании не найдена (выдача — «Облако», «Облака»)'),
    ('мастеровит', '', 'masterovit.ru', '', '', '', 'не снято: «upstream request failed» (сбой загрузки 2ГИС из облака)'),
    ('проф-заборы', '', 'prof-zabory.ru', '', '', '', 'не снято: «upstream request failed»'),
    ('доступные заборы', '', 'dostup-zabor.ru', '', '', '', 'не снято: «upstream request failed»'),
]
extra = []
for q, comp, dom, rt, cnt, adm, note in names:
    extra.append(dict({k: '' for k in maps[0]}, source='2ГИС (поиск по названию)', query=q, region='Москва', page='1', rank='',
                      company=comp, competitor=dom, competitor_group=group_of(dom), address=note, rating=rt, ratings_count=cnt,
                      ad_mark=('нет пометки «Реклама» на карточке' if adm == 'нет' else ''),
                      source_url='https://2gis.ru/moscow/search/' + q, date_collected=D))
write(f'{ROOT}/data/ads_maps.csv', maps + extra)

# ---------- ВКонтакте: что снято в волне 2 ----------
vk = [
    dict(company='10 компаний полного разбора и облегчённые', platform='SeedHunter (seed.targethunter.ru) → Библиотека рекламы / Маркет-платформа',
         date='', format='посевы маркет-платформы ВК', offer_text='', price_or_gift='', cta='', destination='', reach_views='', likes='', erid='', link='',
         status='не снято в волне 2',
         reason='в браузере пользователя расширение перестало пускать сайты («This site is blocked by your site permissions»), затем отключилось («Browser extension is not connected»); из облака SeedHunter без входа открывает только лендинг (seed.targethunter.ru/landing); вход не выполнялся',
         prior_data='data/vk_ads.csv (волна 1): посев Заборово 16.10, 2 посева местной компании, итог поиска по 7 ключам за 23.09–19.10',
         source='seed.targethunter.ru', date_collected=D),
    dict(company='10 компаний полного разбора', platform='поиск ВК по записям (vk.ru/search/statuses) по доменам masterovit.ru, zaborovo.ru и др.',
         date='', format='посты-реклама в городских пабликах', offer_text='', price_or_gift='', cta='', destination='', reach_views='', likes='', erid='', link='',
         status='не снято',
         reason='из облака (Playwright, без входа) страница поиска остаётся пустой «Загружается…» с кнопками «Войти / Регистрация»: поиск по записям требует входа; curl получает vk.com/badbrowser.php; браузер пользователя недоступен',
         prior_data='', source='vk.ru/search/statuses?q=zaborovo.ru', date_collected=D),
    dict(company='10 компаний полного разбора', platform='стены сообществ, записи с пометкой «Реклама» за 20.07–20.10.2026',
         date='', format='промопосты', offer_text='', price_or_gift='', cta='', destination='', reach_views='', likes='', erid='', link='',
         status='снято в волне 1, повторно не дублировалось',
         reason='в волне 1 стены всех 10 просмотрены за 3 месяца: пометка «Реклама» — только у Мастеровита (6 постов 31.08–19.10); у Про-Забора (облегчённый) — 1 видеопост 08.10; новых дней после съёма 20.10 — один',
         prior_data='data/vk_ads.csv, data/social_vk.csv', source='vk.ru, стены сообществ', date_collected=D),
    dict(company='все', platform='VK Реклама (таргет без поста на стене)', date='', format='таргетированная реклама', offer_text='', price_or_gift='', cta='', destination='',
         reach_views='', likes='', erid='', link='', status='снаружи не наблюдается',
         reason='публичной библиотеки объявлений VK Рекламы нет; объявления без публикации на стене снаружи не видны',
         prior_data='', source='—', date_collected=D),
]
write(f'{ROOT}/data/ads_vk.csv', vk)

# ---------- Telegram и MAX ----------
tg = [
    dict(platform='TGStat — поиск по публикациям (tgstat.ru/search)', what='посевы и упоминания конкурентов в каналах МО', status='не снято',
         reason='открывается описание тарифов: бесплатный тариф — 20 последних постов за 7 дней и только после входа; вход не выполнялся', source='https://tgstat.ru/search?q=забор', date_collected=D),
    dict(platform='Telemetr (telemetr.me)', what='поиск каналов и постов', status='не снято',
         reason='главная открывается (HTTP 200), страница поиска каналов по адресу /channels/?search= — 404; поиск постов требует входа', source='https://telemetr.me/', date_collected=D),
    dict(platform='Telegram Ads', what='официальные объявления в каналах', status='снаружи не наблюдается',
         reason='публичной библиотеки объявлений нет', source='—', date_collected=D),
    dict(platform='MAX', what='рекламные посты и посевы', status='не снято',
         reason='поиска по публикациям без входа нет; в волне 1 каналы MAX с контентом найдены только у Мастеровита и Про-Забора (data/social_other.csv)', source='max.ru', date_collected=D),
]
write(f'{ROOT}/data/ads_telegram.csv', tg)
