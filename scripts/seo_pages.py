"""Этап seo, шаг 3: разбор ключевых страниц (главная, страница заборов, гео-страница, блог, портфолио),
редиректы http/www, TTFB, мета, schema.org, CMS, поддомены, объём текста, видео, FAQ, даты статей.
Сохраняет HTML в raw_seo/<domain>/html/ и итог в raw_seo/<domain>/pages.json. Пауза 1.3 с, лимит 60 запросов на домен."""
import sys, os, re, time, json, gzip, collections, urllib.parse as up
import requests
from bs4 import BeautifulSoup

ROOT = '/home/claude/zabory/raw_seo'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36',
      'Accept-Language': 'ru-RU,ru;q=0.9'}
LIMIT = 60

FENCE = {
    'masterovit.ru': 'https://www.masterovit.ru/zabory-i-navesy/',
    'prof-zabory.ru': 'https://prof-zabory.ru/iz-profnastila',
    'zaborkin.ru': 'https://zaborkin.ru/zabory/',
    'oblzabor.ru': 'https://www.oblzabor.ru/zabory/iz-profnastila/',
    'dostup-zabor.ru': 'https://dostup-zabor.ru/zabory-is-profnastila/',
    'zaboroff.ru': 'https://www.zaboroff.ru/profnastil/',
    'pskzabor.ru': 'https://pskzabor.ru/zabory-iz-proflista-profnastila/',
    'zabormo.ru': 'https://zabormo.ru/zabory-iz-profnastila/',
    'moscow.kupitzabor.ru': 'https://moscow.kupitzabor.ru/zabor-iz-profnastila/',
    'pro-zabor.ru': 'https://pro-zabor.ru/uslugi/zaboryi-iz-profnastila/',
    'zabory-deshevo.ru': 'https://zabory-deshevo.ru/zabory/iz-profnastila/',
    'ligazaborov.ru': 'https://ligazaborov.ru/zabor_iz-profnastila/',
}

CMS_SIGNS = [
    ('1С-Битрикс', r'/bitrix/|bx-core|BX\.setJSList|bitrix_sessid'),
    ('WordPress', r'wp-content|wp-includes|wp-json'),
    ('Tilda', r'tildacdn|tilda\.ws|data-tilda'),
    ('Joomla', r'/media/jui/|joomla|/components/com_'),
    ('MODX', r'modx|/assets/components/|/assets/templates/'),
    ('OpenCart', r'catalog/view/theme|route=product'),
    ('Drupal', r'drupal|/sites/default/files'),
    ('Webasyst', r'wa-data|wa-content|webasyst'),
    ('UMI.CMS', r'umi\.cms|/umi/|umi-cms'),
    ('Nethouse', r'nethouse'),
    ('InSales', r'insales'),
    ('Next.js', r'__NEXT_DATA__|/_next/static'),
    ('Nuxt', r'__NUXT__|/_nuxt/'),
    ('HostCMS', r'hostcms'),
    ('NetCat', r'netcat'),
    ('Craftum/Flexbe/LPgenerator', r'flexbe|lpgenerator|craftum'),
]

def text_of(soup):
    s = BeautifulSoup(str(soup), 'lxml')
    for t in s(['script', 'style', 'noscript', 'svg', 'template']):
        t.decompose()
    body = s.body or s
    return re.sub(r'\s+', ' ', body.get_text(' ')).strip()

