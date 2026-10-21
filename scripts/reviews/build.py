# Сборка data/reviews_cards.csv, data/reviews.csv, data/reviews_themes.csv
import sys, json, csv, re, collections, statistics
sys.path.insert(0,'/home/claude/zabory/notes/scripts/reviews')
from codebook import POS, themes
from manual_codes import MANUAL, MAP
from redact import redact
from registry import FULL, LIGHT, GATES
B='/home/claude/zabory/notes/raw_reviews'; D='/home/claude/zabory/data'
TODAY='2026-10-20'; Y12='2025-10-20'
GROUP={**{d:'полный разбор' for d in FULL},**{d:'облегчённо' for d in LIGHT},**{d:'откатные ворота' for d in GATES}}
GROUP['kupitzabor.ru']='облегчённо'
R=json.load(open(B+'/all_reviews.json'))
for r in R:
    if r['company']=='kupitzabor.ru': r['company']='moscow.kupitzabor.ru'
neg=[r for r in R if r['stars'] and r['stars']<=3]; neg.sort(key=lambda r:(r['company'],r['platform'],r['date']))
# облегчённые: только рейтинг и число — тексты в reviews.csv не включаются
NEG_OUT=lambda L:[r for r in L if GROUP.get(r['company'])!='облегчённо']
# ---------- ручная разметка негатива
AUTH_OVR={109:'неясно',523:'неясно',573:'неясно',655:'неясно',656:'неясно',721:'неясно'}
for i,r in enumerate(neg):
    r['themes']=MANUAL[i]; r['theme_method']='ручная'; r['author_type']=AUTH_OVR.get(i,'клиент')
# ---------- признаки накрутки по отзыву
norm=lambda t:' '.join((t or '').lower().split())[:180]
dupc=collections.Counter((r['platform'][:4],r['company'],norm(r['text'])) for r in R if len(r['text'] or '')>40)
day5=collections.Counter((r['card_id'],r['date']) for r in R if r['stars']==5)
for r in R:
    flags=[]
    if len(r['text'] or '')>40 and dupc[(r['platform'][:4],r['company'],norm(r['text']))]>1: flags.append('повтор текста на площадке')
    if r['stars']==5 and day5[(r['card_id'],r['date'])]>=4: flags.append(f"{day5[(r['card_id'],r['date'])]} пятёрок на карточке в один день")
    if r['platform'].startswith('2ГИС') and r['stars']==5 and r.get('author_reviews')==1: flags.append('единственный отзыв автора')
    r['susp']='; '.join(flags)
# ---------- выборка позитива: до 30 последних 4–5 с текстом на компанию (все площадки)
pos_sample=[]
byc=collections.defaultdict(list)
for r in R:
    if r['stars'] and r['stars']>=4 and len((r['text'] or '').strip())>=15 and GROUP.get(r['company'])=='полный разбор': byc[r['company']].append(r)
for c,rs in byc.items():
    rs.sort(key=lambda r:r['date'],reverse=True)
    for r in rs[:30]:
        r['themes']=themes(r['text'],POS); r['theme_method']='ключевые слова'; r['author_type']='клиент'; pos_sample.append(r)
def reply_sum(t):
    t=(t or '').strip()
    if not t: return ''
    s=redact(' '.join(t.split()))
    return s[:220]+('…' if len(s)>220 else '')
