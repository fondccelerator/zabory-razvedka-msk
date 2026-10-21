import sys, json, time, random
sys.path.insert(0,'.')
from ya_search import search
import requests
Q={
 'masterovit.ru':['Мастеровит','masterovit.ru'],
 'prof-zabory.ru':['ПрофЗаборы','Проф заборы','prof-zabory.ru'],
 'zaborkin.ru':['Заборкин','zaborkin.ru'],
 'zavodzaborov.ru':['Завод заборов','zavodzaborov.ru','Забор для всех'],
 'raduga-zaborov.ru':['Радуга заборов'],
 'zaborovo.ru':['Заборово','zaborovo.ru','p-z-z.ru','Подмосковный завод заборов'],
 'oblzabor.ru':['Облзабор','oblzabor.ru'],
 'dostup-zabor.ru':['Доступ забор','Доступный забор','dostup-zabor.ru'],
 'zaboroff.ru':['Заборофф','zaboroff.ru','Забороff'],
 'pskzabor.ru':['ПСК Забор','pskzabor.ru'],
 'zabormo.ru':['zabormo.ru','Забор МО'],
 'pro-zabor.ru':['pro-zabor.ru','Про забор'],
 'kupitzabor.ru':['kupitzabor.ru','Купить забор'],
 '33zabora.ru':['33 забора','33zabora.ru'],
 'zabor-vam.ru':['zabor-vam.ru','Забор вам'],
 'good-zabor.ru':['good-zabor.ru','Гуд забор'],
 'moskovskie-zabory.ru':['Московские заборы','moskovskie-zabory.ru'],
 'ligazaborov.ru':['Лига заборов','ligazaborov.ru'],
 'zabory-deshevo.ru':['Заборы дешево','zabory-deshevo.ru'],
 'gorodzaborov.ru':['Город заборов','gorodzaborov.ru'],
 'alusys.ru':['Алюсис','alusys.ru'],
 'vorota750.ru':['Ворота 750','vorota750.ru'],
 'naves-pod-avto-msk.ru':['naves-pod-avto-msk.ru','Навес под авто'],
 'otkatnie-vorota.com':['otkatnie-vorota.com'],
 'gruppa-masterov.ru':['Группа мастеров ворота','gruppa-masterov.ru'],
 'metalsystems.ru':['Металлические системы','metalsystems.ru'],
 'zabory-prestige.ru':['Заборы Престиж','zabory-prestige.ru'],
 'atlantzabor.ru':['Атлант забор','atlantzabor.ru'],
}
s=requests.Session(); out={}
only=sys.argv[1:] or list(Q)
for dom in only:
    out[dom]=[]
    for q in Q[dom]:
        st,res=search(q,s=s)
        out[dom].append({'q':q,'status':st,'res':res})
        time.sleep(1.5+random.random())
    print(dom, [(r['q'],r['status'],len(r['res'])) for r in out[dom]], flush=True)
json.dump(out,open('/home/claude/zabory/notes/raw_reviews/ya_discover.json','w'),ensure_ascii=False,indent=1)
