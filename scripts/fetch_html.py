import subprocess, sys, time, random, pathlib
from bs4 import BeautifulSoup
OUT = pathlib.Path('/home/claude/zabory/notes/raw_sites/html')
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
for line in open(sys.argv[1]):
    if not line.strip(): continue
    slug, url = line.split()
    f = OUT / f'{slug}.html'
    r = subprocess.run(['curl', '-sS', '-L', '--max-time', '60', '-A', UA, '-o', str(f), '-w', '%{http_code}', url], capture_output=True, text=True)
    try:
        soup = BeautifulSoup(f.read_bytes(), 'lxml')
        for t in soup(['script', 'style', 'noscript', 'svg']): t.decompose()
        txt = '\n'.join(s.strip() for s in soup.get_text('\n').split('\n') if s.strip())
        (OUT / f'{slug}.alltext.txt').write_text(txt)
        print(slug, r.stdout, len(txt), flush=True)
    except Exception as e:
        print(slug, 'ERR', e, flush=True)
    time.sleep(random.uniform(2, 3))
