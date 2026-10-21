"""Этап seo, шаг 9: сборка data/seo_sites.csv и data/seo_pages.csv из raw_seo/*."""
import os, re, json, csv, collections, datetime
from bs4 import BeautifulSoup

R = '/home/claude/zabory/raw_seo'
D = '/home/claude/zabory/data'
DATE = '2026-10-20'

SITES = [  # domain, group, company
    ('masterovit.ru', 'полный разбор', 'ООО «Мастеровит»'),
    ('prof-zabory.ru', 'полный разбор', 'ИП Коротков К. А.'),
    ('sales.prof-zabory.ru', 'второй сайт (лендинг prof-zabory.ru)', 'ИП Коротков К. А.'),
    ('zaborkin.ru', 'полный разбор', 'ООО «Первый строительный»'),
    ('zavodzaborov.ru', 'полный разбор', 'ООО «Мособлстрой»'),
    ('zabor-dlya-vseh.site', 'второй сайт (zavodzaborov.ru)', 'ООО «Мособлстрой»'),
    ('raduga-zaborov.ru', 'полный разбор', 'ИП Смирнов М. И.'),
    ('zaborovo.ru', 'полный разбор', 'ООО «Заборово»'),
    ('p-z-z.ru', 'второй сайт (zaborovo.ru)', 'ООО «Заборово»'),
    ('oblzabor.ru', 'полный разбор', 'ИП Толмачёв Е. Н.'),
    ('dostup-zabor.ru', 'полный разбор', 'ИП (ИНН 443001116031)'),
    ('zaboroff.ru', 'полный разбор', 'ООО «ЗАБОРОФФ»'),
    ('pskzabor.ru', 'полный разбор', 'ООО «Строймонтаж2015»'),
    ('zabormo.ru', 'облегчённо', ''),
    ('moscow.kupitzabor.ru', 'облегчённо', ''),
    ('pro-zabor.ru', 'облегчённо', ''),
    ('33zabora.ru', 'облегчённо', ''),
    ('zabory-deshevo.ru', 'облегчённо', 'ООО «Заборы Дешево» (ИНН не найден)'),
    ('ligazaborov.ru', 'облегчённо', 'ИП Гончар Ю. А.'),
    ('zabor-vam.ru', 'облегчённо', 'ИП Северин В. В.'),
    ('good-zabor.ru', 'облегчённо', 'ООО «СТРОЙ-ЦЕНТР»'),
    ('moskovskie-zabory.ru', 'облегчённо', 'ООО «СВ Компани»'),
    ('gorodzaborov.ru', 'облегчённо', 'ООО «Строй Модуль»'),
]
SUBS = {'good-zabor.ru': 1, 'oblzabor.ru': 94, 'dostup-zabor.ru': 167, 'zabormo.ru': 7, 'zaborkin.ru': 1, 'moscow.kupitzabor.ru': None}
SUB_PAGES = {'oblzabor.ru': 2551, 'dostup-zabor.ru': 1782, 'zabormo.ru': 21}  # URL в sitemap одного проверенного поддомена
M = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}

