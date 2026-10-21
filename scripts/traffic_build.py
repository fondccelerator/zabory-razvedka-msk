"""Сборка CSV этапа traffic из сырых выгрузок Similarweb Pro (notes/raw_traffic/*.txt)."""
import csv
import os
import re

BASE = '/home/claude/zabory'
RAW = os.path.join(BASE, 'notes', 'raw_traffic')
DATA = os.path.join(BASE, 'data')
DATE = '20.10.2026'
PERIOD = 'июль–сентябрь 2026'
SRC_CMP = 'Similarweb Pro, Website analysis → Overview → Website performance (сравнение 5 доменов), Worldwide, весь трафик'
SRC_ONE = 'Similarweb Pro, Website performance (один домен), Worldwide'
LIMIT = 'не собрано: дневной лимит пробного Similarweb Pro («Daily usage limit reached») 20.10.2026'

GROUPS = {
    'полный разбор': ['masterovit.ru', 'prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru',
                      'zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru'],
    'второй сайт': ['zabor-dlya-vseh.site', 'p-z-z.ru', 'sales.prof-zabory.ru'],
    'облегчённо': ['zabormo.ru', 'pro-zabor.ru', 'kupitzabor.ru', '33zabora.ru', 'zabor-vam.ru', 'good-zabor.ru',
                   'moskovskie-zabory.ru', 'ligazaborov.ru', 'zabory-deshevo.ru', 'gorodzaborov.ru'],
    'ворота': ['alusys.ru', 'vorota750.ru', 'gruppa-masterov.ru', 'atlantzabor.ru', 'metalsystems.ru'],
}
GROUP_OF = {d: g for g, ds in GROUPS.items() for d in ds}
CMP_SET = {'masterovit.ru': 'группа 1', 'prof-zabory.ru': 'группа 1', 'zaborkin.ru': 'группа 1',
           'zavodzaborov.ru': 'группа 1', 'raduga-zaborov.ru': 'группа 1', 'zaborovo.ru': 'группа 2',
           'oblzabor.ru': 'группа 2', 'dostup-zabor.ru': 'группа 2', 'zaboroff.ru': 'группа 2', 'pskzabor.ru': 'группа 2'}

CH_MAP = [('Direct', 'Прямые'), ('Email', 'Почта'), ('Referrals', 'Переходы с сайтов'),
          ('Social - Organic', 'Соцсети органические'), ('Social - Paid', 'Соцсети платные'),
          ('Search - Organic', 'Поиск органический'), ('Search - Paid', 'Поиск платный'),
          ('Display Ads', 'Медийная реклама'), ('Gen AI', 'ИИ-ассистенты'), ('Affiliates', 'Партнёрские')]


def read_lines(name):
    with open(os.path.join(RAW, name), encoding='utf-8') as f:
        return [l.rstrip('\n') for l in f if l.strip() and not l.startswith('#')]


def parse_channels(s):
    out = {}
    for name, _ in CH_MAP:
        m = re.search(re.escape(name) + r':(\d+)', s)
        out[name] = int(m.group(1)) if m else 0
    return out


ov, ch, so = {}, {}, {}
for fn in ['ov_g1.txt', 'ov_g2.txt']:
    for l in read_lines(fn):
        p = l.split('|')
        if p[0] == 'OV':
            months = dict(x.split(':') for x in p[4].split(','))
            ds, ms = (p[11].split('/') + ['', ''])[:2]
            ov[p[1]] = dict(visits=int(p[2]), change=float(p[3]), jul=int(months['2026-07']), aug=int(months['2026-08']),
                            sep=int(months['2026-09']), avg=int(p[5]), uu=int(p[6]), dedup=int(p[7]), dur=int(p[8]),
                            ppv=float(p[9]), bounce=float(p[10]), desk=float(ds), mob=float(ms))
        elif p[0] == 'CH':
            ch[p[1]] = parse_channels(p[2])
        elif p[0] == 'SO':
            so[p[1]] = p[2]

