# Сборка CSV этапа «avito» из обезличенных выгрузок Apify (notes/raw_avito/*.json).
import json, csv, re, sys, os, statistics as st, collections, datetime as dt
sys.path.insert(0, '/home/claude/zabory/notes/scripts/reviews')
from codebook import NEG, POS, themes  # noqa: E402
from redact import redact, PHONE, PATR, FIO, FIO2, NAME_RX, SURN  # noqa: E402


def light_redact(t):
    t = PHONE.sub('[телефон]', t)
    t = PATR.sub('[отчество]', t)
    t = FIO.sub('[ФИО]', t); t = FIO2.sub('[ФИО]', t)
    t = NAME_RX.sub('[имя]', t)
    t = SURN.sub('[фамилия]', t)
    return t

ROOT = '/home/claude/zabory'
RAW = ROOT + '/notes/raw_avito'
DATA = ROOT + '/notes/raw_avito/q4_out'
TODAY = dt.date(2026, 10, 21)
DATE_STR = '2026-10-21'
QUERIES = [
    ('zabor_iz_profnastila_pod_klyuch_mo.json', 'забор из профнастила под ключ', 'Москва и Московская область', 'avito.ru, регион «Москва и МО», запрос «забор из профнастила под ключ»; Apify, датасет AcCqnMVNagcDuaFN3, 21.10.2026'),
]
_UNUSED = [
    ('zabor_pod_klyuch_msk.json', 'забор под ключ', 'Москва', 'avito.ru/moskva, раздел «Предложение услуг», запрос «забор под ключ»; Apify, датасет u51jfJMQysJE7Te4I'),
    ('otkatnye_vorota_msk.json', 'откатные ворота', 'Москва', 'avito.ru/moskva, раздел «Предложение услуг», запрос «откатные ворота»; Apify'),
    ('ustanovka_zabora_mo.json', 'установка забора', 'Московская область', 'avito.ru/moskovskaya_oblast, раздел «Предложение услуг», запрос «установка забора»; Apify'),
]
LABELS = json.load(open(RAW + '/_seller_labels.json'))

# ---------- нормализация (латинские двойники букв -> кириллица) ----------
HOMO = str.maketrans({'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с', 'x': 'х', 'y': 'у', 'k': 'к', 'm': 'м', 'h': 'н', 'b': 'в', 't': 'т', 'u': 'и', 'n': 'п', 'r': 'г'})


def norm(t):
    t = (t or '').lower().replace('ё', 'е').replace('\xa0', ' ')
    # латиницу внутри слов с кириллицей переводим в кириллицу
    def fix(m):
        w = m.group(0)
        return w.translate(HOMO) if re.search('[а-я]', w) else w
    return re.sub(r'[a-zа-я]+', fix, t)


HOMO_UP = str.maketrans({'A': 'А', 'B': 'В', 'C': 'С', 'E': 'Е', 'H': 'Н', 'K': 'К', 'M': 'М', 'O': 'О', 'P': 'Р', 'T': 'Т', 'X': 'Х', 'Y': 'У',
                         'a': 'а', 'c': 'с', 'e': 'е', 'o': 'о', 'p': 'р', 'x': 'х', 'y': 'у', 'k': 'к', 'm': 'м', 'n': 'п', 'u': 'и', 'r': 'г'})


def clean_text(t):
    # слова со смешением алфавитов -> кириллица с сохранением регистра (чистые латинские слова не трогаются)
    def fix(m):
        w = m.group(0)
        return w.translate(HOMO_UP) if (re.search('[А-Яа-яЁё]', w) and re.search('[A-Za-z]', w)) else w
    return re.sub(r'[A-Za-zА-Яа-яЁё]+', fix, t or '')


def mixed_words(t):
    return sum(1 for w in re.findall(r'[A-Za-zА-Яа-яЁё]+', t or '') if re.search('[A-Za-z]', w) and re.search('[А-Яа-яЁё]', w))