CMS_FIX = {'zabory-deshevo.ru': '1С-Битрикс (шаблон furniture_pale-blue)', 'zaborovo.ru': 'самописная на Yii2 (признаки yii, krajee в коде)'}
MODEL = {  # вывод по собранным данным
    'masterovit.ru': 'авторитетный домен + контент: 215 статей, 90 видео-страниц, 46 разделов работ; гео-страниц нет',
    'prof-zabory.ru': 'гео-страницы (90, вкл. Тверскую обл.) + блог 91 статья без дат; органика слабая, ставка на рекламу',
    'sales.prof-zabory.ru': 'рекламный лендинг на Tilda, вне органики',
    'zaborkin.ru': 'каталог + 59 гео-страниц МО + 206 статей/новостей + FAQPage и Product/Offer в разметке',
    'zavodzaborov.ru': 'гео-страницы /regions/ (102) при слабой органике; основной канал — реклама',
    'zabor-dlya-vseh.site': 'рекламный одностраничник, домен 2026 г., вне органики',
    'raduga-zaborov.ru': 'гео-страницы (47) + блог 53 статьи; органика слабая, основной канал — реклама',
    'zaborovo.ru': 'гео-страницы по районам (57) + раздел откатных ворот (57 URL); старый домен',
    'p-z-z.ru': 'рекламный сайт на Tilda, домен 2025 г., вне органики',
    'oblzabor.ru': 'поддомены городов (94) с полной копией каталога + каталог дизайнов (2551 URL на домен)',
    'dostup-zabor.ru': 'поддомены городов (167, шесть областей) + 414 гео-страниц + 633 «вопрос-ответ» + 113 договоров в портфолио',
    'zaboroff.ru': 'матрица «материал × город» (724 гео-URL, 7 областей) на старейшем домене (2007)',
    'pskzabor.ru': 'каталог + интернет-магазин (153 товара), гео-страниц нет; органики по 9 запросам нет',
    'zabormo.ru': 'гео-страницы городов МО (73) + 7 поддоменов областных центров',
    'moscow.kupitzabor.ru': 'портфолио как SEO-слой (699 страниц объектов) + поддомены городов РФ',
    'pro-zabor.ru': 'каталог материалов и услуг + 182 кейса с городом в адресе + 95 статей; домен 2023 г.',
    '33zabora.ru': 'малый сайт (33 страницы), sitemap 404, без перехода на https',
    'zabory-deshevo.ru': 'каталог дизайнов (1840 URL: 1344 заборов, 381 откатных ворот) без гео-страниц',
    'ligazaborov.ru': 'гео-страницы (98, из них 32 «материал + город») на WordPress',
    'zabor-vam.ru': 'каталог-магазин (644 URL: 428 заборов, 134 ворот, 69 навесов) без гео-страниц; lastmod sitemap 2022 г.',
    'good-zabor.ru': 'каталог (185 URL, страницы *.html) + FAQ; главная заточена под профнастил; поддомен spb',
    'moskovskie-zabory.ru': 'каталог услуг + 71 статья/новость, гео-страниц нет; старый домен (2012)',
    'gorodzaborov.ru': 'малый сайт (103 URL: 30 заборов, 21 статья, 24 страницы цветов RAL), 1-е место по «забор из евроштакетника»',
}
whois = json.load(open(f'{R}/whois_iks.json'))
render = json.load(open(f'{R}/render.json'))
subchk = json.load(open(f'{R}/subdomains_check.json'))
comp = {r['domain']: r for r in csv.DictReader(open(f'{D}/competitors.csv'))}
serp = {r['domain']: r for r in csv.DictReader(open(f'{D}/serp_presence_msk.csv'))}
keys = json.load(open(f'{D}/keys_queries_msk.json'))

CTR = {1: .28, 2: .15, 3: .10, 4: .07, 5: .05, 6: .04, 7: .03, 8: .025, 9: .02, 10: .018}  # модельная кривая CTR, допущение

def keys_visibility(dom):
    base = dom.replace('moscow.', '')
    s = 0
    for q, v in keys.items():
        org = [x.replace('moscow.', '') for x in v['org']]
        if base in org:
            s += v['f'] * CTR[org.index(base) + 1]
    return round(s)

EXACT = {'забор под ключ': 14205}  # точная частотность Keys.so (data/wordstat_dynamics.csv, 2026-09); для остальных 8 запросов не снята
EXACT_RATIO = 14205 / 57377  # коэффициент «точная/широкая» по «забор под ключ», применён к остальным запросам — оценка

def keys_visibility_exact(dom):
    base = dom.replace('moscow.', '')
    s = 0
    for q, v in keys.items():
        org = [x.replace('moscow.', '') for x in v['org']]
        if base in org:
            f = EXACT.get(q, v['f'] * EXACT_RATIO)
            s += f * CTR[org.index(base) + 1]
    return round(s)

def keys_visibility_equal(dom):
    base = dom.replace('moscow.', '')
    s = 0
    for q, v in keys.items():
        org = [x.replace('moscow.', '') for x in v['org']]
        if base in org:
            s += CTR[org.index(base) + 1] * 100
    return round(s, 1)

SW_ORG = {}
for r in csv.DictReader(open(f'{D}/traffic_channels.csv')):
    if r['channel_similarweb'] == 'Search - Organic':
        SW_ORG[r['domain']] = r['visits_3m_similarweb']

def keys_positions(dom):
    base = dom.replace('moscow.', '')
    out = []
    for q, v in keys.items():
        org = [x.replace('moscow.', '') for x in v['org']]
        if base in org:
            out.append(f'{q} — {org.index(base) + 1}')
    return '; '.join(out)

