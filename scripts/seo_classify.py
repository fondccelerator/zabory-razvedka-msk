"""Этап seo, шаг 2: классификация URL из sitemap по типам страниц.
Вход: raw_seo/<domain>/urls.txt. Выход: raw_seo/<domain>/classified.tsv и сводка JSON raw_seo/classified_summary.json"""
import re, json, os, sys, collections, urllib.parse as up

ROOT = '/home/claude/zabory/raw_seo'

def norm(s):
    s = s.lower()
    for a, b in (('kh', 'h'), ('ts', 'c'), ('shch', 'sch'), ('shh', 'sch'), ('yo', 'e'), ('jo', 'e'), ('ya', 'ja'), ('yu', 'ju'), ('iy', 'ij'), ('yy', 'ij'), ('y', 'j')):
        s = s.replace(a, b)
    return s

# Основы названий городов/районов МО и соседних областей (транслит нормализуется функцией norm)
GEO_STEMS = '''odinc krasnogorsk balash podolsk himk mytisch ljuber lubert kolomn elektrostal sergiev scholk schelk sch-lk noginsk ramensk zhukovsk
pushkin dmitrov istr ruza ruz- chehov serpuh domodedov vidno lobn dolgoprudn korolev korol-v reutov frjazin ivanteev dubn klinsk solnechnogorsk
zelenograd naro-fom narofom mozhajsk mozhaj volokolamsk shatur egorevsk egorjevsk voskresensk stupin kashir zarajsk luhovic ozer ozjor orehovo pavlovsk
elektrogorsk kurovsk likino roshal taldom jahrom lytkarin dzerzhinsk kotelnik bronnic zvenigorod krasnoarmejsk losino chernogolovk hotkov kubink golicyn
aprelevk troick moskovskij scherbink novaja-moskv rublev novorizh kaluzh tuls tversk vladimirsk rjazansk jaroslavsk smolensk obninsk aleksandrov kirzhach
kolchugin borovsk mihnev vereja elektrougl staraja-kupavn kupavn shhelk krasnozavodsk dedovsk tarasovk pirogov sofrino bolshevo jubilejn mozhajsk
lesnoj-gorodok nahabin snegir iksha dmitrovsk kratov malahovk tomilin kraskov udeln bykovo ilinsk vnukov kokoshkin moskovsk-oblast moskovskaja-oblast
podmoskov /klin/ golicin lotoshin tuchkov shahovsk ehlektrostal /tula/ shodn konobeev klimovsk povarov ashukin bojarkin rajon rajone -rn- region regiony regions oblast'''.split()
GEO_STEMS = [norm(x) for x in GEO_STEMS + open('/home/claude/zabory/raw_seo/_ref/geo_stems.txt').read().split()]

MATERIALS = {
    'профнастил': r'prof-?nast|proflist|profnastil|proflista|metalloprofil|profil-?nyj|profnastil',
    'евроштакетник/металлоштакетник': r'shtaket|euro-?sht|evrosht|metallosht|evroshtak',
    'сетка-рабица': r'rabic|rabits|rabica',
    '3D/сварная сетка': r'(^|[-/])3d|gitter|svarn|setk[ai]-?3d|panelnyj|sekcion',
    'жалюзи': r'zhaljuz|zhaluz|zhaljuzi|zhalyuz|zhaluzi',
    'дерево': r'derev|pod-derevo|doska|brus|plank|rancho',
    'кирпич/столбы': r'kirpich|stolb',
    'ковка/сварной металл': r'kovan|kovk|metallicheskie|metalliches',
    'бетон/ЖБ': r'beton|zhb|evrozabor|monolit',
    'поликарбонат': r'polikarbonat',
    'габион/камень': r'gabion|kamen',
}

GEO_RX = re.compile('(^|[/_-])(' + '|'.join(re.escape(x.strip('/-')) for x in GEO_STEMS if x.strip('/-')) + ')')

def is_geo(path_n):
    return bool(GEO_RX.search(path_n)) or bool(re.search(r'(^|[/_-])klin(u|e|a|om)?($|[/_-])', path_n))

