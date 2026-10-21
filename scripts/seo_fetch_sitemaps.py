"""Этап seo, шаг 1: robots.txt + sitemap.xml (рекурсивно по индексам) для списка доменов.
Сохраняет сырые файлы в raw_seo/<domain>/ и список URL в raw_seo/<domain>/urls.txt.
Пауза 1.2 с между запросами, лимит 120 запросов на домен на этом шаге."""
import sys, os, re, time, json, gzip
import requests

DOMAINS = sys.argv[1:] or []
ROOT = '/home/claude/zabory/raw_seo'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'}
LIMIT = 120

def get(s, url, cnt):
    if cnt[0] >= LIMIT:
        return None
    cnt[0] += 1
    time.sleep(1.2)
    try:
        r = s.get(url, headers=UA, timeout=30, allow_redirects=True)
        return r
    except Exception as e:
        print('  ERR', url, e)
        return None

def run(domain):
    d = os.path.join(ROOT, domain); os.makedirs(d, exist_ok=True)
    s = requests.Session(); cnt = [0]
    meta = {'domain': domain, 'date': time.strftime('%Y-%m-%d')}
    r = get(s, f'https://{domain}/robots.txt', cnt)
    robots = ''
    if r is not None:
        meta['robots_status'] = r.status_code; meta['robots_final_url'] = r.url
        if r.status_code == 200 and 'html' not in r.headers.get('content-type', ''):
            robots = r.text
    open(os.path.join(d, 'robots.txt'), 'w').write(robots)
    sm = re.findall(r'(?im)^\s*sitemap:\s*(\S+)', robots)
    host = re.findall(r'(?im)^\s*host:\s*(\S+)', robots)
    meta['robots_sitemaps'] = sm; meta['robots_host'] = host
    meta['robots_disallow_count'] = len(re.findall(r'(?im)^\s*disallow:\s*\S', robots))
    queue = list(dict.fromkeys(sm)) or [f'https://{domain}/sitemap.xml']
    if not sm:
        queue.append(f'https://{domain}/sitemap_index.xml')
    seen = set(); urls = []; files = []; lastmods = []
    while queue:
        u = queue.pop(0)
        if u in seen: continue
        seen.add(u)
        r = get(s, u, cnt)
        if r is None:
            files.append({'url': u, 'status': 'limit/err'}); continue
        body = r.content
        if u.endswith('.gz') or body[:2] == b'\x1f\x8b':
            try: body = gzip.decompress(body)
            except Exception: pass
        txt = body.decode('utf-8', 'replace')
        files.append({'url': u, 'status': r.status_code, 'final': r.url, 'bytes': len(body)})
        if r.status_code != 200 or '<' not in txt[:500] or '<html' in txt[:500].lower():
            continue
        locs = re.findall(r'<(?:\w+:)?loc>\s*(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?\s*</(?:\w+:)?loc>', txt, re.S)
        lm = re.findall(r'<(?:\w+:)?lastmod>\s*(.*?)\s*</(?:\w+:)?lastmod>', txt)
        if 'sitemapindex' in txt[:2000]:
            queue.extend(l.strip() for l in locs)
        else:
            urls.extend(l.strip().replace('&amp;', '&') for l in locs)
            lastmods.extend(lm)
    urls = list(dict.fromkeys(urls))
    open(os.path.join(d, 'urls.txt'), 'w').write('\n'.join(urls))
    meta['sitemap_files'] = files
    meta['sitemap_url_count'] = len(urls)
    lm_sorted = sorted(x[:10] for x in lastmods if re.match(r'\d{4}-\d\d-\d\d', x))
    meta['lastmod_min'] = lm_sorted[0] if lm_sorted else ''
    meta['lastmod_max'] = lm_sorted[-1] if lm_sorted else ''
    meta['requests'] = cnt[0]
    json.dump(meta, open(os.path.join(d, 'sitemap_meta.json'), 'w'), ensure_ascii=False, indent=1)
    print(domain, 'robots', meta.get('robots_status'), 'sm', len(files), 'urls', len(urls), 'req', cnt[0], meta['lastmod_max'])

for dm in DOMAINS:
    try:
        run(dm)
    except Exception as e:
        print('FAIL', dm, e)
