# Сбор отзывов Яндекс Карт через yandex.com (SSR + fetchReviews). Имена авторов не сохраняются.
import sys, re, json, time, random, urllib.parse
import requests
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
def sig(s):
    n=5381
    for c in s: n=((33*n)^ord(c)) & 0xFFFFFFFF
    return n
class Ya:
    def __init__(self):
        self.s=requests.Session(); self.s.headers.update({"User-Agent":UA,"Accept-Language":"ru-RU,ru;q=0.9"})
        self.csrf=None; self.sess=None
    def page(self, oid):
        r=self.s.get(f"https://yandex.com/maps/org/{oid}/reviews/",timeout=40)
        h=r.text
        if 'showcaptcha' in r.url or 'checkcaptcha' in h[:5000]: raise RuntimeError('captcha')
        m=re.search(r'"csrfToken":"([^"]+)"',h); self.csrf=m.group(1) if m else self.csrf
        m=re.search(r'"sessionId":"([^"]+)"',h); self.sess=m.group(1) if m else self.sess
        return h
    def fetch(self, oid, page=1, ranking="by_time", size=50):
        p={"ajax":"1","businessId":str(oid),"csrfToken":self.csrf,"locale":"ru_RU","page":str(page),"pageSize":str(size),"ranking":ranking,"reqId":self.sess,"sessionId":self.sess}
        q=urllib.parse.urlencode(sorted(p.items()))
        p["s"]=str(sig(q))
        r=self.s.get("https://yandex.com/maps/api/business/fetchReviews",params=p,timeout=40)
        try: j=r.json()
        except Exception: return {"_err":r.status_code,"_txt":r.text[:300]}
        if 'csrfToken' in j and 'data' not in j:
            self.csrf=j['csrfToken']; return self.fetch(oid,page,ranking,size)
        return j
if __name__=="__main__":
    y=Ya(); oid=sys.argv[1]; h=y.page(oid)
    j=y.fetch(oid,1,"by_time")
    print(json.dumps(j,ensure_ascii=False)[:1500])
