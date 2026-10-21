import sys, json, re, time; sys.path.insert(0,'/home/claude/zabory/notes/scripts/reviews')
import requests
from ya_search import UA
s=requests.Session()
def info(oid):
    r=s.get(f"https://yandex.com/maps/org/{oid}/",params={"lang":"ru_RU"},headers={"User-Agent":UA,"Accept-Language":"ru-RU"},timeout=40)
    h=r.text
    if 'showcaptcha' in r.url: return {'id':oid,'err':'captcha'}
    i=h.find(f'ymapsbm1://org?oid={oid}')
    o={'id':oid}
    m=re.search(r'"ratingData":\{"ratingCount":(\d+),"ratingValue":([\d.]+),"reviewCount":(\d+)\}',h)
    if m: o.update(cnt=int(m.group(1)),rating=float(m.group(2)),rev=int(m.group(3)))
    seg=h[max(0,i-3000):i+20000] if i>0 else h
    def g(p,src=seg):
        mm=re.search(p,src); return mm.group(1) if mm else ''
    o['title']=g(r'"title":"([^"]+)"'); o['addr']=g(r'"address":"([^"]+)"'); o['url']=g(r'"urls":\["([^"]+)"')
    cm=re.search(r'"categories":\[(.*?)\]',seg); o['cats']=';'.join(re.findall(r'"name":"([^"]+)"',cm.group(1))) if cm else ''
    o['status']=g(r'"status":"([a-z_]+)"'); o['chain']=g(r'"chain":\{"id":"(\d+)"')
    o['ok']=bool(m)
    return o
if __name__=="__main__":
    ids=sys.argv[1:]
    res=[]
    for oid in ids:
        try: o=info(oid)
        except Exception as e: o={'id':oid,'err':str(e)}
        print(json.dumps(o,ensure_ascii=False),flush=True); res.append(o); time.sleep(0.7)
