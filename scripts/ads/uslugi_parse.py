import re, json, sys
h = open(sys.argv[1], encoding='utf-8').read()
m = re.search(r'<script[^>]*>(\{"mordaData".*?)</script>', h, re.S)
st = json.loads(m.group(1))
json.dump(st, open(sys.argv[1] + '.state.json', 'w', encoding='utf-8'), ensure_ascii=False)
def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, path + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o[:3]):
            yield from walk(v, path + '[%d]' % i)
    else:
        yield path, o
print(list(st.keys()))
for p, v in walk(st):
    if isinstance(v, str) and len(v) > 2 and re.search(r'(?i)забор|ворот', v):
        print(p[:160], '=', v[:100])
