import sys, re, json, urllib.parse, requests
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
def blocks(h):
    res={}
    for m in re.finditer(r'"type":"business","requestId":"[^"]*","index":\d+,',h):
        seg=h[m.start():m.start()+15000]
        def g(p):
            mm=re.search(p,seg); return mm.group(1) if mm else ''
        oid=g(r'ymapsbm1://org\?oid=(\d+)')
        if not oid or oid in res: continue
        res[oid]=dict(id=oid,title=g(r'"title":"([^"]+)"'),addr=g(r'"address":"([^"]+)"'),
            url=g(r'"urls":\["([^"]+)"'),rating=g(r'"ratingValue":([\d.]+)'),cnt=g(r'"ratingCount":(\d+)'),rev=g(r'"reviewCount":(\d+)'),
            cat=g(r'"categories":\[\{[^}]*?"name":"([^"]+)"'), chain=g(r'"chain":\{"id":"(\d+)"'), closed=g(r'"status":"(closed|temporary_closed|permanent_closed)"'))
    return list(res.values())
def search(text, ll="37.62,55.75", z=8, s=None):
    s=s or requests.Session()
    u="https://yandex.com/maps/1/moscow-and-moscow-oblast/search/"+urllib.parse.quote(text)+"/"
    r=s.get(u,params={"ll":ll,"z":str(z),"lang":"ru_RU"},headers={"User-Agent":UA,"Accept-Language":"ru-RU"},timeout=40)
    if 'showcaptcha' in r.url: return 'captcha',[]
    return r.status_code, blocks(r.text)
if __name__=="__main__":
    st,res=search(sys.argv[1])
    print(st,len(res))
    for o in res: print(o)