# ---------- кодбук обещаний ----------
CLAIMS = collections.OrderedDict([
    ('цена_за_пм', r'(за|/)\s*(п\.?\s?м\b|пог\w*\.?\s*м|погонн\w* метр|метр\b|м\.?\s?п\b|1 ?м\b)|₽\s*/\s*м\b|руб\w*\.?\s*/\s*м\b|за м\.?п|п\.м'),
    ('цена_под_ключ_с_материалом', r'(цен|стоимост)\w*.{0,60}(с материал|материал и (монтаж|работ)|включ)|с материал\w* и (монтаж|установк|работ)|материал\w* \+ монтаж|работ\w* и материал'),
    ('цена_за_работу_отдельно', r'только монтаж|без материал|материал\w* (заказчика|клиента)|из (вашего|материала заказчика)|монтаж отдельно|работ\w* отдельно|цена (указана )?за работу|стоимость работ'),
    ('гарантия', r'гарант'),
    ('замер_бесплатный', r'бесплатн\w*\s+(выезд|замер|расч)|(замер|выезд)\w*(\s+\S+){0,4}?\s*[-—:–]?\s*бесплатн|(выезд|замер)\w* (специалиста |замерщика |мастера )?за 0'),
    ('замер_платный', r'(замер|выезд)\w*( замерщика| специалиста| мастера| на объект)?\s*[-—:–]?\s*(от )?\d[\d ]*\s?(₽|руб)|(?<!бес)платн\w* (замер|выезд)|стоимост\w* (выезда|замера)[^.\n]{0,15}\d|(выезд|замер)\w*[^.\n]{0,20}(?<!бес)платн'),
    ('сроки_монтажа', r'за (1|один|2|два|3|три|1-2|1–2|2-3|2–3|1-3|1–3) (день|дня|дней|рабоч)|за день|в течение (\d+|одного|двух|трех) (дн|раб)|от 1 (дня|дн)|(монтаж|установк\w*) за (\d|один|одн|два|три|день|сутки)|\d+\s*[-–]\s*\d+\s*(дн|рабоч)'),
    ('оплата_после_монтажа', r'без предоплат|оплат\w*[^.\n]{0,30}(после|по факту|по окончан|по завершен)|по факту (выполнен|работ|монтаж)|оплата в конце|после приемки|принимаете[^.\n]{0,40}оплачиваете'),
    ('предоплата', None),  # особая проверка ниже
    ('рассрочка', r'рассрочк|кредит|оплата частями|сплит|долями'),
    ('скидки_подарки', r'скидк|подар|\bакци|бонус|кешб|кэшб|бесплатн\w* (доставк|покраск|демонтаж|калитк|вывоз)|дешевле на|\bза 1 ₽|за 1 руб'),
    ('своё_производство', r'(собственн\w*|сво\w*) (производств|цех|завод|мастерск)|от производител|мы производим|производим|производител|без посредник'),
    ('толщина_металла', r'толщин|\b0[.,][3-9]\d? ?мм|\b[1-3][.,]\d ?мм|\d{2}\s?[xх×*]\s?\d{2}\s?[xх×*]\s?\d[.,]?\d?'),
    ('бригады_опыт', r'бригад|опыт|стаж|лет на рынке|с (19|20)\d\d год|более \d+ лет|(работаем|работаю|на рынке)[^.\n]{0,20}\d+\+? (лет|года)'),
    ('договор_смета', r'договор|смет|фиксир\w*|цена не (меня|измен)|без скрытых|не меняется|не изменится'),
    ('ворота_автоматика', r'ворот|автоматик|привод|калитк'),
])
CLAIMS_RX = {k: re.compile(v) for k, v in CLAIMS.items() if v}


def claims_of(text):
    t = norm(text)
    res = {k: int(bool(rx.search(t))) for k, rx in CLAIMS_RX.items()}
    pre = 0
    for m in re.finditer(r'предоплат|аванс', t):
        if 'без' not in t[max(0, m.start() - 6):m.start()]:
            pre = 1
    res['предоплата'] = pre
    # значения
    yrs = []
    for m in re.finditer(r'гарант[^.\n!]{0,50}?(\d+(?:[.,]\d)?)\s*(год|лет|г\.|мес)', t):
        v = float(m.group(1).replace(',', '.'))
        yrs.append(v if not m.group(2).startswith('мес') else round(v / 12, 2))
    for m in re.finditer(r'(\d+)\s*(год|лет|года)\w*\s*гарант', t):
        yrs.append(float(m.group(1)))
    yrs = [y for y in yrs if 0 < y <= 50]
    thick = sorted(set(m.group(1).replace(',', '.') for m in re.finditer(r'\b(0[.,][3-9]\d?)\s?мм', t)))
    term = re.search(r'(за (1|один|2|два|3|три|1-2|1–2|2-3|2–3|1-3|1–3) (день|дня|дней|рабоч\w* дн\w*))|за день', t)
    pre_pct = re.search(r'предоплат\w*[^.\n]{0,20}?(\d{1,2})\s?%', t)
    res['_guarantee_years_max'] = max(yrs) if yrs else ''
    res['_metal_thickness_mm'] = '; '.join(thick)
    res['_install_term'] = term.group(0) if term else ''
    res['_prepayment_pct'] = pre_pct.group(1) if pre_pct else ''
    return res


