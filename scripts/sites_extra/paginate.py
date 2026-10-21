import subprocess, sys, time, pathlib, hashlib
from bs4 import BeautifulSoup
OUT = pathlib.Path('/home/claude/zabory/notes/raw_sites/trust_reviews')
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
jobs = [
 ('zavodzaborov.ru','https://zavodzaborov.ru/reviews/?PAGEN_2={}',2,35),
 ('oblzabor.ru','https://www.oblzabor.ru/company/reviews/?PAGEN_1={}',2,23),
 ('zaborovo.ru','https://zaborovo.ru/reviews?page={}',2,40),
 ('prof-zabory.ru','https://prof-zabory.ru/otzyvy?start={}',25,500),
 ('zaboroff.ru','https://www.zaboroff.ru/reviews/page-{}/',2,30),
 ('masterovit.ru','https://www.masterovit.ru/clients/?PAGEN_1={}',2,120),
]
only = sys.argv[1:]
for dom,tpl,a,b in jobs:
    if only and dom not in only: continue
    d=OUT/dom; d.mkdir(parents=True,exist_ok=True)
    prev=None; step = 25 if 'start=' in tpl else 1
    for n in range(a,b+1,step):
        url=tpl.format(n); f=d/f'p{n}.html'
        r=subprocess.run(['curl','-sS','-L','--max-time','60','-A',UA,'-o',str(f),'-w','%{http_code}',url],capture_output=True,text=True)
        soup=BeautifulSoup(f.read_bytes(),'lxml')
        for t in soup(['script','style','noscript','svg']): t.decompose()
        txt='\n'.join(s.strip() for s in soup.get_text('\n').split('\n') if s.strip())
        h=hashlib.md5(txt.encode()).hexdigest()
        (d/f'p{n}.txt').write_text(url+'\n'+txt)
        print(dom,n,r.stdout,len(txt),flush=True)
        if r.stdout!='200' or h==prev: break
        prev=h; time.sleep(1)