def visible_dates(path):
    if not os.path.exists(path):
        return []
    t = BeautifulSoup(open(path).read(), 'lxml').get_text(' ')
    ds = []
    for a, b, c in re.findall(r'\b(\d{1,2})\.(\d{2})\.(20\d{2})\b', t):
        try:
            ds.append(datetime.date(int(c), int(b), int(a)))
        except ValueError:
            pass
    for a, mn, c in re.findall(r'\b(\d{1,2})\s+(' + '|'.join(M) + r')\s+(20\d{2})', t):
        ds.append(datetime.date(int(c), M[mn], int(a)))
    return sorted(set(x for x in ds if x <= datetime.date(2026, 10, 20)))

def schema_set(pg):
    return set((pg.get('schema_jsonld') or []) + (pg.get('schema_microdata') or []))

def yes(b):
    return 'да' if b else 'нет'

def flags(st):
    return {
        'Organization/LocalBusiness': bool(st & {'Organization', 'LocalBusiness', 'Store', 'HomeAndConstructionBusiness'}),
        'Product': 'Product' in st,
        'Offer': bool(st & {'Offer', 'AggregateOffer'}),
        'Review/AggregateRating': bool(st & {'Review', 'AggregateRating', 'Rating'}),
        'FAQPage': bool(st & {'FAQPage', 'QAPage', 'Question'}),
        'BreadcrumbList': 'BreadcrumbList' in st,
    }