# ---------- продукт и единица ----------
PRODUCTS = [
    ('ремонт ворот/автоматики', r'ремонт\w*[^.]{0,30}(ворот|автоматик|привод)|обслуживан\w* (ворот|автоматик)'),
    ('автоматика/привод', r'автоматик|привод'),
    ('откатные ворота', r'откатн'),
    ('распашные ворота', r'распашн'),
    ('жалюзи', r'жалюзи'),
    ('3D-сетка', r'3\s?[dд]\b|3d|3д|сварн\w* сетк|панел\w* сетк'),
    ('евроштакетник', r'штакетн'),
    ('профнастил', r'профнастил|профлист|профлиста'),
    ('рабица', r'рабиц'),
    ('деревянный', r'деревян|из дерева|доск'),
    ('кирпич/бетон', r'кирпич|бетонн\w* забор|еврозабор'),
    ('кованый/сварной', r'ковк|кован|сварн\w* забор'),
    ('навес', r'навес'),
    ('демонтаж/прочее', r'демонтаж|сва[ия]|фундамент'),
]


def product_of(title, desc):
    t = norm(title)
    if re.search(PRODUCTS[0][1], t):
        return PRODUCTS[0][0]
    hits = [(m.start(), name) for name, rx in PRODUCTS[1:] for m in [re.search(rx, t)] if m]
    if hits:
        return min(hits)[1]
    g = re.search(r'ворот', t)
    z = re.search(r'забор|огражд', t)
    if g and (not z or g.start() < z.start()):
        return 'ворота (тип не указан)'
    if z:
        return 'забор (материал не указан)'
    return 'прочее'


GATE_PRODUCTS = {'откатные ворота', 'распашные ворота', 'ворота (тип не указан)', 'автоматика/привод', 'ремонт ворот/автоматики'}


def unit_of(pf, price, product, desc):
    pf = (pf or '').replace('\xa0', ' ')
    if 'за метр' in pf:
        return 'за метр (указано в цене)', 'п.м.'
    if 'за м²' in pf:
        return 'за м² (указано в цене)', 'м²'
    if price and price <= 10:
        return 'цена-заглушка (1–10 ₽)', ''
    if not price:
        return 'цена не указана' if 'договор' not in pf.lower() else 'цена договорная', ''
    if product in GATE_PRODUCTS:
        if price >= 15000:
            return 'не указана; оценка: за изделие/комплект', 'шт.'
        return 'не указана; цена ниже 15 000 ₽ — работа, деталь или приманка (оценка)', ''
    if price <= 10000:
        return 'не указана; оценка: за п.м.', 'п.м.'
    return 'не указана; оценка: за объект или комплект', ''


def member_year(s):
    m = re.search(r'(19|20)\d\d', s or '')
    return int(m.group(0)) if m else ''


def reply_short(s):
    s = (s or '').replace('\xa0', ' ').replace('Отвечает на сообщения ', '').replace('Отвечает ', '')
    return s


COMP_MATCH = {
    'МАСТЕРОВИТ': ('masterovit.ru', 'полный', 'по названию (совпадает с названием компании на сайте)'),
    'Облзабор': ('oblzabor.ru', 'полный', 'по названию; в описании «Компания OBLZABOR»'),
    'Заборкин': ('zaborkin.ru', 'полный', 'только по названию — оценка'),
    'ЗАБОРОВО': ('zaborovo.ru', 'полный', 'только по названию — оценка'),
    'Профзаборы': ('prof-zabory.ru', 'полный', 'только по названию — оценка'),
    'Московские заборы': ('moskovskie-zabory.ru', 'облегчённый', 'только по названию — оценка'),
    'Заборы Престиж': ('zabory-prestige.ru', 'ворота', 'только по названию — оценка'),
}


def med(xs):
    xs = [x for x in xs if x not in (None, '')]
    return st.median(xs) if xs else ''