# прежний съём Similarweb из data/competitors.csv (визиты за июль–сентябрь 2026)
prior = {}
with open(os.path.join(DATA, 'competitors.csv'), encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if r['visits_jul_sep_2026']:
            prior[r['domain']] = int(r['visits_jul_sep_2026'])

RU_SHARE = {'masterovit.ru': ('83,1', 'Similarweb Pro, Website performance (один домен), Geography')}
RU_GROUP2 = '98,0 (по группе 2 в целом)'

LOW = 5000  # порог надёжности по методике: от 5 000 визитов в месяц


def pct(x):
    return f'{x * 100:.1f}'.replace('.', ',')


def num(x, nd=2):
    return f'{x:.{nd}f}'.replace('.', ',')


rows = []
all_domains = [d for ds in GROUPS.values() for d in ds]
for d in all_domains:
    g = GROUP_OF[d]
    if d in ov:
        o = ov[d]
        if d in RU_SHARE:
            ru = RU_SHARE[d]
        elif CMP_SET.get(d) == 'группа 2':
            ru = (RU_GROUP2, SRC_CMP + ', Geography (только по группе)')
        else:
            ru = ('не найдено', 'в сравнении группы 1 виджет Geography вернул 403')
        mins, secs = divmod(o['dur'], 60)
        rows.append({
            'domain': d, 'group': g, 'status': 'собрано',
            'visits_3m': o['visits'], 'visits_2026_07': o['jul'], 'visits_2026_08': o['aug'], 'visits_2026_09': o['sep'],
            'avg_month_visits': o['avg'], 'change_vs_prev_3m_pct': pct(o['change']),
            'unique_visitors_avg_month': o['uu'], 'unique_visitors_dedup': o['dedup'],
            'avg_visit_duration': f'{mins}:{secs:02d}', 'avg_visit_duration_sec': o['dur'],
            'pages_per_visit': num(o['ppv']), 'bounce_rate_pct': pct(o['bounce']),
            'desktop_pct': pct(o['desk']), 'mobile_pct': pct(o['mob']),
            'russia_share_pct': ru[0],
            'reliability': 'модельная оценка: меньше 5 000 визитов в месяц' if o['avg'] < LOW else 'выше порога 5 000 визитов в месяц',
            'visits_3m_prior_stage': prior.get(d, ''),
            'months_12': 'не собрано: пробный доступ отдаёт только 3 месяца (12m → 3m)',
            'source': f'{SRC_CMP} ({CMP_SET[d]}); помесячно — виджет Visits over time; Россия — {ru[1]}',
            'period': PERIOD, 'date': DATE,
        })
    else:
        note = LIMIT
        if d == 'sales.prof-zabory.ru':
            note += '; поддомен отдельно в Similarweb не считается, входит в prof-zabory.ru (includeSubDomains)'
        rows.append({'domain': d, 'group': g, 'status': note,
                     'visits_3m_prior_stage': prior.get(d, ''),
                     'source': ('визиты прошлого съёма — data/competitors.csv (Similarweb, июль–сентябрь 2026)' if d in prior else ''),
                     'period': PERIOD, 'date': DATE})

ov_fields = ['domain', 'group', 'status', 'visits_3m', 'visits_2026_07', 'visits_2026_08', 'visits_2026_09',
             'avg_month_visits', 'change_vs_prev_3m_pct', 'unique_visitors_avg_month', 'unique_visitors_dedup',
             'avg_visit_duration', 'avg_visit_duration_sec', 'pages_per_visit', 'bounce_rate_pct', 'desktop_pct',
             'mobile_pct', 'russia_share_pct', 'reliability', 'visits_3m_prior_stage', 'months_12', 'source', 'period', 'date']
with open(os.path.join(DATA, 'traffic_overview.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=ov_fields)
    w.writeheader()
    w.writerows(rows)

# каналы: одна формула для всех цифр — визиты канала = визиты сайта за 3 мес × доля канала
# доля канала — как в Similarweb Marketing channels (визиты канала / сумма каналов); сырые визиты каналов — только в notes/raw_traffic
MODEL4 = {'raduga-zaborov.ru', 'zaborovo.ru', 'zaboroff.ru', 'pskzabor.ru'}
RU = {d: r['russia_share_pct'] for r in rows for d in [r['domain']] if r.get('russia_share_pct')}
NOTE_DISPLAY = ('площадки медийки у masterovit.ru и zaborovo.ru — yandex.ru / ya.ru, у prof-zabory.ru — web.max.ru; '
                'у Яндекса это, вероятно, клики рекламы Директа и РСЯ; деление с платным поиском уточнится в волне 2 (Spywords, Keys.so РСЯ)')
SHARES = {}
ch_rows = []
for d in all_domains:
    if d not in ch:
        continue
    c = ch[d]
    total = sum(c.values())
    V = ov[d]['visits']
    SHARES[d] = {n: c[n] / total for n, _ in CH_MAP}
    for name, ru in CH_MAP:
        sh = c[name] / total
        note = []
        if d in MODEL4:
            note.append('модель Similarweb: шаблонная структура каналов')
        if ov[d]['avg'] < LOW:
            note.append('меньше 5 000 визитов в месяц')
        if name in ('Display Ads', 'Search - Paid'):
            note.append(NOTE_DISPLAY)
        ch_rows.append({'domain': d, 'group': GROUP_OF[d], 'channel': ru, 'channel_similarweb': name,
                        'share_pct': num(sh * 100, 2), 'site_visits_3m': V,
                        'channel_visits_3m': round(V * sh), 'formula': 'визиты сайта за 3 мес × доля канала',
                        'region': 'весь мир', 'russia_share_pct': RU.get(d, ''),
                        'note': '; '.join(note),
                        'source': f'{SRC_CMP} ({CMP_SET[d]}), Marketing channels',
                        'period': PERIOD, 'date': DATE})
with open(os.path.join(DATA, 'traffic_channels.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(ch_rows[0].keys()))
    w.writeheader()
    w.writerows(ch_rows)

# широкая таблица: доли и визиты по той же формуле
def slug(n):
    return re.sub(r'[^a-z]+', '_', n.lower()).strip('_')

with open(os.path.join(DATA, 'traffic_channels_wide.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['domain', 'visits_3m'] + [slug(n) + '_pct' for n, _ in CH_MAP] + [slug(n) + '_visits' for n, _ in CH_MAP]
               + ['paid_total_pct', 'paid_total_visits', 'reliability', 'region', 'russia_share_pct', 'note', 'source', 'date'])
    for d in all_domains:
        if d not in SHARES:
            continue
        S = SHARES[d]
        V = ov[d]['visits']
        paid = S['Search - Paid'] + S['Display Ads'] + S['Social - Paid']
        rel = 'модель Similarweb: шаблонная структура каналов' if d in MODEL4 else ''
        if ov[d]['avg'] < LOW:
            rel = (rel + '; ' if rel else '') + 'меньше 5 000 визитов в месяц'
        w.writerow([d, V] + [num(S[n] * 100, 2) for n, _ in CH_MAP] + [round(V * S[n]) for n, _ in CH_MAP]
                   + [num(paid * 100, 1), round(V * paid), rel or 'выше порога', 'весь мир', RU.get(d, ''),
                      'платные каналы суммарно = платный поиск + медийная + платные соцсети, оценка Similarweb; ' + NOTE_DISPLAY,
                      SRC_CMP + '; визиты канала = визиты за 3 мес × доля', DATE])

import json
with open(os.path.join(BASE, 'notes', 'raw_traffic', 'shares.json'), 'w', encoding='utf-8') as f:
    json.dump({d: {'visits': ov[d]['visits'], 'shares': SHARES[d]} for d in SHARES}, f, ensure_ascii=False, indent=1)
print('overview', len(rows), 'channels', len(ch_rows))
