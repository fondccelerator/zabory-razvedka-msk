import re, json, requests, sys
sys.path.insert(0,'/home/claude/zabory/notes/scripts/reviews')
from ya_search import blocks, UA, search
def card(oid, s=None):
    s=s or requests.Session()
    r=s.get(f"https://yandex.com/maps/org/{oid}/",params={"lang":"ru_RU"},headers={"User-Agent":UA,"Accept-Language":"ru-RU"},timeout=40)
    h=r.text
    if 'showcaptcha' in r.url: return {'id':oid,'err':'captcha'}
    b=[x for x in blocks(h) if x['id']==str(oid)]
    o=b[0] if b else {'id':oid}
    m=re.search(r'"ratingData":\{"ratingCount":(\d+),"ratingValue":([\d.]+),"reviewCount":(\d+)\}',h)
    if m: o.update(cnt=m.group(1),rating=m.group(2),rev=m.group(3))
    o['final_url']=r.url
    return o
def chain(cid, slug='x', s=None):
    s=s or requests.Session()
    r=s.get(f"https://yandex.com/maps/1/moscow-and-moscow-oblast/chain/{slug}/{cid}/",params={"lang":"ru_RU","ll":"37.62,55.75","z":"8"},headers={"User-Agent":UA},timeout=40)
    return blocks(r.text)
if __name__=="__main__":
    s=requests.Session()
    for a in sys.argv[1:]:
        if a.startswith('ch'):
            for o in chain(a[2:],s=s): print('  chain',a,o)
        elif a.startswith('q:'):
            st,res=search(a[2:],s=s); 
            for o in res: print('  q',a,o)
        else: print(card(a,s=s))

def chain_qty(oid, s=None):
    s=s or requests.Session()
    h=s.get(f"https://yandex.com/maps/org/{oid}/",params={"lang":"ru_RU"},headers={"User-Agent":UA},timeout=40).text
    m=re.search(r'"chain":\{"id":"(\d+)","name":"([^"]+)","seoname":"([^"]+)"(?:,"quantityInCity":(\d+))?',h)
    return m.groups() if m else None
def sweep(query, chain_id=None, s=None, z=10):
    import time
    s=s or requests.Session(); found={}
    pts=[(37.62,55.75),(37.2,55.9),(38.1,55.9),(37.2,55.5),(38.1,55.5),(36.6,55.7),(38.6,55.7),(37.6,56.3),(37.6,55.1),(36.9,56.1),(38.3,56.1),(36.9,55.3),(38.3,55.3)]
    for lon,lat in pts:
        u="https://yandex.com/maps/1/moscow-and-moscow-oblast/search/"+requests.utils.quote(query)+"/"
        r=s.get(u,params={"ll":f"{lon},{lat}","z":str(z),"lang":"ru_RU"},headers={"User-Agent":UA},timeout=40)
        for o in blocks(r.text):
            if chain_id is None or o['chain']==chain_id: found[o['id']]=o
        time.sleep(1.0)
    return list(found.values())