def w(path, rows, cols):
    with open(path, 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        wr.writeheader()
        for r in rows:
            wr.writerow(r)


# ---------- 1. объявления ----------
listings = []
for fn, q, reg, src in QUERIES:
    items = json.load(open(f'{RAW}/{fn}'))['items']
    for pos, i in enumerate(items, 1):
        lab = LABELS.get(i.get('seller.key'), {'kind': 'unknown', 'label': 'продавец не отдан актором'})
        kind = lab['kind']
        if i.get('userType') is None:
            seller_type = 'не отдано актором'
        elif kind == 'private':
            seller_type = 'частный мастер'
        else:
            seller_type = 'компания'
        price = i.get('price')
        prod = product_of(i.get('title'), i.get('description'))
        unit_note, unit = unit_of(i.get('priceFormatted'), price, prod, i.get('description'))
        posted = i.get('postedAt')
        days = ''
        if posted:
            d0 = dt.datetime.strptime(posted[:10], '%Y-%m-%d').date()
            days = (TODAY - d0).days
        vt = i.get('viewsTotal')
        vday = i.get('viewsToday')
        cm = COMP_MATCH.get(lab['label']) if kind == 'company' else None
        desc = i.get('description') or ''
        listings.append({
            'query': q, 'region': reg, 'position_in_export': pos, 'listing_id': i['id'], 'url': i['url'],
            'title': clean_text(i.get('title')), 'product': prod, 'price_rub': price if price else '',
            'price_text': (i.get('priceFormatted') or '').replace('\xa0', ' '), 'price_unit': unit,
            'price_unit_note': unit_note,
            'seller': lab['label'], 'seller_type': seller_type,
            'avito_account_type': {'shop': 'магазин (shop)', 'company': 'компания (company)', 'person': 'частное лицо (person)'}.get(i.get('seller.sellerType'), 'не отдано'),
            'seller_key': i.get('seller.key'),
            'competitor_domain': cm[0] if cm else '', 'competitor_group': cm[1] if cm else '', 'match_basis': cm[2] if cm else '',
            'seller_active_listings': i.get('seller.listingCount', ''), 'seller_rating': i.get('seller.ratingScore', ''),
            'seller_reviews': i.get('seller.reviewCount', ''),
            'seller_on_avito_since': (i.get('seller.memberSince') or '').replace('На Авито с ', ''),
            'seller_reply_time': reply_short(i.get('seller.replyTime')),
            'documents_verified_flag': {True: 'да', False: 'нет'}.get(i.get('seller.isVerified'), 'не отдано'),
            'promotion_marks': 'актор не отдаёт (XL, выделение, поднятие не видны); снимок 21.10 по стр. 1 «забор под ключ» — data/avito_serp.csv',
            'posted_or_raised_at': posted or '', 'days_since_posted': days,
            'views_total': vt if vt is not None else '', 'views_today': vday if vday is not None else '0 или не отдано',
            'views_per_day_since_posted': round(vt / max(days, 1), 1) if (vt is not None and days != '') else '',
            'address': i.get('address') or '', 'image_count': i.get('imageCount', ''), 'has_video': 'да' if i.get('hasVideo') else 'нет',
            'mixed_script_words': mixed_words(desc + ' ' + (i.get('title') or '')),
            'description': light_redact(clean_text(desc)).replace('\r', ''),
            'source': src, 'date_collected': DATE_STR,
        })
LCOLS = list(listings[0].keys())
w(f'{DATA}/avito_listings.csv', listings, LCOLS)

# ---------- 2. продавцы из выдачи (все) ----------
sellers = collections.OrderedDict()
for L in listings:
    k = L['seller_key']
    s = sellers.setdefault(k, {'seller': L['seller'], 'seller_type': L['seller_type'], 'avito_account_type': L['avito_account_type'],
                               'competitor_domain': L['competitor_domain'], 'competitor_group': L['competitor_group'],
                               'active_listings_in_profile': L['seller_active_listings'], 'rating': L['seller_rating'],
                               'reviews': L['seller_reviews'], 'on_avito_since': L['seller_on_avito_since'],
                               'reply_time': L['seller_reply_time'], '_q': collections.Counter(), '_views': [], '_vday': [],
                               '_prices': collections.defaultdict(list), '_ids': set()})
    s['_q'][L['query']] += 1
    if L['listing_id'] not in s['_ids']:
        s['_ids'].add(L['listing_id'])
        if L['views_total'] != '':
            s['_views'].append(L['views_total'])
        if L['views_per_day_since_posted'] != '':
            s['_vday'].append(L['views_per_day_since_posted'])
        if L['price_rub'] != '' and L['price_unit']:
            s['_prices'][(L['product'], L['price_unit'])].append(L['price_rub'])
srows = []
for k, s in sellers.items():
    r = {kk: vv for kk, vv in s.items() if not kk.startswith('_')}
    r['in_top100_zabor_pod_klyuch_msk'] = s['_q']['забор под ключ']
    r['in_top100_otkatnye_vorota_msk'] = s['_q']['откатные ворота']
    r['in_top100_ustanovka_zabora_mo'] = s['_q']['установка забора']
    r['unique_listings_in_3_queries'] = len(s['_ids'])
    r['median_views_total'] = med(s['_views'])
    r['median_views_per_day'] = med(s['_vday'])
    r['prices_by_product'] = '; '.join(f'{p} {u}: {min(v)}–{max(v)} (n={len(v)})' for (p, u), v in s['_prices'].items())
    r['source'] = 'avito.ru, выдача 3 запросов (по 100 объявлений), поля продавца из карточки объявления; Apify'
    r['date_collected'] = DATE_STR
    srows.append(r)
srows.sort(key=lambda r: (-(r['unique_listings_in_3_queries']), -(r['active_listings_in_profile'] or 0)))
w(f'{DATA}/avito_sellers.csv', srows, list(srows[0].keys()))

# ---------- 3. обещания ----------
claim_keys = list(CLAIMS.keys())
crows = []
seen = set()
for L in listings:
    c = claims_of((L['title'] or '') + '\n' + L['description'])
    r = {'source_type': 'объявление', 'query': L['query'], 'listing_id': L['listing_id'], 'url': L['url'], 'seller': L['seller'],
         'seller_type': L['seller_type'], 'competitor_domain': L['competitor_domain'], 'product': L['product'],
         'duplicate_of_other_query': 'да' if L['listing_id'] in seen else 'нет'}
    seen.add(L['listing_id'])
    r.update({k: c[k] for k in claim_keys})
    r.update({'guarantee_years_max': c['_guarantee_years_max'], 'metal_thickness_mm': c['_metal_thickness_mm'],
              'install_term_phrase': c['_install_term'], 'prepayment_pct': c['_prepayment_pct'],
              'no_claims_found': int(sum(c[k] for k in claim_keys if k != 'ворота_автоматика') == 0),
              'method': 'регулярные выражения по заголовку и полному описанию; латинские буквы-двойники переведены в кириллицу',
              'source': 'avito.ru, текст объявления; Apify', 'date_collected': DATE_STR})
    crows.append(r)
profiles = json.load(open(f'{RAW}/seller_profiles.json'))['items']
for p in profiles:
    if not p.get('about'):
        continue
    c = claims_of(p['about'])
    cm = COMP_MATCH.get(p['name'])
    r = {'source_type': 'о компании (профиль)', 'query': '', 'listing_id': '', 'url': p['profileUrl'], 'seller': p['name'],
         'seller_type': 'компания', 'competitor_domain': cm[0] if cm else '', 'product': '', 'duplicate_of_other_query': ''}
    r.update({k: c[k] for k in claim_keys})
    r.update({'guarantee_years_max': c['_guarantee_years_max'], 'metal_thickness_mm': c['_metal_thickness_mm'],
              'install_term_phrase': c['_install_term'], 'prepayment_pct': c['_prepayment_pct'],
              'no_claims_found': int(sum(c[k] for k in claim_keys if k != 'ворота_автоматика') == 0),
              'method': 'регулярные выражения по тексту «О компании»',
              'source': 'avito.ru, профиль продавца, блок «О компании»; Apify', 'date_collected': DATE_STR})
    crows.append(r)
CCOLS = list(crows[0].keys())
w(f'{DATA}/avito_claims.csv', crows, CCOLS)

# доли
uniq = [r for r in crows if r['source_type'] == 'объявление' and r['duplicate_of_other_query'] == 'нет']
share_rows = []


def add_share(scope, group, rows):
    n = len(rows)
    if not n:
        return
    row = {'scope': scope, 'group': group, 'base_n': n}
    for k in claim_keys + ['no_claims_found']:
        v = sum(r[k] for r in rows)
        row[k] = f'{v} ({round(100 * v / n)}%)'
    gy = [r['guarantee_years_max'] for r in rows if r['guarantee_years_max'] != '']
    row['guarantee_years_median'] = med(gy)
    row['note'] = 'база <30, доля ориентировочная' if n < 30 else ''
    row['date_collected'] = DATE_STR
    share_rows.append(row)


add_share('все уникальные объявления 3 запросов', 'все', uniq)
for t in ('компания', 'частный мастер'):
    add_share('тип продавца', t, [r for r in uniq if r['seller_type'] == t])
for q in ('забор под ключ', 'откатные ворота', 'установка забора'):
    add_share('запрос (все 100 объявлений)', q, [r for r in crows if r['query'] == q])
byc = collections.defaultdict(list)
for r in uniq:
    if r['seller_type'] == 'компания':
        byc[r['seller']].append(r)
for s, rows in sorted(byc.items(), key=lambda x: -len(x[1])):
    if len(rows) >= 3:
        add_share('компания (≥3 уникальных объявлений в 3 запросах)', s, rows)
for r in crows:
    if r['source_type'] == 'о компании (профиль)':
        add_share('блок «О компании»', r['seller'], [r])
w(f'{DATA}/avito_claims_shares.csv', share_rows, list(share_rows[0].keys()))

# ---------- 4. профили ----------
MONTHS = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}


