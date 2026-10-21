import json, sys, re
R = '/home/claude/zabory/notes/raw_sites/'
PAT = re.compile(r'предоплат|гарант|скидк|акци|подар|рассроч|от \d[\d ]* ?(₽|р|руб)|\d ?₽|бесплатн|за \d+ дн|лет|бригад|объект', re.I)
for slug in sys.argv[1:]:
    try: d = json.load(open(R + slug + '.json'))
    except Exception as e: print('NO', slug); continue
    m = d.get('meta', {})
    print('\n#####', slug, d.get('final_url'), d.get('status'))
    print('TITLE', m.get('title')); print('H1', m.get('h1')); print('MSG', sorted(set(u.split('?')[0][:40] for u in m.get('messengers', [])))[:8])
    print('PERF', {k: round(v) if isinstance(v, (int, float)) else v for k, v in (d.get('perf_desktop') or {}).items()}, 'mob', (d.get('perf_mobile') or {}).get('mobile_overflow'))
    ls = [l.strip() for l in d.get('text', '').split('\n') if l.strip()]
    print('TOP:', ' | '.join(ls[:45])[:1500])
    seen = set(); out = []
    for l in ls:
        if PAT.search(l) and l not in seen and len(l) < 300:
            seen.add(l); out.append(l)
    print('KEY:', ' || '.join(out[:60])[:3500])
