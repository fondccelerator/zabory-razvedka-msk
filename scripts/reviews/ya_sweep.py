import sys, json, time; sys.path.insert(0,'/home/claude/zabory/notes/scripts/reviews')
from ya_search import blocks, UA
import requests
s=requests.Session()
JOBS=[('masterovit.ru','Мастеровит'),('zavodzaborov.ru','ЗаводЗаборов'),('pskzabor.ru','ПСК Забор'),('zaborovo.ru','Заборово'),
('prof-zabory.ru','Проф заборы'),('dostup-zabor.ru','Доступные заборы'),('oblzabor.ru','Облзабор'),('metalsystems.ru','Металлические системы ворота'),
('kupitzabor.ru','КупитьЗабор'),('zaboroff.ru','Заборофф'),('raduga-zaborov.ru','Радуга заборов'),('zaborkin.ru','Заборкин'),('alusys.ru','Алюсис'),('zabor-dlya-vseh','Забор для всех'),('p-z-z.ru','Подмосковный завод заборов')]
pts=[(37.62,55.75),(37.2,55.9),(38.1,55.9),(37.2,55.5),(38.1,55.5),(36.6,55.7),(38.6,55.7),(37.6,56.3),(37.6,55.1),(36.9,56.1),(38.3,56.1),(36.9,55.3),(38.3,55.3)]
out={}
only=sys.argv[1:]
for dom,q in JOBS:
    if only and dom not in only: continue
    found={}
    for lon,lat in pts:
        u="https://yandex.com/maps/1/moscow-and-moscow-oblast/search/"+requests.utils.quote(q)+"/"
        try:
            r=s.get(u,params={"ll":f"{lon},{lat}","z":"10","lang":"ru_RU"},headers={"User-Agent":UA},timeout=40)
        except Exception as e: print('err',e); continue
        if 'showcaptcha' in r.url: print('CAPTCHA'); break
        for o in blocks(r.text):
            key=dom.split('.')[0]
            if key in o['url'] or key.replace('-','') in o['url']: found[o['id']]=o
        time.sleep(0.8)
    out[dom]=list(found.values())
    print(dom, len(found), [(o['id'],o['addr'][:40],o['cnt']) for o in found.values()], flush=True)
json.dump(out,open('/home/claude/zabory/notes/raw_reviews/ya_sweep.json','w'),ensure_ascii=False,indent=1)
