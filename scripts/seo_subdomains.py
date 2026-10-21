"""Этап seo, шаг 5: выборочная проверка поддоменов городов (живы ли, свои title/H1/canonical, robots, sitemap, ИКС, похожесть текста на главную основного домена).
Выход: raw_seo/subdomains_check.json"""
import sys, re, json, time, difflib
import requests
sys.path.insert(0, '/home/claude/zabory/notes/scripts')
from seo_pages import analyze, text_of, UA
from bs4 import BeautifulSoup

SAMPLE = {
    'oblzabor.ru': ['www.oblzabor.ru', 'odincovo.oblzabor.ru', 'podolsk.oblzabor.ru', 'klin.oblzabor.ru', 'sergiev-posad.oblzabor.ru', 'balashiha.oblzabor.ru'],
    'dostup-zabor.ru': ['dostup-zabor.ru', 'odintsovo.dostup-zabor.ru', 'podolsk.dostup-zabor.ru', 'klin.dostup-zabor.ru', 'tver.dostup-zabor.ru', 'kaluga.dostup-zabor.ru'],
    'zabormo.ru': ['zabormo.ru', 'tula.zabormo.ru', 'tver.zabormo.ru'],
    'kupitzabor.ru': ['kupitzabor.ru', 'moscow.kupitzabor.ru', 'arhangelsk.kupitzabor.ru'],
    'zaborkin.ru': ['spb.zaborkin.ru'],
}
s = requests.Session()
def get(u):
    time.sleep(1.3)
    try:
        return s.get(u, headers=UA, timeout=40)
    except Exception as e:
        return None
out = {}
for dom, hosts in SAMPLE.items():
    base_txt = None
    for h in hosts:
        rec = {}
        r = get(f'https://{h}/')
        if r is None:
            rec['error'] = 'нет ответа'; out[h] = rec; continue
        rec['status'] = r.status_code; rec['final'] = r.url; rec['ttfb_s'] = round(r.elapsed.total_seconds(), 2)
        if r.status_code == 200:
            a = analyze(r.text, r.url, h)
            a.pop('_links')
            for k in ('title', 'description', 'h1', 'canonical', 'robots_meta', 'text_words', 'schema_jsonld', 'schema_microdata'):
                rec[k] = a[k]
            txt = text_of(BeautifulSoup(r.text, 'lxml'))
            if base_txt is None:
                base_txt = txt
            else:
                rec['similarity_to_main'] = round(difflib.SequenceMatcher(None, base_txt[:6000], txt[:6000]).ratio(), 2)
        rr = get(f'https://{h}/robots.txt')
        if rr is not None and rr.status_code == 200:
            rec['robots_host'] = re.findall(r'(?im)^\s*host:\s*(\S+)', rr.text)
            rec['robots_sitemap'] = re.findall(r'(?im)^\s*sitemap:\s*(\S+)', rr.text)
            rec['robots_disallow_all'] = bool(re.search(r'(?im)^\s*disallow:\s*/\s*$', rr.text))
        if rec.get('robots_sitemap'):
            sm = get(rec['robots_sitemap'][0])
            if sm is not None and sm.status_code == 200:
                locs = re.findall(r'<loc>(.*?)</loc>', sm.text)
                rec['sitemap_locs_first_file'] = len(locs)
                rec['sitemap_is_index'] = '<sitemapindex' in sm.text
        wi = get(f'https://webmaster.yandex.ru/siteinfo/?site={h}')
        if wi is not None:
            m = re.search(r'"sqi":(\d+)', wi.text)
            rec['iks'] = int(m.group(1)) if m else 'не найдено'
        out[h] = rec
        print(h, rec.get('status'), rec.get('title', '')[:70], '| H1:', (rec.get('h1') or [''])[:1], '| can:', rec.get('canonical'), '| sim', rec.get('similarity_to_main'), '| iks', rec.get('iks'), '| sm', rec.get('sitemap_locs_first_file'))
json.dump(out, open('/home/claude/zabory/raw_seo/subdomains_check.json', 'w'), ensure_ascii=False, indent=1)
