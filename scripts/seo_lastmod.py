"""Этап seo, шаг 6: lastmod по каждому URL из sitemap (повторная загрузка файлов sitemap, перечисленных в sitemap_meta.json).
Выход: raw_seo/<domain>/lastmod.tsv (url, lastmod)."""
import sys, os, re, json, time, gzip
import requests
ROOT = '/home/claude/zabory/raw_seo'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'}
s = requests.Session()
for d in sys.argv[1:]:
    m = json.load(open(os.path.join(ROOT, d, 'sitemap_meta.json')))
    rows = []
    for f in m['sitemap_files']:
        if f.get('status') != 200:
            continue
        time.sleep(1.2)
        try:
            r = s.get(f['url'], headers=UA, timeout=40)
        except Exception:
            continue
        body = r.content
        if body[:2] == b'\x1f\x8b':
            body = gzip.decompress(body)
        t = body.decode('utf-8', 'replace')
        if 'urlset' not in t:
            continue
        for blk in re.findall(r'<(?:\w+:)?url>(.*?)</(?:\w+:)?url>', t, re.S):
            loc = re.search(r'<(?:\w+:)?loc>\s*(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?\s*</(?:\w+:)?loc>', blk, re.S)
            lm = re.search(r'<(?:\w+:)?lastmod>\s*(.*?)\s*</(?:\w+:)?lastmod>', blk)
            if loc:
                rows.append((loc.group(1).replace('&amp;', '&'), lm.group(1)[:10] if lm else ''))
    with open(os.path.join(ROOT, d, 'lastmod.tsv'), 'w') as fh:
        for a, b in rows:
            fh.write(f'{a}\t{b}\n')
    print(d, len(rows), sum(1 for _, b in rows if b))