site_rows = []; page_rows = []
for dom, group, company in SITES:
    p = json.load(open(f'{R}/{dom}/pages.json'))
    sm = json.load(open(f'{R}/{dom}/sitemap_meta.json')) if os.path.exists(f'{R}/{dom}/sitemap_meta.json') else {}
    bfs = json.load(open(f'{R}/{dom}/bfs_meta.json')) if os.path.exists(f'{R}/{dom}/bfs_meta.json') else None
    cls = [l.rstrip('\n').split('\t') for l in open(f'{R}/{dom}/classified.tsv')] if os.path.exists(f'{R}/{dom}/classified.tsv') else []
    lm = {}
    if os.path.exists(f'{R}/{dom}/lastmod.tsv'):
        for l in open(f'{R}/{dom}/lastmod.tsv'):
            u, x = l.rstrip('\n').split('\t')
            if x:
                lm[u] = max(lm.get(u, ''), x)
    types = collections.Counter(c[1] for c in cls)
    geo = [c for c in cls if c[2] == 'да']
    geo_mat = [c for c in geo if c[3]]
    mats = collections.Counter()
    for c in cls:
        if c[1] in ('заборы и ограждения', 'ворота: откатные', 'ворота и калитки: прочие', 'материалы (продажа)', 'города/районы (гео)') and c[3]:
            for m in c[3].split(';'):
                mats[m] += 1
    otkat = [c for c in cls if c[1] == 'ворота: откатные' or (c[1] == 'города/районы (гео)' and re.search(r'otkat', c[0]))]
    arts = [c[0] for c in cls if c[1] == 'статьи/блог/новости']
    art_lm = sorted(lm[u] for u in arts if u in lm)
    # видимые даты на странице блога
    vd = []
    if dom not in ('dostup-zabor.ru', 'sales.prof-zabory.ru', 'zabory-deshevo.ru'):  # там в blog.html попала отдельная запись или главная
        vd += visible_dates(f'{R}/{dom}/html/blog.html')
    home = p['pages'].get('home', {}); fence = p['pages'].get('fence', {})
    sh, sf = schema_set(home), schema_set(fence)
    fh, ff = flags(sh), flags(sf)
    w = whois.get(dom, {}) if dom != 'moscow.kupitzabor.ru' else whois.get('kupitzabor.ru', {})
    created = w.get('whois_created', '')
    age = round((datetime.date(2026, 10, 20) - datetime.date.fromisoformat(created)).days / 365.25, 1) if created else ''
    rd = render.get(dom, {})
    c0 = comp.get(dom.replace('moscow.', ''), {}); s0 = serp.get(dom.replace('moscow.', ''), {})
    total_urls = len(cls)
    url_source = ('sitemap.xml' if sm.get('sitemap_url_count') else '') if not bfs else ('обход ссылок с главной (sitemap нет или пуст)' + (' + sitemap-store.xml' if dom == 'p-z-z.ru' else ''))
    nsub = SUBS.get(dom)
    sub_pages = nsub * SUB_PAGES[dom] if nsub and dom in SUB_PAGES else ''
    http = p.get('http_root', {}).get('final', '')
    https_redirect = 'да' if http.startswith('https://') else 'нет (http открывается без перехода на https)'
    port = portfolio = types.get('портфолио/наши работы', 0)
    vids = types.get('видео', 0)
    home_title = home.get('title', '')
    row = {
        'domain': dom, 'group': group, 'company': company,
        'cms': CMS_FIX.get(dom) or ', '.join(home.get('cms', [])) or 'не определена',
        'seo_model': MODEL.get(dom, ''),
        'domain_created_whois': created or 'не найдено', 'domain_age_years': age,
        'yandex_iks': w.get('iks', ''), 'yandex_siteinfo_badges': ', '.join(w.get('achievements', [])) or 'нет',
        'https': 'да' if home.get('final', '').startswith('https') else 'нет', 'http_to_https_redirect': https_redirect,
        'robots_txt': 'да' if os.path.exists(f'{R}/{dom}/robots.txt') and os.path.getsize(f'{R}/{dom}/robots.txt') > 0 else 'нет',
        'robots_disallow_rules': sm.get('robots_disallow_count', ''),
        'robots_sitemap_ok': ('нет — указан sitemap чужого домена zabor-doneck.ru' if dom == 'zabor-dlya-vseh.site' else
                              'указан, отдаёт 404' if dom == '33zabora.ru' else
                              'указан, пустой ответ/403 (Tilda)' if dom == 'p-z-z.ru' and not sm.get('sitemap_url_count') else
                              ('да' if sm.get('robots_sitemaps') else 'не указан')),
        'urls_total': total_urls, 'urls_source': url_source,
        'sitemap_lastmod_max': sm.get('lastmod_max', ''),
        'city_subdomains': nsub if nsub is not None else ('не менее 2 (moscow, arhangelsk); полный список не найден' if dom == 'moscow.kupitzabor.ru' else 0),
        'subdomain_urls_estimate': sub_pages,
        'geo_pages_main_domain': len(geo), 'geo_x_material_pages': len(geo_mat),
        'fence_pages': types.get('заборы и ограждения', 0),
        'sliding_gate_pages': len(otkat), 'other_gate_pages': types.get('ворота и калитки: прочие', 0),
        'profnastil_pages': mats.get('профнастил', 0), 'shtaketnik_pages': mats.get('евроштакетник/металлоштакетник', 0),
        'articles_blog_news': len(arts),
        'articles_last_visible_date': str(vd[-1]) if vd else 'не найдено на странице блога',
        'articles_lastmod_max': art_lm[-1] if art_lm else 'нет lastmod',
        'faq_pages': types.get('вопрос-ответ/FAQ', 0),
        'portfolio_pages': port, 'video_pages': vids,
        'price_calc_pages': types.get('цены/калькулятор', 0),
        'home_title': home_title, 'home_title_len': len(home_title),
        'home_description_len': len(home.get('description', '')),
        'home_h1': ' | '.join(h for h in home.get('h1', []) if h) or 'нет H1 (пустой или отсутствует)',
        'home_h1_count': len([h for h in home.get('h1', []) if h]),
        'home_canonical': home.get('canonical', '') or 'нет',
        'home_text_words': home.get('text_words', ''),
        'fence_url': fence.get('final', fence.get('url', '')) or 'нет отдельной страницы',
        'fence_title': fence.get('title', ''), 'fence_h1': ' | '.join(h for h in fence.get('h1', []) if h),
        'fence_description_len': len(fence.get('description', '')) if fence else '',
        'fence_text_words': fence.get('text_words', ''),
        'schema_home': ', '.join(sorted(sh)) or 'нет',
        'schema_fence': ', '.join(sorted(sf)) or ('нет' if fence else ''),
    }
    for k in fh:
        key = 'schema_' + k.lower().replace('/', '_')
        row[key] = 'главная: ' + yes(fh[k]) + '; заборы: ' + (yes(ff[k]) if fence else '—')
    row.update({
        'viewport_mobile': 'да' if home.get('viewport') else 'нет',
        'ttfb_home_s': home.get('ttfb_s', ''),
        'mobile_lcp_ms_cloud': rd.get('lcp_ms', ''), 'mobile_load_ms_cloud': rd.get('load_ms', ''),
        'mobile_page_weight_kb': rd.get('transfer_kb', ''), 'mobile_requests': rd.get('requests', ''),
        'video_on_home': ', '.join(home.get('video', [])) or 'нет',
        'faq_block_home': yes(home.get('faq_text')),
        'visits_jul_sep_2026_similarweb': c0.get('visits_jul_sep_2026', ''),
        'keys_presence_score': s0.get('score', ''), 'keys_organic_hits_of_9': s0.get('organic_hits', ''),
        'keys_best_org_pos': s0.get('best_org_pos', ''), 'keys_alice_hits': s0.get('alice_hits', ''), 'keys_ads_hits': s0.get('ads_hits', ''),
        'keys_organic_positions': keys_positions(dom),
        'keys_visibility_index_estimate': keys_visibility(dom),
        'keys_visibility_index_exact_estimate': keys_visibility_exact(dom),
        'keys_visibility_equal_weight_estimate': keys_visibility_equal(dom),
        'similarweb_organic_visits_3m': SW_ORG.get(dom, 'не снято'),
        'source': f'https://{dom}/robots.txt; sitemap; главная и страница заборов (requests); who.is; webmaster.yandex.ru/siteinfo; Playwright 390×844; Keys.so 05.09–05.10.2026 (serp_presence_msk.csv)',
        'date': DATE,
    })
    site_rows.append(row)
    # seo_pages
    def add(cat, cnt, method, note=''):
        page_rows.append({'domain': dom, 'page_type': cat, 'count': cnt, 'method': method, 'note': note,
                          'source': ((sm.get('robots_sitemaps') or [f'https://{dom}/sitemap.xml'])[0] if not bfs else f'https://{dom}/ (обход ссылок)'), 'date': DATE})
    meth = 'классификация URL sitemap по словам в адресе' if not bfs else 'классификация URL, найденных обходом ссылок'
    add('всего URL', total_urls, url_source)
    for t, n in sorted(types.items(), key=lambda x: -x[1]):
        add(t, n, meth)
    add('гео-страницы × материал (напр. «забор из профнастила в Клину»)', len(geo_mat), meth)
    for m, n in sorted(mats.items(), key=lambda x: -x[1]):
        add('материал: ' + m, n, meth + '; одна страница может относиться к двум материалам')
    add('откатные ворота (вкл. гео)', len(otkat), meth)
    if nsub:
        SUBNOTE = {'oblzabor.ru': 'проверено 5 поддоменов: ответ 200, свой canonical, город в title/H1 главной и внутренних страниц, схожесть первых 6000 знаков текста главной с основным доменом 0,99 (difflib)',
                   'dostup-zabor.ru': 'проверено 5 поддоменов: ответ 200, свой canonical и Host, город в title (H1 общий), robots.txt закрывает поддомены только для Googlebot; внутренние страницы без подстановки города; схожесть первых 6000 знаков текста главной 0,70–0,79 (difflib)',
                   'zabormo.ru': 'поддомены областных центров (Тула, Тверь и др.), 21 URL в sitemap поддомена; схожесть первых 6000 знаков текста главной 0,94 (difflib)',
                   'zaborkin.ru': 'один поддомен spb (Санкт-Петербург), 685 URL в sitemap',
                   'good-zabor.ru': 'один поддомен spb (Санкт-Петербург), не проверялся'}
        add('поддомены городов', nsub, 'ссылки на поддомены в HTML главной', SUBNOTE.get(dom, ''))
        if dom in SUB_PAGES:
            add('URL на поддоменах (оценка)', nsub * SUB_PAGES[dom], f'{nsub} поддоменов × {SUB_PAGES[dom]} URL в sitemap одного проверенного поддомена', 'оценка')

# фиксированный порядок колонок
with open(f'{D}/seo_sites.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(site_rows[0].keys()))
    w.writeheader(); w.writerows(site_rows)
with open(f'{D}/seo_pages.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(page_rows[0].keys()))
    w.writeheader(); w.writerows(page_rows)
print(len(site_rows), len(page_rows))
