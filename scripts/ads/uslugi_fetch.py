# Яндекс Услуги: выдача по запросам (Москва), разбор состояния страницы
import re, json, sys, subprocess, urllib.parse, csv, os, time
OUT = sys.argv[1]
RAW = sys.argv[2]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
queries = [("установка забора", 3), ("забор под ключ", 3), ("откатные ворота", 3), ("заборы", 2),
           ("мастеровит", 1), ("заборкин", 1), ("заборово", 1), ("проф заборы", 1), ("завод заборов", 1),
           ("радуга заборов", 1), ("облзабор", 1), ("доступные заборы", 1), ("заборофф", 1), ("пск забор", 1)]
rows = []
def get(url):
    r = subprocess.run(["curl", "-sS", "-L", "-A", UA, "--max-time", "40", url], capture_output=True)
    return r.stdout.decode('utf-8', 'replace')
for q, pages in queries:
    for p in range(pages):
        url = "https://uslugi.yandex.ru/213-moscow/category?text=" + urllib.parse.quote_plus(q) + ("&p=%d" % p if p else "")
        h = get(url)
        fn = os.path.join(RAW, "uslugi_%s_p%d.html" % (q.replace(' ', '_'), p))
        m = re.search(r'<script[^>]*>(\{"mordaData".*?)</script>', h, re.S)
        if not m:
            print("NO STATE", q, p, len(h), 'captcha' in h.lower()); continue
        st = json.loads(m.group(1))
        json.dump(st['search'], open(fn + '.search.json', 'w', encoding='utf-8'), ensure_ascii=False)
        s = st['search']; w = st['workers']['items']
        total = s['params']['pagination']['totalItems']
        blender = s.get('blender', {}).get('main', [])
        # direct ads
        for kind, d in (('direct', s.get('direct') or {}), ('direct-guarantee', s.get('garantDirect') or {})):
            for pos, ad in d.items():
                li = ad.get('legalInfo') or {}
                rows.append(dict(query=q, page=p + 1, total_in_search=total, block=kind, position=pos,
                    name=li.get('clientName', ''), inn=li.get('clientTin', ''), account_type='рекламодатель Директа',
                    advertised='да (Реклама, Яндекс Директ на Услугах)', rating='', reviews='', finished_orders='',
                    title=ad.get('title', ''), text=(ad.get('body') or '')[:300], domain=ad.get('domain', ''),
                    callouts='; '.join(ad.get('callouts') or []), price_from='', site='', url=url))
        for rank, wid in enumerate(s.get('workerIds', []), 1):
            x = w.get(wid, {}); pi = x.get('personalInfo', {})
            acct = pi.get('accountType', '')
            # цена от: минимальная цена услуг
            prices = []
            for oc in x.get('occupations', []):
                for sp in oc.get('specializations', []):
                    for sv in sp.get('services', []):
                        a = sv.get('attrs') or {}
                        if isinstance(a.get('price'), (int, float)) and a.get('price') > 0 and re.search(r'(?i)забор|ворот|огражд|столб|рабиц|штакет|профнаст|калит', a.get('name', '')):
                            prices.append((a['price'], a.get('priceMeasure', ''), a.get('name', '')))
            rows.append(dict(query=q, page=p + 1, total_in_search=total, block='исполнитель', position=rank + p * 10,
                name=('организация, сайт ' + re.sub(r'^https?://(www\.)?', '', pi.get('site', '')).split('/')[0]) if acct != 'person' and pi.get('site') else ('организация без сайта в профиле' if acct != 'person' else 'частный мастер'),
                inn='', account_type=acct, advertised='да' if x.get('isAdvertised') else 'нет',
                rating=x.get('rating', ''), reviews=x.get('reviewsAmount', ''), finished_orders=pi.get('finishedOrders', ''),
                title='', text=(pi.get('description') or '')[:200].replace('\n', ' ') if acct != 'person' else '',
                domain='', callouts='', price_from=('%s ₽ (%s, %s)' % min(prices) if prices else ''),
                site=pi.get('site', '') if acct != 'person' else '', url=url))
        print(q, p, 'total', total, 'workers', len(s.get('workerIds', [])), 'adv', sum(1 for wid in s.get('workerIds', []) if w.get(wid, {}).get('isAdvertised')), 'blender', blender)
        time.sleep(2)
with open(OUT, 'w', encoding='utf-8', newline='') as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
