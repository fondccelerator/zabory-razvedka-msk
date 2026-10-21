# Обезличивание сырых выгрузок отзывов (тексты, ответы компаний, заголовки)
import sys, json, glob
sys.path.insert(0,'/home/claude/zabory/notes/scripts/reviews')
from redact import redact
B='/home/claude/zabory/notes/raw_reviews'
def fix(path, keys, listkey='reviews'):
    o=json.load(open(path))
    for r in o[listkey]:
        for k in keys:
            if r.get(k): r[k]=redact(r[k])
    json.dump(o,open(path,'w'),ensure_ascii=False)
for f in glob.glob(B+'/yandex/*.json'): fix(f,['text','reply'])
for f in glob.glob(B+'/otzovik/*.json'): fix(f,['title','teaser','plus','minus'])
fix(B+'/2gis/2gis_reviews_raw.json',['x','a'])
A=json.load(open(B+'/all_reviews.json'))
for r in A:
    for k in ('text','reply'):
        if r.get(k): r[k]=redact(r[k])
json.dump(A,open(B+'/all_reviews.json','w'),ensure_ascii=False)
print('ok')
