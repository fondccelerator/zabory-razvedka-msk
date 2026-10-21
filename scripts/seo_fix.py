"""Этап seo, шаг 7: точечная перезагрузка страниц (исправление выбора страницы/кодировки) и BFS-обход сайтов без sitemap.
Дописывает в raw_seo/<domain>/pages.json; BFS сохраняет raw_seo/<domain>/urls.txt (найденные ссылки) с пометкой источника."""
import sys, os, re, json, time, collections, urllib.parse as up
import requests
sys.path.insert(0, '/home/claude/zabory/notes/scripts')
from seo_pages import analyze, UA
ROOT = '/home/claude/zabory/raw_seo'
s = requests.Session()

def fetch(u):
    time.sleep(1.3)
    try:
        r = s.get(u, headers=UA, timeout=40)
        r.encoding = 'utf-8' if (r.encoding or '').lower() in ('iso-8859-1', 'latin-1', 'windows-1252', '') else r.encoding
        return r
    except Exception as e:
        return None

FIX = [
    ('dostup-zabor.ru', 'fence', 'https://dostup-zabor.ru/metallicheskiye-zabory/zabor-is-profnastila/'),
    ('dostup-zabor.ru', 'geo_sub', 'https://odintsovo.dostup-zabor.ru/metallicheskiye-zabory/zabor-is-profnastila/'),
    ('zaborovo.ru', 'fence', 'https://zaborovo.ru/zabory/zabor-iz-profnastila'),
    ('zabor-dlya-vseh.site', 'home', 'https://zabor-dlya-vseh.site/'),
    ('zabory-deshevo.ru', 'blog', 'https://zabory-deshevo.ru/stati/'),
    ('oblzabor.ru', 'geo_sub', 'https://odincovo.oblzabor.ru/zabory/iz-profnastila/'),
    ('33zabora.ru', 'blog', 'https://33zabora.ru/stati/'),
]
for dom, name, u in FIX:
    p = json.load(open(os.path.join(ROOT, dom, 'pages.json')))
    r = fetch(u)
    if r is None:
        p['pages'][name] = {'url': u, 'error': 'нет ответа'}
    else:
        rec = {'url': u, 'final': r.url, 'status': r.status_code, 'ttfb_s': round(r.elapsed.total_seconds(), 2), 'bytes': len(r.content)}
        if r.status_code == 200:
            a = analyze(r.text, r.url, dom); links = a.pop('_links'); rec.update(a)
            if name == 'home':
                p['home_links'] = links
        p['pages'][name] = rec
    if name == 'geo_sub' or (dom == 'oblzabor.ru'):
        p['pages'].pop('geo', None) if dom in ('oblzabor.ru',) else None
    json.dump(p, open(os.path.join(ROOT, dom, 'pages.json'), 'w'), ensure_ascii=False, indent=1)
    print(dom, name, rec.get('status'), rec.get('title', '')[:60], rec.get('h1'), rec.get('text_words'), rec.get('dates_in_text'))
p = json.load(open(os.path.join(ROOT, 'pro-zabor.ru', 'pages.json'))); p['pages'].pop('geo', None)
json.dump(p, open(os.path.join(ROOT, 'pro-zabor.ru', 'pages.json'), 'w'), ensure_ascii=False, indent=1)

# BFS для сайтов без рабочего sitemap
def bfs(dom, start, maxfetch):
    host = up.urlparse(start).netloc
    q = [start]; seen = {start}; fetched = 0; found = set([start])
    while q and fetched < maxfetch:
        u = q.pop(0)
        r = fetch(u); fetched += 1
        if r is None or r.status_code != 200 or 'html' not in r.headers.get('content-type', ''):
            continue
        for h in re.findall(r'href=["\']([^"\'#]+)', r.text):
            v = up.urljoin(r.url, h).split('#')[0]
            pu = up.urlparse(v)
            if pu.netloc != host or re.search(r'\.(jpg|jpeg|png|webp|gif|pdf|svg|css|js|ico|xml|zip|doc|docx)$', pu.path, re.I) or '?' in v:
                continue
            if v not in seen:
                seen.add(v); found.add(v); q.append(v)
    fpath = os.path.join(ROOT, dom, 'urls.txt')
    prev = set(x for x in open(fpath).read().split('\n') if x.startswith('http') and up.urlparse(x).netloc == host) if os.path.exists(fpath) else set()
    open(fpath, 'w').write('\n'.join(sorted(found | prev)))
    json.dump({'method': 'обход ссылок (BFS)', 'fetched': fetched, 'found': len(found), 'queue_left': len(q), 'date': time.strftime('%Y-%m-%d')},
              open(os.path.join(ROOT, dom, 'bfs_meta.json'), 'w'), ensure_ascii=False)
    print('BFS', dom, 'fetched', fetched, 'found', len(found), 'queue_left', len(q))

bfs('33zabora.ru', 'https://33zabora.ru/', 150)
bfs('zabor-dlya-vseh.site', 'https://zabor-dlya-vseh.site/', 40)
bfs('p-z-z.ru', 'https://p-z-z.ru/', 15)
