import json, sys, re
d = json.load(open(f'/home/claude/zabory/notes/raw_sites/{sys.argv[1]}.json'))
t = d.get('text', '')
print('URL', d['url'], d.get('status'), 'H1', d.get('meta', {}).get('h1'), 'len', len(t))
lines = [l.strip() for l in t.split('\n') if l.strip()]
if len(sys.argv) > 2 and sys.argv[2].startswith('/'):
    pat = re.compile(sys.argv[2][1:], re.I)
    for i, l in enumerate(lines):
        if pat.search(l):
            print(i, ' | '.join(lines[max(0, i-1):i+2])[:400])
else:
    a, b = (int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else '0:400').split(':'))
    for l in lines[a:b]: print(l[:300])
