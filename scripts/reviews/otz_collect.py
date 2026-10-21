import re, sys, time, json, os, random, html as H, requests
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
s=requests.Session(); s.headers.update({"User-Agent":UA,"Accept-Language":"ru-RU"})
OUT='/home/claude/zabory/notes/raw_reviews/otzovik'; os.makedirs(OUT,exist_ok=True)
PROFILES=[('masterovit.ru','kompaniya_masterovit_russia_moscow',962),('zavodzaborov.ru','kompaniya_zavod_zaborov_russia_moscow',740),
('zaboroff.ru','kompaniya_zaboroff_russia_moscow',126),('prof-zabory.ru','kompaniya_prof-zabori_russia_moscow',75),
('raduga-zaborov.ru','kompaniya_raduga_zaborov_russia_moscow',55),('zaborovo.ru','kompaniya_zaborovo_russia_pushkino',55),
('zaborkin.ru','firma_zaborkin_russia_moscow',43),('zaborkin.ru','zaborkin',2),('dostup-zabor.ru','kompaniya_po_ustanovke_zaborov_dostupnie_zabori_russia_moskovskaya_oblast',1),
('zavodzaborov.ru','kompaniya_zavod_zaborov',3),('zavodzaborov.ru','kompaniya_po_ustanovke_zaborov_zavod_zaborov_russia_moskovskaya_oblast',1)]
def clean(x): return H.unescape(re.sub(r'<[^>]+>',' ',x)).replace('\xa0',' ').strip()
def parse(h):
    out=[]
    for blk in h.split('itemprop="review" itemscope')[1:]:
        g=lambda p: (re.search(p,blk,flags=re.S).group(1) if re.search(p,blk,flags=re.S) else '')
        out.append(dict(id=g(r'review_(\d+)\.html'),date=g(r'datePublished" content="([\d-]+)'),stars=int(g(r'ratingValue" content="(\d)') or 0),
            title=clean(g(r'class="review-title"[^>]*>(.*?)</a>')),teaser=clean(g(r'class="review-teaser"[^>]*>(.*?)</div>')),
            plus=clean(g(r'class="review-plus"><b>Достоинства:</b>(.*?)</div>')),minus=clean(g(r'class="review-minus"><b>Недостатки:</b>(.*?)</div>')),
            likes=g(r'Отзыв понравился (\d+)'),comments=g(r'commentCount">(\d+)'),karma=g(r'class="karma karma\d">(-?\d+)')))
    return out
for dom,slug,n in PROFILES:
    fn=f'{OUT}/{slug}.json'
    if os.path.exists(fn): continue
    rows=[]; page=1; seen=set(); status='ok'
    while True:
        u=f'https://otzovik.com/reviews/{slug}/' + (f'{page}/' if page>1 else '')
        r=s.get(u,timeout=40)
        if 'captcha' in r.url.lower() or 'captcha' in r.text[:4000].lower() or r.status_code!=200:
            status=f'stop page {page}: {r.status_code} {r.url[:80]}'; print(status); break
        got=parse(r.text); new=[x for x in got if x['id'] not in seen]
        for x in new: seen.add(x['id'])
        rows+=new
        if not new or len(rows)>=n: break
        page+=1; time.sleep(2.5+random.random()*2)
    json.dump({'company':dom,'slug':slug,'expected':n,'got':len(rows),'status':status,'date_collected':'2026-10-20','reviews':rows},open(fn,'w'),ensure_ascii=False)
    print(dom,slug,'expected',n,'got',len(rows),status,flush=True)
    if status!='ok': break