def analyze(html, url, base_domain):
    soup = BeautifulSoup(html, 'lxml')
    d = {}
    d['title'] = (soup.title.get_text(strip=True) if soup.title else '')
    def meta(name=None, prop=None):
        m = soup.find('meta', attrs={'name': name}) if name else soup.find('meta', attrs={'property': prop})
        if not m and name:
            m = soup.find('meta', attrs={'name': re.compile('^' + name + '$', re.I)})
        return (m.get('content') or '').strip() if m else ''
    d['description'] = meta('description')
    d['robots_meta'] = meta('robots')
    d['viewport'] = meta('viewport')
    d['generator'] = meta('generator')
    can = soup.find('link', rel=lambda v: v and 'canonical' in v)
    d['canonical'] = can.get('href', '') if can else ''
    amp = soup.find('link', rel=lambda v: v and 'alternate' in v, media=True)
    d['alt_mobile'] = amp.get('href', '') if amp else ''
    d['h1'] = [re.sub(r'\s+', ' ', h.get_text(' ')).strip() for h in soup.find_all('h1')]
    d['h2_count'] = len(soup.find_all('h2'))
    d['lang'] = soup.html.get('lang', '') if soup.html else ''
    # schema
    types = []
    for s in soup.find_all('script', type='application/ld+json'):
        raw = s.string or s.get_text() or ''
        try:
            obj = json.loads(raw)
        except Exception:
            types.append('JSON-LD(ошибка разбора)')
            continue
        def walk(o):
            if isinstance(o, dict):
                t = o.get('@type')
                if t:
                    types.extend(t if isinstance(t, list) else [t])
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(obj)
    micro = [re.sub(r'^https?://schema\.org/', '', x.get('itemtype', '')) for x in soup.find_all(attrs={'itemtype': True})]
    d['schema_jsonld'] = sorted(set(types))
    d['schema_microdata'] = sorted(set(micro))
    d['og'] = bool(soup.find('meta', attrs={'property': 'og:title'}))
    # text
    txt = text_of(soup)
    d['text_chars'] = len(txt)
    d['text_words'] = len([w for w in txt.split(' ') if len(w) > 2])
    d['img_count'] = len(soup.find_all('img'))
    d['img_no_alt'] = len([i for i in soup.find_all('img') if not i.get('alt')])
    low = html.lower()
    d['video'] = sorted(set(re.findall(r'(youtube\.com/embed|youtube\.com/watch|youtu\.be|rutube\.ru|vk\.com/video|vkvideo\.ru|dzen\.ru/video|<video)', low)))
    d['faq_text'] = bool(re.search(r'(часто задаваемые|вопрос[ыа]? и ответ|вопрос-ответ|faq)', txt.lower()))
    d['reviews_text'] = bool(re.search(r'отзыв', txt.lower()))
    d['cms'] = [n for n, rx in CMS_SIGNS if re.search(rx, html, re.I)]
    # links
    host = up.urlparse(url).netloc
    links = []
    for a in soup.find_all('a', href=True):
        h = up.urljoin(url, a['href'])
        links.append((h, re.sub(r'\s+', ' ', a.get_text(' ')).strip()[:80]))
    reg = base_domain.replace('www.', '')
    root = '.'.join(reg.split('.')[-2:])
    subs = sorted(set(up.urlparse(h).netloc.lower() for h, _ in links
                      if up.urlparse(h).netloc.lower().endswith('.' + root) and up.urlparse(h).netloc.lower() not in (root, 'www.' + root)))
    # поддомены могут быть и в JS/атрибутах
    subs_raw = sorted(set(m.lower() for m in re.findall(r'([a-z0-9-]+\.' + re.escape(root) + r')\b', html, re.I)
                          if m.lower() not in (root, 'www.' + root)))
    d['subdomains_links'] = subs
    d['subdomains_any'] = subs_raw
    internal = [h for h, _ in links if up.urlparse(h).netloc.replace('www.', '') == host.replace('www.', '')]
    d['internal_links'] = len(internal)
    d['internal_links_unique'] = len(set(internal))
    d['dates_in_text'] = sorted(set(re.findall(r'\b(\d{2}\.\d{2}\.20\d{2})\b', txt)))[-15:]
    d['years_in_text'] = collections.Counter(re.findall(r'\b(20[12]\d)\b', txt)).most_common(6)
    d['_links'] = links
    return d

class Fetcher:
    def __init__(self):
        self.s = requests.Session(); self.n = 0
    def get(self, url, **kw):
        if self.n >= LIMIT:
            return None
        for attempt in range(2):
            self.n += 1
            time.sleep(1.3)
            try:
                return self.s.get(url, headers=UA, timeout=40, **kw)
            except Exception as e:
                err = str(e)
                time.sleep(3)
        return {'error': err}

