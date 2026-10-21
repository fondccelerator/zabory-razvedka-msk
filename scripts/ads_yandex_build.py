# Сборка data/ads_yandex.csv и data/ad_budgets.csv из сырья notes/raw_ads (этап ads_yandex, 21.10.2026)
import csv, re, os

RAW = '/home/claude/zabory/notes/raw_ads'
OUT = '/home/claude/zabory/data'
DATE = '21.10.2026'

COLS = ['domain', 'source', 'ad_type', 'query', 'headline', 'headline2', 'text', 'sitelinks', 'display_url',
        'extensions', 'first_seen', 'last_seen', 'days_active', 'inn_erid', 'cpc_forecast', 'position',
        'screenshot', 'source_url', 'date', 'campaign_utm', 'queries_per_ad', 'shown_region', 'creative', 'note']
rows = []


def split_head(h):
    # Заголовок 2 отделяется только явным разделителем « | » (так его отдаёт Keys.so у zaborovo.ru)
    if ' | ' in h:
        a, b = h.split(' | ', 1)
        return a.strip(), b.strip()
    return h.strip(), ''


def url_camp(s):
    s = s.replace('Ссылка: ', '').replace('URL: ', '').strip()
    m = re.match(r'(\S+)(?:\s+camp=(\S+))?(?:\s+site=(\S+))?', s)
    return (m.group(1), m.group(2) or '', m.group(3) or '') if m else (s, '', '')


def keys_search(domain, lines, src_url):
    for ln in lines:
        p = [x.strip() for x in ln.split('||')]
        if len(p) == 5:  # объявление без текста (только заголовок и быстрые ссылки)
            p = [p[0], ''] + p[1:]
        if len(p) < 6:
            continue
        h1, h2 = split_head(p[0])
        url, camp, _ = url_camp(p[3])
        rows.append(dict(domain=domain, source='Keys.so, «Объявления в Яндекс Директе» (база Москва, демо: 10 строк)',
                         ad_type='поиск', headline=h1, headline2=h2, text=p[1], sitelinks=p[2], display_url=url,
                         last_seen=p[5], queries_per_ad=p[4], campaign_utm=camp, source_url=src_url, date=DATE,
                         note='last_seen = поле «Обновлено»; дата первого показа в демо не видна'))


def keys_rsya(domain, lines, src_url):
    for ln in lines:
        p = [x.strip() for x in ln.split('||')]
        if len(p) < 6:
            continue
        ad = [x.strip() for x in p[0].split(' / ')]
        url_part = ad[-1] if ad and ('http' in ad[-1]) else ''
        url, camp, site = url_camp(url_part)
        h1 = ad[0] if ad else ''
        rest = [x for x in ad[1:] if x != url_part]
        h2 = rest[0] if len(rest) == 2 else ''
        text = rest[-1] if rest else ''
        if len(p) == 8:
            adv, typ, reg, days, fs, ls, size = p[1:8]
        else:  # строка без данных рекламодателя
            adv = ''
            typ, reg, days, fs, ls, size = (p[1:7] + [''] * 6)[:6]
        rows.append(dict(domain=domain, source='Keys.so, «Объявления в РСЯ» (демо: 10 последних по дате обнаружения; повторы опущены)',
                         ad_type='РСЯ', headline=h1, headline2=h2, text=text, display_url=url, first_seen=fs,
                         last_seen=ls, days_active=days, inn_erid=adv, campaign_utm=camp, shown_region=reg,
                         creative=f'{typ}; {size}', source_url=src_url, date=DATE,
                         note=('площадка показа: ' + site + '; ' if site else '') +
                              'регион показа — где сервис зафиксировал объявление; в URL у masterovit.ru стоит region=213 (Москва)'))


def spy(domain, lines, src_url):
    for ln in lines:
        p = ln.split('|')
        if p[0] == 'Q' and len(p) >= 11:
            txt = p[3]
            ext = ''
            if ' · ' in txt:
                txt, ext = txt.split(' · ', 1)
            rows.append(dict(domain=domain, source='Spywords, «Анализ домена» → «Запросы домена в Яндекс.Директ» (Москва, превью 5 строк)',
                             ad_type='поиск', query=p[1], headline=p[2], text=txt.strip(), extensions=ext.strip(),
                             display_url=p[4], position=p[5], cpc_forecast=p[9] + ' ₽ (средний CPC Spywords)',
                             source_url=src_url, date=DATE,
                             note=f'частотность точная/базовая/общая: {p[6]}/{p[7]}/{p[8]}; конкурентов по запросу {p[10]}; позиция: СР — спецразмещение, Д — динамические показы, число — позиция в блоке'))
        elif p[0] == 'A' and len(p) >= 5:
            txt = p[2]
            ext = ''
            if ' · ' in txt:
                txt, ext = txt.split(' · ', 1)
            rows.append(dict(domain=domain, source='Spywords, «Уникальные объявления в Яндекс.Директ» (Москва, превью 5 строк)',
                             ad_type='поиск', headline=p[1], text=txt.strip(), extensions=ext.strip(), display_url=p[3],
                             queries_per_ad=p[4], source_url=src_url, date=DATE))


