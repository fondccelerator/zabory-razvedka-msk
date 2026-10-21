import pathlib, re, json
d=pathlib.Path('/home/claude/zabory/notes/raw_sites/trust/masterovit.ru_obj')
urls={}
for l in open('mo_obj.txt'):
    dom,u=l.split(); slug=re.sub(r'[^a-zA-Z0-9]+','_',u.split('://',1)[1].split('/',1)[1]).strip('_'); urls[slug]=u
rows=[]
for slug,u in urls.items():
    t=(d/f'{slug}.txt').read_text().split('\n')
    i=[k for k,l in enumerate(t) if l.startswith('Опубликовано: ')]
    if not i: print('NO', slug); continue
    i=i[0]; blk=t[i-1:i+12]
    def after(lbl):
        for k,x in enumerate(blk):
            if x.startswith(lbl): return blk[k+1] if k+1<len(blk) else ''
        return ''
    rows.append(dict(url=u,title=blk[0],pub=t[i].split(': ')[1],loc=t[i+1],period=after('Срок выполнения'),vol=after('Длина забора')))
json.dump(rows,open('mo_obj.json','w'),ensure_ascii=False,indent=0)
for r in rows: print(r['loc'],'|',r['period'],'|',r['vol'],'|',r['title'][:70])