def rdate(s):
    m = re.match(r'(\d{1,2}) (\w+)(?: (\d{4}))?', s or '')
    if not m:
        return ''
    d, mon, y = int(m.group(1)), MONTHS.get(m.group(2)), m.group(3)
    if not mon:
        return ''
    if y:
        return dt.date(int(y), mon, d).isoformat()
    x = dt.date(2026, mon, d)
    if x > TODAY:
        x = dt.date(2025, mon, d)
    return x.isoformat()


rev_rows = []
for p in profiles:
    for r in p.get('reviews') or []:
        sc = r.get('score')
        text = r.get('text') or ''
        neg = themes(text, NEG) if (sc is not None and sc <= 3) else []
        pos = themes(text, POS) if (sc is not None and sc >= 4) else []
        sr = r.get('sellerReply') or {}
        cm = COMP_MATCH.get(p['name'])
        rev_rows.append({'company': p['name'], 'competitor_domain': cm[0] if cm else '', 'review_id': r['id'],
                         'score': sc if sc is not None else 'без оценки',
                         'date_raw': r.get('date'), 'date': rdate(r.get('date')),
                         'deal_stage': r.get('stageTitle') or 'не указано',
                         'listing_title': r.get('itemTitle') or '', 'text': text.replace('\r', ''),
                         'polarity': 'негатив (1–3★)' if (sc is not None and sc <= 3) else ('позитив (4–5★)' if sc is not None else 'без оценки'),
                         'themes_negative': '; '.join(neg), 'themes_positive': '; '.join(pos),
                         'has_seller_reply': 'да' if sr else 'нет', 'seller_reply_text': (sr.get('text') or '').replace('\r', ''),
                         'seller_reply_date_raw': sr.get('date', ''),
                         'method': 'темы — регулярные выражения кодбука notes/scripts/reviews/codebook.py (тот же, что в reviews_themes.csv); имена и телефоны маскированы',
                         'source': p['profileUrl'] + ' (вкладка отзывов; Apify, до 75 последних)', 'date_collected': DATE_STR})
