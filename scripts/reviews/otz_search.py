import re, sys, time, json, requests
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
s=requests.Session(); s.headers.update({"User-Agent":UA,"Accept-Language":"ru-RU"})
def search(q):
    r=s.get("https://otzovik.com/",params={"search_text":q},timeout=40)
    h=r.text
    if 'captcha' in r.url.lower() or 'captcha' in h[:5000].lower(): return 'captcha'
    res=[]
    for m in re.finditer(r'data-pid="(\d+)"[^>]*data-reviews="(\d+)".*?<a href="(/reviews/[^"]+)" class=.product-name.>(.*?)</a>.*?<span>([\d.]+)</span>',h,flags=re.S):
        res.append(dict(pid=m.group(1),n=int(m.group(2)),url='https://otzovik.com'+m.group(3),name=re.sub('&quot;','"',m.group(4)),rating=m.group(5)))
    return res
QUERIES={'masterovit.ru':['мастеровит'],'prof-zabory.ru':['профзаборы','проф заборы','prof-zabory'],'zaborkin.ru':['заборкин'],
'zavodzaborov.ru':['завод заборов','заводзаборов'],'raduga-zaborov.ru':['радуга заборов'],'zaborovo.ru':['заборово'],'oblzabor.ru':['облзабор'],
'dostup-zabor.ru':['доступные заборы'],'zaboroff.ru':['заборофф','zaboroff'],'pskzabor.ru':['пск забор'],
'zabormo.ru':['про ограда','zabormo'],'pro-zabor.ru':['про-забор','про забор'],'moscow.kupitzabor.ru':['купитьзабор','купить забор'],'33zabora.ru':['33 забора'],
'zabor-vam.ru':['забор вам'],'good-zabor.ru':['good-zabor','гуд забор'],'moskovskie-zabory.ru':['московские заборы'],'ligazaborov.ru':['лига заборов'],
'zabory-deshevo.ru':['заборы дешево'],'gorodzaborov.ru':['город заборов'],'alusys.ru':['алюсис'],'vorota750.ru':['ворота750','ворота 750'],
'naves-pod-avto-msk.ru':['навес под авто'],'otkatnie-vorota.com':['otkatnie-vorota'],'gruppa-masterov.ru':['группа мастеров'],'metalsystems.ru':['металлические системы'],
'zabory-prestige.ru':['престиж заборы','заборы престиж'],'atlantzabor.ru':['атлант забор','атлант-забор']}
if __name__=="__main__":
    out={}
    for dom,qs in QUERIES.items():
        out[dom]=[]
        for q in qs:
            r=search(q); out[dom].append({'q':q,'res':r}); time.sleep(2.5)
            print(dom,q, r if r=='captcha' else [(x['name'][:60],x['n'],x['rating'],x['url']) for x in r[:8]],flush=True)
    json.dump(out,open('/home/claude/zabory/notes/raw_reviews/otz_search.json','w'),ensure_ascii=False,indent=1)
