import sys, json, time, os, random; sys.path.insert(0,'/home/claude/zabory/notes/scripts/reviews')
from ya_fetch import Ya
from ya_cards_all import info
from registry import FULL, LIGHT, GATES
OUT='/home/claude/zabory/notes/raw_reviews/yandex'; os.makedirs(OUT,exist_ok=True)
y=Ya()
def collect(dom, oid, with_reviews=True):
    fn=f'{OUT}/{oid}.json'
    if os.path.exists(fn): return
    o=info(oid); o['company']=dom; o['date_collected']='2026-10-20'
    o['reviews']=[]
    if with_reviews and o.get('ok') and (o.get('rev',0)>0):
        y.page(oid); page=1
        while True:
            j=y.fetch(oid,page,'by_time')
            d=j.get('data')
            if not d: o['err']=str(j)[:300]; break
            for r in d['reviews']:
                bc=r.get('businessComment') or {}
                o['reviews'].append(dict(id=r['reviewId'],date=r.get('updatedTime','')[:10],stars=r.get('rating'),text=r.get('text',''),
                    reply=bc.get('text',''),reply_date=(bc.get('updatedTime') or '')[:10],
                    author_level=(r.get('author') or {}).get('professionLevel',''),photos=len(r.get('photos') or []),likes=(r.get('reactions') or {}).get('likes',0)))
            o['expected']=d['params']['count']; tp=d['params']['totalPages']
            if page>=tp: break
            page+=1; time.sleep(0.6+random.random()*0.4)
    o['got']=len(o['reviews'])
    json.dump(o,open(fn,'w'),ensure_ascii=False)
    print(dom,oid,o.get('title'),o.get('cnt'),o.get('rev'),'expected',o.get('expected'),'got',o['got'],flush=True)
for grp,full in [(FULL,True),(GATES,True),(LIGHT,False)]:
    for dom,ids in grp.items():
        for oid in ids:
            try: collect(dom,oid,full)
            except Exception as e: print('ERR',dom,oid,e,flush=True)
            time.sleep(0.8)
