import json, sys
d = json.load(open(f'/home/claude/zabory/notes/raw_sites/{sys.argv[1]}.json'))
for h in d.get('h', []):
    print(h['y'], h['tag'], h['t'][:150])
if len(sys.argv) > 2:
    t = d.get('text', '')
    a, b = (int(x) for x in sys.argv[2].split(':'))
    print('----TEXT len', len(t)); print(t[a:b])
