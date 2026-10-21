# Выборочная проверка точности кодбука: контекст совпадений.
import csv, re, random, sys
sys.argv = ['x']
src = open('/home/claude/zabory/notes/scripts/avito/build_avito.py').read()
ns = {}
exec(src.split('# ---------- продукт и единица')[0], ns)
L = list(csv.DictReader(open('/home/claude/zabory/data/avito_listings.csv')))
random.seed(1)
u = list({r['listing_id']: r for r in L}.values())
for k, rx in ns['CLAIMS_RX'].items():
    hits = []
    for r in u:
        t = ns['norm'](r['title'] + '\n' + r['description'])
        m = rx.search(t)
        if m:
            hits.append(t[max(0, m.start() - 50):m.end() + 40].replace('\n', ' '))
    print('==', k, len(hits))
    for h in random.sample(hits, min(4, len(hits))):
        print('   ', h)