def pick(urls_types, typ, prefer=None):
    c = [u for u, t, g in urls_types if t == typ]
    if prefer:
        p = [u for u in c if re.search(prefer, u)]
        if p:
            return sorted(p, key=len)[0]
    return sorted(c, key=len)[0] if c else None

def run(domain):
    d = os.path.join(ROOT, domain); hd = os.path.join(d, 'html'); os.makedirs(hd, exist_ok=True)
    F = Fetcher(); out = {'domain': domain, 'date': time.strftime('%Y-%m-%d'), 'pages': {}}
    # редиректы
    for k, u in (('http_root', f'http://{domain}/'), ('www_variant', f'https://www.{domain}/' if not domain.startswith('www.') and domain.count('.') == 1 else None)):
        if not u:
            continue
        r = F.get(u, allow_redirects=True)
        if isinstance(r, dict) or r is None:
            out[k] = {'error': (r or {}).get('error', 'limit')}
        else:
            out[k] = {'final': r.url, 'status': r.status_code, 'chain': [x.status_code for x in r.history]}
    cls = []
    cf = os.path.join(d, 'classified.tsv')
    if os.path.exists(cf):
        for line in open(cf):
            p = line.rstrip('\n').split('\t')
            cls.append((p[0], p[1], p[2]))
    targets = {'home': f'https://{domain}/'}
    targets['fence'] = FENCE.get(domain)
    g = [u for u, t, geo in cls if geo == 'да']
    targets['geo'] = sorted(g, key=len)[len(g) // 2] if g else None
    targets['blog'] = pick(cls, 'статьи/блог/новости', r'/(blog|stati|articles|staty|news|novosti|info/news)/?$')
    targets['portfolio'] = pick(cls, 'портфолио/наши работы', r'/(portfolio|nashi[-_]raboty|vypolnennye-raboty|raboty|cases|gallery|galleries|foto-zaborov)/?$')
    targets['faq'] = pick(cls, 'вопрос-ответ/FAQ')
    for name, u in targets.items():
        if not u:
            continue
        r = F.get(u, allow_redirects=True)
        if r is None or isinstance(r, dict):
            out['pages'][name] = {'url': u, 'error': (r or {}).get('error', 'limit')}
            continue
        rec = {'url': u, 'final': r.url, 'status': r.status_code, 'ttfb_s': round(r.elapsed.total_seconds(), 2),
               'bytes': len(r.content), 'server': r.headers.get('server', ''), 'x_powered_by': r.headers.get('x-powered-by', ''),
               'x_robots': r.headers.get('x-robots-tag', '')}
        html = r.text
        open(os.path.join(hd, name + '.html'), 'w').write(html)
        if r.status_code == 200 and '<' in html[:2000]:
            a = analyze(html, r.url, domain)
            links = a.pop('_links')
            rec.update(a)
            if name == 'home':
                out['home_links'] = links
                if not targets.get('fence'):
                    cand = [h for h, t in links if re.search(r'profnast|proflist', h, re.I) and up.urlparse(h).netloc.replace('www.', '') == domain.replace('www.', '')]
                    cand = cand or [h for h, t in links if re.search(r'zabor', up.urlparse(h).path, re.I) and up.urlparse(h).netloc.replace('www.', '') == domain.replace('www.', '')]
                    if cand:
                        targets['fence'] = sorted(set(cand), key=len)[0]
        out['pages'][name] = rec
    out['targets'] = targets
    out['requests'] = F.n
    json.dump(out, open(os.path.join(d, 'pages.json'), 'w'), ensure_ascii=False, indent=1)
    h = out['pages'].get('home', {})
    print(domain, 'req', F.n, 'home', h.get('status'), h.get('ttfb_s'), h.get('cms'), 'subs', len(h.get('subdomains_any', []) or []), 'fence', targets.get('fence'))

if __name__ == '__main__':
    for dm in sys.argv[1:]:
        try:
            run(dm)
        except Exception as e:
            import traceback; traceback.print_exc()
            print('FAIL', dm, e)
