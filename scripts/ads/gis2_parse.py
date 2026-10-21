import re, sys, csv
RAW = sys.argv[1]; OUT = sys.argv[2]
rows = []
for q in ["заборы", "установка заборов", "откатные ворота", "забор под ключ"]:
    slug = q.replace(' ', '_')
    txt = open(f"{RAW}/2gis_{slug}.txt", encoding='utf-8').read()
    pages = re.split(r'\n#### PAGE (\d)\n', txt)
    chunks = [(1, pages[0])] + [(int(pages[i]), pages[i + 1]) for i in range(1, len(pages) - 1, 2)]
    rank = 0
    for pnum, t in chunks:
        lines = [l.replace('​', '').rstrip('\n') for l in t.split('\n')]
        # начало списка — после фильтров («Опт»)
        try: start = lines.index('Опт') + 1
        except ValueError: start = 0
        cards = []; cur = None
        for l in lines[start:]:
            if l.endswith('\xa0') and l.strip() and not re.match(r'^[\d.,]+$', l.strip()):
                if cur: cards.append(cur)
                cur = [l.strip()]
            elif cur is not None:
                if l.strip(): cur.append(l.strip())
        if cur: cards.append(cur)
        for c in cards:
            if len(c) < 3: continue
            rank += 1
            name = c[0]
            ad_idx = [i for i, l in enumerate(c) if l.startswith('Реклама')]
            rating = next((l for l in c[1:5] if re.match(r'^[0-5]([.,]\d)?$', l)), '')
            cnt = next((re.sub(r'\D', '', l) for l in c[1:6] if re.search(r'\d+ оцен', l)), '')
            branches = next((re.search(r'(\d+) филиал', l).group(1) for l in c if re.search(r'\d+ филиал', l)), '')
            rubric = next((l for l in c if re.search(r'(?i)забор|ворот|огражд|кровл|профнаст|металл', l) and l != name and 'филиал' not in l), '')
            ad_text = c[ad_idx[0] - 1] if ad_idx else ''
            adv = c[ad_idx[0]].replace('Реклама', '').strip() if ad_idx else ''
            cta = c[ad_idx[0] + 1] if ad_idx and ad_idx[0] + 1 < len(c) else ''
            if cta and len(cta) > 40: cta = ''
            rows.append(dict(source='2ГИС', query=q, region='Москва', page=pnum, rank=rank, company=name,
                             card_type=c[1] if not re.match(r'^[0-5]([.,]\d)?$', c[1]) else '',
                             rating=rating, ratings_count=cnt, branches=branches,
                             ad_label='Реклама' if ad_idx else '', advertiser_legal=adv, ad_text=ad_text, cta=cta,
                             date_collected='2026-10-21', source_url=f'https://2gis.ru/moscow/search/{q}' + (f'/page/{pnum}' if pnum > 1 else '')))
with open(OUT, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows))