w(f'{DATA}/avito_reviews.csv', rev_rows, list(rev_rows[0].keys()))

# ---------- 5. профили компаний: обновление avito_profiles.csv ----------
old = list(csv.DictReader(open(f'{RAW}/avito_profiles_wave2_snapshot.csv')))  # снимок волны 2 (до обновления)
OLD_COLS = list(old[0].keys())
old_by_domain = {r['domain']: r for r in old}
prof_rows = []
NEW_COLS = ['avito_name', 'profile_url', 'profile_type', 'active_listings', 'closed_listings', 'subscribers', 'rating_now',
            'reviews_now', 'rating_distribution_1_to_5', 'seller_quality_label', 'reply_time', 'on_avito_since_now',
            'profile_address', 'payment_methods', 'delivery', 'categories_first16_active', 'collections_rubrics',
            'about_text', 'listings_in_top100_zabor_pod_klyuch_msk', 'listings_in_top100_otkatnye_vorota_msk',
            'listings_in_top100_ustanovka_zabora_mo', 'median_views_total_in_3_queries', 'median_views_per_day_in_3_queries',
            'prices_in_3_queries', 'prices_first16_active', 'reviews_collected', 'reviews_neg_share', 'seller_reply_share',
            'showcase_note', 'source_profile', 'date_profile']
