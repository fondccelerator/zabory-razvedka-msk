"""Разбор выгрузок Вордстата (присланы пользователем 21.10.2026): «Динамика» по месяцам и «Регионы».
Вход: загрузки пользователя (копируются в notes/raw_wordstat/); если загрузок нет — читать notes/raw_wordstat/*.csv через parse_raw(). Выход: data/ws_monthly.csv, data/brand_demand_ws.csv, data/wordstat_regions.csv.
Запуск: python3 -I parse_ws.py"""
import csv, glob, re, shutil, os
B = '/home/claude/zabory'
UP = '/root/.claude/uploads/97f9dc36-7fb1-518c-96b3-65ea34b0a075'
RAW = f'{B}/notes/raw_wordstat'
IDS = 'e74b1191 9c360d07 f0789727 4d29bc37 387896a8 8a781156 203fa16e 6d30b2c5 451de6bf 6338a442 eaf28433 3e6ceb4e 25483e3e 16bf9c51 191101cc 95863dee 75696423 d554a2c0 bb83cc07'.split()
MON = {m: i for i, m in enumerate('январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь'.split(), 1)}
BRANDS = {'мастеровит': 'masterovit.ru', 'профзаборы': 'prof-zabory.ru', 'заборкин': 'zaborkin.ru', 'завод заборов': 'zavodzaborov.ru',
          'радуга заборов': 'raduga-zaborov.ru', 'заборово': 'zaborovo.ru', 'облзабор': 'oblzabor.ru', 'доступные заборы': 'dostup-zabor.ru',
          'заборофф': 'zaboroff.ru', 'пск забор': 'pskzabor.ru'}
def n(s): return float(s.replace(' ', '').replace(' ', '').replace(',', '.'))
monthly, regions = [], []
for i in IDS:
    found = glob.glob(f'{UP}/{i}-*.csv')
    if not found:          # загрузки очищены — разбор из копий в notes/raw_wordstat
        continue
    src = found[0]
    txt = open(src, encoding='utf-8-sig').read().replace('\r', '\n')
    m = re.search(r'Динамика частотности запросов «(.+?)», по месяцам, (\S+) — (\S+), (.+?), все устройства', txt)
    if m:
        q, reg = m.group(1), m.group(4)
        kind = 'dyn'
    else:
        m = re.search(r'Частотность запросов «(.+?)» по регионам, (\S+) — (\S+), все устройства', txt)
        q, reg, kind = m.group(1), 'регионы', 'reg'
    slug = re.sub(r'\W+', '_', q).strip('_') + ('_' + ('msk_mo' if reg == 'Москва и область' else 'rf_bez_msk' if 'кроме' in reg else 'regiony'))
    dst = f'{RAW}/{kind}_{slug}.csv'; shutil.copyfile(src, dst)
    body = txt[m.end():]
    toks = [t.strip() for t in body.replace('\n', ';').split(';') if t.strip()]
    if kind == 'dyn':
        for j in range(0, len(toks) - 2, 3):
            mn, yr = toks[j].split()
            monthly.append(dict(query=q, region=reg, month=f'{yr}-{MON[mn]:02d}', count=int(n(toks[j + 1])), share_pct=toks[j + 2].replace(',', '.'),
                                brand_domain=BRANDS.get(q, ''), source=f'Вордстат, «Динамика», по месяцам, {m.group(2)}–{m.group(3)}, {reg}, все устройства; выгрузка пользователя {os.path.basename(dst)}',
                                date_collected='2026-10-21'))
    else:
        period = f'{m.group(2)}–{m.group(3)}'
        for j in range(0, len(toks) - 3, 4):
            regions.append(dict(query=q, region=toks[j], frequency=int(n(toks[j + 1])), share_pct=toks[j + 2].replace(',', '.'),
                                affinity_pct=n(toks[j + 3]), period=period,
                                source=f'Вордстат, «Регионы», {period}, все устройства; выгрузка пользователя {os.path.basename(dst)}', date_collected='2026-10-21'))
if not monthly:          # загрузок нет: разбор копий
    for src in sorted(glob.glob(f'{RAW}/*.csv')):
        txt = open(src, encoding='utf-8-sig').read().replace('\r', '\n')
        m = re.search(r'Динамика частотности запросов «(.+?)», по месяцам, (\S+) — (\S+), (.+?), все устройства', txt)
        if m:
            toks = [t.strip() for t in txt[m.end():].replace('\n', ';').split(';') if t.strip()]
            for j in range(0, len(toks) - 2, 3):
                mn, yr = toks[j].split()
                monthly.append(dict(query=m.group(1), region=m.group(4), month=f'{yr}-{MON[mn]:02d}', count=int(n(toks[j + 1])), share_pct=toks[j + 2].replace(',', '.'),
                                    brand_domain=BRANDS.get(m.group(1), ''), source=f'Вордстат, «Динамика», по месяцам, {m.group(2)}–{m.group(3)}, {m.group(4)}, все устройства; выгрузка пользователя {os.path.basename(src)}', date_collected='2026-10-21'))
        else:
            m = re.search(r'Частотность запросов «(.+?)» по регионам, (\S+) — (\S+), все устройства', txt)
            toks = [t.strip() for t in txt[m.end():].replace('\n', ';').split(';') if t.strip()]
            for j in range(0, len(toks) - 3, 4):
                regions.append(dict(query=m.group(1), region=toks[j], frequency=int(n(toks[j + 1])), share_pct=toks[j + 2].replace(',', '.'),
                                    affinity_pct=n(toks[j + 3]), period=f'{m.group(2)}–{m.group(3)}',
                                    source=f'Вордстат, «Регионы», {m.group(2)}–{m.group(3)}, все устройства; выгрузка пользователя {os.path.basename(src)}', date_collected='2026-10-21'))
def w(path, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        d = csv.DictWriter(f, fieldnames=list(rows[0].keys())); d.writeheader(); d.writerows(rows)
w(f'{B}/data/ws_monthly.csv', monthly)
w(f'{B}/data/brand_demand_ws.csv', [dict(brand=r['query'], month=r['month'], frequency=r['count']) for r in monthly if r['brand_domain'] and r['region'] == 'Москва и область'])
w(f'{B}/data/wordstat_regions.csv', regions)
from collections import Counter
print(Counter((r['query'], r['region']) for r in monthly)); print(Counter(r['query'] for r in regions))
