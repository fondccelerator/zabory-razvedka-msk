"""Выдача Яндекса (органика, «связанные запросы») и Similarweb через Apify, 21.10.2026.
Вход: notes/raw_serp/yandex_serp_apify_21-10.json (dami_studio/yandex-search-engine-scraper, lr=1 «Москва и область», 15 запросов, 2 страницы),
      notes/raw_similarweb/similarweb_apify_21-10.json (tri_angle/similarweb-scraper, 31 домен, снимок за сентябрь 2026).
Выход: data/serp_mo_organic.csv, data/serp_mo_presence.csv, data/serp_related.csv, data/sw_apify.csv, data/sw_similar_sites.csv."""
import csv, json, re
from collections import Counter, defaultdict
B = '/home/claude/zabory'
def w(p, rows):
    with open(f'{B}/data/{p}.csv', 'w', encoding='utf-8', newline='') as f:
        d = csv.DictWriter(f, fieldnames=list(rows[0].keys())); d.writeheader(); d.writerows(rows)
dom = lambda u: re.sub(r'^www\.', '', re.sub(r'^https?://', '', u or '').split('/')[0]).encode().decode('idna') if 'xn--' in (u or '') else re.sub(r'^www\.', '', re.sub(r'^https?://', '', u or '').split('/')[0])
S = json.load(open(f'{B}/notes/raw_serp/yandex_serp_apify_21-10.json', encoding='utf-8'))['items']
SRC = 'Яндекс, регион lr=1 «Москва и Московская область», выдача через Apify (dami_studio/yandex-search-engine-scraper), 21.10.2026; реклама выгрузкой не отдана'
org = [x for x in S if x.get('type') == 'organic']
w('serp_mo_organic', [dict(query=x['searchQuery'], organic_position=x.get('organicPosition'), domain=dom(x['url']), title=x.get('title'), url=x['url'], source=SRC, date_collected='2026-10-21') for x in org])
MAIN = ['masterovit.ru', 'prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru', 'zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']
queries = sorted({x['searchQuery'] for x in org})
pres = defaultdict(lambda: {'top10': 0, 'top20': 0, 'best': 99, 'q': []})
for x in org:
    d = dom(x['url']); p = x.get('organicPosition') or 99
    if p <= 20:
        pres[d]['top20'] += 1
    if p <= 10:
        pres[d]['top10'] += 1; pres[d]['q'].append(x['searchQuery'])
    pres[d]['best'] = min(pres[d]['best'], p)
rows = []
for d, v in sorted(pres.items(), key=lambda kv: (-kv[1]['top10'], kv[1]['best'])):
    if v['top10'] == 0 and d not in MAIN:
        continue
    rows.append(dict(domain=d, in_brief='полный разбор' if d in MAIN else '', queries_top10_of_15=v['top10'], queries_top20_of_15=v['top20'], best_position=v['best'],
                     queries_top10='; '.join(sorted(set(v['q']))), source=SRC, date_collected='2026-10-21'))
for d in MAIN:
    if d not in pres:
        rows.append(dict(domain=d, in_brief='полный разбор', queries_top10_of_15=0, queries_top20_of_15=0, best_position='нет в топ-20', queries_top10='', source=SRC, date_collected='2026-10-21'))
w('serp_mo_presence', rows)
rel = [x for x in S if x.get('relatedSearches')]
w('serp_related', [dict(query=x['searchQuery'], related=r, source=SRC, date_collected='2026-10-21') for x in rel for r in x['relatedSearches']])
SW = json.load(open(f'{B}/notes/raw_similarweb/similarweb_apify_21-10.json', encoding='utf-8'))['items']
SWS = 'Similarweb, публичная страница сайта (снимок за сентябрь 2026), выгрузка Apify tri_angle/similarweb-scraper, 21.10.2026; оценка'
sw, sim = [], []
for x in SW:
    ru = next((c['visitsShare'] for c in x.get('topCountries') or [] if c.get('countryAlpha2Code') == 'RU'), None)
    src = {t['source']: t.get('percentage') for t in x.get('trafficSources') or []}
    sw.append(dict(domain=x['name'], visits_month=x.get('totalVisits'), snapshot=(x.get('snapshotDate') or '')[:7], russia_share_pct=round(100 * ru, 1) if ru is not None else '',
                   search_organic_share_of_search_pct=round(100 * x['organicTraffic'], 1) if x.get('organicTraffic') is not None else '',
                   search_paid_share_of_search_pct=round(100 * x['paidTraffic'], 1) if x.get('paidTraffic') is not None else '',
                   direct_pct=round(100 * src['direct'], 1) if src.get('direct') is not None else '', pages_per_visit=x.get('pagesPerVisit'),
                   bounce_rate_pct=round(100 * x['bounceRate'], 1) if x.get('bounceRate') is not None else '',
                   top_keywords='; '.join(k['name'] for k in (x.get('topKeywords') or [])[:5]),
                   similar_sites='; '.join(c['domain'] for c in (x.get('topSimilarityCompetitors') or [])[:10]),
                   reliability='меньше 5 000 визитов — модельная оценка' if (x.get('totalVisits') or 0) < 5000 else 'выше порога', source=SWS, date_collected='2026-10-21'))
    for c in x.get('topSimilarityCompetitors') or []:
        sim.append(dict(domain=x['name'], similar_site=c['domain'], affinity=round(c.get('affinity') or 0, 3), source=SWS, date_collected='2026-10-21'))
w('sw_apify', sw); w('sw_similar_sites', sim)
cnt = Counter(r['similar_site'] for r in sim if r['domain'] in MAIN + ['sales.prof-zabory.ru'])
print('similar among main:', cnt.most_common(15))
for r in rows[:30]: print(r['domain'], r['in_brief'], r['queries_top10_of_15'], r['best_position'])