sel_by_name = {s['seller']: s for s in srows}
for p in profiles:
    cm = COMP_MATCH.get(p['name'])
    dom = cm[0] if cm else ''
    base = dict(old_by_domain.pop(dom, {})) if (dom and dom != 'zabory-prestige.ru') else {}
    if not base:
        base = {c: '' for c in OLD_COLS}
        base['company'] = p['name']
        base['domain'] = dom or 'нет в списке брифа (игрок Авито)'
        base['group'] = cm[1] if cm else 'вне списка брифа'
        base['match_basis'] = cm[2] if cm else 'профиль выбран по числу объявлений в выдаче 3 запросов'
        _o = [r for r in csv.DictReader(open(f'{DATA}/avito_serp.csv')) if r['seller'].strip().lower() == p['name'].strip().lower()]
        base['ads_in_first_page'] = len(_o)
        base['ranks'] = ', '.join(r['rank'] for r in _o)
        base['promoted_ads'] = sum(1 for r in _o if 'Продвинуто' in r['promotion_mark'])
        base['source'] = 'avito.ru, профиль продавца; Apify'
        base['date_collected'] = DATE_STR
    base['ads_total_in_profile'] = p.get('activeListingCount')
    base['on_avito_since'] = (p.get('registrationDate') or '').replace('На Авито с ', '')
    if 'не снято' in (base.get('note') or '') or 'профиль не открывался' in (base.get('note') or ''):
        base['note'] = 'профиль снят 21.10 через Apify (раньше из браузера не открывался)'
    rd = p.get('ratingDistribution') or {}
    revs = p.get('reviews') or []
    sc = [r for r in revs if r.get('score') is not None]
    s = sel_by_name.get(p['name'])
    acts = p.get('activeListings') or []
    sc16 = collections.Counter(a.get('category') for a in acts)
    base.update({
        'avito_name': p['name'], 'profile_url': p['profileUrl'], 'profile_type': p.get('profileType'),
        'active_listings': p.get('activeListingCount'), 'closed_listings': p.get('closedListingCount'),
        'subscribers': p.get('subscribers'), 'rating_now': p.get('ratingScore'), 'reviews_now': p.get('reviewCount'),
        'rating_distribution_1_to_5': ' / '.join(str(rd.get(str(k), 0)) for k in range(1, 6)),
        'seller_quality_label': p.get('sellerQualityLabel') or 'нет',
        'reply_time': (p.get('replyTime') or 'не отдано').replace('\xa0', ' '),
        'on_avito_since_now': base['on_avito_since'],
        'profile_address': p.get('address') or 'не указан',
        'payment_methods': (p.get('payment') or 'не указано').replace('Способы оплаты - ', '').replace('\n', '; '),
        'delivery': (p.get('delivery') or 'не указано').replace('\n', '; '),
        'categories_first16_active': '; '.join(f'{k} — {v}' for k, v in sc16.items()),
        'collections_rubrics': '; '.join(f"{c['title']} — {c['subtitle']}" for c in (p.get('collections') or [])) or 'не заданы',
        'about_text': (p.get('about') or 'не заполнено').replace('\n', ' '),
        'listings_in_top100_zabor_pod_klyuch_msk': s['in_top100_zabor_pod_klyuch_msk'] if s else 0,
        'listings_in_top100_otkatnye_vorota_msk': s['in_top100_otkatnye_vorota_msk'] if s else 0,
        'listings_in_top100_ustanovka_zabora_mo': s['in_top100_ustanovka_zabora_mo'] if s else 0,
        'median_views_total_in_3_queries': s['median_views_total'] if s else '',
        'median_views_per_day_in_3_queries': s['median_views_per_day'] if s else '',
        'prices_in_3_queries': s['prices_by_product'] if s else '',
        'prices_first16_active': '; '.join(f"{a.get('title')} — {(a.get('priceFormatted') or '').replace(chr(160), ' ')}" for a in acts),
        'reviews_collected': len(revs),
        'reviews_neg_share': f"{sum(1 for r in sc if r['score'] <= 3)} из {len(sc)}" if sc else '0',
        'seller_reply_share': f"{sum(1 for r in revs if r.get('sellerReply'))} из {len(revs)}" if revs else '0',
        'showcase_note': ('витрина ' + str(len(p['showcaseItems'])) + ' объявл.; поля просмотров и избранного в витрине = 0 у всех — не используются') if p.get('showcaseItems') else '',
        'source_profile': p['profileUrl'] + ' ; Apify', 'date_profile': DATE_STR,
    })
    prof_rows.append(base)
for dom, r in old_by_domain.items():
    r = dict(r)
    if dom == 'zabory-prestige.ru':
        r['note'] = ('в снимке стр. 1 (волна 2) «Забор Престиж» — по выгрузке 21.10 аккаунт частного лица (userType private, 5,0; 46 отзывов), '
                     'отдельный от аккаунта компании «Заборы Престиж» (строка выше); связь с сайтом zabory-prestige.ru только по названию — оценка')
        r['group'] = 'ворота'
        prof_rows.append(r)
        continue
    r['note'] = (r.get('note') or '') + ' | 21.10: в 300 объявлениях трёх запросов (Apify) ' + (
        'найден по названию: ' + ', '.join(f"{k}" for k, v in COMP_MATCH.items() if v[0] == dom) if any(v[0] == dom for v in COMP_MATCH.values()) else 'по названию не найден; профиль не снимался')
    if any(v[0] == dom for v in COMP_MATCH.values()):
        nm = [k for k, v in COMP_MATCH.items() if v[0] == dom][0]
        s = sel_by_name.get(nm)
        if s:
            r['company'] = r.get('company') or nm
            r['ads_total_in_profile'] = s['active_listings_in_profile']
            r['on_avito_since'] = s['on_avito_since']
            r['listings_in_top100_zabor_pod_klyuch_msk'] = s['in_top100_zabor_pod_klyuch_msk']
            r['listings_in_top100_otkatnye_vorota_msk'] = s['in_top100_otkatnye_vorota_msk']
            r['listings_in_top100_ustanovka_zabora_mo'] = s['in_top100_ustanovka_zabora_mo']
            r['median_views_total_in_3_queries'] = s['median_views_total']
            r['median_views_per_day_in_3_queries'] = s['median_views_per_day']
            r['prices_in_3_queries'] = s['prices_by_product']
            r['rating_now'] = s['rating']
            r['reviews_now'] = s['reviews']
            r['reply_time'] = s['reply_time']
            r['avito_name'] = nm
            r['date_profile'] = DATE_STR + ' (поля продавца из карточки объявления, профиль не снимался)'
    prof_rows.append(r)
