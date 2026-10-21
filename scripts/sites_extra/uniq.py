import sys, pathlib, collections
dom = sys.argv[1]; d = pathlib.Path('/home/claude/zabory/notes/raw_sites/trust')/dom
files = sorted(d.glob('*.txt'))
cnt = collections.Counter()
for f in files:
    for l in set(f.read_text().split('\n')): cnt[l]+=1
thr = max(2, int(len(files)*0.6)) if len(files)>2 else 99
sel = sys.argv[2:] or [f.stem for f in files]
for s in sel:
    f = d/f'{s}.txt'
    print('#####', s)
    out=[l for l in f.read_text().split('\n') if cnt[l]<thr]
    print('\n'.join(x[:400] for x in out)[:int(sys.argv[0] and 9000)])
