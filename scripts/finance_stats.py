import csv, statistics as S
rows=[r for r in csv.DictReader(open('/home/claude/zabory/data/finance.csv'))]
core=[r for r in rows if r['role'] in ('полный разбор','облегчённо','ворота','связанная компания') and r['inn'] not in ('7805820136','7842469389','7714943243','7720824942','5258147744','9723124815')]
by={}
for r in core: by.setdefault((r['company'],r['inn'],r['role']),{})[r['year']]=r
f=lambda x: float(x) if x not in ('',None) else None
print('company|rev23|rev24|rev25|d25/24%|d25/23%|avg_margin3|margins|recdays25|emp25|rpe25')
dm=[];rd=[];mg=[]
for (c,inn,role),ys in by.items():
    rv={y:f(ys[y]['revenue_th_rub']) if y in ys else None for y in ('2023','2024','2025')}
    m=[f(ys[y]['net_margin_pct']) for y in ('2023','2024','2025') if y in ys and f(ys[y]['net_margin_pct']) is not None]
    d1=round((rv['2025']/rv['2024']-1)*100,1) if rv['2025'] and rv['2024'] else ''
    d2=round((rv['2025']/rv['2023']-1)*100,1) if rv['2025'] and rv['2023'] else ''
    am=round(sum(m)/len(m),1) if m else ''
    r25=ys.get('2025',{})
    print(c,'|',rv['2023'],'|',rv['2024'],'|',rv['2025'],'|',d1,'|',d2,'|',am,'|',m,'|',r25.get('receivable_days'),'|',r25.get('employees_avg'),'|',r25.get('revenue_per_employee_mln_rub'))
    if d1!='' : dm.append((c,d1))
    if r25.get('receivable_days'): rd.append(float(r25['receivable_days']))
    if am!='': mg.append(am)
print('n с двумя годами',len(dm),'падение',sum(1 for c,d in dm if d<0),'рост',sum(1 for c,d in dm if d>0))
print('медиана дней дебиторки 2025',S.median(rd),'n',len(rd))
print('медиана средней 3-летней маржи',S.median(mg),'n',len(mg))