RULES = [  # (тип, regex по нормализованному пути) — порядок важен
    ('портфолио/наши работы', r'portfolio|nashi[-_]raboty|vypolnennye|/raboty|cases/|gallery|galleries|foto-zabor|photo-|karta-obekt|nashi-raboty|realizovann|obekty|/works'),
    ('видео', r'(^|/)video|videoreview'),
    ('вопрос-ответ/FAQ', r'vopros|faq'),
    ('статьи/блог/новости', r'blog|stat[ij]|articles?|news|novost|info/news|/tpost/|poleznoe|sovety'),
    ('цены/калькулятор', r'cen[ay]|price|prajs|calc|kalkuljator|kalk|smeta|stoimost|calculate'),
    ('акции', r'akci|akczi|aktsi|discount|skidk|sale|rasprodazh|action'),
    ('компания/служебные', r'o-kompanii|company|o-nas|about|kontakt|contact|rekvizit|requisites|privacy|politik|police|personal|policy|legal|vakans|vacancy|garanti|dostavka|oplata|otzyv|reviews|sertifikat|certificates|sitemap|karta-sajta|dilera|postavsch|korzin|favorites|compare|data-terms|oferta|staff|nagrad|proizvodstvo|kak-sdelat|pravila|terms|search|login|quiz|opros|information'),
    ('ворота: откатные', r'otkat|gates/otk|sliding|razdvizh'),
    ('ворота и калитки: прочие', r'vorot|gates|kalitk|shlagbaum|avtomatika|privod'),
    ('навесы', r'naves|pergol|parking|besedk|avtomobilnye'),
    ('сваи/фундамент', r'^/(vintovye-)?sva[ij]|^/fundament|^/svai'),
    ('материалы (продажа)', r'materialy|materialyi|/shop/|katalog-stroitelnyh|furnitur|soputstv|komplektuj|tproduct'),
    ('заборы и ограждения', r'zabor|ograzhd|ograzd|ogragd|ograd|ogragzd|profnast|proflist|shtaket|rabic|rabits|3d|gitter|zhaljuz|setk|section|column|stolb|sekcion|svarn|kovk|demontazh|mont|ustanov|uslugi|services|catalog|product'),
]

def classify(url):
    p = up.urlparse(url)
    path = up.unquote(p.path).lower()
    pn = norm(path)
    if path in ('', '/'):
        return 'главная', False, []
    t = 'прочее'
    for name, rx in RULES:
        if re.search(rx, path) or re.search(rx, pn):
            t = name; break
    geo = is_geo(pn) and t not in ('статьи/блог/новости', 'вопрос-ответ/FAQ', 'портфолио/наши работы', 'компания/служебные', 'видео')
    if geo:
        t = 'города/районы (гео)'
    mats = [m for m, rx in MATERIALS.items() if re.search(rx, pn)]
    return t, geo, mats

def main(domains):
    summary = {}
    for d in domains:
        f = os.path.join(ROOT, d, 'urls.txt')
        if not os.path.exists(f):
            continue
        urls = [x for x in open(f).read().split('\n') if x]
        rows = []
        cnt = collections.Counter(); geo_cnt = collections.Counter(); mat_cnt = collections.Counter()
        for u in urls:
            t, geo, mats = classify(u)
            rows.append((u, t, 'да' if geo else '', ';'.join(mats)))
            cnt[t] += 1
            if geo:
                geo_cnt[t] += 1
            if t in ('заборы и ограждения', 'ворота: откатные', 'ворота и калитки: прочие', 'материалы (продажа)', 'города/районы (гео)'):
                for m in mats:
                    mat_cnt[m] += 1
        with open(os.path.join(ROOT, d, 'classified.tsv'), 'w') as fh:
            for r in rows:
                fh.write('\t'.join(r) + '\n')
        summary[d] = {'total': len(urls), 'types': dict(cnt), 'geo_by_type': dict(geo_cnt), 'geo_total': sum(geo_cnt.values()), 'materials': dict(mat_cnt)}
        print(d, len(urls), dict(cnt), 'geo', sum(geo_cnt.values()))
    json.dump(summary, open(os.path.join(ROOT, 'classified_summary.json'), 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main(sys.argv[1:] or sorted(x for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, x))))
