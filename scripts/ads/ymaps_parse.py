import json, csv, sys, glob, os, re
RAW = sys.argv[1]; OUT = sys.argv[2]
rows = []
def items_from(path):
    st = json.load(open(path, encoding='utf-8'))
    return st['stack'][0]['results']['items']
def api_items(path):
    out = []
    for a in json.load(open(path, encoding='utf-8')):
        d = a.get('data') if isinstance(a, dict) else None
        if isinstance(d, dict) and isinstance(d.get('items'), list):
            out += d['items']
    return out
for q in ["заборы", "установка заборов", "откатные ворота", "забор под ключ"]:
    slug = q.replace(' ', '_')
    seen = set(); its = []
    for x in items_from(f"{RAW}/ymaps_{slug}_state.json") + api_items(f"{RAW}/ymaps_{slug}_api.json"):
        if not isinstance(x, dict) or x.get('type') != 'business': continue
        if x.get('id') in seen: continue
        seen.add(x.get('id')); its.append(x)
    for rank, x in enumerate(its, 1):
        adv = x.get('advert') or {}
        promo = (x.get('promo') or {}).get('promoAction') or {}
        oi = (adv.get('ordInfo') or {}).get('client') or {}
        rd = x.get('ratingData') or {}
        urls = x.get('urls') or []
        site = urls[0] if urls else ''
        site = re.sub(r'^https?://(www\.)?', '', site).split('/')[0].split('?')[0]
        offers = []
        for pr in (adv.get('products') or [])[:4]:
            pt = (pr.get('price') or {}).get('text', '') if isinstance(pr.get('price'), dict) else ''
            offers.append(pr.get('title', '').strip() + (' — ' + pt if pt else ''))
        buttons = '; '.join((b.get('title') or b.get('name') or '') for b in (adv.get('actionButtons') or []) if isinstance(b, dict))
        rows.append(dict(
            source='Яндекс Карты', query=q, region='Москва (213)', rank=rank,
            company=x.get('title', ''), site=site, address=x.get('address', ''),
            rating=rd.get('ratingValue', ''), ratings_count=rd.get('ratingCount', ''), reviews_count=rd.get('reviewCount', ''),
            categories='; '.join(c.get('name', '') for c in (x.get('categories') or [])[:3]),
            ad_label='Реклама' if adv else '',
            priority_placement='да' if adv.get('isPriorityCampaign') else ('нет' if adv else ''),
            is_direct='да' if adv.get('isDirect') else ('нет' if adv else ''),
            advertiser=oi.get('name', ''), advertiser_inn=oi.get('tin', ''),
            ad_title=adv.get('title', ''), ad_text=(adv.get('text') or '')[:300], ad_url=re.sub(r'\?.*', '', adv.get('url') or ''),
            ad_products='; '.join(offers), ad_buttons=buttons, highlighted='да' if adv.get('highlighted') else ('нет' if adv else ''),
            promo_action=(promo.get('name', '') + (' — ' + promo.get('description', '') if promo.get('description') else '')).strip(),
            promo_url=re.sub(r'\?.*', '', promo.get('url', '')),
            has_stories='да' if x.get('hasStories') else 'нет',
            date_collected='2026-10-21',
            source_url='https://yandex.ru/maps/213/moscow/search/' + q + '/'))
keys = list(rows[0].keys())
with open(OUT, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
print(len(rows))
adv_keys = set()
