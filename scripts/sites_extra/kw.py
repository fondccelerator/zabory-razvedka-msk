import sys, pathlib, re, collections
root = pathlib.Path('/home/claude/zabory/notes/raw_sites/trust')
pat = re.compile(sys.argv[1], re.I)
doms = sys.argv[2:] or sorted(p.name for p in root.iterdir() if p.is_dir())
for dom in doms:
    files = sorted((root/dom).glob('*.txt'))
    cnt=collections.Counter()
    for f in files:
        for l in set(f.read_text().split('\n')): cnt[l]+=1
    seen=set()
    for f in files:
        for l in f.read_text().split('\n'):
            if pat.search(l) and l not in seen and (cnt[l]<=2 or len(files)<3):
                seen.add(l); print(f'{dom}|{f.stem}| {l[:260]}')
