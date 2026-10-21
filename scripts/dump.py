import json, sys
d = json.load(open(f'/home/claude/zabory/notes/raw_sites/{sys.argv[1]}.json'))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 700
m = d.get('meta', {})
print('URL', d['url'], '->', d.get('final_url'), 'status', d.get('status'), 'H', m.get('height'), 'container', m.get('container'), m.get('containerN'))
print('TITLE', m.get('title')); print('DESC', m.get('description')); print('H1', m.get('h1'))
print('MSG', sorted(set(u.split('?')[0][:60] for u in m.get('messengers', [])))); print('TEL', m.get('tels'))
print('PERF', d.get('perf_desktop'), d.get('perf_mobile'), d.get('t_load_s'), d.get('t_load_mobile_s'))
for i, b in enumerate(d.get('blocks', [])):
    print(f"\n#{i} y={b['y']} h={b['h']} in={b['inputs']} f={b['forms']} ifr={b['iframes'][:2]} H={b['headings'][:4]} BTN={b['buttons'][:6]}")
    print('   ', b['text'][:n])
