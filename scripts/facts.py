import json, sys, re, glob, os
dom = sys.argv[1]
R = '/home/claude/zabory/notes/raw_sites/'
PAT = re.compile(r'предоплат|рассроч|кредит|гарант|бесплатн|подар|скидк|акци|кешб|кэшб|бригад|лет на рынке|с \d{4} год|объект|клиент|км |минут|сроки?|дн(я|ей)\b|за \d+ день|фиксир|смет|производств|договор|без предоплаты|оплат|ответ', re.I)
def lines_of(t):
    return [l.strip() for l in t.split('\n') if l.strip()]
seen = set()
for f in sorted(glob.glob(R + dom + '*.json')):
    d = json.load(open(f))
    slug = os.path.basename(f)[:-5]
    print('\n=====', slug, d.get('url'), d.get('status'), 'H1', d.get('meta', {}).get('h1'))
    ls = lines_of(d.get('text', ''))
    alt = R + 'html/' + slug + '.alltext.txt'
    if os.path.exists(alt):
        ls = lines_of(open(alt).read())
    for i, l in enumerate(ls):
        if PAT.search(l) and l not in seen and len(l) > 3:
            seen.add(l)
            print('  -', l[:260])