# добавить компании брифа, найденные в выдаче, но которых не было в старом файле
have = {r['domain'] for r in prof_rows}
for nm, (dom, grp, basis) in COMP_MATCH.items():
    if dom in have:
        continue
    s = sel_by_name.get(nm)
    if not s:
        continue
    r = {c: '' for c in OLD_COLS + NEW_COLS}
    r.update({'company': nm, 'domain': dom, 'group': grp, 'match_basis': basis, 'ads_in_first_page': 'не было на стр. 1 снимка 21.10',
              'ads_total_in_profile': s['active_listings_in_profile'], 'on_avito_since': s['on_avito_since'],
              'rating': '', 'avito_name': nm, 'rating_now': s['rating'], 'reviews_now': s['reviews'], 'reply_time': s['reply_time'],
              'listings_in_top100_zabor_pod_klyuch_msk': s['in_top100_zabor_pod_klyuch_msk'],
              'listings_in_top100_otkatnye_vorota_msk': s['in_top100_otkatnye_vorota_msk'],
              'listings_in_top100_ustanovka_zabora_mo': s['in_top100_ustanovka_zabora_mo'],
              'median_views_total_in_3_queries': s['median_views_total'], 'median_views_per_day_in_3_queries': s['median_views_per_day'],
              'prices_in_3_queries': s['prices_by_product'],
              'note': 'найден в выдаче 3 запросов 21.10; профиль не снимался (поля продавца из карточки объявления)',
              'source': 'avito.ru, выдача 3 запросов; Apify', 'date_collected': DATE_STR, 'date_profile': DATE_STR})
    prof_rows.append(r)
w(f'{DATA}/avito_profiles.csv', prof_rows, OLD_COLS + NEW_COLS)

# ---------- 6. сравнение с сайтами ----------
SITE_PROD = {'профнастил': 'профнастил', 'евроштакетник': 'евроштакетник', '3D-сетка': '3D', 'рабица': 'рабица', 'жалюзи': 'жалюзи', 'откатные ворота': 'откатные ворота'}
sp = list(csv.DictReader(open(f'{DATA}/sites_prices.csv')))
cmp_rows = []
for nm, (dom, grp, basis) in COMP_MATCH.items():
    ps = collections.defaultdict(list)
    for L in listings:
        if L['seller'] == nm and L['price_rub'] != '':
            ps[L['product']].append((L['price_rub'], L['price_unit'], L['listing_id'], L['price_text']))
    for p in profiles:
        if p['name'] == nm:
            for a in p.get('activeListings') or []:
                if a.get('price'):
                    pr = product_of(a.get('title'), '')
                    u = unit_of(a.get('priceFormatted'), a['price'], pr, '')[1]
                    ps[pr].append((a['price'], u, a['id'], (a.get('priceFormatted') or '').replace('\xa0', ' ')))
    for prod, vals in ps.items():
        uniqv = {v[2]: v for v in vals}.values()
        site = [r for r in sp if r['domain'] == dom and r['product'] == SITE_PROD.get(prod)]
        sprice = float(site[0]['price_from_rub']) if site and site[0]['price_from_rub'] else ''
        sunit = site[0]['unit'] if site else ''
        prices = sorted(v[0] for v in uniqv)
        units = sorted(set(v[1] or 'не определена' for v in uniqv))
        mn = prices[0]
        diff = round(100 * (mn - sprice) / sprice) if sprice else ''
        cmp_rows.append({'company': nm, 'domain': dom, 'group': grp, 'match_basis': basis, 'product': prod,
                         'avito_n_listings': len(prices), 'avito_price_min_rub': mn, 'avito_price_median_rub': med(prices),
                         'avito_price_max_rub': prices[-1], 'avito_unit': '; '.join(units),
                         'avito_price_texts': '; '.join(sorted(set(v[3] for v in uniqv)))[:300],
                         'site_price_from_rub': sprice, 'site_unit': sunit,
                         'avito_min_vs_site_pct': diff,
                         'comparable': 'да' if (sprice and sunit == 'за п.м.' and 'п.м.' in units) or (sprice and sunit == 'за шт.' and 'шт.' in units) else 'нет или оценка',
                         'source_avito': 'объявления в 3 запросах + первые 16 активных объявлений профиля (если снят); Apify',
                         'source_site': 'data/sites_prices.csv (съём 20.10.2026)' if site else 'на сайте цены по продукту нет в sites_prices.csv',
                         'date_collected': DATE_STR})
w(f'{DATA}/avito_vs_sites.csv', cmp_rows, list(cmp_rows[0].keys()))
print('listings', len(listings), 'sellers', len(srows), 'claims', len(crows), 'shares', len(share_rows), 'reviews', len(rev_rows), 'profiles', len(prof_rows), 'cmp', len(cmp_rows))