def sections(path):
    sec, cur = {}, None
    for ln in open(path, encoding='utf-8'):
        ln = ln.rstrip('\n')
        if ln.startswith('# '):
            cur = ln.split()[1]
            sec[cur] = []
        elif cur and ln and '||' in ln:
            sec[cur].append(ln)
    return sec


def body(path):
    return [l.rstrip('\n') for l in open(path, encoding='utf-8') if '||' in l]

# Keys.so — отдельные файлы
keys_search('masterovit.ru', body(f'{RAW}/keys_masterovit.ru_ads.txt'), 'https://www.keys.so/ru/ads?domain=masterovit.ru&db=msk')
keys_rsya('masterovit.ru', [l for l in body(f'{RAW}/keys_masterovit.ru_rsya.txt') if not l.startswith('HDR')], 'https://www.keys.so/ru/rsya/ads?domain=masterovit.ru')
keys_search('sales.prof-zabory.ru', [l for l in body(f'{RAW}/keys_sales.prof-zabory.ru_ads.txt') if not l.startswith('HDR')], 'https://www.keys.so/ru/ads?domain=sales.prof-zabory.ru&db=msk')
keys_rsya('sales.prof-zabory.ru', body(f'{RAW}/keys_sales.prof-zabory.ru_rsya.txt'), 'https://www.keys.so/ru/rsya/ads?domain=sales.prof-zabory.ru')
for d in ['zavodzaborov.ru', 'zaborovo.ru']:
    s = sections(f'{RAW}/keys_{d}.txt')
    keys_search(d, s.get('ads', []), f'https://www.keys.so/ru/ads?domain={d}&db=msk')
    keys_rsya(d, s.get('rsya', []), f'https://www.keys.so/ru/rsya/ads?domain={d}')

# prof-zabory.ru: поисковые объявления только из сводки отчёта (без URL и дат)
for h, t, n in [
    ('Горизонтальные заборы из евроштакетника - цена горизонтального забора из металлического штакетника с установкой под ключ в Москве и области',
     'Заборы из горизонтального штакетника Доставка по Москве и области. Горизонтальный забор из металлического штакетника имеет необычный вид — необычнее, чем аналог с вертикальными штакетинами!', '7'),
    ('Заборы из металлического штакетника. Установка под ключ',
     'Заборы из горизонтального штакетника Доставка по Москве и области. Горизонтальный забор из металлического штакетника имеет необычный вид — необычнее, чем аналог с вертикальными штакетинами!', '1')]:
    rows.append(dict(domain='prof-zabory.ru', source='Keys.so, отчёт по домену, блок «Объявления» (база Москва)', ad_type='поиск',
                     headline=h, text=t, queries_per_ad=n, source_url='https://www.keys.so/ru/report?domain=prof-zabory.ru&db=msk', date=DATE,
                     note='заголовок совпадает с title страницы — вероятно, динамические объявления (оценка)'))
# prof-zabory.ru РСЯ (архив 2023–2025)
for h, t, typ, reg, days, fs in [
    ('Забор секционный из панелей «3D» «под ключ». 1 425 ₽', 'Цена за пог. м. Высота от 1,53 до 2,03 метров. 3 цвета.', 'Директ', 'Москва', '10', '13.01.23'),
    ('Забор «жалюзи» из ламелей «под ключ». 4 400 ₽', 'Цена за пог. м. Высота от 1,5 до 2,5 метров. 15 цветов и 5 текстур. 2 формы.', 'Директ', 'Москва', '0', '15.01.23'),
    ('Забор из металлического штакетника «под ключ». 1 399 ₽', 'Цена за пог. м. Высота от 1,0 до 2.5-х метров. 15 цветов. 4 формы. Зазор 0-10 см', 'Директ', 'Екатеринбург', '0', '05.05.23'),
    ('Забор из сетки - рабицы “Стандарт”', 'Купить на prof-zabory.ru', 'Директ', 'Ростов-на-Дону', '6', '04.06.25')]:
    rows.append(dict(domain='prof-zabory.ru', source='Keys.so, «Объявления в РСЯ» (10 из 10)', ad_type='РСЯ', headline=h, text=t,
                     first_seen=fs, days_active=days, shown_region=reg, creative=typ + '; адаптив',
                     inn_erid='ИП Коротков К. А., ИНН 112103967667, ЕРИР #7010286' if fs.endswith('25') else '',
                     source_url='https://www.keys.so/ru/rsya/ads?domain=prof-zabory.ru', date=DATE,
                     note='архивное объявление; с 2025 г. РСЯ идёт на sales.prof-zabory.ru'))

# Spywords
for d in ['masterovit.ru', 'prof-zabory.ru', 'sales.prof-zabory.ru']:
    spy(d, open(f'{RAW}/spy_{d}.txt', encoding='utf-8').read().splitlines(), f'https://spywords.ru/sword.php?sword={d}&region=msk')

