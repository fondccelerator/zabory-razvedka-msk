import re
import sys, pathlib, collections
from bs4 import BeautifulSoup
dom = sys.argv[1]; d = pathlib.Path('/home/claude/zabory/notes/raw_sites/trust')/dom
files = sorted(d.glob('*.html'))
def items(f):
    s = BeautifulSoup(f.read_bytes(),'lxml'); out=[]
    for i in s.find_all('img'):
        src = i.get('data-src') or i.get('data-lazy-src') or i.get('src') or ''
        out.append(('img', src, (i.get('alt') or '')+' | '+(i.get('title') or '')))
    for a in s.find_all('a', href=True):
        h=a['href']
        if any(h.lower().endswith(x) for x in ('.pdf','.jpg','.jpeg','.png','.webp','.doc','.docx')):
            out.append(('a', h, a.get_text(' ',strip=True)[:80]+' | '+(a.get('title') or '')))
    return out
cnt=collections.Counter()
data={}
for f in files:
    it=items(f); data[f.stem]=it
    for x in set(i[1] for i in it): cnt[x]+=1
thr=max(2,int(len(files)*0.5)) if len(files)>2 else 99
sel = sys.argv[2:] or list(data)
for s in sel:
    print('#####', s)
    seen=set()
    for t,src,alt in data[s]:
        key=(src+' '+alt).lower()
        if cnt[src]<thr and src not in seen and (len(sys.argv)<=2 or re.search(r'sert|cert|diplom|logo|partn|client|klient|nagrad|blagod|gost|licen|svid|award|premi|dogovor|pasport|.pdf|brand|grand|metall|doorhan|alutech|came|nice|roger|bft|an-motors|сертиф|диплом|благод|партн|лиценз|свидет|паспорт|награ|логотип|клиент|гост', key)):
            seen.add(src); print(t, src[:160], '::', alt[:150])
