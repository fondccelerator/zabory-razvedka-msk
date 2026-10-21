import subprocess, sys, time, random, pathlib, re, json
from bs4 import BeautifulSoup
OUT = pathlib.Path('/home/claude/zabory/notes/raw_sites/trust')
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
log = open(OUT/'fetch_log.tsv','a')
for line in open(sys.argv[1]):
    if not line.strip(): continue
    dom, url = line.split()
    d = OUT/dom; d.mkdir(exist_ok=True)
    slug = re.sub(r'[^a-zA-Z0-9]+','_', url.split('://',1)[1].split('/',1)[1] if '/' in url.split('://',1)[1] else '').strip('_') or 'home'
    f = d/f'{slug}.html'
    if f.exists() and f.stat().st_size>2000:
        print('skip', dom, slug); continue
    r = subprocess.run(['curl','-sS','-L','--max-time','60','-A',UA,'-o',str(f),'-w','%{http_code} %{url_effective}',url],capture_output=True,text=True)
    try:
        soup = BeautifulSoup(f.read_bytes(),'lxml')
        for t in soup(['script','style','noscript','svg']): t.decompose()
        txt = '\n'.join(s.strip() for s in soup.get_text('\n').split('\n') if s.strip())
        (d/f'{slug}.txt').write_text(txt)
        print(dom, slug, r.stdout, len(txt), flush=True)
        log.write(f"{dom}\t{url}\t{r.stdout}\t{len(txt)}\t{time.strftime('%Y-%m-%d')}\n"); log.flush()
    except Exception as e:
        print(dom, slug, 'ERR', r.stdout, r.stderr[:200], e, flush=True)
        log.write(f"{dom}\t{url}\tERR {r.stdout}\t0\t{time.strftime('%Y-%m-%d')}\n")
    time.sleep(random.uniform(1,2))