# скриншоты (если сняты)
shots = set(os.listdir('/home/claude/zabory/img/ads')) if os.path.isdir('/home/claude/zabory/img/ads') else set()
for r in rows:
    r.setdefault('screenshot', '')
    for k in COLS:
        r.setdefault(k, '')

with open(f'{OUT}/ads_yandex.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(rows)
print('ads rows', len(rows))

# ---------- бюджеты ----------
B = ['domain', 'source', 'ads_count', 'queries_count', 'queries_per_ad', 'budget_day', 'budget_month', 'traffic_from_ads',
     'traffic_period', 'cpc_calc', 'rsya_ads_count', 'orders_month_est', 'cost_per_order_est', 'source_url', 'date', 'note']
b = []
def add(**k):
    for c in B:
        k.setdefault(c, '')
    k['date'] = DATE
    b.append(k)

KEYS_NOTE = 'Keys.so не подписывает период «прогноза бюджета» и «трафика контекст» в сводке; сравнивать между доменами, в рубли месяца не переводить (оценка)'
for d, ads, q, qa, bud, tr, rsya in [
    ('masterovit.ru', 1039, 5739, 6, 1972900, 72, 2295),
    ('prof-zabory.ru', 18, 27, 2, 959, 0, 10),
    ('zavodzaborov.ru', 395, 1517, 4, 1080872, 18, 835),
    ('zaborovo.ru', 853, 2060, 2, 1331670, 15, 1339)]:
    add(domain=d, source='Keys.so, отчёт по домену, блок «Контекстная реклама» (база Москва)', ads_count=ads, queries_count=q,
        queries_per_ad=qa, budget_month=f'{bud} (прогноз бюджета Keys.so, период не указан)', traffic_from_ads=tr,
        traffic_period='не указан', rsya_ads_count=rsya, source_url=f'https://www.keys.so/ru/report?domain={d}&db=msk', note=KEYS_NOTE)
# sales.prof-zabory.ru и прочие — из блока «Конкуренты» в отчётах Keys.so
for d, q, ads, frm in [
    ('sales.prof-zabory.ru', 2398, 1058, 'masterovit.ru'), ('raduga-zaborov.ru', 2998, 1573, 'masterovit.ru'),
    ('zaboroff.ru', 2321, 912, 'masterovit.ru'), ('oblzabor.ru', 889, 301, 'prof-zabory.ru'), ('zaborkin.ru', 418, 190, 'prof-zabory.ru'),
    ('zabory-deshevo.ru', 1305, 594, 'zavodzaborov.ru'), ('liniya-zaborov.ru', 1003, 569, 'zavodzaborov.ru'),
    ('ni-max.ru', 2310, 959, 'masterovit.ru'), ('robaz.ru', 4697, 1260, 'masterovit.ru'), ('mir-shtaketnika.ru', 908, 80, 'prof-zabory.ru')]:
    add(domain=d, source=f'Keys.so, блок «Конкуренты» контекста в отчёте {frm} (база Москва)', ads_count=ads, queries_count=q,
        queries_per_ad=round(q / ads, 1), source_url=f'https://www.keys.so/ru/report?domain={frm}&db=msk',
        note='бюджет и трафик по домену не сняты: дневной лимит Keys.so исчерпан 21.10.2026 на oblzabor.ru')
add(domain='sales.prof-zabory.ru', source='Keys.so, «Объявления в РСЯ»', rsya_ads_count=382, source_url='https://www.keys.so/ru/rsya/ads?domain=sales.prof-zabory.ru')
# Spywords: бюджет — в день, трафик — переходов за последний месяц (подсказки интерфейса)
CONV = 0.01
for d, q, ads, bday, tr in [('masterovit.ru', 1591, 1247, 17276, 4164), ('prof-zabory.ru', 15, 12, 19, 18), ('sales.prof-zabory.ru', 2395, 2042, 1384.83, 3192)]:
    bm = round(bday * 30)
    cpc = round(bm / tr) if tr else ''
    orders = round(tr * CONV, 1)
    add(domain=d, source='Spywords, «Анализ домена» → «Сводка за последний период», Яндекс, регион Москва', ads_count=ads, queries_count=q,
        queries_per_ad=round(q / ads, 2), budget_day=bday, budget_month=f'{bm} (= дневной × 30, оценка)', traffic_from_ads=tr,
        traffic_period='переходов за последний месяц', cpc_calc=f'{cpc} (= бюджет в месяц / трафик, оценка)' if cpc != '' else '',
        orders_month_est=f'{orders} (= трафик × 1%, оценка)', cost_per_order_est=f'{round(bm / (tr * CONV)) if tr else ""} (оценка)',
        source_url=f'https://spywords.ru/sword.php?sword={d}&region=msk',
        note='Google: 0 запросов в контексте')
with open(f'{OUT}/ad_budgets.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=B)
    w.writeheader()
    w.writerows(b)
print('budget rows', len(b))