rows=NEG_OUT(neg)+pos_sample
with open(D+'/reviews.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['platform','company','group','card_id','source_url','date','stars','text','author_type','themes','theme_method','has_reply','reply_summary','is_suspicious','suspicion_signs','date_collected'])
    for r in sorted(rows,key=lambda r:(r['company'],-(r['stars'] or 0)<=-4,r['date']),reverse=False):
        txt=redact(' '.join((r['text'] or '').split()))
        w.writerow([r['platform'],r['company'],GROUP.get(r['company'],''),r['card_id'],r['url'],r['date'],r['stars'],txt,r['author_type'],'; '.join(r['themes']),r['theme_method'],
                    'да' if r['reply'] else ('нет' if r['platform']!='Отзовик' else 'не собиралось'),reply_sum(r['reply']),'да' if r['susp'] else 'нет',r['susp'],TODAY])
print('reviews.csv',len(rows),'neg',len(neg),'pos',len(pos_sample))
# ---------- темы компания × тема
NEGT=list(MAP.values()); POST=list(POS.keys())
with open(D+'/reviews_themes.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['company','group','polarity','theme','n_reviews_with_theme','base_n','share','method','note'])
    comps=sorted(set(r['company'] for r in rows))
    SEG={'РЫНОК: заборные компании (полный разбор)':'полный разбор','РЫНОК: специалисты по откатным воротам':'откатные ворота','РЫНОК (все компании)':None}
    for c in comps+list(SEG):
        sel=lambda rs:[r for r in rs if (c in SEG and (SEG[c] is None or GROUP.get(r['company'])==SEG[c])) or r['company']==c]
        nn=sel(NEG_OUT(neg)); pp=sel(pos_sample)
        for t in NEGT:
            k=sum(1 for r in nn if t in r['themes'])
            w.writerow([c,GROUP.get(c,'все'),'негатив (1–3★)',t,k,len(nn),round(k/len(nn),3) if nn else '', 'ручная разметка всех текстов 1–3★', 'база <30, доля незначима' if 0<len(nn)<30 else ''])
        for t in POST:
            k=sum(1 for r in pp if t in r['themes'])
            w.writerow([c,GROUP.get(c,'все'),'позитив (4–5★)',t,k,len(pp),round(k/len(pp),3) if pp else '', 'ключевые слова, выборка до 30 последних 4–5★', 'база <30, доля незначима' if 0<len(pp)<30 else ''])
    # позитив по всему массиву 4–5★ (контроль)
    allpos=[r for r in R if r['stars'] and r['stars']>=4 and len((r['text'] or '').strip())>=15 and GROUP.get(r['company'])=='полный разбор']
    for t in POST:
        k=sum(1 for r in allpos if t in themes(r['text'],POS))
        w.writerow(['РЫНОК: заборные компании (полный разбор)','полный разбор','позитив (4–5★), весь массив',t,k,len(allpos),round(k/len(allpos),3),'ключевые слова, все тексты 4–5★',''])
# ---------- карточки
cards=json.load(open(B+'/all_cards_yandex_2gis.json'))
for cd in cards:
    if cd['company']=='kupitzabor.ru': cd['company']='moscow.kupitzabor.ru'
ADDR2={'70000001087091390':'Пушкино, Октябрьская ул., 44','4504128908914181':'Москва, Ленинградский просп., 63','4504128908584094':'Люберцы, Красная ул., 1','70000001041681784':'Москва, Выборгская ул., 16 ст1',
'70000001024778617':'Пушкино, ул. Тургенева, 15а','70000001028833506':'Москва, ул. Яблочкова, 21 к3','70000001092543859':'ТК «Конструктор», МКАД 25 км, вл1','70000001092544108':'Рынок «Петровский», Новорижское ш. 26 км, д. Михалково',
'70000001092541801':'д. Белая, ул. Карла Маркса, 1','70000001092543401':'Селятино, строительный рынок, Киевское ш. 52 км','70000001100792943':'Ногинск, «Dega-Ногинск»','70000001064705381':'д. Ботово, Восточная ул., 5',
'70000001092542640':'Черноголовка, Школьный бульвар, 1а','70000001092544671':'Ногинск, ул. Ильича, 21 к2','70000001094268798':'ТК «Конструктор», МКАД 25 км','70000001087302255':'д. Аленино, Кольцевое ш., 2',
'70000001092544555':'Центральная ул., 3 (МО)','70000001092542464':'Орехово-Зуево, Северная ул., 55','70000001058994515':'Москва (адрес не указан)','70000001091458775':'Москва, ул. Яблочкова, 21 к3',
'70000001092802501':'Москва, Щёлковское ш., 5','4504127909231413':'Москва, Рязанский просп., 75 к4','4504127917489549':'Москва, ул. Кулакова, 20 ст1а','70000001088911786':'Москва, Киевское ш. 22 км, БЦ «Румянцево»',
'70000001049072461':'Москва, ул. Генерала Белова, 26','70000001036234081':'Москва, Куликовская ул., 12','70000001064682156':'Одинцово','70000001094257005':'ТЦ «Стройдом», 2-я Глуховская ул.','70000001099827495':'д. Никулино, 1',
'4504128908742689':'Москва, ул. Генерала Кузнецова, 18','70000001030064226':'Москва, Киевское ш. 22 км, БЦ «Румянцево»','70000001030300751':'Москва, ул. Адмирала Руднева, 2','70000001030323315':'Москва, Ленинградское ш., 236 ст1',
'70000001093911363':'Москва, ул. Коминтерна, 7 к2','70000001094748672':'Раменский округ'}
byid=collections.defaultdict(list)
for r in R: byid[(r['platform'][:4],r['card_id'])].append(r)
out=[]
for cd in cards:
    key=(cd['platform'][:4],cd['card_id']); rs=byid.get(key,[])
    st=collections.Counter(r['stars'] for r in rs)
    txt=[r for r in rs if (r['text'] or '').strip()]
    rep=sum(1 for r in rs if r['reply'])
    avg=round(statistics.mean([r['stars'] for r in rs]),2) if rs else ''
    rating=cd['rating']; rating=round(float(rating),2) if rating not in (None,'') else ''
    addr=cd['address'] or ADDR2.get(cd['card_id'],'')
    note=''
    if cd['platform']=='Яндекс Карты' and rs and rating and abs(float(rating)-avg)>=0.3: note=f'отображаемый рейтинг выше среднего по текстовым отзывам на {round(float(rating)-avg,2)}'
    if GROUP.get(cd['company'])=='облегчённо': note='облегчённый охват: только рейтинг и число отзывов'
    out.append(dict(platform=cd['platform'],company=cd['company'],group=GROUP.get(cd['company'],''),card_id=cd['card_id'],url=cd['url'],address=addr,rating=rating,ratings_count=cd['ratings_count'],
        text_reviews_count=cd['text_reviews'],collected=len(rs),stars_1=st[1] if rs else '',stars_2=st[2] if rs else '',stars_3=st[3] if rs else '',stars_4=st[4] if rs else '',stars_5=st[5] if rs else '',
        avg_stars_collected=avg,last_review_date=max([r['date'] for r in rs]) if rs else '',reviews_12m=sum(1 for r in rs if r['date']>=Y12) if rs else '',
        reply_share=round(rep/len(rs),3) if rs else '',date_collected=TODAY,note=note))
OTHER=[
 ('Отзовик','masterovit.ru','kompaniya_masterovit_russia_moscow','https://otzovik.com/reviews/kompaniya_masterovit_russia_moscow/','Москва',3.7,'',962,320,'собраны последние 320 из 962 (8 страниц), дальше площадка показала проверку «Вы робот?»'),
 ('Отзовик','zavodzaborov.ru','kompaniya_zavod_zaborov_russia_moscow','https://otzovik.com/reviews/kompaniya_zavod_zaborov_russia_moscow/','Москва',4.7,'',740,0,'только счётчик из поиска; тексты не собраны (проверка «Вы робот?»)'),
 ('Отзовик','zaboroff.ru','kompaniya_zaboroff_russia_moscow','https://otzovik.com/reviews/kompaniya_zaboroff_russia_moscow/','Москва',4.5,'',126,0,'только счётчик из поиска'),
 ('Отзовик','prof-zabory.ru','kompaniya_prof-zabori_russia_moscow','https://otzovik.com/reviews/kompaniya_prof-zabori_russia_moscow/','Москва',3.9,'',75,0,'только счётчик из поиска'),
 ('Отзовик','raduga-zaborov.ru','kompaniya_raduga_zaborov_russia_moscow','https://otzovik.com/reviews/kompaniya_raduga_zaborov_russia_moscow/','Москва',3.3,'',55,0,'только счётчик из поиска'),
 ('Отзовик','zaborovo.ru','kompaniya_zaborovo_russia_pushkino','https://otzovik.com/reviews/kompaniya_zaborovo_russia_pushkino/','Пушкино',4.2,'',55,0,'только счётчик из поиска'),
 ('Отзовик','zaborkin.ru','firma_zaborkin_russia_moscow','https://otzovik.com/reviews/firma_zaborkin_russia_moscow/','Москва',3.4,'',43,0,'только счётчик из поиска; второй профиль zaborkin/ — 2 отзыва, 1,0'),
 ('Отзовик','dostup-zabor.ru','kompaniya_po_ustanovke_zaborov_dostupnie_zabori_russia_moskovskaya_oblast','https://otzovik.com/reviews/kompaniya_po_ustanovke_zaborov_dostupnie_zabori_russia_moskovskaya_oblast/','МО',5.0,'',1,0,'только счётчик из поиска'),
 ('Отзовик','moskovskie-zabory.ru','kompaniya_moskovskie_zabori_russia_moscow','https://otzovik.com/reviews/kompaniya_moskovskie_zabori_russia_moscow/','Москва',3.3,'',156,0,'облегчённый охват'),
 ('Отзовик','gorodzaborov.ru','kompaniya_gorod_zaborov_russia_moscow','https://otzovik.com/reviews/kompaniya_gorod_zaborov_russia_moscow/','Москва',1.9,'',12,0,'облегчённый охват'),
 ('Отзовик','zabor-vam.ru','kompaniya_po_ustanovke_zaborov_zabor-vam_russia_moscow','https://otzovik.com/reviews/kompaniya_po_ustanovke_zaborov_zabor-vam_russia_moscow/','Москва',5.0,'',1,0,'облегчённый охват'),
 ('irecommend','zaborkin.ru','zaborkin-proizvodstvo-i-montazh-zaborov','https://irecommend.ru/content/zaborkin-proizvodstvo-i-montazh-zaborov','',1.0,2,2,0,'счётчик со страницы поиска'),
 ('irecommend','prof-zabory.ru','kompaniya-prof-zabory-moskva','https://irecommend.ru/content/kompaniya-prof-zabory-moskva','Москва',4.0,12,12,0,'счётчик со страницы поиска'),
 ('Zoon','masterovit.ru','','https://zoon.ru/search/?query=Мастеровит&city=msk','д. Марфин-Брод',3.6,'',4,0,'поиск Zoon; ещё карточка в Рузе 4,7 / 6 оценок'),
 ('Zoon','prof-zabory.ru','','https://zoon.ru/search/?query=Проф-заборы&city=msk','Пушкино, Октябрьская ул., 44',5.0,2,'',0,'карточка «Проф-заборы» в Ивантеевке (Советский пр.) 4,3 / 21 — принадлежность не подтверждена'),
 ('Zoon','zaborkin.ru','','https://zoon.ru/search/?query=Заборкин&city=msk','Каширское ш. / Варшавское ш.',4.4,'',11,0,'две карточки: Варшавское ш. 4,4 / 11 отзывов; Каширское ш. 3,0 / 1 оценка'),
 ('Zoon','zaborovo.ru','','https://zoon.ru/search/?query=Заборово&city=msk','Пушкино, ул. Тургенева, 15а',4.6,'',20,0,''),
 ('Zoon','oblzabor.ru','','https://zoon.ru/search/?query=Облзабор&city=msk','Москва, Каширское ш., 19 к1',4.8,'',31,0,''),
 ('Zoon','pskzabor.ru','','https://zoon.ru/search/?query=ПСК Забор&city=msk','Селятино',4.7,'',24,0,''),
 ('Zoon','zaboroff.ru','','https://zoon.ru/search/?query=Заборофф&city=msk','Москва',2.0,1,'',0,''),
 ('Zoon','raduga-zaborov.ru','','https://zoon.ru/search/?query=Радуга заборов&city=msk','Москва, Выборгская ул., 16',3.8,'',1,0,''),
 ('Zoon','zavodzaborov.ru','','https://zoon.ru/search/?query=ЗаводЗаборов&city=msk','Москва (ВДНХ / Семёновская)',3.8,'',1,0,'две карточки по 1 отзыву/оценке'),
 ('Яндекс Услуги','masterovit.ru','Masterovit-1691246','https://uslugi.yandex.ru/profile/Masterovit-1691246','',"",64,'',0,'64 оценки; балл в разметке не найден'),
 ('Яндекс Услуги','zavodzaborov.ru','Zavodzaborov-638406','https://uslugi.yandex.ru/profile/Zavodzaborov-638406','',4.8,24,'',0,''),
 ('Яндекс Услуги','prof-zabory.ru','Profzabory-255638','https://uslugi.yandex.ru/profile/Profzabory-255638','',"",4,'',0,'4 оценки'),
]
for p,c,cid,url,addr,rt,cnt,tr,col,note in OTHER:
    out.append(dict(platform=p,company=c,group=GROUP.get(c,''),card_id=cid,url=url,address=addr,rating=rt,ratings_count=cnt,text_reviews_count=tr,collected=col,stars_1='',stars_2='',stars_3='',stars_4='',stars_5='',
        avg_stars_collected='',last_review_date='',reviews_12m='',reply_share='',date_collected=TODAY,note=note))
# Отзовик Мастеровит — распределение по собранным
om=[r for r in R if r['platform']=='Отзовик']
st=collections.Counter(r['stars'] for r in om)
out_m=[o for o in out if o['platform']=='Отзовик' and o['company']=='masterovit.ru'][0]
out_m.update(stars_1=st[1],stars_2=st[2],stars_3=st[3],stars_4=st[4],stars_5=st[5],avg_stars_collected=round(statistics.mean(r['stars'] for r in om),2),last_review_date=max(r['date'] for r in om),reviews_12m=sum(1 for r in om if r['date']>=Y12))
out_m['note']+=f"; собранные охватывают {min(r['date'] for r in om)} – {max(r['date'] for r in om)}"
with open(D+'/reviews_cards.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0].keys())); w.writeheader()
    for o in sorted(out,key=lambda o:(o['group'],o['company'],o['platform'],-(o['ratings_count'] or 0) if isinstance(o['ratings_count'],int) else 0)): w.writerow(o)
print('cards',len(out))
json.dump({'neg':[{k:r[k] for k in ('platform','company','date','stars','themes','rid')} for r in neg]},open(B+'/neg_coded.json','w'),ensure_ascii=False)
