"""Публичные ленты Telegram-каналов конкурентов (t.me/s), окно 20.07–21.10.2026.
Выход: data/tg_posts_wave3.csv (без имён сотрудников и телефонов: текст сокращён до сути, телефоны и имена маскируются)."""
import re, csv, html, time, urllib.request
CH = {'masterovit.ru': 'masterovit_zabory', 'zaborkin.ru': 'zaborkin_ru'}
START = '2026-07-20'
PHONE = re.compile(r'\+?\d[\d\s\-()]{8,}\d')
NAMES = re.compile(r'\b(Ткачев\w*|Илья|Валерьевич|Евгений|Александр\w*)\b')
def get(u):
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
rows = []
for dom, ch in CH.items():
    before = None
    for _ in range(15):
        page = get(f'https://t.me/s/{ch}' + (f'?before={before}' if before else ''))
        posts = re.findall(r'<div class="tgme_widget_message_wrap.*?(?=<div class="tgme_widget_message_wrap|\Z)', page, re.S)
        if not posts:
            break
        ids = []
        for p in posts:
            m = re.search(r'data-post="[^/]+/(\d+)"', p)
            if not m:
                continue
            pid = int(m.group(1)); ids.append(pid)
            dt = re.search(r'<time datetime="([^"]+)"', p)
            date = dt.group(1)[:10] if dt else ''
            v = re.search(r'<span class="tgme_widget_message_views">([^<]+)</span>', p)
            views = v.group(1) if v else ''
            if views.endswith('K'):
                views = str(int(float(views[:-1]) * 1000))
            t = re.search(r'<div class="tgme_widget_message_text[^>]*>(.*?)</div>', p, re.S)
            text = html.unescape(re.sub(r'<br\s*/?>', '\n', re.sub(r'<(?!br)[^>]+>', '', t.group(1)))) if t else ''
            if date and date >= START:
                cost = re.search(r'Стоимость проекта[^:]*:\s*([\d\s ]+)₽', text)
                text_c = NAMES.sub('[имя]', PHONE.sub('[телефон]', re.sub(r'\s+', ' ', text))).strip()
                rows.append(dict(domain=dom, channel=f't.me/{ch}', post_url=f'https://t.me/{ch}/{pid}', date=date, views=views,
                                 ad_marking='да (Erid)' if 'erid' in text.lower() else 'нет',
                                 project_cost_rub=re.sub(r'\D', '', cost.group(1)) if cost else '',
                                 content=text_c[:300], source=f'Telegram, публичная лента t.me/s/{ch}, окно 20.07–21.10.2026', date_collected='2026-10-21'))
        oldest = min(ids) if ids else None
        if not oldest or before == oldest:
            break
        dts = re.findall(r'<time datetime="([^"]+)"', page)
        before = oldest
        if dts and min(dts)[:10] < START:
            break
        time.sleep(1)
rows = sorted({r['post_url']: r for r in rows}.values(), key=lambda r: (r['domain'], r['date']), reverse=True)
with open('/home/claude/zabory/data/tg_posts_wave3.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
from collections import Counter
print(Counter((r['domain'], r['ad_marking']) for r in rows))
for d in CH:
    v = [int(r['views']) for r in rows if r['domain'] == d and r['views'].isdigit()]
    c = sorted(int(r['project_cost_rub']) for r in rows if r['domain'] == d and r['project_cost_rub'])
    print(d, len([r for r in rows if r['domain'] == d]), min(v), max(v), c)
