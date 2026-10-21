#!/usr/bin/env python3
"""Сборка сайта-отчёта «Заборы и откатные ворота, Москва и МО» для «Дома гирлянд».

Запуск (из любой папки):
    python3 -I /home/claude/zabory/notes/scripts/build_site.py            # страница + CSV, картинки только недостающие
    python3 -I /home/claude/zabory/notes/scripts/build_site.py --images   # пересжать все картинки

Читает data/*.csv, data/keys_queries_msk.json, notes/*_spravka.md, notes/answers.md,
notes/reviews_quotes.md, qa/checks_*.csv, img/**. Пишет site/index.html, site/img/, site/data/.

Волна 2 (подхватывается автоматически, если файлы появятся):
- data/ads.csv           — объявления Директа на поиске и РСЯ (любые колонки; ожидаются company/domain, platform, text, ...);
- data/ad_budgets.csv    — бюджеты: domain, budget_month_rub (и опционально queries, ads_unique, source);
- data/brand_demand.csv  — колонка monthly_frequency с числами → график бренд-спроса;
- data/wordstat_dynamics.csv — новые запросы с помесячными значениями → дополнительные ряды сезонности.
Пока данных нет, на их месте стоят заглушки «в работе: досъём».
"""
import csv
from collections import Counter
import html
import json
import math
import re
import shutil
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'data'
N = ROOT / 'notes'
Q = ROOT / 'qa'
IMG = ROOT / 'img'
SITE = ROOT / 'site'
SIMG = SITE / 'img'
SDATA = SITE / 'data'

DATE = '21.10.2026'
WAVE2 = 'в работе: досъём'
FORCE_IMAGES = '--images' in sys.argv

MAIN = ['masterovit.ru', 'prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru',
        'zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']
NAMES = {'masterovit.ru': 'Мастеровит', 'prof-zabory.ru': 'ПрофЗаборы', 'zaborkin.ru': 'Заборкин',
         'zavodzaborov.ru': 'ЗаводЗаборов', 'raduga-zaborov.ru': 'Радуга заборов', 'zaborovo.ru': 'Заборово',
         'oblzabor.ru': 'Облзабор', 'dostup-zabor.ru': 'Доступные заборы', 'zaboroff.ru': 'Заборофф',
         'pskzabor.ru': 'ПСК Забор'}
SECOND = {'prof-zabory.ru': 'sales.prof-zabory.ru', 'zavodzaborov.ru': 'zabor-dlya-vseh.site', 'zaborovo.ru': 'p-z-z.ru'}

esc = html.escape


# ---------------------------------------------------------------- helpers
def rows(name):
    with open(D / f'{name}.csv', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def num(s):
    if s is None:
        return None
    s = str(s).replace('\xa0', '').replace(' ', '').replace(',', '.').replace('%', '').strip()
    try:
        return float(s)
    except ValueError:
        return None


def fnum(v, d=0):
    """Русский формат числа: неразрывный пробел в тысячах, запятая."""
    if v is None:
        return '—'
    s = f'{v:,.{d}f}'.replace(',', ' ').replace('.', ',')
    return s


def pct(v, d=1):
    return '—' if v is None else fnum(v, d) + '%'


def short(t, n):
    t = t or ''
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(' ', 1)[0].rstrip(',;:—- ')
    return cut + '…'


def dname(d):
    return NAMES.get(d, d)


NAME_RE = re.compile(r'(?:ИП\s+)?[А-ЯЁ][а-яё]+(?:\s[А-ЯЁ][а-яё]+)?\s[А-ЯЁ]\.\s?[А-ЯЁ]\.')


def strip_names(s):
    s = re.sub(r'ИП\s+[А-ЯЁ][а-яё]+\s[А-ЯЁ]\.\s?[А-ЯЁ]\.', 'ИП', s)
    s = re.sub(r'ИП\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){0,2}', 'ИП', s)
    s = re.sub(r'\s*\((?:[А-ЯЁ][а-яё]+\s[А-ЯЁ]\.\s?[А-ЯЁ]\.(?:,\s*)?)+\)', '', s)
    s = NAME_RE.sub('', s)
    return s


STYLE_FIX = {'это сверка, а не прогноз': 'это сверка; прогноз строится на базовой конверсии',
             'поэтому H8 проверяет допущение, а не подтверждает канал': 'поэтому H8 проверяет допущение; подтверждением канала один кейс служить не может'}
FILE_HINT = r'(?:data/|notes/|qa/|scripts/|img/|raw_|\.csv|\.md\b|\.py\b|\.json\b|\.js\b)'


def clean(s):
    """Убирает ссылки на рабочие файлы и скрипты из текста справок."""
    s = re.sub(r'\s*\((?:[^()]*?' + FILE_HINT + r'[^()]*?)\)', '', s)
    s = re.sub(r'`([^`]*)`', lambda m: '' if re.search(FILE_HINT, m.group(1)) else m.group(1), s)
    s = re.sub(r'\b[\w./*-]+' + r'\.(?:csv|md|py|json|js)\b', '', s)
    s = re.sub(r'\(\s*[,;]?\s*\)', '', s)
    s = re.sub(r'[ \t]{2,}', ' ', s)
    s = re.sub(r'\s+([,.;:])', r'\1', s)
    s = s.replace('скилл ', '')
    for a, b in STYLE_FIX.items():
        s = s.replace(a, b)
    s = re.sub(r'\s*\((?:C\d{2})[^()]*\)', '', s)
    s = re.sub(r'\bC\d{2}(?:\s*[≥=]\s*\d)?\b,?\s*', '', s)
    s = re.sub(r'\(\s*[,;]?\s*\)', '', s)
    return s.strip()


TAG_RE = re.compile(r'\[(ФАКТ|ВЫВОД|ГИПОТЕЗА|ОЦЕНКА|ОГРАНИЧЕНИЕ)([^\]]*)\]')
TAG_CLS = {'ФАКТ': 'fact', 'ВЫВОД': 'concl', 'ГИПОТЕЗА': 'hyp', 'ОЦЕНКА': 'est', 'ОГРАНИЧЕНИЕ': 'lim'}


def inline(s, names=False):
    s = clean(s)
    if names:
        s = strip_names(s)
    s = esc(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = TAG_RE.sub(lambda m: f'<span class="tag tag-{TAG_CLS[m.group(1)]}">{m.group(1).lower()}{m.group(2)}</span>', s)
    return s


LIST_RE = re.compile(r'^(\s*)([-*]|\d+\.)\s+(.*)')


def md_table(lines):
    out = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-{2,}:?', c) for c in cells if c):
            continue
        out.append(cells)
    return out


def table_html(tab, names=False, cls='tbl'):
    if not tab:
        return ''
    head, body = tab[0], tab[1:]
    h = ''.join(f'<th>{inline(c, names)}</th>' for c in head)
    b = ''.join('<tr>' + ''.join(f'<td>{inline(c, names)}</td>' for c in r) + '</tr>' for r in body)
    return f'<div class="tscroll"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def md_html(text, names=False):
    lines = text.strip('\n').split('\n')
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if ln.lstrip().startswith('|'):
            block = []
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                block.append(lines[i])
                i += 1
            out.append(table_html(md_table(block), names))
            continue
        if ln.startswith('#'):
            out.append(f'<h4>{inline(ln.lstrip("#").strip(), names)}</h4>')
            i += 1
            continue
        m = LIST_RE.match(ln)
        if m:
            ordered = m.group(2)[0].isdigit()
            items = []
            while i < len(lines):
                m2 = LIST_RE.match(lines[i])
                if m2:
                    items.append([len(m2.group(1)) > 0, m2.group(3)])
                    i += 1
                elif lines[i].strip() and lines[i].startswith('  ') and items:
                    items[-1][1] += ' ' + lines[i].strip()
                    i += 1
                else:
                    break
            tag = 'ol' if ordered else 'ul'
            html_items, j = [], 0
            while j < len(items):
                sub, txt = items[j]
                li = inline(txt, names)
                j += 1
                subs = []
                while j < len(items) and items[j][0]:
                    subs.append(f'<li>{inline(items[j][1], names)}</li>')
                    j += 1
                if subs:
                    li += '<ul>' + ''.join(subs) + '</ul>'
                html_items.append(f'<li>{li}</li>')
            out.append(f'<{tag}>' + ''.join(html_items) + f'</{tag}>')
            continue
        para = [ln]
        i += 1
        while i < len(lines) and lines[i].strip() and not LIST_RE.match(lines[i]) \
                and not lines[i].lstrip().startswith('|') and not lines[i].startswith('#'):
            para.append(lines[i])
            i += 1
        out.append(f'<p>{inline(" ".join(para), names)}</p>')
    return '\n'.join(out)


def md_sections(path, level=2):
    text = Path(path).read_text(encoding='utf-8')
    mark = '#' * level + ' '
    secs, cur, buf = {}, None, []
    for ln in text.split('\n'):
        if ln.startswith(mark):
            if cur is not None:
                secs[cur] = '\n'.join(buf)
            cur, buf = ln[len(mark):].strip(), []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        secs[cur] = '\n'.join(buf)
    return secs


def sec(secs, start):
    for k, v in secs.items():
        if k.startswith(start):
            return v
    raise KeyError(start)


# ---------------------------------------------------------------- images
def prep_img(src, dst, width, max_h=None, q=60):
    dst = SIMG / dst
    if dst.exists() and not FORCE_IMAGES:
        return dst.name
    from PIL import Image
    im = Image.open(src).convert('RGB')
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    if max_h and im.height > max_h:
        im = im.crop((0, 0, im.width, max_h))
    im.save(dst, 'JPEG', quality=q, optimize=True, progressive=True)
    return dst.name


def shot(thumb, large, alt, cap='', cls='shot'):
    c = f'<figcaption>{cap}</figcaption>' if cap else ''
    return (f'<figure class="{cls}"><a class="zoom" href="img/{large}" target="_blank" rel="noopener">'
            f'<img src="img/{thumb}" alt="{esc(alt)}" loading="lazy"></a>{c}</figure>')


# ---------------------------------------------------------------- charts (HTML/CSS + SVG)
def legend(items):
    return '<div class="legend">' + ''.join(f'<span><i class="sw {c}"></i>{esc(t)}</span>' for c, t in items) + '</div>'


def hbar(items, vmax=None, refs=(), aria='', cls=''):
    """items: dict(label, sub, tip, series=[(value|None, css_class, text, missing_text)])."""
    vals = [s[0] for it in items for s in it['series'] if s[0] is not None]
    vmax = vmax or (max(vals) if vals else 1)
    ref_html = ''.join(
        f'<span class="hb-ref" style="--x:{min(v / vmax * 100, 100):.2f}%"><em>{esc(t)}</em></span>' for v, t in refs)
    out = []
    for it in items:
        lines = []
        for v, c, t, miss in it['series']:
            if v is None:
                lines.append(f'<div class="hb-line"><span class="hb-miss">{esc(miss or "нет данных")}</span></div>')
            else:
                w = max(v / vmax * 100, 0.6) if v > 0 else 0
                lines.append(f'<div class="hb-line"><span class="hb-bar {c}" style="--w:{w:.2f}%"></span>'
                             f'<span class="hb-val">{t}</span></div>')
        sub = f'<small>{it["sub"]}</small>' if it.get('sub') else ''
        tip = f' data-tip="{esc(it["tip"])}"' if it.get('tip') else ''
        out.append(f'<div class="hb-row"{tip}><div class="hb-lab">{it["label"]}{sub}</div>'
                   f'<div class="hb-track">{"".join(lines)}{ref_html}</div></div>')
    return f'<div class="hb {cls}" role="img" aria-label="{esc(aria)}">' + ''.join(out) + '</div>'


def heat(row_labels, col_labels, matrix, cls_fn, txt_fn, tip_fn=None, corner='', row_subs=None, col_subs=None,
         extra_rows=''):
    th = ''.join(f'<th scope="col">{c}' + (f'<small>{col_subs[i]}</small>' if col_subs else '') + '</th>'
                 for i, c in enumerate(col_labels))
    body = []
    for r, lab in enumerate(row_labels):
        tds = []
        for c, v in enumerate(matrix[r]):
            tip = f' data-tip="{esc(tip_fn(r, c, v))}"' if tip_fn else ''
            tds.append(f'<td class="{cls_fn(v)}"{tip}>{txt_fn(v)}</td>')
        sub = f'<small>{row_subs[r]}</small>' if row_subs else ''
        body.append(f'<tr><th scope="row">{lab}{sub}</th>{"".join(tds)}</tr>')
    return (f'<div class="tscroll"><table class="heat"><thead><tr><th class="corner">{corner}</th>{th}</tr></thead>'
            f'<tbody>{"".join(body)}{extra_rows}</tbody></table></div>')


def season_svg(series, trends=(), aria='Частотность по месяцам', div=1000, dec=1):
    """series: list of (month 'YYYY-MM', value|None, repeated:bool). trends: [(kind 'lin'|'log', a, b, css)]; t = 1 для первого месяца."""
    W, H, top, bot, left = 960, 300, 34, 46, 8
    n = len(series)
    step = (W - left * 2) / n
    bw = min(24, step * 0.62)
    vmax = max(v for _, v, _ in series if v) * 1.08
    out = [f'<svg class="svgc" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(aria)}">']
    base = H - bot
    for g in (0.25, 0.5, 0.75, 1.0):
        y = base - (base - top) * g
        out.append(f'<line class="grid" x1="{left}" x2="{W - left}" y1="{y:.1f}" y2="{y:.1f}"/>')
    out.append(f'<line class="axis" x1="{left}" x2="{W - left}" y1="{base}" y2="{base}"/>')
    mon = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
    for i, (m, v, rep) in enumerate(series):
        cx = left + step * i + step / 2
        y_, mm = m.split('-')
        lab = mon[int(mm) - 1]
        if n <= 24 or int(mm) % 2 == 1:
            out.append(f'<text class="tick" x="{cx:.1f}" y="{base + 16}" text-anchor="middle">{lab}</text>')
        if mm == '01' or i == 0:
            out.append(f'<text class="tick yr" x="{cx:.1f}" y="{base + 32}" text-anchor="middle">{y_}</text>')
        if v is None:
            out.append(f'<text class="tick miss" x="{cx:.1f}" y="{base - 6}" text-anchor="middle">—</text>')
            continue
        h = (base - top) * v / vmax
        x = cx - bw / 2
        y = base - h
        r = min(4, bw / 2)
        path = (f'M{x:.1f},{base} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} '
                f'L{x + bw - r:.1f},{y:.1f} Q{x + bw:.1f},{y:.1f} {x + bw:.1f},{y + r:.1f} L{x + bw:.1f},{base} Z')
        c = 'bar rep' if rep else 'bar'
        tip = f'{lab} {y_}: {fnum(v)} запросов' + (' (значение повторено сервисом без перепроверки)' if rep else '')
        out.append(f'<path class="{c}" d="{path}" data-tip="{esc(tip)}"/>')
        yr_vals = [vv for mm_, vv, _ in series if vv is not None and mm_[:4] == y_]
        if n <= 24 or v in (max(yr_vals), min(yr_vals)):
            out.append(f'<text class="val" x="{cx:.1f}" y="{y - 6:.1f}" text-anchor="middle">{fnum(v / div, dec)}</text>')
    for kind, a, b, css in trends:
        pts = []
        for i in range(n):
            t = i + 1
            v = a + b * (math.log(t) if kind == 'log' else t)
            cx = left + step * i + step / 2
            pts.append(f'{cx:.1f},{base - (base - top) * max(v, 0) / vmax:.1f}')
        out.append(f'<polyline class="trend {css}" fill="none" points="{" ".join(pts)}"/>')
    out.append('</svg>')
    return '<div class="tscroll svgwrap">' + ''.join(out) + '</div>'


def obs(text):
    return f'<aside class="obs"><span class="obs-k">Наблюдение</span><p>{text}</p></aside>'


def wave2(title, what):
    return (f'<div class="w2"><div class="w2-head"><span class="chip-w2">{WAVE2}</span><strong>{esc(title)}</strong></div>'
            f'<p>{what}</p></div>')


def details(summary, body, open_=False):
    o = ' open' if open_ else ''
    return f'<details{o}><summary>{summary}</summary><div class="det">{body}</div></details>'


def block(title, body, lead=''):
    ld = f'<p class="lead">{lead}</p>' if lead else ''
    return f'<section class="blk"><h3>{esc(title)}</h3>{ld}{body}</section>'


def ext_link(u, text):
    if u and u.startswith('http'):
        return f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(text)}</a>'
    return esc(u) if u else '—'


def dlink(d):
    return f'<a href="https://{d}" target="_blank" rel="noopener">{d}</a>'


def tx(s):
    """Текст из CSV для показа: без имён частных лиц, экранированный."""
    s = strip_names(s or '')
    s = re.sub(r'\s*\((?:C\d{2})[^()]*\)', '', s)
    s = re.sub(r'\bC\d{2}(?:\s*[≥=]\s*\d)?\b,?\s*', '', s)
    return esc(s, quote=False)


def md_tables(text):
    """Все таблицы markdown в тексте по отдельности."""
    out, cur = [], []
    for ln in text.split('\n'):
        if ln.lstrip().startswith('|'):
            cur.append(ln)
        elif cur:
            out.append(md_table(cur))
            cur = []
    if cur:
        out.append(md_table(cur))
    return out


def mini_cols(vals, labels, fmtf, unit=''):
    """Маленький столбиковый график на 3 года; отрицательные значения уходят вниз от нуля."""
    W, H, top, bot = 200, 118, 18, 22
    present = [v for v in vals if v is not None]
    if not present:
        return '<div class="mini-empty">нет отчётности</div>'
    vmax = max(max(present), 0)
    vmin = min(min(present), 0)
    span = (vmax - vmin) or 1
    plot_h = H - top - bot
    zero = top + plot_h * (vmax / span)
    step = W / len(vals)
    bw = min(24, step * 0.5)
    out = [f'<svg class="svgc mini" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(unit)}">',
           f'<line class="axis" x1="4" x2="{W - 4}" y1="{zero:.1f}" y2="{zero:.1f}"/>']
    for i, (v, lab) in enumerate(zip(vals, labels)):
        cx = step * i + step / 2
        out.append(f'<text class="tick" x="{cx:.1f}" y="{H - 6}" text-anchor="middle">{lab}</text>')
        if v is None:
            out.append(f'<text class="tick miss" x="{cx:.1f}" y="{zero - 4:.1f}" text-anchor="middle">нет</text>')
            continue
        h = plot_h * abs(v) / span
        y = zero - h if v >= 0 else zero
        cls = 'bar' if v >= 0 else 'bar neg'
        out.append(f'<rect class="{cls}" x="{cx - bw / 2:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(h, 0.8):.1f}" rx="2"/>')
        ty = (y - 4) if v >= 0 else (y + h + 11)
        out.append(f'<text class="val" x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle">{fmtf(v)}</text>')
    out.append('</svg>')
    return ''.join(out)


def chip(text, kind):
    return f'<span class="st st-{kind}">{esc(text)}</span>'


def verdict_kind(v):
    v = (v or '').strip()
    if not v or v in ('—', 'не считается'):
        return 'na'
    if 'не окупается' in v and '…' in v:
        return 'part'
    if 'не окупается' in v:
        return 'open'
    if '…' in v:
        return 'wait'
    if '≤ 11%' in v:
        return 'ok'
    return 'wait'


# ---------------------------------------------------------------- load data
criteria = rows('criteria')
scores = rows('criteria_scores')
ctext = {r['id']: r for r in rows('criteria_text')}
strength = {r['domain']: r for r in rows('competitor_strength')}
traffic = {r['domain']: r for r in rows('traffic_channels_wide')}
tover = {r['domain']: r for r in rows('traffic_overview')}
offers = rows('sites_offers')
prices = rows('sites_prices')
gates = rows('sites_gates')
gspec = rows('sites_gates_specialists')
speed = {r['domain']: r for r in rows('sites_speed')}
seo = {r['domain']: r for r in rows('seo_sites')}
finance = rows('finance')
legal = rows('legal')
vk = rows('social_vk')
vkads = rows('vk_ads')
hyps = rows('hypotheses')
mplan = rows('mediaplan')
wsd = rows('wordstat_dynamics')
brand = rows('brand_demand')
serp = rows('serp_presence_msk')
keys = json.loads((D / 'keys_queries_msk.json').read_text(encoding='utf-8'))
budgets = rows('ad_budgets')
ads_y = rows('ads_yandex')
ads_maps = rows('ads_maps')
ads_pl = rows('ads_platforms')
ads_vk_st = rows('ads_vk')
ads_tg_st = rows('ads_telegram')
tgp = rows('tg_posts_wave3')
psi = rows('sites_pagespeed')
av_list = rows('avito_listings')
av_claims = rows('avito_claims_shares')
av_vs = rows('avito_vs_sites')
av_rev = rows('avito_reviews')
mshop = rows('mystery_shopper')
ovm = rows('offer_vs_market')
ovar = rows('offer_variants')
ttab = rows('transformation_table')
precon = rows('price_reconciliation')
btrend = rows('brand_trend')
wsm = rows('ws_monthly')
bds = rows('brand_demand_stats')
mks = {r['query']: r for r in rows('ws_market_stats')}
wsdist = rows('wordstat_mo_districts')
wstops = rows('ws_tops')
wstopi = rows('ws_tops_intents')
ptc = rows('paid_traffic_cost')
venn = rows('venn_criteria')
valtype = rows('criteria_value_type')
trust = rows('sites_trust')
b2b = rows('sites_b2b_cases')
q4s = rows('avito_q4_summary')
q4sel = rows('avito_q4_sellers')
pw3 = rows('avito_profiles_wave3')
smo = rows('serp_mo_presence')
srel = rows('serp_related')
swa = rows('sw_apify')
brr = {r['domain']: r for r in rows('brand_revenue_ratio')}
rcoef = rows('regional_coef')
with open(Q / 'completeness.csv', encoding='utf-8') as _f:
    compl = list(csv.DictReader(_f))
ADS_DIRECT = {}
for _r in budgets:
    if 'Keys.so' in _r['source'] and num(_r['queries_count']):
        _d = _r['domain']
        _k = 'prof-zabory.ru' if _d == 'sales.prof-zabory.ru' else _d
        if _k in MAIN and (_k not in ADS_DIRECT or _d.startswith('sales.')):
            ADS_DIRECT[_k] = dict(q=num(_r['queries_count']), ads=num(_r['ads_count']),
                                  src='Keys.so, лендинг sales.prof-zabory.ru' if _d.startswith('sales.') else 'Keys.so')

S_SYN = md_sections(N / 'synthesis_spravka.md')
S_REV = md_sections(N / 'reviews_spravka.md')
S_SITES = md_sections(N / 'sites_spravka.md')
S_SEO = md_sections(N / 'seo_spravka.md')
S_DEM = md_sections(N / 'demand_social_spravka.md')
S_FIN = md_sections(N / 'finance_spravka.md')
S_ANS = md_sections(N / 'answers.md')

crit_name = {r['id']: r['criterion'] for r in criteria}
crit_w = {r['id']: num(r['weight']) for r in criteria}
crit_cls = {r['id']: r['class'] for r in criteria}

score_rows = [r for r in scores if r['id'].startswith('C')]
tot = {r['id']: r for r in scores if r['id'].startswith('ИТОГ')}
wscore = {d: num(tot['ИТОГ_ВЗВ'][d]) for d in MAIN}
sumscore = {d: num(tot['ИТОГ'][d]) for d in MAIN}
keyscore = {d: num(tot['ИТОГ_КЛЮЧ'][d]) for d in MAIN}
order_w = sorted(MAIN, key=lambda d: -wscore[d])

# негатив по Яндекс Картам — из таблицы справки отзывов
neg = {}
rev_tab = md_table([l for l in sec(S_REV, '2.').split('\n') if l.startswith('|')])
name2dom = {v: k for k, v in NAMES.items()}
name2dom.update({'Проф-заборы': 'prof-zabory.ru'})
for r in rev_tab[1:]:
    dom = name2dom.get(r[0])
    if dom:
        neg[dom] = num(r[6])

# ---------------------------------------------------------------- numbers for «Коротко»
season_map = {r['month']: int(r['count']) for r in wsm if r['query'] == 'забор под ключ' and r['region'] == 'Москва и область'}
sep26 = season_map.get('2026-09')
jan26, may26 = season_map.get('2026-01'), season_map.get('2026-05')
advertisers = sorted({a for q in keys.values() for a in q['ads']})
ads_counts = [len(q['ads']) for q in keys.values()]
cpcs = [q['cpc'] for q in keys.values()]
cpc_med = statistics.median(cpcs)
budget_total = sum(num(h['budget_rub_assumption']) or 0 for h in hyps)

# ---------------------------------------------------------------- images: prepare
SIMG.mkdir(parents=True, exist_ok=True)
SDATA.mkdir(parents=True, exist_ok=True)

FS = []  # first screens
for o in offers:
    d = o['domain']
    src_d = IMG / 'sites' / f'{d}_desktop.png'
    src_m = IMG / 'sites' / f'{d}_mobile.png'
    if not src_d.exists():
        continue
    t = prep_img(src_d, f'fs_{d}_d.jpg', 640)
    L = prep_img(src_d, f'fs_{d}_dl.jpg', 1200)
    tm = lm = None
    if src_m.exists():
        tm = prep_img(src_m, f'fs_{d}_m.jpg', 240, max_h=520)
        lm = prep_img(src_m, f'fs_{d}_ml.jpg', 600)
    FS.append((o, t, L, tm, lm))

GT = {}
for g in gates:
    p = g['screenshot']
    if not p:
        continue
    src = ROOT / p
    if src.exists() and (g['domain'] in MAIN or g['group'].startswith('специализ')):
        GT[g['domain']] = (prep_img(src, f'gt_{g["domain"]}.jpg', 640), prep_img(src, f'gt_{g["domain"]}_l.jpg', 1200))

IDEAL_IMG = {1: 'dostup-zabor.ru_b02.jpg', 2: 'dostup-zabor.ru_b11.jpg', 3: 'masterovit.ru_b12.jpg',
             4: 'zaborkin.ru_b04.jpg', 5: 'zabor-dlya-vseh.site_b03.jpg', 7: 'masterovit.ru_b04.jpg',
             8: 'p-z-z.ru_b14.jpg', 9: 'p-z-z.ru_b15.jpg', 10: 'zaborkin.ru_b08.jpg',
             11: 'raduga-zaborov.ru_b11_reshoot.jpg', 12: 'zaborkin.ru_b09.jpg', 14: 'zaborkin.ru_b10.jpg',
             15: 'dostup-zabor.ru_b12.jpg'}
BL = {}
for k, f in IDEAL_IMG.items():
    src = IMG / 'sites' / 'blocks' / f
    if src.exists():
        BL[k] = (prep_img(src, f'bl_{k:02d}.jpg', 640, max_h=900), prep_img(src, f'bl_{k:02d}_l.jpg', 900, max_h=2600))
if 'prof-zabory.ru' in GT:
    BL[6] = GT['prof-zabory.ru']

MAPS_IMG = []
for _f, _c in (('yandex.ru_maps_zabor_pod_klyuch.png', 'Яндекс Карты: «забор под ключ»'),
               ('yandex.ru_maps_otkatnye_vorota.png', 'Яндекс Карты: «откатные ворота»'),
               ('2gis.ru_search_zabor_pod_klyuch.png', '2ГИС: «забор под ключ»')):
    _src = IMG / 'ads_social' / _f
    if _src.exists():
        _b = _f.rsplit('.', 1)[0]
        MAPS_IMG.append((prep_img(_src, f'mp_{_b}.jpg', 640), prep_img(_src, f'mp_{_b}_l.jpg', 1200), _c))

VKIMG = None
src = IMG / 'ads_vk' / 'zaborovo.ru_targethunter_posev_sergiev_posad.png'
if src.exists():
    VKIMG = prep_img(src, 'vk_zaborovo_posev.jpg', 640, q=70)

# ---------------------------------------------------------------- CSV for download
DOWNLOADS = [
    ('criteria', 'Критерии выбора: вес по голосу клиента, класс, охват рынка'),
    ('criteria_scores', 'Оценки 0–5: критерии × 10 компаний, итоговые баллы'),
    ('criteria_text', 'Факты по критериям × компаниям'),
    ('competitor_strength', 'Сила конкурента: визиты, оценки, соцсети, выручка'),
    ('competitors', 'Список конкурентов: роль, юрлицо, визиты, присутствие в выдаче'),
    ('traffic_overview', 'Трафик Similarweb: визиты, вовлечённость, устройства'),
    ('traffic_channels_wide', 'Каналы трафика: доли и визиты'),
    ('serp_presence_msk', 'Присутствие доменов в выдаче Яндекса, Москва, 9 запросов'),
    ('seo_sites', 'SEO: страницы, гео, поддомены, ИКС, разметка'),
    ('ws_monthly', 'Вордстат: 17 рядов по месяцам, январь 2024 — сентябрь 2026'),
    ('ws_market_stats', 'Вордстат: сезон и динамика 4 запросов рынка'),
    ('brand_demand_stats', 'Вордстат: бренд-спрос 10 конкурентов'),
    ('brand_revenue_ratio', 'Выручка на брендовый запрос и оценка выручки ИП'),
    ('wordstat_mo_districts', 'Вордстат: округа МО по двум запросам'),
    ('wordstat_dynamics', 'Keys.so: частотность «забор под ключ» по месяцам (сверка)'),
    ('wordstat_tops', 'Уточнения запросов и подсказки'),
    ('sites_offers', 'Офферы 13 посадочных'),
    ('sites_prices', 'Цены с сайтов'),
    ('sites_gates', 'Откатные ворота: цены 4 м и «от», состав, условия'),
    ('sites_gates_specialists', 'Специализированные игроки по воротам'),
    ('sites_speed', 'Скорость сайтов (Lighthouse, замер браузером)'),
    ('reviews_cards', 'Карточки на картах и площадках отзывов'),
    ('reviews_themes', 'Темы отзывов по компаниям'),
    ('social_vk', 'Сообщества ВКонтакте'),
    ('vk_ads', 'Рекламные посты и посевы ВКонтакте'),
    ('finance', 'Финансы ООО по ГИР БО, 2023–2025'),
    ('hypotheses', 'Гипотезы теста с 22.10.2026'),
    ('mediaplan', 'Медиаплан по сценариям и трём сценариям чека'),
    ('ads_yandex', 'Объявления Директа и РСЯ: тексты, быстрые ссылки, дни в показе'),
    ('ad_budgets', 'Директ: объявления, запросы, бюджеты (оценки Spywords и Keys.so)'),
    ('ads_maps', 'Яндекс Карты и 2ГИС: карточки, реклама, акции, витрины'),
    ('ads_platforms', 'Яндекс Услуги: исполнители и объявления Директа'),
    ('avito_sellers', 'Авито: продавцы трёх выдач'),
    ('avito_claims_shares', 'Авито: доли обещаний'),
    ('avito_vs_sites', 'Авито против сайтов: цены'),
    ('mystery_shopper', 'Прозвон конкурентов: наблюдения по этапам'),
    ('offer_vs_market', 'Целевой оффер против рынка: исполнено и обещание'),
    ('offer_variants', 'Конструктор оффера: три варианта по блокам'),
    ('transformation_table', 'Трансформационная идея и эмоции до и после'),
    ('price_reconciliation', 'Сверка цен стратегии заказчика с сайтами'),
    ('brand_trend', 'Тренды: линейный, логарифмический, скользящая сумма 12 месяцев'),
    ('ws_tops', 'Вордстат: «Топы запросов» с классами намерения и критериев'),
    ('ws_tops_intents', 'Вордстат: доли намерений, критериев и материалов'),
    ('ws_tops_mo_phrases', 'Вордстат: фразы с Москвой, МО и городами области'),
    ('tg_posts_wave3', 'Telegram: посты каналов Мастеровита и Заборкина'),
    ('sites_pagespeed', 'PageSpeed Insights: 13 посадочных, телефон и компьютер'),
    ('paid_traffic_cost', 'Стоимость рекламного трафика: визиты × цена клика'),
    ('venn_criteria', 'Диаграмма Венна: критерии по зонам'),
    ('criteria_value_type', 'Эксплицитные и имплицитные ценности с цитатами'),
    ('sites_trust', 'Сертификаты, партнёрства, награды, рейтинги'),
    ('sites_b2b_cases', 'B2B-заказчики и объекты в СНТ и посёлках'),
    ('avito_q4_summary', 'Авито: «забор из профнастила под ключ», сводка'),
    ('avito_q4_sellers', 'Авито: «забор из профнастила под ключ», продавцы'),
    ('avito_profiles_wave3', 'Авито: профили Заборкина, Заборово, ПрофЗаборов'),
    ('serp_mo_presence', 'Выдача Яндекса, Москва и МО: домены в топ-10 и топ-20 по 15 запросам'),
    ('serp_mo_organic', 'Выдача Яндекса, Москва и МО: все органические результаты'),
    ('serp_related', '«Связанные запросы» Яндекса'),
    ('sw_apify', 'Similarweb, сентябрь 2026: 31 домен'),
    ('sw_similar_sites', 'Similarweb: похожие сайты'),
    ('regional_coef', 'Региональный коэффициент по округам МО'),
]
DOWNLOADS = [d for d in DOWNLOADS if (D / f'{d[0]}.csv').exists()]
DROP_COLS = {'director', 'founders', 'address_private', 'advertiser_legal', 'advertiser_inn', 'inn'}
IP_FULL = re.compile(r'(?:ИП|Индивидуальный предприниматель)\s+[А-ЯЁ][а-яё]+\s[А-ЯЁ]\.\s?[А-ЯЁ]\.|(?:ИП|Индивидуальный предприниматель)\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){0,2}')
PERS_NAME = re.compile(r'\bСвятослав\b')  # аккаунт Авито с личным именем вместо названия
for name, _ in DOWNLOADS:
    src = D / f'{name}.csv'
    with open(src, encoding='utf-8') as f:
        rdr = csv.DictReader(f)
        cols = [c for c in rdr.fieldnames if c not in DROP_COLS]
        data = [{c: PERS_NAME.sub('компания с личным именем в названии', IP_FULL.sub('ИП', r.get(c) or '')) for c in cols} for r in rdr]
    with open(SDATA / f'{name}.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(data)

# ================================================================ TAB 1 — Коротко
ANSWERS = [
    ('Какую долю рынка может забрать новый игрок',
     'Рынок заборов под ключ Москвы и МО оценивается в 12–30 млрд ₽ в год (центральная оценка 20 млрд ₽), откатных ворот — '
     '2,8–5,2 млрд ₽. Потолок 5 бригад — 210–400 объектов в год; выручка зависит от чека: консервативно 14–91 млн ₽ '
     '(0,07–0,45% рынка), при базовом чеке — 55–104 млн ₽ на заборах и 74–180 млн ₽ на пакетах с воротами (0,27–0,90%), '
     'все цифры — оценка. Крупнейший игрок, группа «Мастеровит», — 3 295 млн ₽ выручки за 2025 год.'),
    ('Насколько конкуренты зависят от платного трафика',
     'Директ крутят 8 из 10 компаний; бюджет Мастеровита — около 518 тыс. ₽ в месяц по Spywords (нижняя оценка, Keys.so '
     'даёт 1,97 млн ₽ без периода). У всех 10 первых карточек Яндекс Карт по 4 запросам есть реклама, за карты платят 6 из 10 '
     'компаний; на Авито 44 из первых 50 объявлений «забор под ключ» продвигаются. Доля платных каналов по Similarweb — '
     'от 4,8% у zaborkin.ru до 64–68% у prof-zabory.ru и oblzabor.ru (оценка).'),
    ('Насколько легко масштабировать работы',
     'Начать одной бригадой просто, трудность — удержать качество при росте: жалоб на качество монтажа на 100 отзывов '
     'Яндекс Карт — от 0,6 у pskzabor.ru до 10,6 у крупнейшего игрока. Рост ограничивают сезон (спрос в январе в 2,7–6 раз ниже '
     'майского, Вордстат) и контроль бригад: после 4–5 бригад нужны прораб, контроль скрытых работ и сервисная служба (гипотеза).'),
    ('Сколько оборотного капитала нужно для роста',
     'Рынок берёт предоплату от 5 000 ₽ до 40% (прозвон 21.10), оплату после монтажа обещают 3 из 10 компаний. При оплате '
     'после приёмки 10 объектов одновременно требуют около 2,0 млн ₽ на заборах и 2,7–3,5 млн ₽ на пакетах при базовом чеке, '
     '0,5–1,7 млн ₽ при консервативном; при авансе 50% — 0,7–1,2 млн ₽ (оценки). Условия отсрочки у поставщиков открытые '
     'источники не показывают.'),
    ('Какие скрытые расходы съедают прибыль после монтажа',
     'Главные потери — переделки и гарантийные выезды: качество монтажа — 31,4% жалоб, гарантия — 27,6%, ошибка замера — '
     '9,5%, столбы после зимы — 8,2%. К ним добавляются выезды замерщика без договора (рынок берёт за них 2 000–5 500 ₽), '
     'доплаты за грунт при фиксированной смете, простой бригад зимой и НДС на УСН с 2027 года. Стоимость гарантийных '
     'выездов в рублях не найдена.'),
    ('Есть ли окно возможностей на 2–3 года',
     'Рынок не закрывает связь после оплаты (28,4% жалоб, закрыта у 2 из 10), пакет «забор + ворота» с итоговой суммой '
     '(0 из 13 страниц), письменное КП (в прозвоне — 1 компания), неустойку в рублях, гарантию с проверкой после первой зимы '
     'и подсветку въезда (0 из 10). У 10 из 12 ООО выручка 2025 года ниже 2024-го; бренд-спрос за год вырос у Заборово (+38,6%), '
     'падает у Заборкина, а также по частично общим запросам «доступные заборы» и «завод заборов» (Вордстат). Окно сужают акции «автоматика за 1 ₽» '
     'у лидеров, плотная платная конкуренция на Картах и Авито и НДС с 2027 года.'),
    ('Как меняются цены материалов относительно монтажа',
     'На сайтах с раздельной ценой монтаж евроштакетника — около 33% цены метра (pskzabor.ru), установка откатных ворот — '
     '28% цены (zaborkin.ru); по исследованию ворот в воротах с автоматикой материалы — 50% чека, работа — 23%. '
     'На Авито медиана профнастила — 700 ₽ за п.м. против 1 690 ₽ «от» на сайтах: карточка Авито чаще показывает нижнюю '
     'границу без состава. Динамику цен металла за 2–3 года открытые данные не показали.'),
    ('На что клиенты чаще всего жалуются',
     'В 851 негативном отзыве о 10 компаниях: качество монтажа — 31,4%, связь после оплаты — 28,4%, материал и покраска — '
     '27,7%, гарантия — 27,6%, смета и замер — 18,0%. Прозвон подтверждает смету изнутри продажи: «эта цена обычно на замере '
     'увеличивается на 20%». У специалистов по откатным воротам первое место — связь (54,3%); на Авито негатив мягче — '
     '5,7% отзывов 1–3★.'),
]


def answer_facts(i):
    for k, v in S_ANS.items():
        if k.startswith(f'{i}.'):
            return md_html(v, names=True)
    return '<p>Факты не найдены.</p>'


direct_n = sum(1 for d in MAIN if d in ADS_DIRECT)
tiles = [
    (fnum(sep26), 'запросов «забор под ключ» в сентябре 2026', 'Вордстат, Москва и область, все устройства'),
    (f'×{fnum(may26 / jan26, 1)}', 'разница спроса май / январь 2026', f'январь — {fnum(jan26)}, май — {fnum(may26)}; в 2024–2025 — ×2,7–3,4; Вордстат, Москва и МО'),
    (f'{direct_n} из 10', 'компаний крутят Яндекс Директ', 'Keys.so и Spywords, Москва, 21.10.2026'),
    ('85–124 ₽', 'цена клика на поиске', 'прогноз Keys.so — расчёт Spywords по masterovit.ru; по запросам 71–245 ₽; оценка'),
    ('4 270–6 200 ₽', 'цена заявки с поиска', 'медиаплан, конверсия страницы 2%; оценка'),
    ('350–450 тыс. ₽', 'чек объекта с воротами под ключ', 'прозвон команды 21.10; забор без ворот — медиана сумм в отзывах 259 825 ₽'),
]
nb = lambda v: str(v).replace(' ', '\u00a0')
tiles_html = '<div class="tiles">' + ''.join(
    f'<div class="tile"><div class="tile-v">{nb(v)}</div><div class="tile-l">{esc(l)}</div><div class="tile-s">{esc(s)}</div></div>'
    for v, l, s in tiles) + '</div>'

ans_html = '<div class="answers">' + ''.join(
    f'<article class="ans"><h4><span class="qn">{i}</span>{esc(t)}</h4><p>{esc(a)}</p>'
    f'{details("На каких фактах", answer_facts(i))}</article>'
    for i, (t, a) in enumerate(ANSWERS, 1)) + '</div>'

hyps_sorted = sorted(hyps, key=lambda h: int(h['hypothesis_id'][1:]))
test_list = '<ol class="testlist">' + ''.join(
    f'<li><strong>{h["hypothesis_id"]}</strong> · {tx(h["channel"])} · бюджет {fnum(num(h["budget_rub_assumption"]))} ₽ '
    f'(допущение)<br><span>{tx(h["offer"].split(". В квизе")[0])}</span></li>' for h in hyps_sorted) + '</ol>'

TAB1 = (
    block('Цифры ниши', tiles_html,
          'Шесть цифр для старта рекламы 22.10.2026. Цена клика — диапазон двух оценок, фактическую цену покажет тест.') +
    obs('Спрос сезонный: в январе запросов «забор под ключ» в 2,7–6,0 раза меньше, чем в мае, в ноябре — 50–84% сентябрьских '
        '(Вордстат, Москва и МО, 2024–2026). Осенний тест покажет цену заявки '
        'и конверсию страницы; объём весенних заказов по нему не прогнозируется. Окупаемость поиска зависит от чека: '
        'при чеке пакета 350–450 тыс. ₽ реклама занимает 10,5–19,7% чека, при модельном чеке 170–226 тыс. ₽ — 21–40%.') +
    block('Ответы на вопросы заказчика', ans_html,
          'По 2–3 предложения; под каждым ответом — факты с источниками. Метки: факт — снято с источника, вывод — следует '
          'из приведённых цифр, гипотеза и оценка — расчёт на допущениях.') +
    obs('Ответы на вопросы 3, 5, 6 и 8 сходятся в одном: рынок теряет клиентов после оплаты — на монтаже, гарантии и связи. '
        'Прозвон добавляет второе слабое место: смету «уточняют» на замере, а письменное КП присылает одна компания.') +
    block('Что брать в тест с 22.10', test_list + '<p class="note">Подробно — на вкладке «Гипотезы». Бюджет всех гипотез '
          f'{fnum(budget_total)} ₽ — допущение аналитика, заказчик бюджет не называл.</p>') +
    obs('Пакет «забор + ворота» (H2) ближе всех к окупаемости на поиске, но его объём в ноябре ограничен 161–172 кликами. '
        'Авито (H8) по кейсу укладывается в 11% базового чека, кейс один. Карты (H7) и база клиентов (H6) не считаются '
        'заранее: цена обращения с карт и размер базы не найдены.')
)

# ================================================================ TAB 2 — Как выбирает клиент
CLS_COLOR = {'ключевой': 's1', 'свободный': 's2', 'обязательный': 's3', 'второстепенный': 'sg'}
crit_items = []
for r in criteria:
    w = num(r['weight'])
    crit_items.append(dict(
        label=f'<span class="rk">{r["rank"]}</span>{esc(r["criterion"])}',
        sub=f'{esc(r["class"])} · в оффере у {r["market_offers_n"]} из 10 · закрыто (3+) у {r["companies_score_ge3"]} из 10',
        tip=f'{r["criterion"]}: вес {fnum(w, 1)}; голос клиента — {r["voice_measure"]}',
        series=[(w, CLS_COLOR.get(r['class'], 'sg'), fnum(w, 1), None)]))
crit_chart = legend([('s1', 'ключевой: важен, закрыт у 4–7 компаний'), ('s3', 'обязательный: важен, есть у 8–10'),
                     ('s2', 'свободный: важен, рынок не закрывает (0–3)'), ('sg', 'второстепенный: вес ниже 10')]) + \
    hbar(crit_items, vmax=100, aria='Вес критериев выбора по голосу клиента', cls='hb-crit')

rules = ('<p class="note">Вес = 100 × (0,7 × доля отзывов с темой / максимум + 0,3 × уточнения запроса с критерием / максимум). '
         'Отзывы: 851 негативный (1–3★) и 3 985 позитивных (4–5★) о 10 компаниях; уточнения: 49 формулировок (9 похожих '
         'фраз Keys.so и 40 подсказок Яндекса). Вес — относительная важность, долю покупателей он не показывает. '
         'Класс — важность (вес от 10) × охват рынка (сколько компаний из 10 получили 3 балла и выше).</p>')

# жалобы — таблица справки отзывов
comp_tab = md_table([l for l in sec(S_REV, '3.').split('\n') if l.startswith('|')])
comp_items = []
for r in comp_tab[1:]:
    a, b = num(r[1]), num(r[2])
    comp_items.append(dict(label=esc(r[0]), tip=f'{r[0]}: все годы {r[1]}, за 24 месяца {r[2]}, без Мастеровита {r[3]}',
                           series=[(a, 's1', pct(a), None), (b, 's2', pct(b), None)]))
comp_chart = legend([('s1', 'все годы, n=851'), ('s2', 'последние 24 месяца, n=407')]) + \
    hbar(comp_items, aria='Темы негативных отзывов')

pos_tab = md_table([l for l in sec(S_REV, '4.').split('\n') if l.startswith('|')])
pos_items = [dict(label=esc(r[0]), series=[(num(r[1]), 's3', r[1], None)]) for r in pos_tab[1:]]
pos_chart = hbar(pos_items, aria='Темы позитивных отзывов')

# цитаты
qsecs = md_sections(N / 'reviews_quotes.md')
quote_html = []
for k, v in qsecs.items():
    if not re.match(r'[1-9]\.', k):
        continue
    title = re.sub(r'^\d+\.\s*', '', k)
    qs = []
    for ln in v.split('\n'):
        ln = ln.strip()
        if not ln.startswith('- '):
            continue
        m = re.match(r'- (.+?)\s+—\s+(.+)$', ln)
        if not m:
            continue
        body, src_ = m.group(1), m.group(2)
        qs.append(f'<blockquote><p>{esc(body.replace("[имя]", "…"))}</p><cite>{esc(src_)}</cite></blockquote>')
    quote_html.append(f'<div class="qgroup"><h4>{inline(title)}</h4>{"".join(qs)}</div>')
quotes = '<div class="quotes">' + ''.join(quote_html) + '</div>'

motives = md_html(sec(S_REV, '8.'))

TAB2 = (
    block('Критерии выбора по весу', rules + crit_chart,
          f'{len(criteria)} критериев. Вес считается только по голосу клиента: отзывам и уточнениям поисковых запросов. Под названием — '
          'класс, сколько компаний бьются этим критерием в оффере и сколько его закрывают.') +
    obs('Первые четыре критерия — исполнение и поведение после оплаты: качество монтажа (70,0), связь после оплаты (63,4), '
        'покраска (61,9), гарантия (61,6). Рынок бьётся в офферах скидками и подарками (10 из 10) и гарантией (8 из 10), '
        'а связь после оплаты обещает 1 компания из 10. Гипотеза: оффер с обязательствами после монтажа выделится сильнее скидки.') +
    block('На что жалуются и за что хвалят', '<h4>Негатив, доля отзывов 1–3★ с темой</h4>' + comp_chart +
          '<h4>Позитив, доля отзывов 4–5★ с темой (n=3 985)</h4>' + pos_chart,
          'Негатив размечен вручную, один отзыв может содержать несколько тем. Позитив — по ключевым словам.') +
    obs('Претензии к изделию — 55,0% негатива, к обслуживанию после продажи — 47,4%, к цене и смете — 28,1%. Самые частые '
        'похвалы — скорость и соблюдение сроков (52,0%) и ровный результат (47,3%); выгодную цену хвалят в 11,1% отзывов.') +
    block('Голос клиента: цитаты по ключевым темам', quotes,
          'Цитаты укорочены до одной фразы, орфография авторов сохранена, имена удалены. Яндекс Карты, 2ГИС, Отзовик.') +
    obs('Одни и те же сюжеты повторяются у разных компаний: «после предоплаты начинаются проблемы», «цена выросла после '
        'замера», «после зимы выдавило столбы». В позитиве отдельно хвалят то, что цена после замера не изменилась.') +
    block('Скрытые мотивы', motives, 'То, что клиент не называет критерием прямо, но что повторяется в отзывах.') +
    obs('Клиент покупает уверенность, что его не бросят после оплаты и что забор переживёт первую зиму. Гарантия на '
        'покраску, которую клиенты цитируют в отзывах (20 дней — 1 год), короче этого срока.')
)

# ================================================================ TAB 3 — Кто и как отвечает
def score_cls(v):
    return 'h0' if v is None else f'h{int(v)}'


row_labels, matrix, row_subs = [], [], []
srows = sorted(score_rows, key=lambda r: -(crit_w.get(r['id']) or 0))
for r in srows:
    row_labels.append(esc(r['criterion']))
    row_subs.append(f'{r["class"]} · вес {fnum(crit_w.get(r["id"]), 1)}')
    matrix.append([num(r[d]) for d in order_w])


def tip_score(ri, ci, v):
    cid = srows[ri]['id']
    d = order_w[ci]
    fact = ctext.get(cid, {}).get(d, '')
    return f'{dname(d)} — {srows[ri]["criterion"]}: {fnum(v)} из 5. {fact}'


extra = ''
for key, lab in (('ИТОГ', f'Сумма баллов (из {5 * len(score_rows)})'), ('ИТОГ_ВЗВ', 'Взвешенный балл 0–5'),
                 ('ИТОГ_КЛЮЧ', 'Балл по ключевым и свободным')):
    vals = {d: num(tot[key][d]) for d in order_w}
    dg = 0 if key == 'ИТОГ' else 2
    extra += '<tr class="sum"><th scope="row">' + lab + '</th>' + ''.join(
        f'<td>{fnum(vals[d], dg)}</td>' for d in order_w) + '</tr>'

heatmap = legend([('h0', '0 — нет или худшее'), ('h1', '1'), ('h2', '2'), ('h3', '3'), ('h4', '4'), ('h5', '5 — лучшее на рынке')]) + \
    heat(row_labels, [dname(d) for d in order_w], matrix, score_cls, lambda v: fnum(v), tip_score,
         corner='Критерий · класс · вес', row_subs=row_subs, col_subs=order_w, extra_rows=extra)

rank_items = [dict(label=f'{esc(dname(d))}', sub=d,
                   tip=f'{dname(d)}: взвешенный {fnum(wscore[d], 2)}, по ключевым и свободным {fnum(keyscore[d], 2)}, сумма {fnum(sumscore[d])} из {5 * len(score_rows)}',
                   series=[(wscore[d], 's1', fnum(wscore[d], 2), None), (keyscore[d], 's2', fnum(keyscore[d], 2), None)])
              for d in order_w]
rank_chart = legend([('s1', f'взвешенный балл по всем {len(score_rows)} критериям'), ('s2', 'только ключевые и свободные')]) + \
    hbar(rank_items, vmax=5, aria='Взвешенные баллы компаний')

# сила конкурента
str_order = sorted(MAIN, key=lambda d: -(num(strength[d]['visits_month_similarweb']) or 0))
vis_items, rat_items, neg_items = [], [], []
for d in str_order:
    s = strength[d]
    v = num(s['visits_month_similarweb'])
    model = 'модель Similarweb' if 'модель' in traffic[d]['reliability'] else ''
    vis_items.append(dict(label=esc(dname(d)), sub=d + (f' · {model}' if model else ''),
                          series=[(v, 's1', fnum(v), None)]))
for d in sorted(MAIN, key=lambda d: -(num(strength[d]['yandex_ratings']) or 0)):
    s = strength[d]
    rat_items.append(dict(label=esc(dname(d)), sub=f'ответов на отзывы {s["reply_share_pct"]}%',
                          series=[(num(s['yandex_ratings']), 's1', fnum(num(s['yandex_ratings'])), None)]))
for d in sorted(MAIN, key=lambda d: (neg.get(d) or 0)):
    neg_items.append(dict(label=esc(dname(d)), sub=f'текстов {fnum(num(strength[d]["yandex_texts"]))}',
                          series=[(neg.get(d), 's2', pct(neg.get(d)), None)]))
str_table = '<div class="tscroll"><table class="tbl"><thead><tr><th>Компания</th><th>Визитов в месяц</th><th>Платные каналы</th>' \
            '<th>Оценок на Яндекс Картах</th><th>Ответов на отзывы</th><th>Директ: объявлений / запросов</th><th>Бюджет Директа, оценка</th>' \
            '<th>Реклама на Яндекс Картах</th><th>Авито, первые 50</th><th>Соцсети</th><th>Выручка 2025, млн ₽</th></tr></thead><tbody>' + \
    ''.join(f'<tr><th scope="row">{esc(dname(d))}<small>{d}</small></th><td class="n">{fnum(num(strength[d]["visits_month_similarweb"]))}</td>'
            f'<td class="n">{strength[d]["paid_channels_pct_similarweb"]}%</td><td class="n">{fnum(num(strength[d]["yandex_ratings"]))}</td>'
            f'<td class="n">{strength[d]["reply_share_pct"]}%</td><td>{tx(strength[d].get("direct_ads_queries", ""))}</td>'
            f'<td>{tx(strength[d].get("direct_budget", ""))}</td><td>{tx(strength[d].get("yandex_maps_ads", ""))}</td>'
            f'<td>{tx(strength[d].get("avito_serp_top50", ""))}</td><td>{esc(strength[d]["social"])}</td>'
            f'<td class="n">{esc(fnum(num(strength[d]["revenue_2025_mln_rub"]), 1) if num(strength[d]["revenue_2025_mln_rub"]) else "ИП, отчётности нет")}</td></tr>'
            for d in str_order) + '</tbody></table></div>'

strength_html = ('<div class="grid2"><div><h4>Визитов в месяц, июль–сентябрь 2026</h4>' + hbar(vis_items, aria='Визиты в месяц') +
                 '<p class="note">Similarweb, весь мир, оценка. У raduga-zaborov.ru и pskzabor.ru меньше 5 000 визитов в месяц — '
                 'цифры модельные.</p></div><div><h4>Оценок на Яндекс Картах</h4>' + hbar(rat_items, aria='Оценки на картах') +
                 '<h4>Доля 1–3★ в текстовых отзывах Яндекс Карт</h4>' + hbar(neg_items, aria='Доля негатива') +
                 '</div></div>' + str_table)

# абзацы по компаниям из справки синтеза
paras = []
for ln in sec(S_SYN, '2.').split('\n'):
    m = re.match(r'\*\*(.+?)\.\*\*\s*(.*)', ln)
    if m and '(' in m.group(1):
        dom = re.search(r'\(([a-z0-9.-]+\.ru)', m.group(1))
        dom = dom.group(1) if dom else ''
        ws = f'<span class="pill">балл {fnum(wscore.get(dom), 2)}</span>' if dom in wscore else ''
        paras.append(f'<article class="comp"><h4>{esc(m.group(1))} {ws}</h4><p>{inline(m.group(2))}</p></article>')
comp_html = '<div class="comps">' + ''.join(paras) + '</div>'

TAB3 = (
    block('Тепловая карта: критерии × компании', heatmap,
          'Оценка 0–5: лучшее на рынке — 5, отсутствие или худшее — 0. Строки — по убыванию веса, столбцы — по взвешенному '
          'баллу. Наведите на ячейку, чтобы увидеть факт, на котором стоит оценка. Обещания оценены по сайтам 20.10.2026, '
          'исполнение — по жалобам на 100 отзывов Яндекс Карт.') +
    obs('Лучшие решения рассыпаны по разным компаниям: оплата после монтажа — у Радуги, Облзабора и Доступных заборов, '
        'фиксированная смета — у ПСК Забор, цена ворот рядом с автоматикой — у ПрофЗаборов и ЗаводЗаборов, связь после оплаты не закрыта '
        'ни у кого выше 3 баллов. Их сборка в одном предложении проверяется гипотезой H1.') +
    block('Итоговые баллы', rank_chart,
          f'Взвешенный балл = Σ(балл × вес) / Σ вес. Сумма по {len(score_rows)} критериям — в нижних строках тепловой карты.') +
    obs(f'Масштаб не поднимает балл: Мастеровит — первый по силе конкурента (выручка группы 3 295 млн ₽, Директ, реклама на картах) '
        f'и {order_w.index("masterovit.ru") + 1}-й по взвешенному баллу ({fnum(wscore["masterovit.ru"], 2)}). Высокий балл дают низкий негатив, '
        f'снятие риска оплаты и квалификация: Заборово — {fnum(wscore["zaborovo.ru"], 2)}, Доступные заборы — {fnum(wscore["dostup-zabor.ru"], 2)}, '
        f'ПрофЗаборы — {fnum(wscore["prof-zabory.ru"], 2)}.') +
    block('Сила конкурента', strength_html,
          'Визиты, реклама, оценки, подписчики и выручка описывают силу компании; критериями выбора клиента они не являются и '
          'в сумму баллов не входят. Директ, Карты и Авито — 21.10.2026; визиты — Similarweb, оценка.') +
    obs('Рейтинг на карточке плохо различает компании: у шести из десяти он 4,9–5,0, а доля 1–3★ в текстах — от 4,3% до 31,9%. '
        'Для сравнения надёжности подходит доля негатива в текстовых отзывах.') +
    block('Компании по очереди', comp_html, 'В чём силён и где проседает каждый из 10 конкурентов полного разбора.') +
    obs('У лидеров по объёму (Мастеровит, ЗаводЗаборов) жалобы смещены на «после монтажа»: ржавчина, гарантия, столбы. '
        'У средних игроков — на «до монтажа»: смета, связь, сроки. Оффер новичка может закрывать обе группы сразу.')
)

# ================================================================ TAB 4 — Реклама
# 1. Кто крутит Директ
dir_items = []
for d in sorted(MAIN, key=lambda d: -(ADS_DIRECT.get(d, {}).get('q') or 0)):
    a = ADS_DIRECT.get(d)
    if a:
        sub = (f'{d} · {a["src"]}')
        dir_items.append(dict(label=esc(dname(d)), sub=esc(sub),
                              tip=f'{dname(d)}: {fnum(a["q"])} запросов в контексте, {fnum(a["ads"])} объявлений; {a["src"]}',
                              series=[(a['q'], 's1', fnum(a['q']), None), (a['ads'], 's2', fnum(a['ads']), None)]))
    else:
        dir_items.append(dict(label=esc(dname(d)), sub=d,
                              series=[(None, 's1', '', 'не найдено в отчётах Keys.so и Spywords; отдельный отчёт не открыт (лимит)'),
                                      (None, 's2', '', '—')]))
dir_chart = legend([('s1', 'запросов в контексте'), ('s2', 'объявлений на поиске')]) + hbar(dir_items, aria='Директ по компаниям')

# 2. Бюджеты
bud_rows = []
for r in budgets:
    if 'Spywords' in r['source'] or num(r['budget_month'].split(' ')[0] if r['budget_month'] else None):
        bm = num((r['budget_month'] or '').split(' ')[0])
        bud_rows.append((r['domain'], 'Spywords' if 'Spywords' in r['source'] else 'Keys.so', bm, r))
b_items = []
for d in ['masterovit.ru', 'zaborovo.ru', 'zavodzaborov.ru', 'sales.prof-zabory.ru', 'prof-zabory.ru']:
    sp = next((x for x in bud_rows if x[0] == d and x[1] == 'Spywords'), None)
    ks = next((x for x in bud_rows if x[0] == d and x[1] == 'Keys.so'), None)
    b_items.append(dict(label=esc(d), sub=esc('лендинг ПрофЗаборов' if d.startswith('sales.') else dname(d)),
                        series=[(sp[2] if sp else None, 's2', (fnum(sp[2]) + ' ₽ в месяц') if sp else '', 'Spywords не снят'),
                                (ks[2] if ks else None, 'sg', (fnum(ks[2]) + ' ₽, период не указан') if ks else '', 'Keys.so не снят')]))
bud_chart = legend([('s2', 'Spywords: дневной бюджет × 30, оценка'), ('sg', 'Keys.so: «прогноз бюджета» без периода')]) + \
    hbar(b_items, aria='Бюджеты Директа')
sp_tab = '<div class="tscroll"><table class="tbl"><thead><tr><th>Домен</th><th>Бюджет в день</th><th>В месяц (× 30)</th>' \
         '<th>Переходов из рекламы в месяц</th><th>Цена клика</th><th>Заявок при конверсии 1%</th><th>Цена заявки</th></tr></thead><tbody>' + ''.join(
    f'<tr><th scope="row">{esc(r["domain"])}</th><td class="n">{fnum(num(r["budget_day"]))} ₽</td><td class="n">{fnum(bm)} ₽</td>'
    f'<td class="n">{fnum(num(r["traffic_from_ads"]))}</td><td class="n">{esc((r["cpc_calc"] or "").split(" ")[0])} ₽</td>'
    f'<td class="n">{fnum(num((r["orders_month_est"] or "").split(" ")[0]), 1)}</td><td class="n">{fnum(num((r["cost_per_order_est"] or "").split(" ")[0]))} ₽</td></tr>'
    for d_, s_, bm, r in bud_rows if s_ == 'Spywords') + '</tbody></table></div>'

# 3. Объявления: тексты
ad_cards = []
for dom, title in (('masterovit.ru', 'Мастеровит'), ('sales.prof-zabory.ru', 'ПрофЗаборы (лендинг sales.prof-zabory.ru)'),
                   ('zavodzaborov.ru', 'ЗаводЗаборов'), ('zaborovo.ru', 'Заборово')):
    rows_d = [a for a in ads_y if a['domain'] == dom and a['headline']]
    srch = sorted([a for a in rows_d if a['ad_type'] == 'поиск'], key=lambda a: -(num(a['queries_per_ad']) or 0))
    seen, srch_u = set(), []
    for a in srch:
        k = (a['headline'], a['text'])
        if k not in seen:
            seen.add(k)
            srch_u.append(a)
    rsya = sorted([a for a in rows_d if a['ad_type'] == 'РСЯ'], key=lambda a: -(num(a['days_active']) or 0))

    def ad_li(a, kind):
        meta = []
        if num(a['queries_per_ad']):
            meta.append(f'{fnum(num(a["queries_per_ad"]))} запросов')
        if num(a['days_active']):
            meta.append(f'{fnum(num(a["days_active"]))} дн. в показе')
        if a['first_seen'] or a['last_seen']:
            meta.append(f'{a["first_seen"] or "…"} — {a["last_seen"] or "…"}')
        if a['position']:
            meta.append(f'позиция {a["position"]}')
        sl = f'<p class="ad-sl">Быстрые ссылки: {tx(a["sitelinks"])}</p>' if a['sitelinks'] else ''
        ex = f'<p class="ad-sl">Уточнения: {tx(a["extensions"])}</p>' if a['extensions'] else ''
        return (f'<li class="ad"><p class="ad-h">{tx(a["headline"])}{(" · " + tx(a["headline2"])) if a["headline2"] else ""}</p>'
                f'<p class="ad-t">{tx(a["text"])}</p>{sl}{ex}<p class="ad-m">{kind} · {esc(" · ".join(meta))}</p></li>')

    body = '<ul class="ads">' + ''.join(ad_li(a, 'поиск') for a in srch_u[:4]) + ''.join(ad_li(a, 'РСЯ') for a in rsya[:2]) + '</ul>'
    rest = srch_u[4:] + rsya[2:]
    more = details(f'Ещё {len(rest)} объявлений', '<ul class="ads">' + ''.join(ad_li(a, a['ad_type']) for a in rest) + '</ul>') if rest else ''
    ad_cards.append(f'<article class="adcard"><h4>{esc(title)}</h4>{body}{more}</article>')
ads_html = '<div class="adcards">' + ''.join(ad_cards) + '</div>'

S_ADY = md_sections(N / 'ads_yandex_spravka.md')
argu = sec(S_ADY, '4.')
argu_tab = md_tables(argu)[0] if md_tables(argu) else []
argu_html = table_html(argu_tab, names=True)
campaigns = md_html('\n'.join(l for l in argu.split('\n') if not l.lstrip().startswith('|')), names=True)
checklist = md_html(sec(S_ADY, '5.'), names=True)

# 4. Яндекс Карты
ym = [r for r in ads_maps if r['source'] == 'Яндекс Карты']
q_items = []
for q in ('заборы', 'установка заборов', 'забор под ключ', 'откатные ворота'):
    rs = [r for r in ym if r['query'] == q]
    ad = [r for r in rs if r['ad_mark'].startswith('рекламное')]
    top10 = [r for r in rs if (num(r['rank']) or 99) <= 10]
    top10_ad = [r for r in top10 if r['ad_mark'].startswith('рекламное')]
    pr = [r for r in rs if r['priority_placement'] == 'да']
    q_items.append(dict(label=f'«{esc(q)}»', sub=f'карточек в списке {len(rs)} · в первых 10 с рекламой {len(top10_ad)} из {len(top10)} · приоритетное размещение {len(pr)}',
                        series=[(len(ad), 's2', f'{len(ad)} с рекламой', None), (len(rs) - len(ad), 'sg', f'{len(rs) - len(ad)} без рекламы', None)]))
maps_chart = legend([('s2', 'карточек с рекламным блоком'), ('sg', 'карточек без рекламы')]) + hbar(q_items, aria='Реклама на Яндекс Картах')
mp_rows = []
for d in MAIN:
    rs = [r for r in ym if r['competitor'] == d]
    ad = [r for r in rs if r['ad_mark'].startswith('рекламное')]
    pr = [r for r in rs if r['priority_placement'] == 'да']
    promo = next((r['promo_action'] for r in rs if r['promo_action']), '')
    prods = next((r['ad_products_prices'] for r in rs if r['ad_products_prices']), '')
    best = min([int(num(r['rank'])) for r in ad if num(r['rank'])] or [0])
    mp_rows.append(f'<tr><th scope="row">{esc(dname(d))}<small>{d}</small></th><td class="n">{len(rs)}</td><td class="n">{len(ad)}</td>'
                   f'<td class="n">{len(pr)}</td><td class="n">{best or "—"}</td><td>{tx(short(promo, 140)) or "—"}</td><td>{tx(short(prods, 140)) or "—"}</td></tr>')
maps_tab = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Компания</th><th>Появлений в 4 выдачах</th><th>С рекламой</th>'
            '<th>Приоритетное размещение</th><th>Лучшее место с рекламой</th><th>Акция в карточке</th><th>Витрина с ценами</th></tr></thead><tbody>' +
            ''.join(mp_rows) + '</tbody></table></div>')
maps_shots = '<div class="shots">' + ''.join(shot(t, l, c, esc(c)) for t, l, c in MAPS_IMG) + '</div>' if MAPS_IMG else ''

S_ADS = md_sections(N / 'ads_social_spravka.md')
obs_items = {}
for ln in sec(S_ADS, 'Наблюдения').split('\n'):
    m = re.match(r'(\d+)\.\s+(.*)', ln)
    if m:
        obs_items[int(m.group(1))] = m.group(2)
gis_usl = ''.join(f'<p>{inline(obs_items[k], names=True)}</p>' for k in (9, 10) if k in obs_items)

# Директ на страницах Яндекс Услуг
usl_direct = Counter()
for r in ads_pl:
    if r['platform'] == 'Яндекс Услуги' and r['block'].startswith('объявление Яндекс Директа') and r['competitor']:
        usl_direct[r['competitor']] += 1

# 5. ВК и Telegram
vk_rows = ''.join(
    f'<tr><td>{esc(r["date"])}</td><td>{esc(r["company"])}</td><td>{esc(r["format"])}</td><td>{tx(short(r["offer_text"], 220))}</td>'
    f'<td class="n">{esc(r["likes"])}</td><td>{ext_link(r["source"], "пост")}</td></tr>'
    for r in vkads if r['date'])
vk_table = ('<div class="tscroll"><table class="tbl"><thead><tr><th>Дата</th><th>Компания</th><th>Формат</th><th>Текст и оффер</th>'
            '<th>Лайков</th><th>Ссылка</th></tr></thead><tbody>' + vk_rows + '</tbody></table></div>')
vk_fig = shot(VKIMG, VKIMG, 'Посев Заборово в сообществе Сергиева Посада',
              'Посев Заборово 16.10.2026: 8 519 просмотров, оффер «откатные ворота за 1 ₽» через квиз') if VKIMG else ''
st_rows = ''.join(f'<tr><td>{tx(r["platform"])}</td><td>{tx(r.get("format") or r.get("what", ""))}</td><td>{tx(r["status"])}</td>'
                  f'<td>{esc(clean(short(r["reason"], 200)))}</td></tr>' for r in ads_vk_st + ads_tg_st)
status_tab = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Площадка</th><th>Что искали</th><th>Статус</th><th>Причина</th>'
              '</tr></thead><tbody>' + st_rows + '</tbody></table></div>')

# 6. Keys.so: рекламодатели по запросам и цена клика
kq_items = []
for q, v in sorted(keys.items(), key=lambda kv: -len(kv[1]['ads'])):
    ads_ = v['ads']
    main_in = [a for a in ads_ if a in MAIN]
    kq_items.append(dict(label=f'«{esc(q)}»', sub=f'{fnum(v["f"])} запросов · прогноз клика {v["cpc"]} ₽',
                         tip=f'{q}: рекламодатели — {", ".join(ads_) if ads_ else "нет"}',
                         series=[(len(ads_), 's1', f'{len(ads_)}' + (f' · из списка: {", ".join(dname(a) for a in main_in)}' if main_in else ''), None)]
                         if ads_ else [(None, 's1', '', 'рекламодателей в выдаче нет')]))
kq_chart = hbar(kq_items, vmax=max(ads_counts), aria='Рекламодатели в выдаче по запросам')

if (D / 'ads_more.csv').exists():
    more_block = '<p>Досъём объявлений подключён.</p>'
else:
    more_block = (wave2('Директ по 6 компаниям: тексты объявлений',
                        'raduga-zaborov.ru, zaboroff.ru, oblzabor.ru, zaborkin.ru (Директ идёт, тексты не сняты), dostup-zabor.ru '
                        'и pskzabor.ru (данных нет). Нужен отчёт Keys.so по каждому домену после сброса дневного лимита и Spywords.') +
                  wave2('Живая выдача Яндекса и скриншоты 5–8 лучших объявлений',
                        'Визитка, фавикон, рейтинг и позиция объявлений без подписки сервисов не видны; выдача Яндекса '
                        'и снимки объявлений не сняты (браузер был недоступен 21.10).'))

# стоимость рекламного трафика (методика 1.4.8)
ptc_rows = ''.join(
    f'<tr><th scope="row">{esc(dname(r["domain"]))}<small>{esc(r["domain"])}</small></th><td class="n">{fnum(num(r["paid_search_visits_month"]))}</td>'
    f'<td class="n">{fnum(num(r["search_cost_month_rub_low"]) / 1000)}–{fnum(num(r["search_cost_month_rub_high"]) / 1000)}</td>'
    f'<td class="n">{fnum(num(r["other_paid_visits_month"]))}</td><td>{esc(r["other_budgets_seen"])}</td><td>{esc(r["reliability"])}</td></tr>'
    for r in sorted(ptc, key=lambda r: -num(r['search_cost_month_rub_high'])))
_pm = {r['domain']: r for r in ptc}
OBS_PTC = (f'По Similarweb платный поиск Мастеровита стоит {fnum(num(_pm["masterovit.ru"]["search_cost_month_rub_low"]) / 1000)}–'
           f'{fnum(num(_pm["masterovit.ru"]["search_cost_month_rub_high"]) / 1000)} тыс. ₽ в месяц, по Spywords — 518 тыс. ₽, по Keys.so — 1,97 млн ₽ без периода; '
           f'у ПрофЗаборов — {fnum(num(_pm["prof-zabory.ru"]["search_cost_month_rub_low"]) / 1e6, 1)}–{fnum(num(_pm["prof-zabory.ru"]["search_cost_month_rub_high"]) / 1e6, 1)} млн ₽ '
           'против 41,5 тыс. ₽ по Spywords (лендинг sales.prof-zabory.ru; по основному домену Spywords и Keys.so показывают меньше 1 тыс. ₽). '
           'Источники расходятся в 3–50 раз и в разные стороны: у Мастеровита Similarweb ниже Spywords, у ПрофЗаборов — выше; '
           'Similarweb, вероятно, относит часть кликов Директа к медийной рекламе и переходам с yandex.ru. Перевести рекламу конкурентов в рубли '
           'по внешним данным надёжно нельзя. По Similarweb больше всех платного трафика у ПрофЗаборов, Мастеровита, Облзабора и ЗаводЗаборов; '
           'по прогнозу Keys.so порядок другой: Мастеровит, Заборово, ЗаводЗаборов (по Облзабору данных Keys.so нет).')
ptc_html = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Компания</th><th>Визитов из платного поиска в месяц</th>'
            '<th>× 85–124 ₽ = тыс. ₽ в месяц</th><th>Прочих платных визитов (медийная, соцсети)</th><th>Бюджеты из Spywords и Keys.so</th>'
            '<th>Надёжность Similarweb</th></tr></thead><tbody>' + ptc_rows + '</tbody></table></div>')


# доверие и B2B (сайты, 21.10)
def _vk(v):
    v = v.lower()
    return 'документ' if v.startswith('да') else 'частично' if v.startswith('частично') else 'слово'
_tr_dom = {}
for r in trust:
    d = _tr_dom.setdefault(r['domain'], {'документ': 0, 'частично': 0, 'слово': 0, 'рейтинг': 0, 'партнёрство подтв.': 0})
    if r['type'] == 'рейтинг':
        d['рейтинг'] += 1 if r['verifiable'].startswith('да') else 0
    else:
        d[_vk(r['verifiable'])] += 1
        if r['type'] == 'партнёрство' and _vk(r['verifiable']) == 'документ':
            d['партнёрство подтв.'] += 1
_named = lambda r: bool(re.search(r'юрлицо \(ООО\)|СНТ \(юрлицо|ассоциация|коттеджный посёлок$|гостинич', r['client_type'])) and not r['client_type'].endswith('(оценка)') and 'не указано' not in r['client_type'] + r['client_name_or_desc']
_b2b_dom = {}
for r in b2b:
    if _named(r):
        _b2b_dom[r['domain']] = _b2b_dom.get(r['domain'], 0) + 1
trust_rows = ''.join(
    f'<tr><th scope="row">{esc(dname(d))}<small>{esc(d)}</small></th><td class="n">{v["документ"]}</td><td class="n">{v["частично"]}</td>'
    f'<td class="n">{v["слово"]}</td><td class="n">{v["партнёрство подтв."]}</td><td class="n">{v["рейтинг"]}</td><td class="n">{_b2b_dom.get(d, 0)}</td></tr>'
    for d, v in sorted(_tr_dom.items(), key=lambda kv: -kv[1]['документ']))
trust_html = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Компания</th><th>Документ показан</th><th>Частично</th>'
              '<th>Только слово</th><th>Из них дипломы и письма поставщиков, дилерство</th><th>Сторонние рейтинги-подборки (публикация показана)</th><th>Названные объекты и заказчики-организации</th>'
              '</tr></thead><tbody>' + trust_rows + '</tbody></table></div>' +
              '<p class="note">Сайты 10 компаний: «О компании», «Сертификаты», «Партнёры», «Наши работы», отзывы; поиск рейтингов в интернете; 21.10.2026. '
              '«Документ показан» — изображение документа на сайте, включая дипломы и письма поставщиков; чужие и просроченные сертификаты — в столбце «Частично». '
              'Вторые сайты компаний (zabor-dlya-vseh.site — ЗаводЗаборов, p-z-z.ru — Заборово) показаны отдельными строками. Таблицы — sites_trust.csv и sites_b2b_cases.csv.</p>')
OBS_TRUST = ('Сертификат соответствия на свою продукцию или монтаж не показала ни одна из 10 компаний. Документы, выданные самой компании, есть у двух: '
             'у Мастеровита — сертификаты поставщиков металла 2025 года с ним как получателем, у ЗаводЗаборов — письма ВНИИС 2022 года о том, что продукция '
             'не подлежит обязательной сертификации. У четырёх показаны чужие или просроченные документы поставщиков (prof-zabory и dostup-zabor — один и тот же '
             'набор до 2018 года), у четырёх — только слова. Дилерство документом подтверждено у одной компании (ЗаводЗаборов, «Металл Профиль», 2026), '
             'логотипы DoorHan, CAME, Nice, Grand Line у пяти — без документов; СРО, ассоциаций и ISO нет ни у кого. Заказчики-организации с названием — у двух: '
             'Мастеровит (ассоциация «Стародачное», ООО «ДТ Груп»), ЗаводЗаборов (СНТ «Наука», СНТ «Лен»); у ПСК Забор — 6 названных объектов в коттеджных посёлках '
             'и на курорте, кто был заказчиком, не указано. Гипотеза для оффера: образец гарантийного талона и кейс с названием организации-заказчика и объёмом работ — '
             'этого нет ни у кого из 10; документы с компанией как получателем есть у двух из 10.')

# Венн и тип ценности
_vz = {}
for r in venn:
    _vz.setdefault(r['zone'], []).append(r)
venn_svg = ('<div class="tscroll"><div style="min-width:760px">' + (N / 'venn.svg.html').read_text(encoding='utf-8') + '</div></div>') if (N / 'venn.svg.html').exists() else ''
venn_rows = ''.join(
    f'<tr><th scope="row">{esc(r["criterion"])}<small>{esc(r["criterion_id"])} · {esc(r["class"])}</small></th><td class="n">{fnum(num(r["weight"]), 1)}</td>'
    f'<td class="n">{esc(r["n_companies_score_ge3"])}</td><td>{esc(r["zone"].replace("∩ наше", "∩ оффер").replace("догоняем", "нужно догнать"))}</td><td>{esc(r["our_status"])}</td></tr>'
    for r in sorted(venn, key=lambda r: -num(r['weight'])))
venn_tab = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Критерий</th><th>Вес</th><th>Компаний с оценкой 3+</th><th>Зона</th>'
            '<th>Оффер «Дома гирлянд»</th></tr></thead><tbody>' + venn_rows + '</tbody></table></div>')
vt_rows = ''.join(
    f'<tr><th scope="row">{esc(r["criterion"])}</th><td>{esc(r["value_type"])}</td><td>{esc(r["confidence"])}</td><td>{esc(r["hidden_motive"]) or "—"}</td>'
    f'<td>{esc(r["quote"])}<small>{esc(r["quote_source"])}</small></td></tr>' for r in valtype if r['value_type'] == 'имплицитная')
vt_html = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Имплицитный критерий</th><th>Тип</th><th>Уверенность</th><th>Скрытый мотив</th>'
           '<th>Цитата</th></tr></thead><tbody>' + vt_rows + '</tbody></table></div>')
_nexp = sum(1 for r in valtype if r['value_type'] == 'эксплицитная'); _nimp = len(valtype) - _nexp
OBS_VENN = ('Отдельного критерия, которого нет ни у кого, не нашлось: у каждого из 38 критериев оценку 3+ имеет хотя бы одна компания, зона «только наше» пуста. '
            'Обязательный минимум — 12 критериев (39,7% веса), оффер закрывает все 12. Отставание — там, где сильны 1–2 компании: связь после оплаты '
            '(вес 63,4, 2-й по весу), акт и паспорт объекта, демонтаж, неустойка. Отстройка возможна уровнем обещания: в 7 критериях (28,6% веса) обещание '
            'выше всех 10 компаний, но у 6 из 7 этот уровень шкалы добавлен 21.10 под оффер (в исходной шкале выше рынка только неустойка в рублях), а все 30 закрытых '
            'критериев пока обещание, исполнения нет. Вне оффера — качество монтажа (вес 70,0, первый) и уровень цены.')
OBS_VAL = (f'Эксплицитных ценностей — {_nexp}, имплицитных — {_nimp}: неустойка, письменное КП, опыт и масштаб, квиз со сметой, доказательства на сайте, '
           'посадочная страница. Вес по голосу клиента их занижает (1,4% суммы), хотя рынок в них вкладывается: квиз и доказательства на сайте есть у 9 из 10. '
           'Оффер закрывает 4 из 6 имплицитных; не закрыты опыт и масштаб и доказательства на сайте. Порог «клиент называет сам» — 2% отзывов или '
           'одно уточнение запроса (допущение; при 1% имплицитных осталось бы 3).')


# выдача Яндекса по Москве и МО (Apify) и Similarweb сентябрь 2026
_MAIN10 = ['masterovit.ru', 'prof-zabory.ru', 'zaborkin.ru', 'zavodzaborov.ru', 'raduga-zaborov.ru', 'zaborovo.ru', 'oblzabor.ru', 'dostup-zabor.ru', 'zaboroff.ru', 'pskzabor.ru']
_smo_top = [r for r in smo if int(r['queries_top10_of_15']) > 0][:24]
_smo_top += [r for r in smo if r['domain'] in _MAIN10 and r not in _smo_top]
smo_items = [dict(label=esc(dname(r['domain']) if r['domain'] in _MAIN10 else r['domain']), sub=('полный разбор · ' if r['in_brief'] else '') + f'лучшая позиция {esc(str(r["best_position"]))}',
                  series=[(num(r['queries_top10_of_15']), 's1' if r['in_brief'] else 'sg', f'{r["queries_top10_of_15"]} из 15', None)]) for r in _smo_top]
_rel_by = {}
for r in srel:
    _rel_by.setdefault(r['query'], []).append(r['related'])
rel_html = ''.join(f'<p><strong>{esc(q)}</strong>: {esc("; ".join(v))}</p>' for q, v in _rel_by.items())
smo_html = (hbar(smo_items, vmax=15, aria='Домены в топ-10 органики Яндекса, Москва и МО') +
            details('«Связанные запросы» внизу выдачи (6 запросов из 15)', rel_html) +
            '<p class="note">Яндекс, регион «Москва и Московская область» (lr=1), 15 запросов, первые 20 органических результатов; выгрузка Apify 21.10.2026. '
            'Синие столбцы — 10 компаний полного разбора (показаны все, в том числе без топ-10). Набор запросов и регион другие, чем в блоке SEO ниже (там Москва, 9 запросов, Keys.so). '
            'Рекламные места выгрузка не отдала, поэтому объявления Директа здесь не показаны.</p>')
_p = {r['domain']: r for r in smo}
OBS_SMO = (f'В органике по Москве и МО чаще всех в топ-10 Мастеровит ({_p["masterovit.ru"]["queries_top10_of_15"]} из 15) и Заборкин '
           f'({_p["zaborkin.ru"]["queries_top10_of_15"]}); Авито — в {_p["avito.ru"]["queries_top10_of_15"]}, Яндекс Услуги — в {_p["uslugi.yandex.ru"]["queries_top10_of_15"]}. '
           f'ЗаводЗаборов в топ-10 по {_p["zavodzaborov.ru"]["queries_top10_of_15"]} запросу, ПСК Забор — ни по одному (лучшая позиция {_p["pskzabor.ru"]["best_position"]}). '
           'По запросам о воротах в топ-10 стоят специалисты, которых нет среди 10 заборных компаний: vorota750.ru, otkatnye-vorota-tut.ru, vorota-group.ru, '
           'automaticheskie-vorota.ru. «Связанные запросы» повторяют «Топы» Вордстата: цена за погонный метр, цена за работу, с установкой, калькулятор, '
           'Московская область, винтовые сваи, своими руками.')
_swd = {r['domain']: r for r in swa}
sw_rows = ''.join(
    f'<tr><th scope="row">{esc(dname(r["domain"]) if r["domain"] in _MAIN10 else r["domain"])}<small>{esc(r["domain"])}</small></th><td class="n">{fnum(num(r["visits_month"])) if num(r["visits_month"]) else "—"}</td>'
    f'<td class="n">{fnum(num(r["russia_share_pct"]), 1) if r["russia_share_pct"] else "—"}</td><td class="n">{fnum(num(r["search_paid_share_of_search_pct"]), 1) if r["search_paid_share_of_search_pct"] and (num(r["visits_month"]) or 0) >= 5000 else "—"}</td><td>{esc(r["similar_sites"]) or "—"}</td>'
    f'<td>{esc(r["reliability"])}</td></tr>' for r in sorted(swa, key=lambda r: -(num(r['visits_month']) or 0)))
sw_html = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Сайт</th><th>Визитов, сентябрь 2026</th><th>Доля России, %</th>'
           '<th>Платный поиск в поисковом трафике, %</th><th>Похожие сайты по Similarweb</th><th>Надёжность</th></tr></thead><tbody>' + sw_rows + '</tbody></table></div>'
           '<p class="note">Similarweb, публичная страница сайта, снимок за сентябрь 2026; выгрузка Apify 21.10.2026: ответ по 29 доменам из 31 (без ответа — '
           'naves-pod-avto-msk.ru и moscow.kupitzabor.ru), у трёх из 29 визитов нет. «Платный поиск» здесь — доля внутри поискового трафика; во вкладке «Каналы трафика» '
           'выше — доля от всех визитов за июль–сентябрь (Pro), поэтому числа не совпадают. Для сайтов меньше 5 000 визитов доля не показывается: цифры модельные.</p>')
OBS_SW = ('Сентябрьские визиты по публичной странице Similarweb совпадают с полной версией, снятой 20.10 (Мастеровит — 107 798, ПрофЗаборы — 73 841). '
          'Лендинг sales.prof-zabory.ru получает 58 873 визита, из поискового трафика 60,9% — платный. В «похожих сайтах» у четырёх компаний полного разбора '
          'встречается russkiyzabor.ru, которого нет в списке конкурентов; в топ-10 выдачи по Москве и МО он есть по 1 запросу из 15 («забор с откатными воротами», 3-е место) — кандидат на проверку. '
          'Входят ли визиты лендинга в 73 841 визит prof-zabory.ru, по публичной странице не видно. '
          'У трёх доменов (zabory-prestige.ru, zabormo.ru, 33zabora.ru) Similarweb данных не показывает.')


# Telegram: каналы Мастеровита и Заборкина (публичные ленты t.me/s, 21.10)
tg_rows = ''.join(f'<tr><th scope="row">{esc(dname(r["domain"]))}<small>{esc(r["date"])}</small></th><td class="n">{fnum(num(r["views"]))}</td>'
                  f'<td>{esc(r["ad_marking"])}</td><td class="n">{fnum(num(r["project_cost_rub"])) if r["project_cost_rub"] else "—"}</td><td>{esc(short(r["content"], 220))}</td><td>{ext_link(r["post_url"], "пост")}</td></tr>' for r in tgp)
_tm = [r for r in tgp if r['domain'] == 'masterovit.ru']; _tz = [r for r in tgp if r['domain'] == 'zaborkin.ru']
_vm = [num(r['views']) for r in _tm if num(r['views'])]; _vz = [num(r['views']) for r in _tz if num(r['views'])]
_cz = sorted(num(r['project_cost_rub']) for r in _tz if r['project_cost_rub'])
_tg_tiles = '<div class="tiles">' + ''.join(f'<div class="tile"><div class="tile-v">{v}</div><div class="tile-l">{esc(l)}</div></div>' for v, l in (
    (f'{sum(1 for r in _tm if r["ad_marking"].startswith("да"))} из {len(_tm)}', 'постов Мастеровита с пометкой «Реклама» и Erid'),
    (f'{fnum(min(_vm))}–{fnum(max(_vm))}', 'просмотров на пост у Мастеровита'),
    (f'{len(_cz)} из {len(_tz)}', 'постов Заборкина с полной стоимостью объекта'),
    (f'{fnum(statistics.median(_cz) / 1000)} тыс. ₽', f'медиана стоимости объекта у Заборкина (n={len(_cz)})'))) + '</div>'
tg_html = (_tg_tiles + details(f'Все посты: {len(tgp)}', '<div class="tscroll"><table class="tbl small"><thead><tr><th>Канал</th><th>Просмотров</th><th>Маркировка рекламы</th>'
           '<th>Стоимость объекта, ₽</th><th>Содержание</th><th>Ссылка</th></tr></thead><tbody>' + tg_rows + '</tbody></table></div>') +
           '<p class="note">Telegram, публичные ленты каналов t.me/s, все посты с 20.07 по 21.10.2026. Имена сотрудников и телефоны в тексте скрыты. '
           'Посевы в чужих каналах снаружи не найдены: TGStat и Telemetr требуют входа, поиск по публичным страницам вернул только собственные каналы.</p>')
OBS_TG = (f'У Мастеровита {sum(1 for r in _tm if r["ad_marking"].startswith("да"))} из {len(_tm)} постов за три месяца — реклама с Erid (треть ленты), '
          'остальное — серия «схемы обмана на рынке», ролики с производства, адреса офисов. Механики рекламных постов те же, что на сайте и в Директе: '
          '«автоматика за 1 ₽», «свая за 1 ₽», скидки 20–28%, бот «РАСЧЕТ»; отдельно — замер толщины металла при клиенте, без замера можно не оплачивать остаток. '
          f'Просмотров — {fnum(min(_vm))}–{fnum(max(_vm))} на пост. Заборкин публикует {len(_tz)} постов, из них {len(_cz)} — кейсы с полной стоимостью объекта: '
          f'{fnum(_cz[0] / 1000)}–{fnum(_cz[-1] / 1000)} тыс. ₽, медиана {fnum(statistics.median(_cz) / 1000)} тыс. ₽ (в основном Ленинградская область), '
          f'со скидкой 33% на монтаж и отложенным монтажом на 6 месяцев; просмотров {fnum(min(_vz))}–{fnum(max(_vz))}. Гипотеза для «Дома гирлянд»: формат «кейс + '
          'полная смета объекта» закрывает критерий прозрачной цены; у Заборкина он есть, но при таких просмотрах эффект снаружи не виден.')

# PageSpeed Insights (Apify, 21.10)
_psi_items = []
for r in sorted(psi, key=lambda r: -(num(r['psi_mobile_score']) or -1)):
    _psi_items.append(dict(label=esc(dname(r['domain']) if r['domain'] in MAIN else r['domain']), sub=esc(r['note']) or f'LCP на телефоне {fnum(num(r["psi_mobile_lcp_s"]), 1)} с' if r['psi_mobile_lcp_s'] else esc(r['note']),
                           series=[(num(r['psi_mobile_score']), 's1', f'телефон {r["psi_mobile_score"]}', 'телефон — нет ответа'),
                                   (num(r['psi_desktop_score']), 's2', f'компьютер {r["psi_desktop_score"]}', 'компьютер — нет ответа')]))
psi_html = (legend([('s1', 'телефон'), ('s2', 'компьютер')]) + hbar(_psi_items, vmax=100, aria='PageSpeed Insights: баллы производительности') +
            '<p class="note">Google PageSpeed Insights, лабораторный замер Lighthouse на серверах Google, 21.10.2026; запуск через Apify. По masterovit.ru (телефон), '
            'zaborkin.ru, sales.prof-zabory.ru и dostup-zabor.ru (компьютер) сервис не ответил за отведённое время. Данные реальных посетителей (CrUX) выгрузка не отдаёт. '
            'Балл и LCP колеблются от запуска к запуску на 5–15 пунктов.</p>')
_pm = {r['domain']: r for r in psi}
_low = [dname(r['domain']) if r['domain'] in MAIN else r['domain'] for r in psi if r['psi_mobile_score'] and num(r['psi_mobile_score']) < 50]
OBS_PSI = (f'По PageSpeed на телефоне ниже 50 баллов — {len(_low)} из {sum(1 for r in psi if r["psi_mobile_score"])} ответивших страниц: {", ".join(_low)}. '
           f'Быстрее всех ЗаводЗаборов ({_pm["zavodzaborov.ru"]["psi_mobile_score"]}) и ПСК Забор ({_pm["pskzabor.ru"]["psi_mobile_score"]}), LCP 2,4–2,8 с. '
           f'У ПрофЗаборов главный экран на телефоне появляется через {fnum(num(_pm["prof-zabory.ru"]["psi_mobile_lcp_s"]), 0)} с, у Заборово — через '
           f'{fnum(num(_pm["zaborovo.ru"]["psi_mobile_lcp_s"]), 0)} с, при 94% мобильных визитов у prof-zabory.ru. Облачный Lighthouse 20.10 давал ниже баллы '
           '(у ЗаводЗаборов 27 против 95); оба замера сделаны не из России, причина расхождения не установлена — для сравнения компаний между собой годится каждый, абсолютные значения проверить из Москвы. Цель для посадочной «Дома гирлянд» — 80+ на телефоне и LCP до 2,5 с.')

TAB4 = (
    block('Кто крутит Директ', dir_chart,
          'Keys.so (база «Москва») и Spywords (регион «Москва»), 21.10.2026. Отсутствие компании в списках «Конкуренты» '
          'не доказывает, что она не крутит Директ: списки показывают 10 доменов с наибольшим пересечением запросов.') +
    obs('Директ фиксируется у 8 из 10 компаний. Больше всех запросов — у Мастеровита (5 739 по Keys.so или 1 591 по Spywords) '
        'и Радуги заборов (2 998 запросов, 1 573 объявления). ПрофЗаборы рекламирует не основной сайт, а лендинг-калькулятор '
        'sales.prof-zabory.ru (2 398 запросов). Рядом в рекламе стоят продавцы материалов и агрегаторы: robaz.ru, ni-max.ru, '
        'Профи.ру, Яндекс Услуги.') +
    block('Бюджеты: оценки с диапазоном', bud_chart + sp_tab,
          'Spywords: «бюджет на контекст» в день × 30 и переходы за последний месяц; цена клика = бюджет / переходы, заявки — '
          'при конверсии 1% (допущение). Keys.so показывает «прогноз бюджета» без периода — его можно использовать только '
          'как ранг. Все цифры — оценка.') +
    obs('Бюджет Мастеровита — от 518 тыс. ₽ в месяц (Spywords) до 1,97 млн ₽ (Keys.so, без периода): расхождение в 3,8 раза, '
        'поэтому 518 тыс. ₽ — нижняя оценка. Цена клика Мастеровита около 124 ₽ лежит внутри CPC его запросов (71–173 ₽). '
        'У лендинга ПрофЗаборов расчётный клик 13 ₽ в 3–19 раз ниже CPC его же запросов — бюджет 41,5 тыс. ₽ взят как нижняя граница.') +
    block('Стоимость рекламного трафика: визиты × цена клика', ptc_html,
          'Методика: платные визиты Similarweb (весь мир, июль–сентябрь 2026, в среднем за месяц) × цена клика 85–124 ₽ из медиаплана. '
          'Для медийной рекламы и соцсетей цена клика не измерена, они показаны визитами. Всё — оценка.') +
    obs(OBS_PTC) +
    block('Объявления на поиске и в РСЯ', ads_html,
          'Тексты, быстрые ссылки и уточнения — Keys.so (демо: 10 строк на домен) и Spywords (превью: 5 строк), 21.10.2026. '
          'Для поиска — сколько запросов ведут на объявление; для РСЯ — дни в показе. Долгий показ — косвенный признак '
          'работающего объявления; окупаемость снаружи не видна.') +
    obs('Три из четырёх рекламодателей выносят в объявление честную толщину металла («Замеряем толщину металла при Вас», '
        '«Гарантия толщины 100%»), цену «от» за метр — тоже три (742 ₽, 750 ₽, 2 150 ₽), бесплатный замер — три. '
        'Дольше всех в видимой выборке РСЯ держится калькулятор sales.prof-zabory.ru — 107 дней. Объявлений про откатные '
        'ворота под ключ с автоматикой в видимых строках нет.') +
    block('Чем бьются в объявлениях', argu_html + details('Структура кампаний и РСЯ', campaigns) +
          details('Чек-лист объявления по методике: 4 компании', checklist)) +
    block('Яндекс Карты: реклама в каждой из первых 10 карточек', maps_chart + '<h4>10 компаний полного разбора на картах</h4>' +
          maps_tab + maps_shots,
          'Яндекс Карты, Москва, 4 запроса, 21.10.2026. Признак рекламы — рекламный блок с маркировкой в данных карточки. '
          'Компания может появляться в выдаче несколькими филиалами.') +
    obs('По всем 4 запросам у всех 10 первых карточек есть реклама; за карты платят 6 из 10 компаний полного разбора. '
        'Мастеровит — реклама в 17 из 20 появлений, Заборово — 1-е место по «забор под ключ» с акцией «рама откатных ворот '
        'за 1 ₽». По «откатные ворота» реклама у 27 компаний — производители и дилеры ворот, ни одной из 10 заборных.') +
    block('2ГИС и Яндекс Услуги', gis_usl + ('<p class="note">Объявления Директа конкурентов на страницах Яндекс Услуг (показов в '
          'снятых страницах): ' + esc(', '.join(f'{dname(k)} — {v}' for k, v in usl_direct.most_common())) + '.</p>' if usl_direct else '')) +
    obs('2ГИС заборные компании из списка для рекламы не используют: там платят продавцы профлиста и стройбазы. На Яндекс Услугах '
        'исполнители — в основном частные мастера (104 из 110), а деньги компаний идут в Директ на тех же страницах.') +
    block('ВКонтакте, Telegram, MAX', vk_table + vk_fig + '<h4>Что снято и что нет</h4>' + status_tab,
          'Посты с пометкой «Реклама» на стенах сообществ и посевы в библиотеке SeedHunter (волна 1). Таргетированная '
          'реклама без поста на стене снаружи не видна.') +
    obs('Рекламу во ВК видно у 2 из 10 компаний, механизм повторяется: «элемент за 1 ₽» при заказе забора. '
        'Гипотеза авитолога «ВК-таргет и Макс» снаружи не подтверждается и не опровергается — её проверяет собственный тест H4.') +
    block('Telegram: каналы Мастеровита и Заборкина, июль–октябрь 2026', tg_html) +
    obs(OBS_TG) +
    block('Рекламодатели в выдаче по 9 запросам (Keys.so)', kq_chart,
          'Keys.so, Москва, топ выдачи, 05.09–05.10.2026. Цена клика здесь — прогноз сервиса «Средняя ставка».') +
    block('Что ещё не снято', more_block)
)

# ================================================================ TAB 5 — Откуда клиенты
CH = [('direct', 'Прямые'), ('search_organic', 'Поиск, органика'), ('search_paid', 'Поиск, платный'),
      ('display_ads', 'Медийная'), ('social', 'Соцсети'), ('referrals', 'Переходы'), ('email', 'Почта'),
      ('gen_ai', 'ИИ-ассистенты'), ('affiliates', 'Партнёрские')]


def ch_val(t, k):
    if k == 'social':
        return (num(t['social_organic_pct']) or 0) + (num(t['social_paid_pct']) or 0), \
            (num(t['social_organic_visits']) or 0) + (num(t['social_paid_visits']) or 0)
    return num(t[f'{k}_pct']), num(t[f'{k}_visits'])


def share_cls(v):
    if v is None or v == 0:
        return 'h0'
    for i, lim in enumerate((2, 5, 15, 30, 50), 1):
        if v < lim:
            return f'h{i}'
    return 'h6'


tr_order = sorted(MAIN, key=lambda d: -(num(traffic[d]['visits_3m']) or 0))
tm = []
for d in tr_order:
    tm.append([ch_val(traffic[d], k) for k, _ in CH])
tr_heat = legend([('h1', 'до 2%'), ('h2', '2–5%'), ('h3', '5–15%'), ('h4', '15–30%'), ('h5', '30–50%'), ('h6', '50% и выше')]) + heat(
    [esc(dname(d)) for d in tr_order], [l for _, l in CH], tm,
    lambda v: share_cls(v[0]), lambda v: pct(v[0]),
    lambda r, c, v: f'{dname(tr_order[r])} · {CH[c][1]}: {pct(v[0])} = {fnum(v[1])} визитов за 3 месяца',
    corner='Компания · визитов за 3 мес.',
    row_subs=[f'{fnum(num(traffic[d]["visits_3m"]))}' + (' · модель' if 'модель' in traffic[d]['reliability'] else '') for d in tr_order])

# помесячно
mon_items = []
for d in tr_order:
    o = tover[d]
    vals = [num(o['visits_2026_07']), num(o['visits_2026_08']), num(o['visits_2026_09'])]
    mon_items.append(dict(label=esc(dname(d)), sub=f'платные каналы {traffic[d]["paid_total_pct"]}%',
                          series=[(vals[0], 'y1', fnum(vals[0]), None), (vals[1], 'y2', fnum(vals[1]), None),
                                  (vals[2], 'y3', fnum(vals[2]), None)]))
mon_chart = legend([('y1', 'июль 2026'), ('y2', 'август 2026'), ('y3', 'сентябрь 2026')]) + hbar(mon_items, aria='Визиты по месяцам')

# сезонность и бренд-спрос — Вордстат, выгрузки пользователя 21.10.2026
sgn = lambda v: f'{v:+.1f}%'.replace('.', ',').replace('-', '−')
WS_MONTHS = [f'{y}-{m:02d}' for y in (2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 9)]
bt_map = {r['series']: r for r in btrend}


def ws_series(q, reg='Москва и область'):
    return {r['month']: int(r['count']) for r in wsm if r['query'] == q and r['region'] == reg}


def coef(eq):
    a, b = eq.split('=')[1].split('·')[0].split(' + ')
    return float(a), float(b)


def ws_chart(q, series_name, aria, div=1000, dec=1, anomal=()):
    sm = ws_series(q)
    tr = bt_map.get(series_name)
    trends = []
    if tr:
        trends = [('lin',) + coef(tr['linear_equation']) + ('',), ('log',) + coef(tr['log_equation']) + ('tlog',)]
    ser = [(mm, sm.get(mm), mm in anomal) for mm in WS_MONTHS]
    leg = ('<p class="note"><span class="lg-line"></span>линейный тренд · <span class="lg-line tlog"></span>логарифмический тренд'
           + (f' · R² {fnum(num(tr["linear_r2"]), 2)} и {fnum(num(tr["log_r2"]), 2)}: тренды объясняют малую часть колебаний, '
              f'направление считается по скользящей сумме за 12 месяцев — {esc(tr["direction"])}' if tr else '') + '</p>')
    return season_svg(ser, trends=trends, aria=aria, div=div, dec=dec) + leg


mk_cols = [('avg_month_last12_mo', 'В месяц, среднее за 12 мес.', fnum), ('sep_2026_mo', 'Сентябрь 2026', fnum),
           ('may_to_jan', 'Май / январь 2026', lambda v: '×' + fnum(v, 1)), ('nov_to_sep_2025', 'Ноябрь / сентябрь 2025', lambda v: fnum(v * 100) + '%'),
           ('jan_sep_2026_vs_2025_pct', 'Янв–сен 2026 к 2025', lambda v: f'{v:+.1f}%'.replace('.', ',').replace('-', '−')),
           ('jan_sep_2026_vs_2024_pct', 'Янв–сен 2026 к 2024', lambda v: f'{v:+.1f}%'.replace('.', ',').replace('-', '−')),
           ('rest_jan_sep_2026_vs_2025_pct', 'Остальная Россия: янв–сен 2026 к 2025', lambda v: f'{v:+.1f}%'.replace('.', ',').replace('-', '−')),
           ('mo_share_of_rf_pct', 'Доля Москвы и МО в России, окт 2025 — сен 2026', lambda v: fnum(v, 1) + '%'),
           ('mo_share_of_rf_prev12_pct', 'То же годом раньше', lambda v: fnum(v, 1) + '%')]
mk_tab = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Запрос</th>' + ''.join(f'<th>{esc(h)}</th>' for _, h, _ in mk_cols) +
          '</tr></thead><tbody>' + ''.join(
              f'<tr><th scope="row">{esc(q)}</th>' + ''.join(
                  f'<td class="n">{f(num(r[k])) if num(r[k]) is not None else "не снято"}</td>' for k, _, f in mk_cols) + '</tr>'
              for q, r in mks.items()) + '</tbody></table></div>')
ks = next((r for r in wsd if r['query'] == 'забор под ключ' and r['month'] == '2026-09'), None)
keys_note = ''
if ks:
    _ks = {r['month']: num(r['frequency_broad']) for r in wsd if r['query'] == 'забор под ключ' and re.fullmatch(r'\d{4}-\d{2}', r['month']) and 'повторяет' not in r['note']}
    _rat = [_ks[m] / season_map[m] for m in _ks if m in season_map and _ks[m]]
    _yk = round(100 * (_ks['2026-05'] / _ks['2025-05'] - 1))
    _yw = round(100 * (season_map['2026-05'] / season_map['2025-05'] - 1))
    keys_note = (f'<p class="note">Сверка с Keys.so: широкая частотность «забор под ключ» в базе «Москва» за сентябрь 2026 — '
                 f'{fnum(num(ks["frequency_broad"]))}, Вордстат по Москве и области — {fnum(sep26)}. Отношение Keys.so к Вордстату по месяцам — '
                 f'от {fnum(min(_rat), 1)} до {fnum(max(_rat), 1)}; год к году источники расходятся по знаку '
                 f'(май 2026 к маю 2025: Keys.so {sgn(_yk)}, Вордстат {sgn(_yw)}). В отчёте взят Вордстат как первоисточник; '
                 'динамика 2026 года к 2025-му — оценка. Ёмкость кликов медиаплана = широкая частотность Keys.so × 0,248, что близко к Вордстату '
                 '(расхождение 5–12%), сезонный множитель 0,51–0,70 совпадает с Вордстатом (ноябрь / сентябрь 2025 — 0,50), поэтому медиаплан не меняется.</p>')
season_chart = (ws_chart('забор под ключ', 'рынок «забор под ключ», Москва и МО', 'Частотность «забор под ключ» по месяцам, Москва и МО') +
                '<h4>«Откатные ворота», Москва и МО</h4>' +
                ws_chart('откатные ворота', 'рынок «откатные ворота», Москва и МО', 'Частотность «откатные ворота» по месяцам, Москва и МО') +
                '<h4>Четыре запроса рынка: сезон и динамика</h4>' + mk_tab +
                '<p class="note">Значения на столбцах — тысячи запросов. Вордстат, «Динамика», по месяцам, январь 2024 — сентябрь 2026, '
                'Москва и область, все устройства; выгрузка 21.10.2026. «Остальная Россия» — регион «Россия, кроме Москвы и области»; '
                'по «установка забора» он не выгружался.</p>' + keys_note)

# бренд-спрос
an_ob = next((r['anomaly_months'].split(';') for r in bds if r['query'] == 'облзабор' and r['anomaly_months']), [])
brand_items = []
for r in bds:
    yoy = num(r['yoy_pct'])
    sub = f'{esc(dname(r["domain"]))} · за год {sgn(yoy)}' + (' (всплески 2025 года)' if r['anomaly_months'] else '')
    brand_items.append(dict(label=esc(r['query']), sub=sub, tip=r['note'] or None,
                            series=[(num(r['avg_month_last12']), 's1', f'{fnum(num(r["avg_month_last12"]))} в месяц · {fnum(num(r["share_of_10_brands_pct"]), 1)}%', None)]))
brand_chart = hbar(brand_items, aria='Бренд-спрос 10 конкурентов, запросов в месяц')
brand_rows = ''
for r in bds:
    tr = bt_map.get(f'бренд «{r["query"]}» ({r["domain"]})', {})
    rr = brr.get(r['domain'], {})
    rev = (f'{fnum(num(rr["revenue_per_brand_query_rub"]))} ₽ на запрос (ГИР БО)' if rr.get('revenue_per_brand_query_rub')
           else f'{esc(rr.get("revenue_est_rub", ""))} — оценка' if rr.get('revenue_est_rub') else '—')
    brand_rows += (f'<tr><th scope="row">{esc(r["query"])}<small>{esc(r["domain"])}</small></th>'
                   f'<td class="n">{fnum(num(r["sum_last12"]))}</td><td class="n">{fnum(num(r["sep_2026"]))}</td>'
                   f'<td class="n">{sgn(num(r["yoy_pct"]))}</td>'
                   f'<td>{esc(tr.get("direction", "—"))}; наклон {fnum(num(tr.get("rolling12_slope_pct_per_month")), 2) if tr else "—"}% в месяц</td>'
                   f'<td>{rev}</td><td>{tx(clean(r["note"])) or "—"}</td></tr>')
brand_tab = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Бренд</th><th>Запросов за 12 мес. (окт 2025 — сен 2026)</th>'
             '<th>Сентябрь 2026</th><th>Год к году</th><th>Тренд (скользящая сумма 12 мес.)</th><th>Выручка на брендовый запрос / оценка выручки 2025</th>'
             '<th>Пометка</th></tr></thead><tbody>' + brand_rows + '</tbody></table></div>')
trend_html = (
    '<h4>Бренд-спрос 10 конкурентов</h4>'
    '<p>Вордстат, «Динамика», помесячно, январь 2024 — сентябрь 2026, Москва и область. Справа — среднее в месяц за последние '
    '12 месяцев и доля в сумме 10 брендов. Год к году — октябрь 2025 — сентябрь 2026 против октября 2024 — сентября 2025.</p>' +
    brand_chart +
    '<h4>Мастеровит: бренд-спрос по месяцам и тренды</h4>' +
    ws_chart('мастеровит', 'бренд «мастеровит» (masterovit.ru)', 'Бренд-спрос «мастеровит» по месяцам, Москва и МО') +
    '<p class="note">Линейный тренд y = a + b·t, логарифмический y = a + b·ln(t), t — номер месяца (1 = январь 2024). '
    'У сырого ряда R² низкий из-за сезона, поэтому направление бренда определяется по скользящей сумме за 12 месяцев: в ней сезон '
    'взаимно гасится.</p>' +
    details('Таблица: бренд-спрос, тренд и выручка на брендовый запрос', brand_tab +
            '<p class="note">Выручка на брендовый запрос = выручка ООО за 2025 год (ГИР БО) / бренд-запросы за 2025 год по Москве и МО. '
            'Для ИП отчётности нет, выручка оценена как бренд-запросы × выручка на запрос у пяти ООО без Мастеровита. Ограничения: '
            'бренд-запросы взяты только по Москве и МО, выручка — по всем регионам и товарам компании; «завод заборов» и «доступные заборы» '
            'частично общие запросы.</p>'))

# регионы
def dist_items(q, n=12):
    sel = [r for r in wsdist if r['query'] == q and not r['district'].startswith(('Москва', 'ИТОГО', 'Россия'))][:n]
    return [dict(label=esc(r['district'].replace(' (городской округ)', '').replace(' городской округ', '')),
                 sub=f'индекс интереса {fnum(num(r["affinity_pct"]))}%',
                 series=[(num(r['frequency']), 's1', f'{fnum(num(r["frequency"]))} · {fnum(num(r["share_of_msk_mo_pct"]), 1)}%', None)]) for r in sel]
def dist_total(q, k):
    return next(r for r in wsdist if r['query'] == q and r['district'].startswith(k))
dist_tab_rows = ''.join(
    f'<tr><td>{esc(r["query"])}</td><th scope="row">{esc(r["district"])}</th><td class="n">{fnum(num(r["frequency"]))}</td>'
    f'<td class="n">{fnum(num(r["share_of_msk_mo_pct"]), 2) + "%" if r["share_of_msk_mo_pct"] else "—"}</td><td class="n">{fnum(num(r["affinity_pct"])) + "%" if r["affinity_pct"] else "—"}</td></tr>'
    for r in wsdist)
rc_html = ('<h4>Где в МО ищут: округа</h4>'
           '<p>Вордстат, «Регионы», 20.09–20.10.2026, все устройства. Длина столбца — число запросов за месяц; после точки — доля в сумме '
           '«Москва и область». Индекс интереса — насколько чаще среднего по России жители округа задают этот запрос (100% — как в среднем).</p>'
           '<div class="grid2"><div><h4>«Забор под ключ»</h4>' + hbar(dist_items('забор под ключ'), aria='Округа МО: забор под ключ') +
           '</div><div><h4>«Откатные ворота»</h4>' + hbar(dist_items('откатные ворота'), aria='Округа МО: откатные ворота') + '</div></div>' +
           f'<p class="note">Москва отдельно в выгрузке не выделена; часть округов (Подольск, Балашиха, Химки, Домодедово, Серпухов, Коломна и др.) '
           f'отдельной строки не получила. Их сумма вместе с Москвой — {fnum(num(dist_total("забор под ключ", "Москва")["share_of_msk_mo_pct"]), 1)}% запросов '
           f'«забор под ключ» и {fnum(num(dist_total("откатные ворота", "Москва")["share_of_msk_mo_pct"]), 1)}% — «откатные ворота». Региональный коэффициент '
           'методики (частотность округа / частотность Москвы и области) и оценка визитов конкурента масштаба Мастеровита в округе — '
           'в файле regional_coef.csv.</p>' +
           details('Таблица: все округа МО по двум запросам', '<div class="tscroll"><table class="tbl small"><thead><tr><th>Запрос</th><th>Округ</th>'
                   '<th>Запросов за месяц</th><th>Доля Москвы и МО</th><th>Индекс интереса</th></tr></thead><tbody>' + dist_tab_rows + '</tbody></table></div>'))
brand_block = trend_html + rc_html

# Топы запросов Вордстата: намерения и критерии
def tops_html(q, reg):
    it = [r for r in wstopi if r['query'] == q and r['region'] == reg and r['dimension'] == 'намерение' and num(r['share_pct'])]
    it.sort(key=lambda r: -num(r['share_pct']))
    head = it[0]
    items = [dict(label=esc(r['value']), series=[(num(r['share_pct']), 's1', fnum(num(r['share_pct']), 1) + '%', None)]) for r in it]
    cr = sorted([r for r in wstopi if r['query'] == q and r['region'] == reg and r['dimension'] in ('критерий', 'материал') and num(r['share_pct']) >= 0.3], key=lambda r: -num(r['share_pct']))
    cr_items = [dict(label=esc(r['value']), sub=esc(r['dimension']), series=[(num(r['share_pct']), 's2', fnum(num(r['share_pct']), 1) + '%', None)]) for r in cr]
    top = sorted([r for r in wstops if r['query'] == q and r['region'] == reg and r['intent'] == 'цена и заказ'], key=lambda r: -int(r['count']))[:12]
    tl = ''.join(f'<li>{esc(r["phrase"])} — {fnum(int(r["count"]))}</li>' for r in top)
    return (f'<h4>«{esc(q)}», {esc(reg)}: {fnum(num(head["head_frequency"]))} запросов за месяц, {fnum(num(head["phrases"]))} фраз</h4>'
            '<div class="grid2"><div><h4>Намерение (доля частот фраз)</h4>' + hbar(items, vmax=100, aria='Намерения: ' + q) +
            '</div><div><h4>Критерии и материалы в формулировках</h4>' + hbar(cr_items, aria='Критерии: ' + q) + '</div></div>' +
            details('Самые частые фразы «цена и заказ»', f'<ul>{tl}</ul>'))
_tq = sorted({r['query'] for r in wstopi})
_REG_MAIN = 'Россия, кроме Москва и область'
_REG_MO = 'Россия без 16 областей Центра (Москва и МО входят)'
_ti_all = {(r['query'], r['region'], r['value']): num(r['share_pct']) for r in wstopi}
_cmp_rows = ''.join(
    f'<tr><td>{esc(q)}</td><th scope="row">{esc(v)}</th><td class="n">{fnum(_ti_all.get((q, _REG_MAIN, v), 0), 1)}%</td><td class="n">{fnum(_ti_all.get((q, _REG_MO, v), 0), 1)}%</td></tr>'
    for q in _tq for v in ('цена и заказ', 'монтаж и изготовление', 'своими руками', 'комплектующие и автоматика', 'правовой вопрос', 'бренд производителя'))
_mo_rows = ''.join(f'<tr><td>{esc(r["query"])}</td><th scope="row">{esc(r["phrase"])}</th><td class="n">{fnum(num(r["count_incl_msk_mo"]))}</td><td class="n">{fnum(num(r["count_rf_without_msk_mo"]))}</td></tr>'
                   for q in _tq for r in [x for x in rows('ws_tops_mo_phrases') if x['query'] == q][:15])
tops_block = ''.join(tops_html(q, _REG_MAIN) for q in _tq) + (
    '<h4>Регион с Москвой и МО: доли намерений против России без Москвы и МО</h4>'
    '<div class="tscroll"><table class="tbl small"><thead><tr><th>Запрос</th><th>Намерение</th><th>Россия без Москвы и МО</th>'
    '<th>Россия без 16 областей Центра (Москва и МО входят)</th></tr></thead><tbody>' + _cmp_rows + '</tbody></table></div>' +
    details('Фразы с Москвой, МО и городами области (по 15 на запрос)',
            '<div class="tscroll"><table class="tbl small"><thead><tr><th>Запрос</th><th>Фраза</th><th>Регион с Москвой и МО</th><th>Россия без Москвы и МО</th></tr></thead><tbody>'
            + _mo_rows + '</tbody></table></div>') +
    f'<p class="note">Вордстат, «Топы запросов», 20.09–20.10.2026, все устройства; две выгрузки 21.10.2026: «{esc(_REG_MAIN)}» и «Россия, кроме 16 областей Центра» '
    '(Москва и МО в неё входят, выгрузки только по Москве и МО нет). Графики выше — по первой. '
    'Фразы вложены друг в друга (частота «установка забора цена» входит в «установка забора»), поэтому доли показывают структуру спроса; '
    'число людей по ним не считается. Классы назначены по словам во фразе (словарь классов — в файле ws_tops_intents.csv и скрипте разбора). '
    'Выгрузка строго по Москве и МО не делалась. «0» во втором столбце таблицы фраз — фраза ниже порога выгрузки (Вордстат отдаёт до 2 000 фраз). При выборочной проверке 60 фраз 9 были отнесены к классу неточно; на направление выводов это не влияет.</p>')
_ti = {(r['query'], r['value']): num(r['share_pct']) for r in wstopi if r['region'] == 'Россия, кроме Москва и область'}
_tb = {(r['query'], r['value']): num(r['share_pct']) for r in wstopi if r['dimension'] == 'бренды' and r['region'] == 'Россия, кроме Москва и область'}
OBS_TOPS = (
    f'Об откатных воротах чаще спрашивают, как сделать самому ({fnum(_ti[("откатные ворота", "своими руками")], 1)}% частот фраз) и какие '
    f'взять комплектующие и автоматику ({fnum(_ti[("откатные ворота", "комплектующие и автоматика")], 1)}%), чем цену и заказ '
    f'({fnum(_ti[("откатные ворота", "цена и заказ")], 1)}%); фразы с брендом ворот или автоматики (Алютех, DoorHan, CAME, Nice) — '
    f'{fnum(_tb[("откатные ворота", "фразы с брендом")], 1)}%. В «установка забора» на цену и заказ приходится '
    f'{fnum(_ti[("установка забора", "цена и заказ")], 1)}%, на вопросы о соседях, правилах и нормах — {fnum(_ti[("установка забора", "правовой вопрос")], 1)}%; '
    f'в формулировках есть фундамент и столбы ({fnum(_ti[("установка забора", "фундамент и столбы")], 1)}%), цена работы без материала '
    f'({fnum(_ti[("установка забора", "цена работы отдельно от материала")], 1)}%), уклон участка ({fnum(_ti[("установка забора", "уклон и сложный участок")], 1)}%) '
    f'и рассрочка ({fnum(_ti[("установка забора", "рассрочка")], 1)}%). В регионе, куда входят Москва и МО, доля цены и заказа в «установка забора» выше — '
    f'{fnum(_ti_all[("установка забора", _REG_MO, "цена и заказ")], 1)}% против {fnum(_ti_all[("установка забора", _REG_MAIN, "цена и заказ")], 1)}%; среди фраз с Москвой и МО — «установка заборов в московской области» (1 652 в месяц) и брендовая «установка заборов московские заборы» (2 539). '
    'Гипотеза: объявление о воротах с названием бренда автоматики против объявления без него при равном бюджете; оставить вариант, '
    'если CTR выше на 20% и цена заявки не выше. В предложении по забору — цена работы отдельной строкой и согласование границы с соседом.')


# наблюдения по Вордстату — числа из данных
_z, _g = ws_series('забор под ключ'), ws_series('откатные ворота')
_mz, _mg = mks['забор под ключ'], mks['откатные ворота']
OBS_SEASON = (
    f'«Забор под ключ», Москва и МО: май / январь — ×{fnum(num(_mz["may_to_jan_2024"]), 1)} в 2024 году, ×{fnum(num(_mz["may_to_jan_2025"]), 1)} в 2025-м '
    f'и ×{fnum(num(_mz["may_to_jan"]), 1)} в 2026-м; ноябрь — {fnum(100 * num(_mz["nov_to_sep_2024"]))}% и {fnum(100 * num(_mz["nov_to_sep_2025"]))}% сентября, '
    f'декабрь — {fnum(100 * num(_mz["dec_to_sep_2024"]))}% и {fnum(100 * num(_mz["dec_to_sep_2025"]))}% (2024 и 2025 годы). '
    f'«Откатные ворота» ровнее: май / январь ×{fnum(num(_mg["may_to_jan_2025"]), 1)}–{fnum(num(_mg["may_to_jan_2024"]), 1)}, ноябрь — '
    f'{fnum(100 * num(_mg["nov_to_sep_2025"]))}–{fnum(100 * num(_mg["nov_to_sep_2024"]))}% сентября, пик — август 2026 ({fnum(_g["2026-08"])}). '
    f'В 2025 году «забор под ключ» в Москве и МО вырос сильнее, чем в остальной России ({sgn(num(_mz["jan_sep_2025_vs_2024_pct"]))} против '
    f'{sgn(num(_mz["rest_jan_sep_2025_vs_2024_pct"]))} за январь–сентябрь). В 2026-м по трём заборным запросам Москва и МО — '
    f'{sgn(num(mks["установка забора"]["jan_sep_2026_vs_2025_pct"]))}…{sgn(num(mks["забор из профнастила"]["jan_sep_2026_vs_2025_pct"]))} к 2025-му '
    f'при {sgn(num(mks["забор из профнастила"]["rest_jan_sep_2026_vs_2025_pct"]))}…{sgn(num(_mz["rest_jan_sep_2026_vs_2025_pct"]))} в остальной России, '
    f'по воротам {sgn(num(_mg["jan_sep_2026_vs_2025_pct"]))} против {sgn(num(_mg["rest_jan_sep_2026_vs_2025_pct"]))}; доля Москвы и МО в России по '
    f'«забор под ключ» за 12 месяцев — {fnum(num(_mz["mo_share_of_rf_pct"]), 1)}% против {fnum(num(_mz["mo_share_of_rf_prev12_pct"]), 1)}% годом раньше. '
    'Причина не установлена, Keys.so даёт по тем же месяцам другой знак, вывод о сжатии рынка не делается; бренд-спрос Мастеровита за год не упал. '
    'Тест в ноябре–декабре идёт на спаде: по заборам запросов меньше сентябрьских, ворота проседают слабее.')
_b = {r['query']: r for r in bds}
_r = {r['query']: r for r in brr.values()}
_ratios = sorted(num(r['revenue_per_brand_query_rub']) for d, r in brr.items() if r['revenue_per_brand_query_rub'] and d not in ('masterovit.ru', 'zaborkin.ru'))
_rall = sorted(num(r['revenue_per_brand_query_rub']) for d, r in brr.items() if r['revenue_per_brand_query_rub'] and d != 'masterovit.ru')
_falling = [dname(r['domain']) for r in bds if bt_map.get(f'бренд «{r["query"]}» ({r["domain"]})', {}).get('direction', '').startswith('падение (устойчивый')]
_rising = [dname(r['domain']) for r in bds if bt_map.get(f'бренд «{r["query"]}» ({r["domain"]})', {}).get('direction', '').startswith('рост (устойчивый')]
_small = [num(r['avg_month_last12']) for r in bds if r['query'] not in ('мастеровит', 'завод заборов', 'заборово')]
OBS_BRAND = (
    f'Бренд-спрос Мастеровита — {fnum(num(_b["мастеровит"]["avg_month_last12"]))} в месяц, {fnum(num(_b["мастеровит"]["share_of_10_brands_pct"]), 1)}% '
    f'суммы 10 брендов, за год {sgn(num(_b["мастеровит"]["yoy_pct"]))}. Следом «завод заборов» — {fnum(num(_b["завод заборов"]["avg_month_last12"]))} '
    f'(частично общий запрос) и Заборово — {fnum(num(_b["заборово"]["avg_month_last12"]))}, {sgn(num(_b["заборово"]["yoy_pct"]))} за год. '
    f'У остальных семи — {fnum(min(_small))}–{fnum(max(_small))} в месяц. Устойчиво растёт: {", ".join(_rising)}; устойчиво падает: {", ".join(_falling)} (у ЗаводЗаборов и Доступных заборов запросы частично общие). '
    f'У Облзабора в 2025 году всплески до {fnum(num(_b["облзабор"]["peak_value"]))} запросов при медиане {fnum(statistics.median(ws_series("облзабор").values()))}; в расчётах они исключены. '
    f'Выручка на брендовый запрос у четырёх ООО — {fnum(_ratios[0])}–{fnum(_ratios[-1])} ₽, у Заборкина — '
    f'{fnum(num(_r["заборкин"]["revenue_per_brand_query_rub"]))} ₽ (65,9% визитов из органики, Similarweb). Оценка выручки ИП за 2025 год по всему '
    f'диапазону пяти ООО ({fnum(_rall[0])}–{fnum(_rall[-1])} ₽ на запрос): Радуга заборов {_r["радуга заборов"]["revenue_est_rub"].split(" (")[0]}, '
    f'ПрофЗаборы {_r["профзаборы"]["revenue_est_rub"].split(" (")[0]}, Облзабор {_r["облзабор"]["revenue_est_rub"].split(" (")[0]} — у этих двух 64–68% '
    f'платного трафика, оценка занижена; Доступные заборы {_r["доступные заборы"]["revenue_est_rub"].split(" (")[0]} — завышена частично общим запросом.')
_dz = [r for r in wsdist if r['query'] == 'забор под ключ' and not r['district'].startswith(('Москва', 'ИТОГО', 'Россия'))]
_dg = [r for r in wsdist if r['query'] == 'откатные ворота' and not r['district'].startswith(('Москва', 'ИТОГО', 'Россия'))]
_short = lambda r: r['district'].replace(' (городской округ)', '').replace(' городской округ', '').replace(' район', '')
_top_aff = sorted(_dz, key=lambda r: -num(r['affinity_pct']))[:5]
_tz, _tg = dist_total('забор под ключ', 'ИТОГО'), dist_total('откатные ворота', 'ИТОГО')
_rz, _rg = dist_total('забор под ключ', 'Россия'), dist_total('откатные ворота', 'Россия')
OBS_GEO = (
    f'За 20.09–20.10.2026 Москва и область дали {fnum(100 * num(_tz["frequency"]) / num(_rz["frequency"]), 1)}% запросов «забор под ключ» по России '
    f'и {fnum(100 * num(_tg["frequency"]) / num(_rg["frequency"]), 1)}% — «откатные ворота». Больше всего запросов о заборе — '
    + ', '.join(f'{_short(r)} ({fnum(num(r["frequency"]))})' for r in _dz[:4]) +
    '; самый высокий интерес — ' + ', '.join(f'{_short(r)} ({fnum(num(r["affinity_pct"]))}%)' for r in _top_aff) +
    '. О воротах чаще спрашивают ' + ', '.join(f'{_short(r)} ({fnum(num(r["frequency"]))})' for r in _dg[:4]) +
    f'. Это выгрузка за один месяц вне сезона, а Москва и крупные округа без отдельной строки дают '
    f'{fnum(num(dist_total("забор под ключ", "Москва")["share_of_msk_mo_pct"]), 1)}% и {fnum(num(dist_total("откатные ворота", "Москва")["share_of_msk_mo_pct"]), 1)}% '
    'запросов, поэтому приоритет округов по этим данным не устанавливается. Гипотеза для теста: сравнить цену заявки в округах с индексом '
    'интереса выше 250% и в остальной области.')

# SEO
geo_items = []
for d in sorted(MAIN, key=lambda d: -(num(seo[d]['geo_pages_main_domain']) or 0) - (num(seo[d]['city_subdomains']) or 0) * 2):
    s = seo[d]
    g, sd = num(s['geo_pages_main_domain']) or 0, num(s['city_subdomains']) or 0
    geo_items.append(dict(label=esc(dname(d)), sub=f'в топ-10 по {s["keys_organic_hits_of_9"] or 0} из 9 запросов · ИКС {s["yandex_iks"]}',
                          series=[(g, 's1', fnum(g), None), (sd, 's2', fnum(sd), None)]))
geo_chart = legend([('s1', 'гео-страниц на основном домене'), ('s2', 'поддоменов городов')]) + hbar(geo_items, aria='Гео-страницы и поддомены')
sub_tab = md_table([l for l in sec(S_SEO, 'Модель «поддомены').split('\n') if l.startswith('|')])
sub_html = table_html(sub_tab)
org_items = [dict(label=esc(dname(d)), sub=f'доля органики {traffic[d]["search_organic_pct"]}%',
                  series=[(num(traffic[d]['search_organic_visits']), 's3', fnum(num(traffic[d]['search_organic_visits'])), None)])
             for d in sorted(MAIN, key=lambda d: -(num(traffic[d]['search_organic_visits']) or 0))]
org_chart = hbar(org_items, aria='Органические визиты')

terms = md_html(sec(S_SEO, 'Что нужно «Дому гирлянд»'))

# площадки
plat = [r for r in serp if r['domain'] in ('avito.ru', 'uslugi.yandex.ru', 'profi.ru')]
plat_items = [dict(label=esc({'avito.ru': 'Авито', 'uslugi.yandex.ru': 'Яндекс Услуги', 'profi.ru': 'Профи.ру'}[r['domain']]),
                   sub=f'лучшая позиция в органике — {r["best_org_pos"]}',
                   series=[(num(r['organic_hits']), 's1', f'{r["organic_hits"]} из 9 в органике', None),
                           (num(r['ads_hits']), 's2', f'{r["ads_hits"]} из 9 в рекламе', None)]) for r in plat]
plat_chart = legend([('s1', 'запросов, где площадка в топ-10 органики'), ('s2', 'запросов, где площадка в рекламе')]) + hbar(plat_items, vmax=9, aria='Площадки в выдаче')

# соцсети
vk_main = [r for r in vk if r['domain'] in MAIN or r['group'].startswith('облег') and r['subscribers']]
vk_tab = '<div class="tscroll"><table class="tbl"><thead><tr><th>Сайт</th><th>Список</th><th>Подписчиков</th><th>Постов за 13 недель</th>' \
         '<th>Постов в неделю</th><th>Лайков на пост</th><th>Рекламных постов</th><th>Последний пост</th></tr></thead><tbody>' + ''.join(
    f'<tr><th scope="row">{esc(dname(r["domain"]))}<small>{r["domain"]}</small></th><td>{esc(r["group"])}</td>'
    f'<td class="n">{esc(r["subscribers"] or "сообщества нет")}</td><td class="n">{esc(r["posts_3m"] or "—")}</td>'
    f'<td class="n">{esc(r["posts_per_week"] or "—")}</td><td class="n">{esc(r["avg_likes"] or "—")}</td>'
    f'<td class="n">{esc(r["posts_marked_ad_3m"] or "—")}</td><td>{esc(r["last_post"] or "—")}</td></tr>' for r in vk_main) + '</tbody></table></div>'
avito = md_html(sec(S_DEM, 'Гипотеза авитолога'))
tg = md_html('\n'.join(l for l in sec(S_DEM, 'Наблюдения').split('\n') if l.startswith('9.') or l.startswith('10.')))

TAB5 = (
    block('Каналы трафика', tr_heat,
          'Доля визитов по каналам, июль–сентябрь 2026, Similarweb, весь мир, оценка. Под названием — визиты за 3 месяца. '
          'У четырёх сайтов с пометкой «модель» структура каналов почти одинаковая — вероятно, шаблон модели Similarweb; '
          'выводы о них не делаются.') +
    obs('Работают три разные модели: бренд и прямые заходы (Мастеровит — 63,9% прямых), платные каналы (Облзабор 67,9%, '
        'ПрофЗаборы 64,1%), органика (Заборкин — 65,9%). Соцсети дают каждому сайту от 0,3 до 5,4% визитов; Авито, Профи.ру '
        'и Яндекс Услуги среди видимых источников переходов не встречаются.') +
    block('Посещаемость по месяцам', mon_chart, 'Similarweb, весь мир, оценка.') +
    obs('У сайтов с долей платных каналов 64–68% посещаемость колеблется в 2,3–2,5 раза за квартал, у органического Заборкина — '
        'в 1,6 раза. В сентябре падение есть у всех: часть колебаний даёт сезон.') +
    block('Спрос и сезонность: «забор под ключ», Москва и МО', season_chart) +
    obs(OBS_SEASON) +
    block('Бренд-спрос и география спроса', brand_block) +
    obs(OBS_BRAND) +
    obs(OBS_GEO) +
    block('Что ищут вместе с запросом: «Топы запросов» Вордстата', tops_block) +
    obs(OBS_TOPS) +
    block('SEO: гео-страницы и поддомены городов', geo_chart + '<h4>Модель «поддомены городов»</h4>' + sub_html +
          '<h4>Органические визиты за 3 месяца</h4>' + org_chart,
          'Гео-страница — посадочная под город или район («заборы в Одинцово»). Поддомен города — отдельный адрес вида '
          'odincovo.oblzabor.ru. ИКС — индекс качества сайта Яндекса. Органика — переходы из нерекламной выдачи.') +
    obs('Число гео-страниц само по себе видимость не объясняет: у ЗаводЗаборов 102 гео-страницы и ни одного запроса из 9 в топ-10, '
        'у Доступных заборов 413 страниц и 167 поддоменов при лучшей позиции 8. Заборкин держит 8 из 9 запросов за счёт '
        '206 статей, гео-слоя и разметки; рядом в топ-10 стоят малые сайты на 27–103 страницы с запросом в заголовке.') +
    block('Что нужно, чтобы получить органику, и за какой срок', terms) +
    obs('Органика не заменит рекламный запуск: это канал на 6–18 месяцев. Вклад, который нельзя купить, — страницы '
        'выполненных объектов и гео-страницы с реальными фото.') +
    block('Выдача Яндекса по Москве и МО: кто в топ-10 органики', smo_html) +
    obs(OBS_SMO) +
    block('Similarweb, сентябрь 2026: 29 доменов из 31 и похожие сайты', sw_html) +
    obs(OBS_SW) +
    block('Площадки в выдаче', plat_chart,
          'По 9 запросам в топ-10 Яндекса (Москва) площадки занимают 7 из 89 мест. Авито в этот прогон не входит — отдельная задача.') +
    obs('Яндекс Услуги и Авито стоят в органике по «установка забора» и «забор из профнастила под ключ»: профиль на Яндекс '
        'Услугах и карточка в Яндекс Бизнесе дают присутствие в выдаче без возраста домена.') +
    block('Соцсети и MAX', vk_tab + tg,
          'Сообщества ВКонтакте 10 компаний полного разбора и облегчённого списка, где сообщество найдено; окно 20.07–20.10.2026.') +
    obs('Регулярно во ВК пишут 5 из 10 компаний; вовлечённость заметна только у Заборово (25,3 лайка и 21,6 репоста на пост). '
        'Подписчиков у Московских заборов (11,9 тыс.) больше, чем у Мастеровита (10,4 тыс.); у КупитьЗабор (8,7 тыс.) и '
        'Про-Забора (5,9 тыс.) — больше, чем у остальных девяти компаний полного разбора.') +
    block('Проверка гипотезы авитолога: «в стройке работают ВК-таргет и Макс»', avito) +
    obs('Снаружи гипотеза подтверждается частично: промопосты ВК видны у 1 из 10 компаний, посев — у 1, MAX стоит на сайтах 7 '
        'из 10 как способ написать. Таргет без поста снаружи не виден — его проверяет собственный тест H4.')
)

# ================================================================ TAB Авито
S_AV = md_sections(N / 'avito_spravka.md')
av_obs = sec(S_AV, 'Наблюдения')
av_tables = md_tables(av_obs)

# компании и частные по запросам
mix_items = []
for q, reg in (('забор под ключ', 'Москва'), ('откатные ворота', 'Москва'), ('установка забора', 'МО')):
    rs = [r for r in av_list if r['query'] == q]
    top = [r for r in rs if (num(r['position_in_export']) or 999) <= 20]
    for lab, sub in ((rs, f'все {len(rs)} объявлений'), (top, 'первые 20 строк выдачи')):
        c = sum(1 for r in lab if r['seller_type'] == 'компания')
        p_ = sum(1 for r in lab if r['seller_type'] == 'частный мастер')
        o = len(lab) - c - p_
        mix_items.append(dict(label=f'«{esc(q)}», {reg}', sub=esc(sub) + (f' · не отдано {o}' if o else ''),
                              series=[(c, 's1', f'компании {c}', None), (p_, 's2', f'частные {p_}', None)]))
mix_chart = legend([('s1', 'объявления компаний'), ('s2', 'объявления частных мастеров')]) + hbar(mix_items, aria='Компании и частные на Авито')

sellers_html = table_html(av_tables[0], names=True) if av_tables else ''
price_html = table_html(av_tables[1], names=True) if len(av_tables) > 1 else ''
vs_rows = ''.join(
    f'<tr><th scope="row">{esc(r["company"])}<small>{esc(r["domain"])}</small></th><td>{esc(r["product"])}</td>'
    f'<td class="n">{esc(r["avito_n_listings"])}</td><td class="n">{fnum(num(r["avito_price_min_rub"]))}–{fnum(num(r["avito_price_max_rub"]))} ₽</td>'
    f'<td class="n">{fnum(num(r["avito_price_median_rub"]))} ₽</td><td class="n">{fnum(num(r["site_price_from_rub"]))} ₽</td>'
    f'<td class="n">{("+" if (num(r["avito_min_vs_site_pct"]) or 0) > 0 else "") + esc(r["avito_min_vs_site_pct"])}%</td></tr>'
    for r in av_vs if r['comparable'] == 'да')
vs_tab = ('<div class="tscroll"><table class="tbl"><thead><tr><th>Компания</th><th>Продукт</th><th>Объявлений</th><th>Авито, мин–макс</th>'
          '<th>Авито, медиана</th><th>Сайт, «от»</th><th>Минимум Авито к сайту</th></tr></thead><tbody>' + vs_rows +
          '</tbody></table></div><p class="note">Только пары «продукт — единица», сопоставимые с ценой сайта (за п.м.). Сайты — съём 20.10.2026.</p>')

CLAIMS = [('гарантия', 'гарантия'), ('договор_смета', 'договор или смета'), ('ворота_автоматика', 'ворота или автоматика'),
          ('бригады_опыт', 'бригады или опыт'), ('своё_производство', 'своё производство, «без посредников»'),
          ('замер_бесплатный', 'бесплатный замер или выезд'), ('скидки_подарки', 'скидки и подарки'),
          ('сроки_монтажа', 'срок монтажа с числом дней'), ('толщина_металла', 'толщина металла'),
          ('оплата_после_монтажа', 'оплата после монтажа, «без предоплаты»'), ('рассрочка', 'рассрочка'),
          ('цена_за_пм', 'цена за п.м. в тексте'), ('предоплата', 'предоплата'), ('замер_платный', 'платный замер')]


def share_of(row, k):
    m = re.search(r'\((\d+)%\)', row.get(k, '') or '')
    return int(m.group(1)) if m else None


sh_all = next((r for r in av_claims if r['group'] == 'все'), {})
sh_c = next((r for r in av_claims if r['scope'] == 'тип продавца' and r['group'] == 'компания'), {})
sh_p = next((r for r in av_claims if r['scope'] == 'тип продавца' and r['group'] == 'частный мастер'), {})
cl_items = [dict(label=esc(t), sub=f'все объявления: {esc(sh_all.get(k, ""))}',
                 series=[(share_of(sh_c, k), 's1', f'{share_of(sh_c, k)}%', None), (share_of(sh_p, k), 's2', f'{share_of(sh_p, k)}%', None)])
            for k, t in CLAIMS]
cl_chart = legend([('s1', f'компании, n={sh_c.get("base_n", "")}'), ('s2', f'частные мастера, n={sh_p.get("base_n", "")}')]) + \
    hbar(cl_items, vmax=100, aria='Что обещают на Авито')

# отзывы
neg_rv = [r for r in av_rev if num(r['score']) is not None and num(r['score']) <= 3]
pos_rv = [r for r in av_rev if num(r['score']) is not None and num(r['score']) >= 4]
tn, tp = Counter(), Counter()
for r in neg_rv:
    for t in filter(None, [x.strip() for x in (r['themes_negative'] or '').split(';')]):
        tn[t] += 1
for r in pos_rv:
    for t in filter(None, [x.strip() for x in (r['themes_positive'] or '').split(';')]):
        tp[t] += 1
THEME_RU = {'качество_позитив': 'качество', 'скорость': 'скорость монтажа', 'консультация': 'консультация', 'цена_позитив': 'цена',
            'бригада': 'бригада', 'чистота': 'чистота', 'договор_документы': 'договор и документы', 'смета_замер': 'смета и замер',
            'гарантия': 'гарантия', 'связь_менеджер': 'связь', 'качество_монтажа': 'качество монтажа', 'предоплата_деньги': 'предоплата и деньги',
            'материал': 'материал', 'сроки': 'сроки'}
neg_items = [dict(label=esc(THEME_RU.get(t, t.replace('_', ' '))), series=[(n, 's2', f'{n} из {len(neg_rv)}', None)]) for t, n in tn.most_common(8)]
pos_items = [dict(label=esc(THEME_RU.get(t, t.replace('_', ' '))), series=[(n, 's3', f'{n} из {len(pos_rv)} ({fnum(n / len(pos_rv) * 100, 0)}%)', None)])
             for t, n in tp.most_common(7)] if pos_rv else []
reply = sum(1 for r in av_rev if r['has_seller_reply'] == 'да')
rev_html = (f'<p>Отзывов {len(av_rev)} у {len({r["company"] for r in av_rev})} компаний; с оценкой {len(neg_rv) + len(pos_rv)}, из них 1–3★ — '
            f'{len(neg_rv)} ({fnum(len(neg_rv) / max(1, len(neg_rv) + len(pos_rv)) * 100, 1)}%); ответ продавца — у {reply} из {len(av_rev)}.</p>'
            '<div class="grid2"><div><h4>Темы негатива (1–3★)</h4>' + hbar(neg_items, aria='Темы негатива Авито') +
            '<p class="note">База мала: доли по темам ориентировочные.</p></div><div><h4>Темы позитива (4–5★)</h4>' +
            hbar(pos_items, aria='Темы позитива Авито') + '</div></div>')
avitolog = md_html(sec(S_AV, 'Гипотеза авитолога'), names=True)
av_limits = md_html(sec(S_AV, 'Что не удалось'), names=True)


# Авито: 4-й запрос и профили трёх компаний (21.10, вечер)
_q20 = next(r for r in q4s if r['scope'] == 'первые 20'); _q100 = next(r for r in q4s if r['scope'] == 'все 100')
_q4cs = {r['group']: r for r in csv.DictReader(open(N / 'raw_avito' / 'q4_out' / 'avito_claims_shares.csv', encoding='utf-8')) if r['scope'].startswith('все') or r['scope'] == 'тип продавца'}
_m3row = next(r for r in csv.DictReader(open(D / 'avito_claims_shares.csv', encoding='utf-8')) if r['scope'].startswith('все'))
_m3 = lambda k: _m3row[k].split(' (')[1].rstrip(')')
_cl = lambda g, k: _q4cs[g][k].split(' (')[1].rstrip(')') if g in _q4cs and k in _q4cs[g] else '—'
q4_sel_rows = ''.join(f'<tr><th scope="row">{esc(r["seller"])}<small>{esc(r["competitor_domain"] or r["seller_type"])}</small></th><td class="n">{esc(r["listings_in_top100"])}</td>'
                      f'<td class="n">{esc(r["best_position"])}</td><td class="n">{esc(r["active_listings"])}</td><td class="n">{esc(r["rating"])} · {esc(r["reviews"])}</td></tr>' for r in q4sel[:12])
q4_html = (f'<div class="tiles">' + ''.join(f'<div class="tile"><div class="tile-v">{v}</div><div class="tile-l">{esc(l)}</div></div>' for v, l in (
    (f'{_q20["companies"]} из 20', 'первых объявлений — компании'), (f'{_q100["companies"]} из 100', 'компании во всей выдаче'),
    (f'{fnum(num(_q100["profnastil_pm_median"]))} ₽', f'медиана профнастила за п.м. (n={_q100["profnastil_pm_n"]}; половина цен — {_q100["profnastil_pm_q1_q3"]} ₽)'),
    (fnum(num(_q100['median_views_total'])), 'медиана просмотров объявления'))) + '</div>' +
    '<div class="tscroll"><table class="tbl small"><thead><tr><th>Продавец</th><th>Объявлений в первых 100</th><th>Лучшая позиция</th>'
    '<th>Активных в профиле</th><th>Рейтинг · отзывов</th></tr></thead><tbody>' + q4_sel_rows + '</tbody></table></div>')
OBS_Q4 = (f'По «забор из профнастила под ключ» в первых 20 объявлениях компаний и частных мастеров поровну ({_q20["companies"]} и {_q20["private"]}), '
          f'во всех 100 частных больше ({_q100["private"]}); объявления принадлежат {len({r["seller_key"] for r in csv.DictReader(open(N / "raw_avito" / "q4_out" / "avito_listings.csv", encoding="utf-8"))})} продавцам. '
          f'Из компаний брифа в выдаче (по названию, оценка) Мастеровит, Облзабор, ПрофЗаборы и Заборы Престиж; '
          f'больше всего объявлений — у трёх частных мастеров и двух небольших компаний (7–8 из 100). Медиана цены профнастила — '
          f'{fnum(num(_q100["profnastil_pm_median"]))} ₽ за п.м. (n={_q100["profnastil_pm_n"]}), в первых 20 — {fnum(num(_q20["profnastil_pm_median"]))} ₽ (n={_q20["profnastil_pm_n"]}); '
          'в трёх основных запросах — 700 ₽: другой запрос и регион. '
          f'Обещания: гарантия — {_cl("все", "гарантия")} (в трёх основных запросах — {_m3("гарантия")}), бесплатный замер — {_cl("все", "замер_бесплатный")} '
          f'({_m3("замер_бесплатный")}), своё производство — {_cl("все", "своё_производство")} ({_m3("своё_производство")}), оплата после монтажа — '
          f'{_cl("все", "оплата_после_монтажа")} ({_m3("оплата_после_монтажа")}).')
pw3_rows = ''.join(f'<tr><th scope="row">{esc(r["company"])}<small>{esc(r["domain"])}</small></th><td class="n">{esc(r["active"])}</td><td class="n">{fnum(num(r["closed"]))}</td>'
                   f'<td class="n">{esc(r["rating"])}</td><td class="n">{esc(r["reviews"])}</td><td>{esc(r["distribution"])}</td><td class="n">{esc(r["seller_replies"])} из {esc(r["reviews_loaded"])}</td>'
                   f'<td>{esc(r["since"])}</td><td>{esc(r["reply"])}</td></tr>' for r in pw3)
pw3_html = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Компания</th><th>Активных объявлений</th><th>Закрытых</th><th>Рейтинг</th>'
            '<th>Отзывов с оценкой</th><th>Оценки 1/2/3/4/5</th><th>Ответ продавца</th><th>На Авито с</th><th>Отвечает</th></tr></thead><tbody>' + pw3_rows + '</tbody></table></div>')
OBS_PW3 = ('У Заборкина 24 089 закрытых объявлений при 317 активных и 10 оценках, у Заборово — 2 051 закрытое и 4 оценки: объявлений много, отзывов на Авито почти нет. '
           'ПрофЗаборы на Авито с 2022 года: 61 оценка, средняя 4,8, четыре оценки 1–2★; продавец отвечает на 64 из 75 отзывов. '
           'Три из четырёх негативных отзывов ПрофЗаборов — об ошибках замера (не учтён уровень дороги, не досчитана планка, неверное задание монтажникам), '
           'два — о качестве работы бригады. Гипотеза для оффера: контроль замера (фото и подпись клиента под схемой) как отдельное обещание.')

TAB_AV = (
    block('Кто в выдаче: компании и частные мастера', mix_chart,
          'Авито, раздел «Предложение услуг», 21.10.2026: «забор под ключ» и «откатные ворота» — Москва, «установка забора» — '
          'Московская область, по 100 объявлений с описанием. Порядок строк выгрузки принят как порядок выдачи (оценка). '
          'Имена частных мастеров не сохранялись.') +
    obs('В Москве верх выдачи занимают компании (17 из первых 20 по «забор под ключ»), в МО — частные мастера (17 из 20 по '
        '«установка забора»). По 249 уникальным объявлениям частных 55%, компаний 44%. Сравнение — по одному съёму на запрос.') +
    block('У кого больше всего объявлений', sellers_html,
          'Активные и закрытые объявления — из профиля продавца; «в выдаче» — уникальные объявления в трёх запросах. '
          'Связь с компаниями брифа по названию помечена «оценка».') +
    obs('Самый крупный аккаунт из списка — Мастеровит: 655 активных и 1 071 закрытое объявление, 15 объявлений в трёх выдачах, '
        'но медиана просмотров на объявление — 105. Медиана 2 000–3 600 — у продавцов с 3–4 объявлениями в трёх выдачах (ДИАС, '
        'МОСКВАЗАБОР24, «ЗАБОР / НАВЕС ЗА 2 ДНЯ», «Заборы Ворота Навесы»), хотя в профиле у них 106–400 активных объявлений; '
        'у Облзабора с 2 объявлениями в выдаче — 286: связь просмотров с числом карточек слабая (n=15 продавцов, оценка). Из 10 компаний полного разбора в выдаче найдены 5, у трёх — по совпадению названия; Облзабор завёл аккаунт в апреле 2026.') +
    block('Цены: Авито и сайты', price_html + '<h4>Те же компании на Авито и на сайте</h4>' + vs_tab,
          'Единица цены указана у 16 из 249 объявлений; остальное — оценка единицы: заборы до 10 000 ₽ — за п.м., ворота от '
          '15 000 ₽ — за комплект. Цены 1 ₽ (4 объявления) из медиан исключены.') +
    obs('Медиана профнастила на Авито — 700 ₽ за п.м. (n=33), на 59% ниже медианы цены «от» на сайтах (1 690 ₽): карточка '
        'Авито чаще показывает нижнюю границу без состава. У Мастеровита цены Авито и сайта совпадают, у Облзабора Авито '
        'дешевле на 46% по минимуму, у Заборкина дороже (n=1).') +
    block('Что обещают в объявлениях', cl_chart,
          'Разметка по заголовку и полному описанию 249 уникальных объявлений, доля объявлений с обещанием.') +
    obs('Набор обещаний у компаний и частных мастеров почти одинаков: гарантия (82% и 85%), договор, бесплатный замер. '
        'Различают толщина металла (34% против 12%), рассрочка (15% против 4%) и цена за метр в тексте (12% против 2%). '
        'Цену с единицей и составом в тексте пишут 6% объявлений — это место свободно.') +
    block('Отзывы на Авито', rev_html,
          'До 75 последних отзывов на профиль у 11 компаний; темы размечены тем же кодбуком, что отзывы с карт.') +
    obs('Отзывы на Авито мягче, чем на картах: у Мастеровита 1–3★ на Авито — 7% по всем 157 оценкам профиля (11) и 9% среди 75 '
        'последних отзывов (7) против 27,2% в текстах всех площадок. Среди редких жалоб первые темы — договор и смета после замера, как и на картах.') +
    block('Гипотеза авитолога «ворота через Авито — 400–700 ₽ за заявку»', avitolog) +
    obs('Цена заявки снаружи не измеряется: продвижение, контакты и продажи видны только в кабинете продавца. Гипотезу '
        'проверяет тест H8 с метриками «расход», «контакты», «целевые заявки», «замеры».') +
    block('Ограничения съёма', av_limits) +
    block('Запрос «забор из профнастила под ключ», Москва и МО: 100 объявлений', q4_html,
          'Авито, регион «Москва и Московская область», 21.10.2026; выгрузка Apify. Частные мастера обезличены. Обещания — тот же список, что выше.') +
    obs(OBS_Q4) +
    block('Профили Заборкина, Заборово и ПрофЗаборов', pw3_html, 'Авито, профили продавцов, 21.10.2026; выгрузка Apify. Связь профиля с сайтом — по названию, оценка. Имена в отзывах скрыты.') +
    obs(OBS_PW3)
)

# ================================================================ TAB 6 — Сайты и офферы
fs_cards = []
for o, t, L, tmb, lm in FS:
    d = o['domain']
    mob = f'<a class="zoom mob" href="img/{lm}" target="_blank" rel="noopener"><img src="img/{tmb}" alt="{esc(d)}, телефон" loading="lazy"></a>' if tmb else ''
    sp = speed.get(d, {})
    fs_cards.append(
        f'<article class="fs"><div class="fs-imgs"><a class="zoom" href="img/{L}" target="_blank" rel="noopener">'
        f'<img src="img/{t}" alt="{esc(d)}, первый экран на компьютере" loading="lazy"></a>{mob}</div>'
        f'<div class="fs-txt"><h4>{dlink(d)}</h4><p class="h1q">«{esc(short(o["h1_first_screen"], 140))}»</p>'
        f'<dl><dt>Предоплата</dt><dd>{esc(short(o["prepayment"], 150))}</dd><dt>Следующий шаг</dt><dd>{esc(short(o["next_step"], 150))}</dd>'
        f'<dt>Ответ на заявку</dt><dd>{esc(short(o["response_time"], 100))}</dd>'
        f'<dt>Lighthouse, телефон</dt><dd>{esc(sp.get("lighthouse_mobile_score", "—"))}/100</dd></dl></div></article>')
fs_html = '<div class="fsgrid">' + ''.join(fs_cards) + '</div>'

off_rows = ''.join(
    f'<tr><th scope="row">{esc(o["domain"])}</th><td>{esc(short(o["usp"], 220))}</td><td>{esc(short(o["promos"], 220))}</td>'
    f'<td>{esc(short(o["lead_magnets"], 180))}</td><td>{esc(short(o["guarantees"], 140))}</td></tr>' for o in offers)
off_table = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Сайт</th><th>Обещание (УТП)</th><th>Акции</th>'
             '<th>Лид-магниты</th><th>Гарантия</th></tr></thead><tbody>' + off_rows + '</tbody></table></div>')

# цены профнастил
pn = {}
for p in prices:
    if p['product'] == 'профнастил' and p['comparable_in_per_unit_compare'] == 'да' and p['domain'] not in pn:
        pn[p['domain']] = p
pn_vals = [num(pn[d]['price_from_rub']) for d in MAIN if d in pn]
pn_med = statistics.median(pn_vals)
pn_items = []
for d in sorted(MAIN, key=lambda d: num(pn[d]['price_from_rub']) if d in pn else 1e9):
    p = pn.get(d)
    sec_note = ''
    if d in SECOND and SECOND[d] in pn:
        sec_note = f' · второй сайт {SECOND[d]}: {fnum(num(pn[SECOND[d]]["price_from_rub"]))} ₽'
    pn_items.append(dict(label=esc(dname(d)), sub=esc((short(p['includes'], 70) if p else '') + sec_note),
                         tip=f'{d}: {p["includes"]} {p["note"]}' if p else d,
                         series=[(num(p['price_from_rub']) if p else None, 's1', fnum(num(p['price_from_rub'])) + ' ₽' if p else '', 'цена не опубликована')]))
pn_chart = hbar(pn_items, refs=[(pn_med, f'медиана {fnum(pn_med)} ₽')], aria='Цена профнастила за погонный метр')

# ворота 4 м сопоставимые (10 компаний)
gmap = {g['domain']: g for g in gates}
med_mech = statistics.median([num(g['mech_4m_for_median_rub']) for g in gates if num(g['mech_4m_for_median_rub'])])
med_auto = statistics.median([num(g['auto_4m_for_median_rub']) for g in gates if num(g['auto_4m_for_median_rub'])])
n_mech = len([g for g in gates if num(g['mech_4m_for_median_rub'])])
n_auto = len([g for g in gates if num(g['auto_4m_for_median_rub'])])


def gate_items(domains):
    out = []
    for d in domains:
        g = gmap.get(d)
        if not g:
            continue
        m_, a_ = num(g['mech_4m_for_median_rub']), num(g['auto_4m_for_median_rub'])
        fr = []
        if num(g['price_from_mech_rub']):
            fr.append(f'«от» {fnum(num(g["price_from_mech_rub"]))} ₽')
        if num(g['price_from_auto_rub']):
            fr.append(f'с автоматикой «от» {fnum(num(g["price_from_auto_rub"]))} ₽')
        note = g['comparable_note'] or ''
        pm, pa = num(g['price_mech_4m_rub']), num(g['price_auto_4m_rub'])
        miss_m = (f'4 м — {fnum(pm)} ₽, состав несопоставим' if pm and not m_ else
                  'нет цены 4 м' + (f' ({"; ".join(fr)})' if fr else ''))
        miss_a = (f'4 м с автоматикой — {fnum(pa)} ₽, состав несопоставим' if pa and not a_ else 'нет цены 4 м с автоматикой')
        out.append(dict(label=esc(dname(d)), sub=esc(d + (' · ' + note if note else '')),
                        tip=f'{d}: {"; ".join(fr) or "цен «от» нет"}. Состав: {g["infill_included"]}, {g["foundation"]}, высота {g["height_m"]}, привод {g["drive"]}',
                        series=[(m_, 's1', fnum(m_) + ' ₽' if m_ else '', miss_m), (a_, 's2', fnum(a_) + ' ₽' if a_ else '', miss_a)]))
    return out


gate_main_chart = legend([('s1', 'механические, 4 м с монтажом'), ('s2', 'с автоматикой, 4 м с монтажом')]) + hbar(
    gate_items(MAIN), vmax=150000, refs=[(med_mech, f'медиана мех. {fnum(med_mech)} ₽'), (med_auto, f'медиана авт. {fnum(med_auto)} ₽')],
    aria='Цены откатных ворот 4 м')

# идеальная страница
ideal_tab = md_table([l for l in sec(S_SITES, 'Идеальная страница').split('\n') if l.startswith('|')])
ideal_cards = []
for r in ideal_tab[1:]:
    n_ = int(r[0])
    im = BL.get(n_)
    img_html = shot(im[0], im[1], f'Блок {n_}: {r[1]}') if im else '<div class="noimg">Пример блока — текстом, без снимка</div>'
    ideal_cards.append(f'<article class="ideal"><div class="ideal-n">{n_}</div><div class="ideal-t"><h4>{inline(r[1])}</h4>'
                       f'<p>{inline(r[2])}</p><p class="src">Взято у: {inline(r[3])}</p></div>{img_html}</article>')
ideal_html = '<div class="ideals">' + ''.join(ideal_cards) + '</div>'
ideal_src_n = len({x for r in ideal_tab[1:] for x in re.findall(r'[a-z0-9.-]+\.(?:ru|site)', r[3])})
ideal_rest = sec(S_SITES, 'Идеальная страница')
all_do = md_html(ideal_rest.split('### Что делают все')[1].split('###')[0]) if '### Что делают все' in ideal_rest else ''
none_do = md_html(ideal_rest.split('### Чего нет ни у кого')[1]) if '### Чего нет ни у кого' in ideal_rest else ''

lh_items = []
for o in sorted(offers, key=lambda o: -(num(speed.get(o['domain'], {}).get('lighthouse_mobile_score')) or 0)):
    sp = speed.get(o['domain'], {})
    lh_items.append(dict(label=esc(o['domain']), sub=f'LCP на телефоне {esc(sp.get("lighthouse_mobile_lcp_s", "—"))} с' + (' · горизонтальная прокрутка' if sp.get('mobile_horizontal_scroll') == 'да' else ''),
                         series=[(num(sp.get('lighthouse_mobile_score')), 's1', f'{sp.get("lighthouse_mobile_score")}', None),
                                 (num(sp.get('lighthouse_desktop_score')), 's3', f'{sp.get("lighthouse_desktop_score")}', None)]))
lh_chart = legend([('s1', 'телефон'), ('s3', 'компьютер')]) + hbar(lh_items, vmax=100, aria='Баллы Lighthouse')

rec_rows = ''.join(
    f'<tr><th scope="row">{tx(r["company"])}</th><td>{tx(r["item"])}</td><td class="n">{fnum(num(r["strategy_rub"]))} ₽</td>'
    f'<td class="n">{(fnum(num(r["site_rub"])) + " ₽") if num(r["site_rub"]) else tx(r["site_rub"])}</td>'
    f'<td class="n">{tx(r["diff_site_vs_strategy"])}</td><td>{tx(r["value_taken"])}</td><td>{tx(clean(r["why"]))}</td></tr>'
    for r in precon)
recon_tab = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Компания</th><th>Позиция</th><th>Стратегия заказчика, 19.10</th>'
             '<th>Сайт, 20–21.10</th><th>Разница сайта к стратегии</th><th>Что взято</th><th>Почему</th></tr></thead><tbody>' +
             rec_rows + '</tbody></table></div>')

TAB6 = (
    block('Первые экраны', fs_html,
          '13 посадочных: снимок компьютера (1440 px) и телефона (390 px) через 3 секунды после загрузки, 20.10.2026. '
          'Нажмите на снимок, чтобы открыть крупно. Регион просмотра — без привязки к Москве.') +
    obs('Условие без риска на первом экране — у Доступных заборов («без предоплаты и бесплатным замером» в H1) и Радуги '
        '(«оплата после монтажа»). У Заборово слайдер первого экрана пустой, у ЗаводЗаборов заголовок ниже 1 800 px, '
        'у Мастеровита в заголовке «до 5 лет» гарантии при 24 месяцах в карточках.') +
    block('Доверие: сертификаты, дилерство, рейтинги, заказчики-организации', trust_html) +
    obs(OBS_TRUST) +
    block('Офферы и акции', off_table, 'Обещание, акции, лид-магниты (что дают за контакт) и гарантия по 13 посадочным.') +
    obs('Подарки-доработки вместо скидок (забутовка, покраска, фурнитура) — у 8 из 10 компаний. Акции с прошедшей датой '
        'висят у 5 сайтов на 20.10.2026. Смету в мессенджер присылают 2 сайта, итог калькулятора без контакта показывают 3.') +
    block('Цены: профнастил с монтажом за погонный метр', pn_chart,
          'Цена «от» на главном сайте, первая строка «профнастил» с монтажом. Сравнение условное: у части компаний это лист '
          '0,3–0,35 мм высотой 1,5 м.') +
    obs(f'Разброс — от 850 до 2 150 ₽, медиана {fnum(pn_med)} ₽ (n={len(pn_vals)}). Вторые сайты компаний дешевле основных: '
        'zabor-dlya-vseh.site — 1 376 ₽ против 1 854 ₽. У 6 из 10 компаний цены внутри сайта расходятся между собой.') +
    block('Сверка цен стратегии заказчика с сайтами', recon_tab,
          'Цены конкурентов из стратегии «Дома гирлянд» от 19.10.2026 против сайтов 20–21.10.2026. В расчётах отчёта взяты '
          'цены сайтов: у них известны дата, высота и состав.') +
    obs('Расхождения — от −61% до +23%: у компаний по нескольку цен «от» на разных площадках (у ЗаводЗаборов — 742, 1 376, '
        '1 854 и 2 157 ₽). Сравнивать цены можно только с указанием высоты, листа и состава; без этого цифры стратегии и '
        'сайтов описывают разные комплекты.') +
    block('Цены: откатные ворота 4 м, сопоставимый состав', gate_main_chart,
          f'В медианы вошли только комплекты с проёмом 4 м, полотном с наполнением, высотой 1,9–2,0 м и монтажом, без калитки; '
          f'механические n={n_mech}, с автоматикой n={n_auto} (вместе с облегчённым списком и специалистами). Все цены — '
          'на вкладке «Откатные ворота».') +
    obs('Цену 4 м механических и с автоматикой рядом публикуют 3 из 10 компаний: ПрофЗаборы, ЗаводЗаборов, '
        'Заборово (у последнего автоматические — без наполнения). Остальные дают цену «от» без размера или шаблон.') +
    block('Скорость: баллы Lighthouse', lh_chart,
          'Lighthouse 12, облачный сервер вне РФ: абсолютные значения хуже, чем у посетителя из Москвы; годятся для сравнения.') +
    obs('По облачному Lighthouse у 11 из 13 страниц балл на телефоне ниже 50. Быстрее всех Радуга (56) и Доступные заборы (53) — у них же сильный '
        'первый экран. Доля мобильных визитов у prof-zabory.ru — 94%, у zavodzaborov.ru — 81%. Оценки критерия «посадочная страница» и сводки компаний '
        'опираются на этот замер 20.10.') +
    block('Скорость: Google PageSpeed Insights, телефон и компьютер', psi_html) +
    obs(OBS_PSI) +
    block('Идеальная страница: структура из лучших блоков рынка', ideal_html,
          'Нумерация блоков используется в карточках гипотез. Снимок — пример блока у того, у кого он взят.') +
    obs(f'15 блоков взяты у {ideal_src_n} разных сайтов: лучшие решения рынка рассыпаны по компаниям. Блоки 1, 5 и 12 '
        'закрывают главные страхи клиента: цену без риска, итог без звонка и гарантию после монтажа.') +
    block('Что делают все и чего нет ни у кого', '<div class="grid2"><div><h4>Что делают все</h4>' + all_do +
          '</div><div><h4>Чего нет ни у кого из 13 страниц</h4>' + none_do + '</div></div>') +
    obs('Обязательный минимум повторяют все, поэтому он не отличает. Отличие лежит в пустых местах: пакет с итоговой суммой, '
        'неустойка в рублях, дата ближайшего монтажа, рейтинг карт на первом экране.')
)

# ================================================================ TAB Прозвон
stages = []
for r in mshop:
    if r['funnel_stage'] not in stages:
        stages.append(r['funnel_stage'])
KEY_METRIC = {}
for st in stages:
    rs = [r for r in mshop if r['funnel_stage'] == st]
    KEY_METRIC[st] = ' · '.join(dict.fromkeys(r['value'] for r in rs if r['value']))
funnel = '<ol class="funnel">' + ''.join(
    f'<li><span class="fn-n">{esc(st.split(".")[0])}</span><span class="fn-t">{esc(st.split(". ", 1)[-1])}</span>'
    f'<span class="fn-v">{esc(short(KEY_METRIC[st], 70))}</span></li>' for st in stages) + '</ol>'
stage_cards = []
for st in stages:
    rs = [r for r in mshop if r['funnel_stage'] == st]
    lis = ''.join(
        f'<li><p><strong>{tx(r["company"])}</strong>: {tx(r["observation"])}</p>'
        + (f'<p class="impl">Для оффера: {tx(r["implication_for_offer"])}</p>' if r['implication_for_offer'] and r['implication_for_offer'] != '—' else '')
        + '</li>' for r in rs)
    stage_cards.append(f'<article class="stage"><h4>{esc(st)}</h4><ul>{lis}</ul></article>')
stage_html = '<div class="stages">' + ''.join(stage_cards) + '</div>'

TAB_PZ = (
    block('Воронка продаж конкурентов по этапам', funnel + stage_html,
          'Прозвон командой «Дома гирлянд» 21.10.2026 по сценарию «частный клиент, забор с воротами под ключ». В сводной '
          'таблице команды компании не названы, кроме ЗаводЗаборов и ПрофЗаборов (по сообщениям после звонка); число '
          'звонков не указано, персонаж один. Итоговые цены после замера не сняты.') +
    obs('На этапе расчёта рынок выглядит одинаково: расчёт с калькулятора по телефону, базовая комплектация, скидка «без '
        'размера» у всех, чек объекта с воротами 350–450 тыс. ₽. Различия начинаются после звонка: письменный расчёт с '
        'материалами доверия прислали ПрофЗаборы; итоговое КП прислала одна компания; три варианта въезда с ценами '
        '(730–950 тыс. ₽) дала одна компания.') +
    obs('Два признака слабой продажи: часть компаний ничего не спрашивает и не выясняет, кто принимает решение; менеджер '
        'одной компании сам говорит, что цена «на замере обычно увеличивается на 20%». Бесплатный замер из рекламы на деле '
        'часто бесплатен только при договоре: у ЗаводЗаборов без договора выезд стоит 3 000–5 500 ₽.') +
    block('Что из прозвона идёт в оффер',
          '<ul><li>Письменное КП с двумя вариантами и исключениями — в прозвоне его прислала одна компания.</li>'
          '<li>Квалификация по скрипту: дом, материал, метры, ворота, сроки, адрес, фото — часть рынка её пропускает.</li>'
          '<li>Цена, которая не меняется после замера, — рынок сам предупреждает о росте на 20%.</li>'
          '<li>Неценовые бонусы вместо «мангала и грядки» и скидки без размера.</li>'
          '<li>Прогрев после расчёта: сообщение с примерами работ и отзывами, как у ПрофЗаборов.</li></ul>') +
    obs('Прозвон закрывает этап методики частично: нужны названия компаний, два персонажа (частный клиент и строитель) '
        'и прогон отдела продаж «Дома гирлянд» по тому же сценарию для сравнения.')
)

# ================================================================ TAB 7 — Откатные ворота
groups = [('Полный разбор', [g['domain'] for g in gates if g['group'].startswith('полный')]),
          ('Облегчённый список', [g['domain'] for g in gates if g['group'].startswith('облег')]),
          ('Специалисты по воротам', [g['domain'] for g in gates if g['group'].startswith('специализ')])]
gall = ''
for title, doms in groups:
    gall += f'<h4>{title}</h4>' + hbar(gate_items(doms), vmax=150000,
                                       refs=[(med_mech, 'мед. мех.'), (med_auto, 'мед. авт.')], aria=f'Цены ворот, {title}')
gall = legend([('s1', 'механические, 4 м'), ('s2', 'с автоматикой, 4 м')]) + gall

surch = [num(g['auto_surcharge_rub']) for g in gates if num(g['auto_surcharge_rub'])]
n_auto_pub = sum(1 for g in gates if num(g['price_auto_4m_rub']))
spec_rows = ''.join(
    f'<tr><th scope="row">{dlink(s["domain"])}</th><td>{esc(s["h1"])}</td><td>{esc(s["offer"])}</td><td>{esc(s["promos"])}</td>'
    f'<td>{esc(short(gmap.get(s["domain"], {}).get("prepayment", ""), 80))}</td><td>{esc(short(gmap.get(s["domain"], {}).get("guarantee", ""), 60))}</td></tr>'
    for s in gspec)
spec_table = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Сайт</th><th>Заголовок</th><th>Оффер</th><th>Акции</th>'
              '<th>Предоплата</th><th>Гарантия</th></tr></thead><tbody>' + spec_rows + '</tbody></table></div>')
spec_shots = '<div class="shots">' + ''.join(
    shot(GT[s['domain']][0], GT[s['domain']][1], f'{s["domain"]}, страница откатных ворот', esc(s['domain']))
    for s in gspec if s['domain'] in GT) + '</div>'
main_shots = '<div class="shots">' + ''.join(
    shot(GT[d][0], GT[d][1], f'{d}, страница откатных ворот', esc(dname(d))) for d in MAIN if d in GT) + '</div>'

spec_line = [l for l in sec(S_REV, '3.').split('\n') if l.startswith('Специалисты по откатным воротам')]
spec_vals = re.findall(r'(связь|сроки|гарантия|материал) — (\d+,\d)%', spec_line[0]) if spec_line else []
gcomp = hbar([dict(label=esc(t.capitalize()), series=[(num(v), 's2', v + '%', None)]) for t, v in spec_vals], vmax=100,
             aria='Жалобы на специалистов по воротам') if spec_vals else ''
gate_offer = md_html(sec(S_SYN, '6.'))

TAB7 = (
    block('Цены: все игроки', gall,
          'Только явный проём 4 м и сопоставимый состав; если цены 4 м нет, рядом — цена «от» без размера. Наведите на строку, '
          'чтобы увидеть состав комплекта. Сайты, 20.10.2026.') +
    obs(f'Медиана механических ворот 4 м с монтажом — {fnum(med_mech)} ₽ (n={n_mech}), с автоматикой — {fnum(med_auto)} ₽ '
        f'(n={n_auto}). Надбавка за автоматику на одной странице — от {fnum(min(surch))} до {fnum(max(surch))} ₽, медиана '
        f'{fnum(statistics.median(surch))} ₽ (оценка: фундамент и марка привода у пар разные). Цену 4 м с автоматикой '
        f'публикуют {n_auto_pub} из {len(gates)} сайтов.') +
    block('Страницы ворот у компаний полного разбора', main_shots) +
    block('Специалисты по откатным воротам', spec_table + spec_shots,
          '8 специализированных игроков: страница откатных ворот, оффер, акции, условия оплаты и гарантии.') +
    obs('Специалисты продают скорость и производство: изготовление за 1–2 дня, «более 2 000 ворот в год», 3D-макет. '
        'Без предоплаты работают Алюсис и Ворота750. У Группы мастеров на странице висят акции сентября 2025 года.') +
    block('На что жалуются клиенты специалистов', gcomp,
          'Доля тем в отзывах 1–3★ о четырёх специалистах (Алюсис, Металлические системы, Заборы Престиж, Ворота750), n=35. '
          'База меньше 30 по каждой компании — доли по компаниям незначимы.') +
    obs('У специалистов по воротам главные жалобы — связь (54,3% против 28,4% у заборных компаний) и сроки (34,3% против 10,3%). '
        'Обещание срока монтажа и сервисного выезда в договоре закрывает эти темы.') +
    block('Откатные ворота на Яндекс Картах', f'<p>{inline(obs_items.get(8, ""), names=True)}</p>') +
    obs('На картах ворота продают другие компании, чем заборы: производители и дилеры ворот. Цены в их витринах — '
        '38 800–90 000 ₽ за ворота и 14 000–17 000 ₽ за привод; это ниже медиан сайтов, потому что в витрине чаще цена без монтажа '
        'или минимального размера (оценка).') +
    block('Оффер по откатным воротам для «Дома гирлянд»', gate_offer) +
    obs('Спрос смещается к уже стоящим воротам: запросы о приводах +20,8% за год при падении запросов о новых воротах на '
        '20–55% (исследование ворот). Автоматизация стоящих ворот — небольшой растущий сегмент, его проверяют H5 и H8.')
)

# ================================================================ TAB 8 — Предложение
S_OC = md_sections(N / 'offer_constructor.md')
S_OC3 = md_sections(N / 'offer_constructor.md', level=3)

ROLE_KIND = {'обещание закрывает свободный критерий': 'ok', 'обещание, которого нет ни у кого из 10': 'ok',
             'на уровне лучших обещаний рынка': 'wait', 'ниже лучших обещаний рынка': 'part',
             'не можем конкурировать на старте': 'open'}
ROLE_SHORT = {'обещание закрывает свободный критерий': 'закрывает свободный критерий',
              'обещание, которого нет ни у кого из 10': 'обещания нет ни у кого из 10',
              'на уровне лучших обещаний рынка': 'на уровне лучших обещаний',
              'ниже лучших обещаний рынка': 'ниже лучших обещаний',
              'не можем конкурировать на старте': 'на старте не конкурирует'}
ovm_rows = []
for r in sorted([x for x in ovm if x['id'].startswith('C')], key=lambda x: -(num(x['weight']) or 0)):
    marks = []
    if r['scale_level_added_21_10'] and r['scale_level_added_21_10'] != 'нет':
        marks.append('шкала дополнена 21.10')
    if r['client_decision_variant'] and r['client_decision_variant'] != '—':
        marks.append('решение заказчика: ' + r['client_decision_variant'])
    mk = ''.join(f'<span class="mark">{tx(m)}</span>' for m in marks)
    role = r['role']
    ovm_rows.append(
        f'<tr><th scope="row">{tx(r["criterion"])}<small>{esc(r["class"])} · вес {fnum(num(r["weight"]), 1)}</small></th>'
        f'<td class="n">{esc(r["market_best_executed"])} / {esc(r["market_median_executed"].replace(".", ","))}</td>'
        f'<td class="n">{esc(r["market_best_promise_only"])}</td>'
        f'<td class="n dg">{esc(r["dom_girlyand_promise"])}</td>'
        f'<td>{tx(clean(r["dom_girlyand_basis"]))}{mk}</td>'
        f'<td class="n">{esc(r["competitors_promise_at_or_above"])}</td>'
        f'<td>{chip(ROLE_SHORT.get(role, role), ROLE_KIND.get(role, "na"))}</td></tr>')
ovm_tab = ('<div class="tscroll"><table class="tbl small ovm"><thead><tr><th>Критерий</th><th>Рынок — исполнено: лучший / медиана</th>'
           '<th>Рынок — лучшее обещание</th><th>«Дом гирлянд» — обещание</th><th>Что обещаем</th>'
           '<th>Компаний с обещанием не ниже</th><th>Роль</th></tr></thead><tbody>' + ''.join(ovm_rows) + '</tbody></table></div>')
roles_tab = md_tables(sec(S_OC, '1.'))
roles_html = table_html(roles_tab[0], names=True) if roles_tab else ''
pay_note = [p for p in sec(S_OC, '1.').split('\n') if p.startswith('**Оплата после приёмки')]
pay_html = f'<p>{inline(pay_note[0])}</p>' if pay_note else ''

# варианты
def strip_num(t):
    return re.sub(r'^\d+\.\s*', '', t)


DIST_KIND = {'свободно': 'ok', 'почти свободно': 'wait', 'есть у рынка': 'open'}
var_html = []
for vname in dict.fromkeys(r['variant'] for r in ovar):
    rs = [r for r in ovar if r['variant'] == vname]
    line = ''
    for k, v in S_OC3.items():
        if k.startswith('Вариант ' + vname[1]):
            m = re.search(r'Одной строкой:\s*(.+)', v)
            line = m.group(1).strip() if m else ''
    trs = ''.join(
        f'<tr><th scope="row">{esc(strip_num(r["block"]))}</th><td>{tx(r["text"])}</td>'
        f'<td class="ev">{tx(clean(r["evidence"]))}</td><td class="n">{esc(r["competitors_same_n_of_10"])}</td>'
        f'<td>{chip(r["distinct"], DIST_KIND.get(r["distinct"], "na")) if r["distinct"] not in ("—", "") else "—"}</td></tr>'
        for r in rs)
    var_html.append(f'<article class="variant"><h4>{esc(vname)}</h4>' + (f'<p class="oneline">{inline(line)}</p>' if line else '') +
                    '<div class="tscroll"><table class="tbl small"><thead><tr><th>Блок</th><th>Содержание</th><th>Основание</th>'
                    '<th>Говорят то же, из 10</th><th>Отличимость</th></tr></thead><tbody>' + trs + '</tbody></table></div></article>')
variants_html = ''.join(var_html)

# трансформационная идея
def tt_table(kind, layers):
    rs = [r for r in ttab if r['table'] == kind and r['layer'] in layers]
    trs = ''.join(f'<tr><th scope="row">{esc(r["layer"])}<small>{esc(r["dimension"])}</small></th><td>{tx(r["before"])}</td>'
                  f'<td>{tx(r["after"])}</td><td class="ev">{tx(r["evidence_quote"])}</td></tr>' for r in rs)
    return ('<div class="tscroll"><table class="tbl small tt"><thead><tr><th>Слой</th><th>Было</th><th>Стало</th><th>Основание</th></tr>'
            '</thead><tbody>' + trs + '</tbody></table></div>')


t_layers = list(dict.fromkeys(r['layer'] for r in ttab))
t_offer = [l for l in t_layers if l.startswith('оффер')]
t_result = [l for l in t_layers if not l.startswith('оффер')]
trans_html = ('<h4>Трансформационная идея: оффер</h4>' + tt_table('Трансформационная идея', t_offer) +
              '<h4>Трансформационная идея: результат после монтажа и после первой зимы</h4>' + tt_table('Трансформационная идея', t_result) +
              '<h4>Эмоции до и после: оффер</h4>' + tt_table('Эмоции до и после', t_offer) +
              '<h4>Эмоции до и после: результат</h4>' + tt_table('Эмоции до и после', t_result))

prod = sec(S_SYN, '4.')
prod = re.sub(r'\(скрипт[^)]*\)', '', prod).split('**Эмоциональная ценность')[0]
s5 = sec(S_SYN, '5.')
utp = s5[s5.find('**Одна фраза'):] if '**Одна фраза' in s5 else s5

# SWOT
swot = md_tables(sec(S_OC, '5.'))
if swot and len(swot[0]) >= 4:
    t = swot[0]
    sw = [(t[0][0], t[1][0], 'sw-s'), (t[0][1], t[1][1], 'sw-w'), (t[2][0], t[3][0], 'sw-o'), (t[2][1], t[3][1], 'sw-t')]
    swot_html = '<div class="swot">' + ''.join(
        f'<div class="swq {c}"><h4>{inline(h.replace("**", ""))}</h4><ul>' +
        ''.join(f'<li>{inline(x.strip())}</li>' for x in re.split(r';\s+', b) if x.strip()) + '</ul></div>' for h, b, c in sw) + '</div>'
else:
    swot_html = md_html(sec(S_OC, '5.'))
recs_html = md_html(sec(S_OC, '6.'), names=True)
strat_html = md_html(sec(S_OC, '3.'), names=True)

TAB8 = (
    block('Целевой оффер против рынка', roles_html + pay_html + details('Таблица по 38 критериям', ovm_tab, open_=True),
          'Рынок оценён по исполнению: в 7 критериях балл складывается из обещания на сайте и жалоб в отзывах, в 2 — только '
          'из отзывов. «Дом гирлянд» оценён по обещанию: исполнения и отзывов ещё нет. Шкала дополнена 21.10 под целевой '
          'оффер (уровни 5 у пяти критериев, 4 — у двух, две новые строки), ни одна из 10 компаний под новые уровни не '
          'подпадает. Поэтому итог подан ролями критериев, сумма баллов победой не считается.') +
    obs('Обещания закрывают три свободных критерия — связь после оплаты, пакет «забор + ворота» с итоговой суммой, сервис '
        'автоматики — и добавляют шесть обещаний, которых нет ни у кого из 10: гарантию с весенним осмотром, итоговую сумму '
        'с исключениями, защиту газона в акте, фото-акт и паспорт, неустойку в рублях, письменное КП. На старте целевой '
        'оффер не конкурирует по отзывам, производству, своей бригаде, опыту и кейсам.') +
    block('Общее, уникальное и оффер «Дома гирлянд»: диаграмма Венна', venn_svg + details('Таблица: 38 критериев по зонам', venn_tab),
          'Критерий у компании есть, если её оценка 3 и выше из 5. Общее — у 7–10 из 10 компаний, уникальное — у 1–2, середина рынка (3–6) '
          'вынесена под диаграмму. Круг оффера — обещание целевого оффера «Дома гирлянд» по той же шкале. На телефоне диаграмму можно прокрутить вбок.') +
    obs(OBS_VENN) +
    block('Явные и скрытые ценности', vt_html,
          'Эксплицитная — клиент называет сам (уточнение запроса или 2% отзывов и больше); имплицитная — вслух почти не называется. Цитаты без имён.') +
    obs(OBS_VAL) +
    block('Конструктор оффера: три варианта', variants_html,
          'Сегмент → боль → обещание → механизм → доказательства → снятие рисков → бонусы → срочность → следующий шаг. '
          '«Говорят то же» — сколько из 10 компаний обещают то же по рубрике оценки.') +
    obs('Самый отличимый — вариант 2 «въездная группа в одной смете»: во всех шести блоках с подсчётом то же говорят 0–2 '
        'компании. У варианта 1 свободны риски, бонусы и срочность, обещание и доказательства есть у рынка. Вариант 3 почти '
        'свободен, но объём поиска мал: около 55 кликов за 28 дней в ноябре (оценка).') +
    block('Трансформационная идея и эмоции до и после', trans_html,
          'Было → стало по логике, эмоциям и технологии отдельно для оффера, результата после монтажа и после первой зимы. '
          'Основание — цитаты из отзывов и прозвона.') +
    obs('Обещание оффера проверяется дважды: в день приёмки (сумма не изменилась, акт подписан) и после первой зимы '
        '(столбы, калитка, покрытие). Вторая проверка — то, о чём клиенты пишут в негативных отзывах чаще всего.') +
    block('Целевой продукт по 11 вопросам', md_html(prod),
          'Продукт собран из лучших решений рынка; у кого взято — в скобках. Основной персонаж — гипотеза.') +
    block('УТП: идея и три выгоды', md_html(utp),
          'Суммы неустойки, сроки выезда и порядок оплаты — параметры на решение заказчика.') +
    obs('Скидки и подарки есть в оффере у 10 из 10 компаний, в прозвоне скидку без размера дают все — скидка как главный '
        'мотив слабо отличает. Твёрдая цена, точная дата и гарантия после зимы закрывают смету (18,0% жалоб), сроки (10,3%), '
        'гарантию (27,6%) и связь после оплаты (28,4%).') +
    block('SWOT «Дома гирлянд» против рынка', swot_html) +
    block('Рекомендации: слабая сторона → возможность → способ', recs_html) +
    obs('Главная слабая сторона на старте — отсутствие отзывов и кейсов; её закрывают база клиентов «Дома гирлянд» (H6) '
        'и фото-акты первых 20–30 объектов. Оплата после приёмки требует оборотных денег — вариант с авансом 50% остаётся '
        'решением заказчика.') +
    block('Десять офферов стратегии заказчика: статус на рынке', strat_html,
          'Офферы из стратегии «Дома гирлянд» от 19.10.2026 против сайтов и прозвона.') +
    obs('Свободны два оффера стратегии: проверка возможности автоматизации ворот и въезд с освещением и автоматикой. '
        'Почти свободны три: визуальное согласование, три варианта въезда с ценами, замена с демонтажем.')
)

# ================================================================ TAB 9 — Гипотезы
cid_re = re.compile(r'C\d{2}\s*')


def crit_human(s):
    return cid_re.sub('', s).replace('  ', ' ').strip()


def base_row(hid):
    rs = [m for m in mplan if m['hypothesis_id'] == hid]
    for m in rs:
        if m['scenario'].startswith(('база', 'по кейсам')):
            return m
    return rs[0] if rs else None


def upper(s):
    vals = [num(x) for x in re.findall(r'\d[\d  ]*(?:,\d+)?', s or '')]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None


# матрица: гипотеза × сценарий чека
mx_rows = []
for h in hyps_sorted:
    m = base_row(h['hypothesis_id'])
    cells = []
    for k in (1, 2, 3):
        if not m or not m.get(f'check{k}_name') or m.get(f'check{k}_name') == '—':
            cells.append('<td class="mx na">—</td>')
            continue
        v = m[f'check{k}_verdict']
        kind = verdict_kind(v)
        share = m[f'check{k}_ad_share']
        cells.append(f'<td class="mx mx-{kind}" data-tip="{esc(m[f"check{k}_name"] + ": чек " + m[f"check{k}_rub"] + " ₽; безубыточная заявка " + m[f"check{k}_breakeven_cpl_rub"] + " ₽")}">'
                     f'<b>{esc(share if share != "не считается" else "—")}</b><small>{esc(v)}</small>'
                     f'<small class="ck">чек {esc(m[f"check{k}_rub"])} ₽</small></td>')
    sub = (f'{fnum(num(h["budget_rub_assumption"]))} ₽ · заявка {esc(h["expected_cpl_rub"])}'
           + (' ₽' if num(h['expected_cpl_rub']) or '–' in h['expected_cpl_rub'] else '')
           + (f' · заказ {esc(h["expected_cpo_rub"])} ₽' if num(h['expected_cpo_rub']) or '–' in h['expected_cpo_rub'] else ''))
    mx_rows.append(f'<tr><th scope="row"><strong>{h["hypothesis_id"]}</strong> {tx(h["channel"])}<small>{sub}</small></th>{"".join(cells)}</tr>')
cnames = []
for k in (1, 2, 3):
    cnames.append({1: 'Консервативный чек', 2: 'Базовый чек', 3: 'Верхний чек'}[k])
mx_tab = ('<div class="tscroll"><table class="tbl mxt"><thead><tr><th>Гипотеза · бюджет · цена заявки и заказа (база)</th>' +
          ''.join(f'<th>{c}</th>' for c in cnames) + '</tr></thead><tbody>' + ''.join(mx_rows) + '</tbody></table></div>')
mx_legend = ('<div class="legend"><span>' + chip('≤ 11% чека', 'ok') + ' реклама не больше 11% чека</span><span>' +
             chip('по марже', 'wait') + ' реклама в пределах валовой маржи 25%</span><span>' + chip('на границе', 'part') +
             ' зависит от цены клика</span><span>' + chip('не окупается', 'open') + ' реклама больше маржи</span></div>')

# цена заявки против безубыточной заявки при базовом чеке
thr_items = []
for h in hyps_sorted:
    m = base_row(h['hypothesis_id'])
    cpl = upper(h['expected_cpl_rub'])
    be = upper(m['check2_breakeven_cpl_rub']) if m and m.get('check2_breakeven_cpl_rub') not in (None, '', '—') else None
    if be is None and m:
        be = upper(m.get('check1_breakeven_cpl_rub'))
    thr = upper(h['threshold_cpl_ad11pct_rub'])
    thr_items.append(dict(label=f'<strong>{h["hypothesis_id"]}</strong> {tx(h["channel"])}', sub=f'базовый чек {esc(h["base_check_rub"])} ₽',
                          series=[(cpl, 's1', (f'до {fnum(cpl)} ₽') if cpl else '', 'цена заявки не считается'),
                                  (be, 's3', (f'до {fnum(be)} ₽') if be else '', 'нет'),
                                  (thr, 'sg', (f'до {fnum(thr)} ₽') if thr else '', 'нет')]))
thr_chart = legend([('s1', 'ожидаемая цена заявки (верх диапазона)'), ('s3', 'безубыточная заявка при базовом чеке'),
                    ('sg', 'порог «реклама = 11% чека» при базовом чеке')]) + hbar(thr_items, aria='Цена заявки против порогов')

cards = []
for h in hyps_sorted:
    mp = [m for m in mplan if m['hypothesis_id'] == h['hypothesis_id']]
    mp_rows = ''.join(
        f'<tr><td>{tx(m["scenario"])}</td><td class="n">{esc(m["cpc_rub"])}</td><td class="n">{esc(m["clicks"])}</td>'
        f'<td class="n">{esc(m["page_conversion"])}</td><td class="n">{esc(m["leads"])}</td><td class="n">{esc(m["cpl_rub"])}</td>'
        f'<td class="n">{esc(m["close_rate"])}</td><td class="n">{esc(m["orders"])}</td><td class="n">{esc(m["cpo_rub"])}</td>'
        f'<td>{esc(m["check1_ad_share"])} / {esc(m["check2_ad_share"])} / {esc(m["check3_ad_share"])}</td></tr>' for m in mp)
    mp_tab = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Сценарий</th><th>Клик, ₽</th><th>Клики</th>'
              '<th>Конверсия страницы</th><th>Заявки</th><th>Цена заявки, ₽</th><th>Закрытие</th><th>Заказы</th><th>Цена заказа, ₽</th>'
              '<th>Реклама в чеке: консерв. / база / верх</th></tr></thead>'
              f'<tbody>{mp_rows}</tbody></table></div>') if mp else ''
    cpc = h['cpc_rub']
    cards.append(f'''<article class="hyp"><header><span class="hid">{h["hypothesis_id"]}</span><div><h4>{tx(h["offer"])}</h4>
<p class="hmeta">{tx(h["channel"])} · {tx(h["test_period"])}</p></div></header>
<dl class="hdl">
<dt>Бюджет</dt><dd>{fnum(num(h["budget_rub_assumption"]))} ₽ <span class="tag tag-est">допущение</span></dd>
<dt>Цена клика</dt><dd>{esc(cpc)}{" ₽" if any(c.isdigit() for c in cpc) else ""}</dd>
<dt>Семантика и аудитория</dt><dd>{tx(h["semantics_audience"])}</dd>
<dt>Посадочная</dt><dd>{tx(h["landing_blocks"])}</dd>
<dt>Базовый сценарий</dt><dd>{tx(h["base_scenario"])}; заявка {esc(h["expected_cpl_rub"])}; заказов {esc(h["expected_orders"])}; заказ {esc(h["expected_cpo_rub"])}</dd>
<dt>Окупаемость по сценариям чека</dt><dd>{tx(h["verdict_by_check"])}</dd>
<dt>Базовый чек</dt><dd>{esc(h["base_check_rub"])} ₽ <span class="tag tag-est">оценка</span>; порог «реклама = 11% чека» — заявка до {esc(h["threshold_cpl_ad11pct_rub"])} ₽</dd>
<dt>Главная метрика</dt><dd>{tx(h["main_metric"])}</dd>
<dt class="stop">Остановить</dt><dd>{tx(h["stop_rule"])}</dd>
<dt class="go">Продолжить</dt><dd>{tx(h["scale_rule"])}</dd>
<dt>Что проверяет</dt><dd>{tx(crit_human(h["criteria_tested"]))}</dd>
</dl>{details("Медиаплан по сценариям и другие сценарии", mp_tab + (f'<p class="note">{tx(h["other_scenarios"])}</p>' if h["other_scenarios"] not in ("", "—") else ""))}</article>''')
hyp_html = '<div class="hyps">' + ''.join(cards) + '</div>'

qual = tx(hyps[0]['qualified_lead_definition'])
s7 = sec(S_SYN, '7.')
assump = s7.split('Допущения:')[1].split('\n|')[0] if 'Допущения:' in s7 else ''
rules_par = [p for p in s7.split('\n') if p.startswith('Правила продолжения')]

TAB9 = (
    block('Окупаемость при трёх сценариях чека', mx_legend + mx_tab,
          'Доля рекламы в чеке = цена заказа / чек при базовом сценарии трафика. Консервативный чек — модель «длина × цена «от»»; '
          'базовый — медиана сумм заказов в отзывах (забор, 259 825 ₽, n=20) и прозвон 21.10 (пакет 350–450 тыс. ₽); верхний — '
          'третий квартиль сумм в отзывах и КП конкурента 730–950 тыс. ₽. Цена клика поиска — диапазон 85–124 ₽ '
          '(Keys.so — Spywords), крайние 71–245 ₽. Все цифры — оценка.') +
    obs('Окупаемость поиска зависит от чека. При модельном чеке поиск с конверсией 2% не окупается; при пакете по прозвону '
        '(350–450 тыс. ₽) реклама занимает 10,5–19,7% чека — в пределах валовой маржи; забор по медиане сумм в отзывах '
        '(259 825 ₽) — 18–27%, на границе маржи. 19 из 20 сумм в отзывах взяты из негативных отзывов, поэтому базовый чек '
        'забора смещён к крупным и проблемным заказам.') +
    block('Цена заявки против безубыточной', thr_chart,
          'Безубыточная заявка — цена заявки, при которой реклама съедает валовую маржу 25% базового чека при закрытии 9% '
          '(Авито — 2,3% по кейсу).') +
    obs('Пакет «забор + ворота» (H2) — первый кандидат в поиске, но его объём в ноябре ограничен 161–172 кликами. Авито (H8) '
        'по кейсу укладывается в 11% базового чека; кейс с продажами один (2 из 86 обращений), поэтому H8 проверяет '
        'допущение; подтверждением канала один кейс служить не может. Вопрос заказчику: какую базу чека брать — суммы первых КП покажут её через 2–3 недели.') +
    block('Карточки гипотез H1–H8', hyp_html,
          f'Все бюджеты — допущение аналитика, всего {fnum(budget_total)} ₽; заказчик бюджет не называл.') +
    block('Квалифицированная заявка и допущения', f'<p class="qual">{qual}</p>' + md_html(assump) +
          (f'<p>{inline(rules_par[0])}</p>' if rules_par else ''),
          'По доле квалифицированных заявок срабатывают правила остановки (меньше 50%) и продолжения (от 60%).') +
    obs('За 3–4 недели теста ожидается 0–4 заказа на гипотезу — для решения о масштабе этого мало. Решение по тесту '
        'принимается по цене заявки, конверсии страницы, доле квалифицированных и среднему чеку первых КП.')
)

# ================================================================ TAB 10 — Финансы и рынок
YEARS = ('2023', '2024', '2025')
fin_main = [r for r in finance if r['role'] in ('полный разбор', 'облегчённо', 'ворота')]
fin_group = [r for r in finance if r['role'].startswith('сумма группы')]
fin_by = {}
for r in fin_group + fin_main:
    fin_by.setdefault((r['domain'].split(' ')[0], r['company']), {})[r['year']] = r


def fin_val(ys, y, k, div=1.0):
    v = num(ys.get(y, {}).get(k))
    return None if v is None else v / div


def f_rev(v):
    return fnum(v, 1 if abs(v) < 100 else 0)


def f_one(v):
    return fnum(v, 1)


def f_int(v):
    return fnum(v)


fin_cards = []
order_fin = sorted(fin_by.items(), key=lambda kv: -(fin_val(kv[1], '2025', 'revenue_th_rub') or fin_val(kv[1], '2024', 'revenue_th_rub') or 0))
for (dom, comp), ys in order_fin:
    rev = [fin_val(ys, y, 'revenue_th_rub', 1000) for y in YEARS]
    if not any(rev):
        continue
    net = [fin_val(ys, y, 'net_profit_th_rub', 1000) for y in YEARS]
    mar = [fin_val(ys, y, 'net_margin_pct') for y in YEARS]
    rd = [fin_val(ys, y, 'receivable_days') for y in YEARS]
    yl = [y[2:] for y in YEARS]
    emp = ys.get('2025', {}).get('employees_avg') or ys.get('2024', {}).get('employees_avg') or '—'
    fin_cards.append(
        f'<article class="fin"><h4>{esc(comp)}<small>{esc(dom)} · сотрудников: {esc(emp)}</small></h4><div class="fin-g">'
        f'<figure><figcaption>Выручка, млн ₽</figcaption>{mini_cols(rev, yl, f_rev, "Выручка")}</figure>'
        f'<figure><figcaption>Чистая прибыль, млн ₽</figcaption>{mini_cols(net, yl, f_one, "Чистая прибыль")}</figure>'
        f'<figure><figcaption>Чистая маржа, %</figcaption>{mini_cols(mar, yl, f_one, "Маржа")}</figure>'
        f'<figure><figcaption>Дебиторка, дней</figcaption>{mini_cols(rd, yl, f_int, "Дебиторка")}</figure>'
        '</div></article>')
fin_grid = '<div class="fins">' + ''.join(fin_cards) + '</div>'

fin_obs = md_html(sec(S_FIN, 'Главные наблюдения'), names=True)
pairs = md_table([l for l in sec(S_FIN, 'Группы и связи').split('\n') if l.startswith('|')])
pairs_html = table_html([[p[0], p[1], p[3]] for p in pairs], names=True) if pairs else ''
groups_html = ('<ul>'
               '<li><strong>Группа «Мастеровит»</strong> — ООО «Мастеровит», ООО «Мастеровит Руф» (кровля, с 2022 года), два ООО '
               '«Мастеровит СПБ» (старое и созданное в декабре 2024 года), ООО «Парус»: общий директор и участники по ЕГРЮЛ. '
               'Оборот перетекает на новые юрлица: ООО «Мастеровит» −12% за 2025 год, группа с «Мастеровит Руф» +3%.</li>'
               '<li><strong>ООО «Мособлстрой»</strong> (zavodzaborov.ru и zabor-dlya-vseh.site) — через участника связано с ООО '
               '«ЦЕНТРЗАБОРОВ» (выручка до 0 к 2024 году, вероятный предшественник, оценка) и ООО «ЗЗ-НН» в Нижнем Новгороде.</li>'
               '<li><strong>ООО «Заборово»</strong> — оба сайта (zaborovo.ru и p-z-z.ru) на одном юрлице.</li>'
               '<li><strong>moskovskie-zabory.ru</strong> — ООО «СВ Компани» и ООО «М-ЗАБОР» (признано банкротом) принадлежат одному лицу.</li>'
               '</ul>')
ip_rows = ''.join(
    f'<tr><th scope="row">{dlink(r["domain"].split(" ")[0])}</th><td>{esc(r["role"])}</td><td>{esc(r["reg_date"][-4:])}</td>'
    f'<td>{esc(short(r["tax_regime"], 60))}</td><td>{esc(short(r["okved_main"], 60))}</td></tr>'
    for r in legal if r['legal_form'] in ('ИП', 'не установлено'))
ip_tab = ('<div class="tscroll"><table class="tbl small"><thead><tr><th>Сайт</th><th>Список</th><th>ИП с</th><th>Налоговый режим</th>'
          '<th>Основной вид деятельности</th></tr></thead><tbody>' + ip_rows + '</tbody></table></div>')
n_ip = sum(1 for r in legal if r['legal_form'] == 'ИП' and r['role'] != 'связанная компания')

TAB10 = (
    block('Динамика 2023–2025 по каждому ООО', fin_grid,
          'ГИР БО (государственный информационный ресурс бухгалтерской отчётности): выручка — строка 2110, чистая прибыль — '
          '2400; маржа = чистая прибыль / выручка; дни дебиторки = дебиторская задолженность / выручка × 365. Группа «Мастеровит» — '
          'сумма двух ООО без исключения внутригрупповых оборотов. У упрощённой отчётности в дебиторку входят прочие оборотные '
          'активы — дни у малых ООО завышены. Отрицательные значения уходят вниз от нулевой линии.') +
    obs('У 10 из 12 ООО выручка 2025 года ниже 2024-го; сильнее всех упали ЗАБОРОФФ (−61%), Первый строительный (−44%) и '
        'Мособлстрой (−36%). Чистая маржа низкая: медиана средней маржи за 3 года — 3,8% (n=15), у ООО «Мастеровит» она '
        'снизилась с 6,1% до 2,5%. Быстрее всех деньги получают модели с предоплатой: дебиторка Мастеровита — 8 дней, '
        'ЗАБОРОФФ — 12 дней.') +
    block('Группы и связи', groups_html + '<h4>Совпадения между брендами без подтверждения реестром</h4>' + pairs_html,
          'Связи — по ЕГРЮЛ; совпадения адресов и текстов — по сайтам, картам и отзывам. Имена физлиц в отчёт не включены.') +
    obs('Между разными брендами списка общих участников, директоров и юрадресов в ЕГРЮЛ нет. Самый сильный признак связи — '
        'карточка «Доступные заборы» в Химках входит в сеть ЗаводЗаборов на Яндекс Картах; реестром не подтверждён.') +
    block('ИП и компании без отчётности', ip_tab,
          f'{n_ip} сайтов оформлены на ИП: выручка ИП в открытых реестрах не раскрывается. Имена предпринимателей не показаны.') +
    obs('Среди ИП — лидер по визитам ПрофЗаборы (366 903 визита за июль–сентябрь 2026), Радуга заборов, Облзабор и Доступные '
        'заборы. Их выручку можно оценить только косвенно: бригады × объекты × чек.') +
    block('Все наблюдения по финансам', details('Открыть 10 наблюдений', fin_obs))
)

# ================================================================ TAB 11 — Источники и данные
SOURCES = [
    ('Выдача и реклама Яндекса', 'Keys.so, база «Москва», топ-10 по 9 запросам', '05.09–05.10.2026', 'https://www.keys.so/'),
    ('Объявления и бюджеты Директа, РСЯ', 'Keys.so (отчёты по 4 доменам, демо), Spywords (превью по 3 доменам), регион Москва', '21.10.2026', 'https://spywords.ru/'),
    ('Цена клика', 'Keys.so «Средняя ставка (CPC)» (05.09–02.10.2026) и расчёт Spywords «бюджет / переходы»', '21.10.2026', 'https://www.keys.so/'),
    ('Яндекс Карты и 2ГИС как реклама', 'Яндекс Карты (4 запроса, 312 карточек), 2ГИС (4 запроса × 3 страницы)', '21.10.2026', 'https://yandex.ru/maps/'),
    ('Яндекс Услуги', '14 запросов: исполнители и объявления Директа на страницах Услуг', '21.10.2026', 'https://uslugi.yandex.ru/'),
    ('Авито', '3 запроса × 100 объявлений, 12 профилей компаний, 368 отзывов; выгрузка Apify', '21.10.2026', 'https://www.avito.ru/'),
    ('Прозвон конкурентов', 'команда «Дома гирлянд»: сводная таблица по этапам воронки и сообщения после звонков', '21.10.2026', ''),
    ('Стратегия заказчика', 'документ «Заборы и откатные ворота. Стратегия запуска нового направления»', '19.10.2026', ''),
    ('Частотность, сезонность, бренд-спрос, округа МО', 'Вордстат: «Динамика» 17 рядов и «Регионы» 2 запроса, выгрузки пользователя; Keys.so и подсказки Яндекса — сверка', 'янв 2024 — сен 2026 и 20.09–20.10.2026; съём 21.10.2026', 'https://wordstat.yandex.ru/'),
    ('Трафик сайтов', 'Similarweb Pro, Website performance, весь мир', 'июль–сентябрь 2026, съём 20.10.2026', 'https://pro.similarweb.com/'),
    ('Сайты конкурентов', '13 посадочных полностью, 10 облегчённо, 8 страниц ворот; Lighthouse 12; пересъёмка первых экранов', '20–21.10.2026', ''),
    ('Отзывы', 'Яндекс Карты (75 карточек), 2ГИС (35), Отзовик, irecommend, Zoon, Яндекс Услуги', '20.10.2026', 'https://yandex.ru/maps/'),
    ('Финансы и юрлица', 'ГИР БО, ЕГРЮЛ, zachestnyibiznes.ru (штат, суды, госзакупки)', '20.10.2026', 'https://bo.nalog.gov.ru/'),
    ('SEO', 'robots.txt и sitemap.xml сайтов, who.is, Яндекс Вебмастер (ИКС)', '20.10.2026', 'https://webmaster.yandex.ru/siteinfo/'),
    ('Соцсети и посевы', 'ВКонтакте, SeedHunter (библиотека посевов), Telegram, MAX, YouTube, Rutube', 'окно 20.07–20.10.2026', 'https://seed.targethunter.ru/'),
    ('Исследования проекта', 'рынок заборов под ключ (13.10.2026), рынок откатных ворот (19.10.2026)', '13.10 и 19.10.2026', ''),
    ('Данные авитолога', 'цена заявки на Авито: ворота 400–700 ₽, септики 1 200–1 800 ₽', 'октябрь 2026', ''),
]
src_rows = ''.join(f'<tr><th scope="row">{esc(a)}</th><td>{esc(b)}</td><td>{esc(c)}</td>'
                   f'<td>{ext_link(u, "открыть")}</td></tr>'
                   for a, b, c, u in SOURCES)
src_tab = ('<div class="tscroll"><table class="tbl"><thead><tr><th>Что</th><th>Источник</th><th>Период и дата съёма</th><th>Ссылка</th>'
           '</tr></thead><tbody>' + src_rows + '</tbody></table></div>')
comp_links = '<div class="clinks">' + ''.join(
    f'<span>{dlink(d)}<small>{esc(dname(d))}</small></span>' for d in MAIN) + '</div>'

GAPS = [
    'Директ: тексты объявлений по 6 компаниям (raduga-zaborov.ru, zaboroff.ru, oblzabor.ru, zaborkin.ru — Директ есть; dostup-zabor.ru, pskzabor.ru — данных нет), живая выдача Яндекса и скриншоты объявлений — лимит Keys.so и недоступный браузер 21.10.',
    'Бюджеты Директа в рублях — по 3 доменам Spywords; прогноз Keys.so без периода; Spywords и Keys.so по Мастеровиту расходятся в 3,8 раза.',
    'Вордстат: «Топ запросов» по «откатные ворота» и динамика «установка забора» по остальной России не выгружались; Москва отдельно от области в «Регионах» не выделяется, часть округов МО (Подольск, Балашиха, Химки и др.) отдельной строки не получила.',
    'Прозвон: компании в сводной таблице не названы (кроме двух), число звонков не указано, один персонаж; итоговые цены после замера и прогон своего отдела продаж — не сняты.',
    'Авито: страницы 2–3 и запрос «забор из профнастила» не выгружались; отметки продвижения (XL, выделение) и цена заявки снаружи не видны.',
    'Similarweb: 18 доменов не собраны (дневной лимит пробного доступа); Россия отдельно и 12 месяцев пробный доступ не даёт.',
    'Регион и период источников не совпадают с рамкой «Москва и МО»: частотность и выдача — Москва, Similarweb — весь мир, июль–сентябрь 2026.',
    'Профи.ру — бот-защита; Google Trends, TGStat, Telemetr, число подписчиков MAX — ограничения сервисов.',
    'Отсрочка поставщиков, стоимость гарантийных выездов, динамика цен металла и монтажа за 2–3 года — не найдено.',
    'База чека забора — 20 сумм из отзывов, 19 из них негативные: смещение к крупным и проблемным заказам.',
    'Размер базы клиентов «Дома гирлянд» и доля владельцев домов в ней — заполняет заказчик.',
]
gaps_html = '<ul>' + ''.join(f'<li>{esc(g)}</li>' for g in GAPS) + '</ul>'

QA_TEXT = {
    'K1': ('В расчёт видимости в выдаче не вошли 4 сайта облегчённого списка, из-за этого список лидеров органики был неверен.',
           'Сайты добавлены, индекс видимости и раскладка мест в топ-10 пересчитаны.'),
    'K2': ('В сырых выгрузках отзывов оставались имена, отчества и телефоны авторов.',
           'Выгрузки обезличены, исходные страницы удалены; повторная проверка нашла 0 телефонов и 0 отчеств.'),
    'I1': ('Доля Мастеровита в негативе рынка (56%) зависела от числа его карточек и площадок.',
           'Для сравнения используется доля 1–3★ в собственных отзывах: 27,2% у Мастеровита против 12,0% у остальных девяти.'),
    'I2': ('Падение выручки ООО на 19% зависело от того, какие юрлица включены в сумму.',
           'Показаны три варианта суммы; с ООО «Мастеровит Руф» падение — 9,1%.'),
    'I3': ('В списке конкурентов не было строки pskzabor.ru.', 'Строка добавлена, визиты сверены.'),
    'I4': ('Финансовый блок не упоминал совпадения адресов и текстов между брендами.',
           'Добавлена таблица совпадений с пометкой, что реестр юридических связей не подтверждает.'),
    'I5': ('Видимость в выдаче и органический трафик по Similarweb расходились больше чем на 20%.',
           'Причины описаны, индекс видимости используется только для сравнения сайтов по 9 запросам; съём органики Keys.so ждёт сброса лимита.'),
    'I6': ('Визиты каналов считались двумя способами, расхождение доходило до 38%.',
           'Все визиты каналов пересчитаны одной формулой: визиты сайта × доля канала.'),
    'I7': ('Деление платного трафика на поиск и медийную рекламу для Рунета ненадёжно.',
           'В выводах используется сумма платных каналов с пометкой «оценка Similarweb, весь мир».'),
    'I8': ('Медианы цен ворот 4 м смешивали разный состав комплектов.',
           'Несопоставимые позиции исключены: медиана механических 71 087 ₽ (n=12), с автоматикой 103 025 ₽ (n=6).'),
    'I9': ('Пробелы методики (объявления, бюджеты, звонки «тайного покупателя») не были названы.',
           'Пробелы перечислены в разделе ограничений; объявления и бюджеты — вторая волна.'),
    'I10': ('Регион и период источников не совпадают с рамкой «Москва и МО».', 'Ограничение указано у цифр и в списке пробелов.'),
    'I11': ('Выводы на малой базе (60 и 320 визитов) были поданы как факт.', 'Переведены в гипотезы с абсолютными числами.'),
    'M1': ('Цена ворот 31 428 ₽ записана как цена 4 м с автоматикой; на сайте это шаблонная цена «от».',
           'Перенесена в цены «от», в сравнение 4 м не входит.'),
    'M2': ('Пустые ячейки ИНН и выручки 2024 года.', 'Заполнены по реестрам.'),
    'M3': ('После обезличивания оставались отчества и номера договоров.', 'Удалены.'),
    'M4': ('Две доли ответов Мастеровита без указания базы.', 'Базы подписаны: 1 134 из 1 306 и 395 из 416.'),
    'M5': ('База позитивных отзывов не воспроизводилась.', 'Фильтр описан: 4 008 отзывов минус 23 коротких = 3 985.'),
    'M6': ('Два разных значения ширины страницы zaborkin.ru на телефоне.', 'Указано «более 5 000 px» с обоими замерами.'),
    'M7': ('Имена директоров и адрес с номером квартиры не нужны в отчёте.', 'На этой странице не показаны.'),
    'M8': ('Цены за кв. м и за п. м. стояли в одном столбце.', 'Добавлены единица и признак сопоставимости; в сравнении за п. м. — только сопоставимые строки.'),
    'M9': ('Вырезка блока отзывов была пустой — виджет не загрузился.', 'Блок переснят.'),
    'M10': ('В топ-10 выдачи есть подрядчики вне списка.', 'Шесть проверены облегчённо (возраст домена, ИКС, число страниц); в сравнение по критериям не входят.'),
    'M11': ('У облегчённых компаний подписчиков ВК больше, чем у части полного списка.', 'Добавлены в таблицу сообществ на вкладке «Откуда клиенты».'),
    'M12': ('Фраза о совпадении визитов «по всем 10 сайтам» неверна для pskzabor.ru.', 'Исправлена.'),
    'SK1': ('Вес критериев складывался в основном из офферов конкурентов, поэтому «акции» попадали в первую тройку.',
            'Вес считается только по голосу клиента (отзывы 0,7, уточнения запросов 0,3); офферы — отдельной колонкой.'),
    'SK2': ('Класс критерия определялся только охватом рынка.',
            'Класс = важность (вес от 10) × охват; добавлен класс «второстепенный», показатели силы компаний вынесены отдельно.'),
    'SK3': ('Динамика доли негатива Мастеровита по годам была указана неверно.', 'Исправлено: 27% (2021), 43% (2024), 47% (2025), 24% (2026).'),
    'SK4': ('Чек забора (80 м) был выше третьего квартиля длин в отзывах.',
            'Чек задан диапазоном 40–73 м: забор 67 600–123 370 ₽, пакет 170 625–226 395 ₽.'),
    'SK5': ('Порог «реклама = 11% чека» был назван безубыточностью.',
            'Разведены два порога: «реклама = 11% чека» и безубыточность по валовой марже 25%.'),
    'SK6': ('Сценарий «по кейсам» неявно предполагал конверсию страницы 6,6–8,2%.',
            'Неявная конверсия подписана; сценарий подан как сверка, прогноз строится на базовой конверсии.'),
    'SK7': ('Ёмкость кликов считалась по широкой частотности.',
            'Ёмкость × 0,248 (точная к широкой) и сезон 0,51–0,70; бюджеты H2 и H5 снижены под ёмкость.'),
    'SK8': ('Выбор персонажа «владелец дома» не был помечен как гипотеза, доли «дача / дом» не воспроизводились.',
            'Доли пересчитаны (дача 8,0%, дом 1,0–3,1%), персонаж — гипотеза; добавлены вопрос «дом / дача» в квиз и гипотеза H6.'),
    'SK9': ('Число жалоб на сторонний монтаж давалось тремя разными значениями.', 'Везде 19 из 851 (14 у Мастеровита), ручная разметка.'),
    'SK10': ('Голос клиента у части критериев был взят по неподходящей теме.', 'Темы заменены; у каждого критерия указано, чем измерен голос клиента.'),
    'SK11': ('Вывод о колебаниях трафика платных сайтов стоял на сравнении одного сайта с одним.', 'Добавлен третий сайт и оговорка о сезоне.'),
    'SK12': ('Квалифицированная заявка не была определена.', 'Определение добавлено в карточки гипотез.'),
    'SK13': ('У цены клика не было даты и определения метрики.', 'Указаны: Keys.so, «Средняя ставка (CPC)», Москва, 05.09–02.10.2026, прогноз сервиса.'),
    'SM1': ('Отдельные ручные оценки расходились с рубрикой.', 'Оценки исправлены по рубрике.'),
    'SM2': ('Цена ворот ЗаводЗаборов указана на бетоне, в сравнении — на сваях.', 'Показаны оба варианта.'),
    'SM3': ('Неточные доли ответов на отзывы и база жалоб.', 'Исправлены с базами.'),
    'SM4': ('Себестоимость и условия предоплаты сформулированы неточно.', 'Уточнены: себестоимость 76,6–76,8%, у Заборово — выезд без предоплаты и аванс перед монтажом.'),
    'SM5': ('В SEO-блоке оставались визиты каналов по старой формуле.', 'Приведены к одной формуле.'),
    'SM6': ('В рамке не было вопросов заказчика и бюджета теста.', 'Вопросы добавлены; бюджет помечен как допущение.'),
    'SM7': ('Расхождение с исследованием 13.10 по предоплате у Заборофф.', 'На сайте 20.10.2026 предоплата не найдена; расхождение указано в оценке.'),
}


QA_TEXT.update({
    'W2-K1': ('Критерий «квалификация и консультация» измерялся общей похвалой («профессионалы», «вежливые») и вышел на первое место.',
              'Голос клиента сужен до консультации, менеджера и замерщика: критерий стал 7-м (вес 35,6); первые пять — монтаж, связь, покраска, гарантия, смета.'),
    'W2-K2': ('Чек в медиаплане (длина × цена «от») в 1,5–2,6 раза ниже чека по прозвону и суммам заказов в отзывах.',
              'Медиаплан посчитан в трёх сценариях чека: консервативный (модель), базовый (медиана сумм в отзывах и прозвон), верхний (третий квартиль и КП конкурента).'),
    'W2-V1': ('Логика гипотезы по Авито брала дешёвую цену обращения из одного кейса и закрытие из другого.',
              'База H8 — кейс Авито целиком (обращение 230 ₽, закрытие 2,3%); закрытие 9% — оптимистичный сценарий; правило продолжения через цену заказа.'),
    'W2-V2': ('Сравнение целевого оффера с рынком ставило обещание рядом с исполнением, а шкала дополнялась под целевой оффер.',
              'Таблица разделяет «рынок — исполнено» и «Дом гирлянд — обещание», шкала подписана «дополнена 21.10», итог подан ролями критериев; оплата после приёмки помечена решением заказчика.'),
    'W2-V3': ('Выводы стояли на одной цене клика 124 ₽, бюджет 518 тыс. ₽ без оговорки.',
              'Цена клика — диапазон 85–124 ₽, крайние 71–245 ₽; 518 тыс. ₽ — нижняя оценка Spywords, Keys.so — 1,97 млн ₽ без периода.'),
    'W2-V4': ('Цены конкурентов из стратегии заказчика не сведены с ценами сайтов: расхождение до 61%.',
              'Добавлена таблица сверки: 8 позиций, что взято и почему (вкладка «Сайты и офферы»).'),
    'W2-V5': ('Два рекламодателя на Яндекс Картах — физлица, их ФИО и ИНН попали в рабочие данные.', 'Данные заменены меткой; в отчёт не попадали.'),
    'W2-V6': ('Реклама собрана частично: тексты Директа по 4 компаниям, нет живой выдачи и скриншотов объявлений.',
              'Открыто: досъём после сброса лимита Keys.so и восстановления браузера; на вкладке «Реклама» — пустые места с пометкой.'),
    'W2-V7': ('Бренд-спрос, региональный коэффициент и сезонность Москвы и МО не сняты: Вордстат требует вход.',
              'Снято 21.10: выгрузки Вордстата — 10 брендов и 4 запроса рынка по месяцам за 33 месяца, округа МО по двум запросам; тренды и коэффициент пересчитаны.'),
    'W2-V8': ('Авито был снят на одной странице одного запроса, профили и отзывы продавцов — нет.',
              'После проверки снят Авито: 3 запроса × 100 объявлений, 12 профилей компаний, 368 отзывов (вкладка «Авито»).'),
    'W2-V9': ('Отчёт был собран до сводок второй волны.', 'Отчёт пересобран 21.10.2026 — эта версия.'),
    'W2-M1': ('Подпись источника цены клика в медиаплане.', 'Исправлена.'),
    'W2-M2': ('Цена заявки считалась от округлённого числа заявок.', 'Пересчитана без округления: 12 447 ₽ и 3 167 ₽.'),
    'W2-M3': ('Неверная подпись размера выборки в ответе о платном трафике.', 'Исправлено: «n=2 против n=1».'),
    'W2-M4': ('Служебная фраза без диапазона; 88% продвинутых на Авито не сведены с данными исследования ворот.', 'Диапазон и сверка добавлены.'),
    'W2-M5': ('Вывод «тренд спроса слабый» при R² 0,08.', 'Заменён оценкой с оговоркой «вывод не делается».'),
    'W2-M6': ('Бюджет Мастеровита без метки «оценка».', 'Метка добавлена.'),
    'W2-M7': ('Метка цены клика стояла у гипотез, где клик не применяется.', 'Метка оставлена только у поиска и РСЯ.'),
    'W2-M8': ('Доля ответов Радуги на негатив — два значения.', 'Подписаны обе базы: 47% по всем площадкам, 49% на Яндекс Картах.'),
    'W2-M9': ('При пересъёмке сайтов принимались баннеры cookies — правило брифа это запрещало.', 'Принято с оговоркой: cookies принимать можно, оферты и формы — нет.'),
    'W2-M10': ('На снимке dostup-zabor.ru (телефон) пустой блок под шапкой — баннер не догрузился.', 'Принято с оговоркой: переснять при следующем съёме.'),
    'W2-M11': ('Бюджет H2 равнялся нижней границе ёмкости запросов.', 'Бюджет H2 снижен до 14 000 ₽, в карточке — оговорка о CTR.'),
    'W2-M12': ('ИП в рекламных данных записаны полным ФИО.', 'На этой странице ИП показаны без имени — по сайту и названию бренда.'),
})

QA_TEXT.update({
    'FIN-K1': ('Страница открывалась под тёмным окном просмотра картинок, вкладки не нажимались.',
               'Окно скрыто до клика по картинке; все 13 вкладок проверены на телефоне (390 px) и компьютере (1320 px).'),
    'FIN-V1': ('В таблицах для скачивания оставались полные ФИО трёх предпринимателей.', 'ФИО убраны, предприниматели — по названию бренда и сайту.'),
    'FIN-V2': ('Вывод о связи просмотров на Авито с числом объявлений противоречил таблице продавцов.', 'Вывод переформулирован: связь слабая, n=15 продавцов, оценка.'),
    'FIN-V3': ('Сильные стороны оффера были описаны шире, чем показывает таблица ролей критериев.',
               'Уточнено: обещания закрывают три из первых пяти критериев и два свободных; покрытие ниже лучшего на рынке, качество монтажа на старте не подтверждено.'),
    'FIN-V4': ('В таблице полноты стояли служебные пометки и устаревшие статусы.', 'Пометки убраны, статусы обновлены после проверки.'),
    'FIN-V5': ('Термины и сокращения не были расшифрованы.', 'В шапке страницы добавлен блок «Термины и сокращения».'),
    'FIN-M1': ('Обрывок текста в строке «Уровень цены» таблицы критериев.', 'Исправлено.'),
    'FIN-M2': ('Доля 1–3★ Мастеровита на Авито дана двумя значениями без баз.', 'Показаны обе базы: 7% (11 из 157) и 9% (7 из 75).'),
    'FIN-M3': ('Доля негатива лидера в SWOT без указания площадки.', 'Добавлено «на Яндекс Картах».'),
    'FIN-M4': ('Служебные слова в тексте для заказчика.', 'Заменены датами съёма и обычными словами.'),
    'FIN-M5': ('Формы первого лица в таблице оффера.', 'Заменены названием заказчика.'),
    'FIN-M6': ('Опечатки и перенос внутри чисел в плитках.', 'Исправлены.'),
    'FIN-M7': ('Квартили сумм заказов и цен Авито посчитаны разными методами (расхождение до 4%).', 'Цифры не менялись: база чека — медиана, она от метода не зависит.'),
    'FIN-M8': ('Скрипт пересчёта отставал от доработанных таблиц.', 'Обновлён: 191 проверка, включая 43 ключевых значения на вкладках, без расхождений.'),
})


def qa_status(s):
    s = s.lower()
    if s.startswith('закрыто') or 'проверено перед публикацией' in s:
        return 'ok', 'закрыто после повторной проверки'
    if s.startswith('исправлено — проверено') or s.startswith('исправлено - проверено'):
        return 'ok', 'исправлено, проверено повторно'
    if 'ждёт проверки' in s:
        return 'wait', 'исправлено, ждёт повторной проверки'
    if s.startswith('исправлено'):
        return 'ok', 'исправлено'
    if s.startswith('частично'):
        return 'part', 'частично'
    if s.startswith('принято'):
        return 'part', 'принято с оговоркой'
    return 'open', 'открыто'


qa_rows, qa_count = [], {}
for f, stage in (('checks_wave1.csv', 'Первый сбор данных'), ('checks_synthesis.csv', 'Расчёты и выводы'),
                 ('checks_wave2.csv', 'Досбор рекламы и пересчёт'), ('checks_final.csv', 'Проверка перед публикацией')):
    if not (Q / f).exists():
        continue
    with open(Q / f, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            st_cls, st = qa_status(r['status'])
            qa_count[st_cls] = qa_count.get(st_cls, 0) + 1
            found, fix = QA_TEXT.get(r['id'], (short(clean(r['issue']).split('. ')[0], 240), short(clean(r['fix']), 240)))
            qa_rows.append(f'<tr><td>{esc(stage)}</td><td><span class="lvl lvl-{"c" if r["level"].startswith("Крит") else "i" if r["level"].startswith("Важ") else "m"}">'
                           f'{esc(r["level"].lower())}</span></td><td>{esc(found)}</td><td>{esc(fix)}</td>'
                           f'<td><span class="st st-{st_cls}">{esc(st)}</span></td></tr>')
qa_tab = ('<div class="tscroll"><table class="tbl small qa"><thead><tr><th>Этап</th><th>Уровень</th><th>Что найдено</th>'
          '<th>Как решено</th><th>Статус</th></tr></thead><tbody>' + ''.join(qa_rows) + '</tbody></table></div>')
qa_lead = (f'Каждый этап проверял независимый проверяющий: пересчёт цифр, сверка источников, логика выводов, стиль. '
           f'Всего замечаний — {len(qa_rows)}: закрыто или исправлено — {qa_count.get("ok", 0)}, '
           f'исправлено и ждёт повторной проверки — {qa_count.get("wait", 0)}, частично или с оговоркой — {qa_count.get("part", 0)}, '
           f'открыто — {qa_count.get("open", 0)}.')

# полнота по методике
COMP_UPDATE = {}  # обновления перенесены в qa/completeness.csv (проверка перед публикацией 21.10)
PUB_FIX = [(r'\s*\((?:W2|SK|SM|M|I|K|V)-?[A-Z]?\d+[^()]*\)', ''), (r'\b(?:W2-[KVM]\d+|SK\d+|SM\d+)(?:,\s*)?', ''),
           (r'\bsynthesis\b(?: v3)?', 'расчёты'), (r'\breport\b', 'отчёт'), (r'агент сайтов', 'сбор по сайтам'),
           (r'criteria_text', 'таблица фактов по критериям'), (r'ad_texts', 'таблица текстов объявлений'),
           (r'\s*\(traffic_channels\)', ''), (r'\s*\(Claude in Chrome\)', ''), (r'сводок волны 2', 'сводок по рекламе'),
           (r'второй волны', 'досбора 21.10'), (r'волны 2', 'досбора 21.10'), (r'Файл КА:', 'Шаблон конкурентного анализа:'),
           (r'УралНеруд:', 'Шаблон разбора B2B-рынка:'), (r'находки\s*;', ''), (r'\s+\)', ')'), (r'\s{2,}', ' '), (r'^\s*[—–-]\s*$', '—')]


def pub(t):
    for a, b in PUB_FIX:
        t = re.sub(a, b, t)
    t = t.strip(' ,;')
    return t or '—'


ST_KIND = {'сделано': 'ok', 'частично': 'wait', 'не сделано': 'open', 'не требуется': 'na'}
comp_rows, comp_cnt = [], Counter()
for r in compl:
    comp_cnt[r['status']] += 1
    upd = COMP_UPDATE.get(r['id'])
    gap = pub(clean(r['gap_and_reason'])) if r['gap_and_reason'] not in ('—', '') else '—'
    todo = pub(clean(r['to_close_who_access'])) if r['to_close_who_access'] not in ('—', '') else '—'
    comp_rows.append(f'<tr><td>{esc(r["block"])}</td><td>{tx(pub(r["element"]))}</td><td>{chip(r["status"], ST_KIND.get(r["status"], "na"))}</td>'
                     f'<td>{tx(gap)}' + (f'<p class="upd">Обновление: {esc(upd)}</p>' if upd else '') + f'</td><td>{tx(todo)}</td></tr>')
comp_tab = ('<div class="tscroll"><table class="tbl small compl"><thead><tr><th>Блок</th><th>Элемент методики</th><th>Статус</th>'
            '<th>Что не закрыто и почему</th><th>Как закрыть</th></tr></thead><tbody>' + ''.join(comp_rows) + '</tbody></table></div>')
comp_sum = hbar([dict(label=esc(k), series=[(v, {'сделано': 's3', 'частично': 's2'}.get(k, 'sg'), f'{v} из {len(compl)}', None)])
                 for k, v in comp_cnt.most_common()], vmax=len(compl), aria='Полнота по методике')

dl_html = '<ul class="dl">' + ''.join(
    f'<li><a href="data/{n}.csv" target="_blank" rel="noopener">{n}.csv</a><span>{esc(t)}</span></li>' for n, t in DOWNLOADS) + '</ul>'

TAB11 = (
    block('Источники и даты съёма', src_tab + '<h4>Компании полного разбора</h4>' + comp_links) +
    block('Полнота по методике', comp_sum + details(f'Открыть таблицу: {len(compl)} элемента методики', comp_tab, open_=False),
          'Проверка полноты 21.10.2026 независимым проверяющим: каждый элемент методики и просьбы пользователя — сделано, частично или нет, '
          'и почему. Статусы обновлены после проверки перед публикацией 21.10.2026.') +
    obs('Открытыми остаются две группы: реклама Директа по 6 компаниям и скриншоты объявлений (лимит Keys.so и браузер), '
        'прозвон с названиями компаний и вторым персонажем (команда заказчика). Вордстат снят 21.10 по выгрузкам.') +
    block('Что не удалось снять и ограничения', gaps_html) +
    block('Проверка данных', qa_tab, qa_lead) +
    obs('Крупные исправления второй волны: критерий «консультация» перестал быть первым после сужения темы, медиаплан '
        'посчитан в трёх сценариях чека, гипотеза по Авито построена на одном кейсе целиком, сравнение оффера с рынком '
        'разделено на «исполнено» и «обещание».') +
    block('Рабочие данные для скачивания', dl_html,
          'Таблицы в формате CSV (UTF-8, разделитель — запятая). Имена предпринимателей и физлиц, ИНН физлиц из таблиц удалены.')
)

GLOSSARY = [('CPC', 'цена клика в рекламе'), ('CTR', 'доля показов объявления, по которым кликнули'), ('РСЯ', 'Рекламная сеть Яндекса: объявления на сайтах-партнёрах, не в поиске'), ('ГИР БО', 'государственный ресурс бухгалтерской отчётности ФНС'), ('ЕРИР', 'единый реестр интернет-рекламы (маркировка)'), ('УТП', 'уникальное торговое предложение: чем предложение отличается от конкурентов'), ('SWOT', 'сильные и слабые стороны, возможности и угрозы'), ('оффер', 'предложение клиенту: что, на каких условиях и почему сейчас'), ('лендинг', 'одностраничный сайт под рекламу'), ('квиз', 'опрос из нескольких вопросов на сайте, после которого клиент получает расчёт'), ('ретаргетинг', 'показ рекламы тем, кто уже был на сайте'), ('медиана', 'середина ряда: половина значений меньше, половина больше'), ('Q1–Q3', 'границы средней половины значений (первый и третий квартили)'), ('n', 'число наблюдений, на которых стоит цифра'), ('SLA', 'обещанный срок ответа или работы'), ('CRM', 'база клиентов и сделок'), ('Lighthouse, LCP', 'замер скорости страницы; LCP — время до появления главного блока'), ('UTM', 'метки в ссылке объявления, по которым видна кампания'), ('ИКС', 'индекс качества сайта Яндекса'), ('Keys.so, Spywords, Similarweb', 'сервисы оценки рекламы, запросов и посещаемости сайтов')]
GLOSS_HTML = '<details class="gloss"><summary>Термины и сокращения</summary><dl>' + ''.join(f'<dt>{esc(a)}</dt><dd>{esc(b)}</dd>' for a, b in GLOSSARY) + '</dl></details>'

# ================================================================ page assembly
TABS = [
    ('korotko', 'Коротко', 'Ответы на вопросы заказчика', TAB1),
    ('klient', 'Как выбирает клиент', 'Критерии выбора и голос клиента', TAB2),
    ('otvet', 'Кто и как отвечает', 'Оценка 10 конкурентов по критериям', TAB3),
    ('reklama', 'Реклама', 'Директ, РСЯ, Яндекс Карты, 2ГИС, Услуги, ВКонтакте', TAB4),
    ('trafik', 'Откуда клиенты', 'Каналы, спрос, SEO, площадки, соцсети', TAB5),
    ('avito', 'Авито', 'Компании и частные мастера, цены, обещания, отзывы', TAB_AV),
    ('saity', 'Сайты и офферы', 'Первые экраны, цены, сверка, идеальная страница', TAB6),
    ('prozvon', 'Прозвон', 'Воронка продаж конкурентов по этапам', TAB_PZ),
    ('vorota', 'Откатные ворота', 'Цены, специалисты, жалобы, оффер', TAB7),
    ('predlozhenie', 'Предложение', 'Оффер против рынка, конструктор, УТП, SWOT', TAB8),
    ('gipotezy', 'Гипотезы', 'Тест рекламы с 22.10.2026: три сценария чека', TAB9),
    ('finansy', 'Финансы и рынок', 'Динамика 2023–2025, группы, ИП', TAB10),
    ('istochniki', 'Источники и данные', 'Полнота, ограничения, проверка', TAB11),
]

nav = '<nav class="tabs" aria-label="Разделы отчёта"><div class="tabs-in" role="tablist">' + ''.join(
    f'<a role="tab" href="#{k}" id="t-{k}" data-tab="{k}" aria-selected="{"true" if i == 0 else "false"}">{esc(t)}</a>'
    for i, (k, t, _, _) in enumerate(TABS)) + '</div></nav>'
panels = ''.join(
    f'<section class="panel" id="{k}" role="tabpanel" aria-labelledby="t-{k}"{"" if i == 0 else " hidden"}>'
    f'<header class="ph"><h2>{esc(t)}</h2><p>{esc(sub)}</p></header>{body}</section>'
    for i, (k, t, sub, body) in enumerate(TABS))

CSS = r'''
/* Layout: sticky tab bar over a single reading column (max 1180px); charts are HTML bars, heatmaps are tables. */
:root{
  --bg:#f3f4f1; --surface:#ffffff; --ink:#18201b; --ink2:#4b554f; --muted:#7b8580; --line:#dde1dc;
  --accent:#2e5a43; --accent-soft:#e4ede7; --w2:#9a6510; --w2-bg:#fbf3e3; --w2-line:#e3c27e;
  --c1:#2a78d6; --c2:#eb6834; --c3:#1baf7a; --cg:#a9aca6;
  --y1:#86b6ef; --y2:#3987e5; --y3:#1c5cab;
  --h0:#eeefec; --h1:#cde2fb; --h2:#9ec5f4; --h3:#6da7ec; --h4:#3987e5; --h5:#1c5cab; --h6:#0d366b;
  --ht0:#7b8580; --ht1:#18201b; --ht2:#18201b; --ht3:#18201b; --ht4:#ffffff; --ht5:#ffffff; --ht6:#ffffff;
  --good:#1f7a3a; --warn:#9a6510; --bad:#b33a2e;
  --f-display:"Onest","Golos Text",system-ui,-apple-system,"Segoe UI",sans-serif;
  --f-body:"Golos Text",system-ui,-apple-system,"Segoe UI",sans-serif;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#111513; --surface:#191e1b; --ink:#e8ece9; --ink2:#b6bfb9; --muted:#88928c; --line:#2c332f;
  --accent:#8cc2a2; --accent-soft:#1d2b23; --w2:#e6b25a; --w2-bg:#2a2214; --w2-line:#6b5428;
  --c1:#3987e5; --c2:#d95926; --c3:#199e70; --cg:#5d625e;
  --y1:#184f95; --y2:#3987e5; --y3:#9ec5f4;
  --h0:#202622; --h1:#0d366b; --h2:#184f95; --h3:#256abf; --h4:#3987e5; --h5:#6da7ec; --h6:#b7d3f6;
  --ht0:#88928c; --ht1:#e8ece9; --ht2:#e8ece9; --ht3:#ffffff; --ht4:#ffffff; --ht5:#0b1a2e; --ht6:#0b1a2e;
  --good:#5cc27a; --warn:#e6b25a; --bad:#ef7f72; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#111513; --surface:#191e1b; --ink:#e8ece9; --ink2:#b6bfb9; --muted:#88928c; --line:#2c332f;
  --accent:#8cc2a2; --accent-soft:#1d2b23; --w2:#e6b25a; --w2-bg:#2a2214; --w2-line:#6b5428;
  --c1:#3987e5; --c2:#d95926; --c3:#199e70; --cg:#5d625e;
  --y1:#184f95; --y2:#3987e5; --y3:#9ec5f4;
  --h0:#202622; --h1:#0d366b; --h2:#184f95; --h3:#256abf; --h4:#3987e5; --h5:#6da7ec; --h6:#b7d3f6;
  --ht0:#88928c; --ht1:#e8ece9; --ht2:#e8ece9; --ht3:#ffffff; --ht4:#ffffff; --ht5:#0b1a2e; --ht6:#0b1a2e;
  --good:#5cc27a; --warn:#e6b25a; --bad:#ef7f72; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:15px;line-height:1.55;margin:0}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--surface)}
a{color:var(--accent)}
a:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--c1);outline-offset:2px}
.wrap{max-width:1180px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.top{background:var(--surface);border-bottom:1px solid var(--line)}
.top .wrap{padding-block:28px 20px}
.eyebrow{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 8px}
h1{font-family:var(--f-display);font-weight:700;font-size:clamp(24px,3.6vw,36px);line-height:1.15;margin:0 0 10px;text-wrap:balance;letter-spacing:-.01em}
.meta{display:flex;flex-wrap:wrap;gap:8px 18px;color:var(--ink2);font-size:14px;margin:0}
.meta b{color:var(--ink)}
.chip-date{display:inline-flex;gap:6px;align-items:center;background:var(--accent-soft);color:var(--accent);border-radius:999px;padding:2px 10px;font-weight:600}
.legend-tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;font-size:13px;color:var(--ink2);align-items:center}
.tabs{position:sticky;top:env(safe-area-inset-top,0px);z-index:9;background:var(--surface);border-bottom:1px solid var(--line)}
.tabs-in{max-width:1180px;margin:0 auto;display:flex;gap:2px;overflow-x:auto;scrollbar-width:thin;padding-left:max(10px,env(safe-area-inset-left,0px));padding-right:max(10px,env(safe-area-inset-right,0px))}
.tabs a{flex:0 0 auto;padding:12px 12px 10px;text-decoration:none;color:var(--ink2);font-size:14px;border-bottom:3px solid transparent;white-space:nowrap}
.tabs a:hover{color:var(--ink)}
.tabs a[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
main{padding-block:24px 64px}
.ph{margin:4px 0 18px}
.ph h2{font-family:var(--f-display);font-size:clamp(22px,2.8vw,30px);margin:0;line-height:1.2;text-wrap:balance}
.ph p{margin:4px 0 0;color:var(--muted)}
.blk{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:20px clamp(14px,2.4vw,24px);margin-top:16px;min-width:0}
.blk h3{font-family:var(--f-display);font-size:19px;margin:0 0 6px;text-wrap:balance}
.blk h4{font-size:15px;margin:18px 0 8px}
.lead{color:var(--ink2);margin:0 0 14px;max-width:78ch;font-size:14px}
.note{color:var(--muted);font-size:13px;max-width:90ch}
.blk p,.blk li{max-width:90ch}
.obs{margin:10px 0 0;padding:12px 16px;background:var(--accent-soft);border-radius:10px;display:grid;gap:4px}
.obs-k{font-size:11px;letter-spacing:.09em;text-transform:uppercase;font-weight:700;color:var(--accent)}
.obs p{margin:0;max-width:95ch}
.tag{display:inline-block;font-size:11px;letter-spacing:.03em;padding:0 6px;border-radius:4px;border:1px solid var(--line);color:var(--ink2);margin-right:4px;vertical-align:1px;white-space:normal}
.tag-fact{border-color:var(--c1);color:var(--c1)}
.tag-hyp,.tag-est{border-color:var(--w2-line);color:var(--w2)}
.tag-concl{border-color:var(--c3);color:var(--good)}
/* tiles */
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.tile{border:1px solid var(--line);border-radius:10px;padding:14px;display:grid;gap:4px;align-content:start}
.tile-v{font-family:var(--f-display);font-size:28px;font-weight:700;line-height:1.1}
.tile-l{font-size:14px;color:var(--ink)}
.tile-s{font-size:12px;color:var(--muted)}
/* answers */
.answers{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.ans{border:1px solid var(--line);border-radius:10px;padding:14px 16px;min-width:0}
.ans h4{margin:0 0 6px;display:flex;gap:10px;align-items:baseline;font-size:16px;text-wrap:balance}
.qn{font-family:var(--f-display);color:var(--accent);font-weight:700}
.ans>p{margin:0 0 8px}
details{border-top:1px dashed var(--line);margin-top:8px}
summary{cursor:pointer;color:var(--accent);font-size:14px;padding:8px 0;font-weight:600}
.det{font-size:14px;color:var(--ink2)}
.det ul,.det ol{padding-left:18px}
.testlist{padding-left:20px;display:grid;gap:8px}
.testlist span{color:var(--ink2);font-size:14px}
/* legend */
.legend{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:var(--ink2);margin:4px 0 10px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
.s1{background:var(--c1)}.s2{background:var(--c2)}.s3{background:var(--c3)}.sg{background:var(--cg)}
.y1{background:var(--y1)}.y2{background:var(--y2)}.y3{background:var(--y3)}
.sw.h0{background:var(--h0);border:1px solid var(--line)}.sw.h1{background:var(--h1)}.sw.h2{background:var(--h2)}.sw.h3{background:var(--h3)}.sw.h4{background:var(--h4)}.sw.h5{background:var(--h5)}.sw.h6{background:var(--h6)}
/* horizontal bars */
.hb{display:grid;gap:2px;margin:6px 0 4px}
.hb-row{display:grid;grid-template-columns:minmax(150px,32%) minmax(0,1fr);gap:12px;align-items:center;padding:5px 4px;border-radius:6px}
.hb-row:hover{background:var(--bg)}
.hb-lab{font-size:14px;min-width:0;line-height:1.3}
.hb-lab small{display:block;color:var(--muted);font-size:12px;margin-top:1px}
.hb-lab .rk{display:inline-block;min-width:24px;color:var(--muted);font-variant-numeric:tabular-nums}
.hb-track{position:relative;display:grid;gap:3px;min-width:0}
.hb-line{display:flex;align-items:center;gap:6px;min-height:16px;min-width:0}
.hb-bar{display:block;height:14px;width:calc(var(--w) * .74);border-radius:0 4px 4px 0;flex:0 0 auto}
.hb-val{font-size:13px;color:var(--ink);font-variant-numeric:tabular-nums;line-height:1.25;min-width:0;overflow-wrap:anywhere}
.hb-miss{font-size:12px;color:var(--muted);font-style:italic;position:relative;z-index:1;background:var(--surface);padding-right:4px}
.hb-row:hover .hb-miss,.hb-row:hover .hb-val{background:var(--bg)}
.hb-val{position:relative;z-index:1;background:var(--surface);padding-right:3px}
.hb-ref{position:absolute;top:-4px;bottom:-4px;left:calc(var(--x) * .74);border-left:1px dashed var(--ink2);pointer-events:none}
.hb-ref em{position:absolute;top:-14px;left:3px;font-size:11px;color:var(--ink2);font-style:normal;white-space:nowrap}
.hb-crit .hb-row{grid-template-columns:minmax(200px,44%) minmax(0,1fr)}
.hb .hb-row:first-child .hb-ref em{display:inline}
.hb-row:not(:first-child) .hb-ref em{display:none}
.hb-row:first-child{margin-top:12px}
/* tables */
.tscroll{overflow-x:auto;margin:8px 0;-webkit-overflow-scrolling:touch}
.tbl{border-collapse:collapse;width:100%;font-size:14px}
.tbl th,.tbl td{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
.tbl thead th{font-size:12px;color:var(--muted);font-weight:600;text-transform:none;background:var(--surface);position:sticky;top:0}
.tbl tbody th{font-weight:600}
.tbl th small,.heat th small{display:block;color:var(--muted);font-weight:400;font-size:12px}
.tbl td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tbl.small{font-size:13px}
.tbl.small td{min-width:140px}
.heat{border-collapse:separate;border-spacing:2px;font-size:13px}
.heat th{font-weight:600;text-align:left;padding:6px 8px}
.heat thead th{font-size:12px;vertical-align:bottom;min-width:84px}
.heat thead th.corner{color:var(--muted);font-weight:400;min-width:240px}
.heat tbody th{min-width:240px;max-width:320px;font-weight:500}
.heat td{text-align:center;font-variant-numeric:tabular-nums;padding:6px 4px;border-radius:4px;min-width:56px;font-weight:600}
.heat td.h0{background:var(--h0);color:var(--ht0)}.heat td.h1{background:var(--h1);color:var(--ht1)}.heat td.h2{background:var(--h2);color:var(--ht2)}
.heat td.h3{background:var(--h3);color:var(--ht3)}.heat td.h4{background:var(--h4);color:var(--ht4)}.heat td.h5{background:var(--h5);color:var(--ht5)}.heat td.h6{background:var(--h6);color:var(--ht6)}
.heat tr.sum th,.heat tr.sum td{border-top:2px solid var(--line);background:var(--bg);color:var(--ink)}
/* svg chart */
.svgwrap svg{min-width:720px;width:100%;height:auto;display:block}
.svgc .grid{stroke:var(--line);stroke-width:1}
.svgc .axis{stroke:var(--muted);stroke-width:1}
.svgc .bar{fill:var(--c1)}
.svgc .bar.rep{fill:var(--y1)}
.svgc .tick{fill:var(--muted);font-size:12px;font-family:var(--f-body)}
.svgc .tick.yr{fill:var(--ink2);font-weight:600}
.svgc .val{fill:var(--ink);font-size:12px;font-family:var(--f-body)}
/* quotes */
.quotes{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
.qgroup h4{margin:0 0 8px}
blockquote{margin:0 0 8px;padding:8px 12px;border:1px solid var(--line);border-radius:8px}
blockquote p{margin:0;font-size:14px}
cite{display:block;font-style:normal;font-size:12px;color:var(--muted);margin-top:4px}
/* companies */
.comps{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.comp{border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.comp h4{margin:0 0 6px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.comp p{margin:0;font-size:14px;color:var(--ink2)}
.pill{font-size:12px;background:var(--bg);border:1px solid var(--line);border-radius:999px;padding:0 8px;font-weight:600;color:var(--ink)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px}
.grid2>div{min-width:0}
/* wave 2 placeholder */
.w2{border:1.5px dashed var(--w2-line);background:var(--w2-bg);border-radius:10px;padding:14px 16px;margin:10px 0}
.w2-head{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}
.w2 p{margin:6px 0 0;color:var(--ink2);font-size:14px}
.chip-w2{font-size:12px;font-weight:700;color:var(--w2);border:1px solid var(--w2-line);border-radius:999px;padding:1px 10px;letter-spacing:.02em;background:var(--surface)}
/* screenshots */
.fsgrid{display:grid;gap:14px}
.fs{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:16px;border:1px solid var(--line);border-radius:10px;padding:12px}
.fs-imgs{display:flex;gap:10px;align-items:flex-start;min-width:0}
.fs-imgs a{display:block;min-width:0}
.fs-imgs a:first-child{flex:1 1 auto}
.fs-imgs a.mob{flex:0 0 26%}
.fs-imgs img,.shot img,.ideal img{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:var(--bg)}
.fs-txt{min-width:0}
.fs-txt h4{margin:0 0 4px}
.h1q{margin:0 0 8px;font-weight:600}
.fs dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;margin:0;font-size:13px}
.fs dt{color:var(--muted)}
.fs dd{margin:0;min-width:0}
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.shot{margin:0}
.shot figcaption{font-size:12px;color:var(--muted);margin-top:4px}
.ideals{display:grid;gap:12px}
.ideal{display:grid;grid-template-columns:44px minmax(0,1fr) minmax(0,300px);gap:14px;border:1px solid var(--line);border-radius:10px;padding:12px;align-items:start}
.ideal-n{font-family:var(--f-display);font-size:26px;font-weight:700;color:var(--accent);line-height:1}
.ideal h4{margin:0 0 4px}
.ideal p{margin:0 0 6px;font-size:14px}
.ideal .src{color:var(--ink2);font-size:13px}
.ideal figure{margin:0}
.noimg{font-size:12px;color:var(--muted);border:1px dashed var(--line);border-radius:6px;padding:16px;text-align:center}
/* hypotheses */
.hyps{display:grid;gap:14px}
.hyp{border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.hyp header{display:flex;gap:14px;align-items:flex-start}
.hid{font-family:var(--f-display);font-weight:700;font-size:22px;color:var(--surface);background:var(--accent);border-radius:8px;padding:4px 10px;flex:0 0 auto}
.hyp h4{margin:0;font-size:16px;text-wrap:pretty}
.hmeta{margin:4px 0 0;color:var(--muted);font-size:13px}
.hdl{display:grid;grid-template-columns:minmax(150px,220px) minmax(0,1fr);gap:6px 16px;font-size:14px;margin:12px 0 0}
.hdl dt{color:var(--muted)}
.hdl dd{margin:0;min-width:0}
.hdl dt.stop{color:var(--bad);font-weight:600}
.hdl dt.go{color:var(--good);font-weight:600}
.qual{font-weight:600}
/* qa */
.lvl,.st{font-size:12px;border-radius:999px;padding:1px 8px;white-space:nowrap;border:1px solid var(--line)}
.lvl-c{color:var(--bad);border-color:var(--bad)}.lvl-i{color:var(--warn);border-color:var(--w2-line)}.lvl-m{color:var(--muted)}
.st-ok{color:var(--good);border-color:var(--good)}.st-wait{color:var(--warn);border-color:var(--w2-line)}.st-part{color:var(--warn)}.st-open{color:var(--bad);border-color:var(--bad)}
.qa td{min-width:110px}
.dl{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:6px 18px}
.dl li{display:grid;gap:0}
.dl span{font-size:13px;color:var(--muted)}
.clinks{display:flex;flex-wrap:wrap;gap:8px 18px}
.clinks small{display:block;color:var(--muted);font-size:12px}
footer{color:var(--muted);font-size:13px;padding-block:20px 40px;border-top:1px solid var(--line)}
/* tooltip + lightbox */
#tip{position:fixed;z-index:30;max-width:340px;background:var(--ink);color:var(--surface);font-size:13px;line-height:1.4;padding:8px 10px;border-radius:6px;pointer-events:none;box-shadow:0 4px 18px rgba(0,0,0,.18)}
#lb{position:fixed;inset:0;z-index:40;background:rgba(10,14,12,.86);display:flex;align-items:flex-start;justify-content:center;overflow:auto;padding:calc(16px + env(safe-area-inset-top,0px)) max(16px,env(safe-area-inset-right,0px)) 16px max(16px,env(safe-area-inset-left,0px))}
#lb[hidden]{display:none}
.gloss{margin:6px 0 0;font-size:13px}.gloss summary{cursor:pointer;color:var(--muted,#555)}.gloss dl{display:grid;grid-template-columns:max-content 1fr;gap:2px 12px;margin:8px 0 0}.gloss dt{font-weight:600}.gloss dd{margin:0}@media(max-width:600px){.gloss dl{grid-template-columns:1fr}.gloss dd{margin:0 0 6px}}
#lb img{max-width:min(1200px,100%);height:auto;border-radius:6px;background:#fff}
#lb button{position:fixed;top:calc(10px + env(safe-area-inset-top,0px));right:calc(12px + env(safe-area-inset-right,0px));font-size:15px;padding:6px 12px;border-radius:6px;border:0;background:#fff;color:#111;cursor:pointer}
@media (max-width:640px){
  .hb-row,.hb-crit .hb-row{grid-template-columns:minmax(0,1fr);gap:4px}
  .fs{grid-template-columns:1fr}
  .ideal{grid-template-columns:34px minmax(0,1fr)}
  .ideal figure,.ideal .noimg{grid-column:1/-1}
  .hdl{grid-template-columns:1fr;gap:2px}
  .hdl dd{margin-bottom:8px}
  .answers,.quotes,.comps,.grid2{grid-template-columns:1fr}
  .heat tbody th,.heat thead th.corner{min-width:170px}
}

/* v2 additions */
.chip-demo{display:inline-block;font-size:12px;font-weight:700;color:var(--w2);border:1px dashed var(--w2-line);border-radius:999px;padding:0 8px;margin-right:6px;background:var(--w2-bg)}
.svgc .trend{stroke:var(--ink2);stroke-width:1.5;stroke-dasharray:5 4;fill:none}
.svgc .trend.tlog{stroke:var(--c2);stroke-dasharray:2 3;stroke-width:2}
.lg-line{display:inline-block;width:22px;border-top:2px dashed var(--ink2);vertical-align:middle;margin-right:6px}
.lg-line.tlog{border-top:2px dotted var(--c2)}
.svgc .trendlab{fill:var(--ink2)}
.svgc .bar.neg{fill:var(--c2)}
.fins{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,460px),1fr));gap:12px}
.fin{border:1px solid var(--line);border-radius:10px;padding:10px 12px;min-width:0}
.fin h4{margin:0 0 6px;font-size:15px}
.fin h4 small{display:block;font-weight:400;color:var(--muted);font-size:12px}
.fin-g{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}
.fin-g figure{margin:0;min-width:0}
.fin-g figcaption{font-size:11px;color:var(--muted);line-height:1.2;min-height:2.4em}
.svgc.mini{width:100%;height:auto;display:block}
.svgc.mini .val{font-size:15px}
.svgc.mini .tick{font-size:14px}
.mini-empty{font-size:12px;color:var(--muted);padding:20px 0}
.adcards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:12px}
.adcard{border:1px solid var(--line);border-radius:10px;padding:12px 14px;min-width:0}
.adcard h4{margin:0 0 8px}
.ads{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.ad{border-left:3px solid var(--c1);padding:4px 0 4px 10px}
.ad p{margin:0}
.ad-h{color:var(--c1);font-weight:600;font-size:14px}
.ad-t{font-size:14px}
.ad-sl{font-size:12px;color:var(--ink2)}
.ad-m{font-size:12px;color:var(--muted)}
.funnel{list-style:none;padding:0;margin:4px 0 14px;display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:6px}
.funnel li{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;display:grid;gap:2px;align-content:start}
.fn-n{font-family:var(--f-display);font-weight:700;color:var(--accent);font-size:18px;line-height:1}
.fn-t{font-weight:600;font-size:13px}
.fn-v{font-size:12px;color:var(--ink2)}
.stages{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:12px}
.stage{border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.stage h4{margin:0 0 6px}
.stage ul{padding-left:18px;margin:0;display:grid;gap:6px;font-size:14px}
.stage p{margin:0}
.impl{color:var(--accent);font-size:13px}
.variant{border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-top:12px}
.variant h4{margin:0 0 4px}
.oneline{font-weight:600;margin:0 0 6px}
.tbl td.ev{color:var(--ink2);font-size:12px}
.tbl td.dg{font-weight:700;color:var(--accent)}
.mark{display:inline-block;font-size:11px;border:1px dashed var(--w2-line);color:var(--w2);border-radius:4px;padding:0 5px;margin:2px 4px 0 0}
.swot{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.swq{border:1px solid var(--line);border-radius:10px;padding:10px 14px}
.swq h4{margin:0 0 6px}
.swq ul{padding-left:18px;margin:0;font-size:14px;display:grid;gap:4px}
.sw-s{border-top:3px solid var(--c3)}.sw-w{border-top:3px solid var(--c2)}.sw-o{border-top:3px solid var(--c1)}.sw-t{border-top:3px solid var(--bad)}
.mxt td.mx{min-width:150px;vertical-align:top}
.mxt td.mx b{display:block;font-variant-numeric:tabular-nums}
.mxt td.mx small{display:block;font-size:12px;color:var(--ink2)}
.mxt td.mx small.ck{color:var(--muted)}
.mx-ok{background:color-mix(in srgb,var(--good) 14%,transparent)}
.mx-wait{background:color-mix(in srgb,var(--warn) 14%,transparent)}
.mx-part{background:color-mix(in srgb,var(--c2) 16%,transparent)}
.mx-open{background:color-mix(in srgb,var(--bad) 14%,transparent)}
.st-na{color:var(--muted)}
.st-part{border-color:var(--c2);color:var(--c2)}
.upd{margin:4px 0 0;font-size:12px;color:var(--accent)}
.compl td{min-width:120px}
.ovm th[scope=row]{min-width:190px}
.ovm td:nth-child(5){min-width:260px}
.ovm td{min-width:70px}
@media (max-width:640px){.swot{grid-template-columns:1fr}.fin-g{grid-template-columns:repeat(2,minmax(0,1fr))}}

@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
'''

JS = r'''
(function(){
  var tabs=[].slice.call(document.querySelectorAll('.tabs a[data-tab]'));
  var panels=[].slice.call(document.querySelectorAll('.panel'));
  function show(id,scroll){
    var ok=panels.some(function(p){return p.id===id});
    if(!ok) id=panels[0].id;
    panels.forEach(function(p){p.hidden=(p.id!==id)});
    tabs.forEach(function(t){var on=t.dataset.tab===id;t.setAttribute('aria-selected',on?'true':'false');if(on&&t.scrollIntoView){try{t.scrollIntoView({block:'nearest',inline:'nearest'})}catch(e){}}});
    try{localStorage.setItem('zabory-tab',id)}catch(e){}
    if(scroll) window.scrollTo(0,0);
  }
  tabs.forEach(function(t){t.addEventListener('click',function(e){e.preventDefault();show(t.dataset.tab,true);try{history.replaceState(null,'','#'+t.dataset.tab)}catch(err){}})});
  var start=(location.hash||'').replace('#','');
  if(!start){try{start=localStorage.getItem('zabory-tab')||''}catch(e){}}
  show(start,false);
  window.addEventListener('hashchange',function(){show(location.hash.replace('#',''),true)});
  document.querySelectorAll('[data-goto]').forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();show(a.dataset.goto,true)})});
  var tip=document.createElement('div');tip.id='tip';tip.hidden=true;document.body.appendChild(tip);
  function place(x,y){var w=tip.offsetWidth,h=tip.offsetHeight;var nx=Math.min(x+14,window.innerWidth-w-8),ny=y+16;if(ny+h>window.innerHeight-8)ny=y-h-12;tip.style.left=Math.max(8,nx)+'px';tip.style.top=Math.max(8,ny)+'px'}
  document.addEventListener('mouseover',function(e){var el=e.target.closest&&e.target.closest('[data-tip]');if(!el){tip.hidden=true;return}tip.textContent=el.getAttribute('data-tip');tip.hidden=false;place(e.clientX,e.clientY)});
  document.addEventListener('mousemove',function(e){if(!tip.hidden)place(e.clientX,e.clientY)});
  document.addEventListener('scroll',function(){tip.hidden=true},{passive:true});
  var lb=document.createElement('div');lb.id='lb';lb.hidden=true;lb.innerHTML='<button type="button">Закрыть</button><img alt="">';document.body.appendChild(lb);
  var lbimg=lb.querySelector('img');
  document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a.zoom');if(!a)return;e.preventDefault();lbimg.src=a.getAttribute('href');lbimg.alt=(a.querySelector('img')||{}).alt||'';lb.hidden=false;lb.scrollTop=0;lb.querySelector('button').focus()});
  lb.addEventListener('click',function(e){if(e.target!==lbimg){lb.hidden=true;lbimg.removeAttribute('src')}});
  document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!lb.hidden){lb.hidden=true;lbimg.removeAttribute('src')}});
})();
'''

page = f'''<title>Разведка: заборы МО</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="Конкурентная разведка ниши заборов под ключ и откатных ворот в Москве и МО для «Дома гирлянд»: критерии выбора, оценка 10 конкурентов, трафик, офферы, гипотезы теста рекламы.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700&family=Onest:wght@600;700&display=swap">
<style>{CSS}</style>
<header class="top"><div class="wrap">
<p class="eyebrow">Конкурентная разведка · заборы под ключ и откатные ворота · Москва и Московская область</p>
<h1>Как заходить в нишу заборов и откатных ворот</h1>
<p class="meta"><span class="chip-date">Данные актуальны на {DATE}</span><span>Для «Дома гирлянд» · тест рекламы с 22.10.2026</span>
<span>10 компаний полного разбора, 10 облегчённо, 8 специалистов по воротам</span></p>
<p class="legend-tags">Метки в тексте: <span class="tag tag-fact">факт</span> снято с источника <span class="tag tag-concl">вывод</span> следует из цифр
<span class="tag tag-hyp">гипотеза</span> <span class="tag tag-est">оценка</span> расчёт на допущениях · <span class="chip-w2">{WAVE2}</span> — данные ещё не сняты, причина указана в блоке</p>
{GLOSS_HTML}
</div></header>
{nav}
<main class="wrap">{panels}</main>
<footer class="wrap">Данные актуальны на {DATE}. Источники и даты съёма — на вкладке «Источники и данные». Решения остаются за заказчиком: в отчёте факты, закономерности и гипотезы.</footer>
<script>{JS}</script>
'''

PAGE_FIX = [(' (isAdvertised)', ''), ('из облака (Playwright, без входа)', 'без входа'),
            ('не выгружались в главной сессии (бюджет Apify)', 'не выгружались (лимит бюджета выгрузки)'),
            ('— актор не отдаёт.', '— выгрузка не отдаёт.'), ('Актор не отдаёт', 'Выгрузка не отдаёт'), ('актор не отдаёт', 'выгрузка не отдаёт'),
            ('(снимок волны 2)', '(снимок 21.10.2026)'), ('почти нет (волна 2)', 'почти нет (съём 21.10)'), ('не снято в волне 2', 'не снято 21.10'),
            ('(волна 1)', '(съём 20.10.2026)'), ('тем же кодбуком', 'тем же списком тем'), ('(кодбук «консультация»', '(тема «консультация»'),
            ('Источник: ГИР БО,.', 'Источник: ГИР БО.'), ('(сумма H1–H8 )', '(сумма H1–H8)'),
            ('— (у нас 0)', '— (у «Дома гирлянд» 0)'), ('оффер (что обещаем)', 'оффер (обещание)'), ('<th>Что обещаем</th>', '<th>Что обещает «Дом гирлянд»</th>'),
            ('снято в волне 1', 'снято 20.10.2026'), ('повторно не дублировалось', 'повторно не снималось'), ('>в волне 1 стены', '>при съёме 20.10.2026 стены'), ('в волне 1 каналы MAX', 'при съёме 20.10.2026 каналы MAX')]
for _a, _b in PAGE_FIX:
    page = page.replace(_a, _b)
(SITE / 'index.html').write_text(page, encoding='utf-8')

# ---------------------------------------------------------------- report
total = 0
for p in sorted(SITE.rglob('*')):
    if p.is_file():
        total += p.stat().st_size
img_total = sum(p.stat().st_size for p in SIMG.glob('*'))
print(f'index.html: {(SITE / "index.html").stat().st_size / 1024:.0f} KB')
print(f'img: {len(list(SIMG.glob("*")))} files, {img_total / 1024 / 1024:.2f} MB')
print(f'data: {len(list(SDATA.glob("*")))} files, {sum(p.stat().st_size for p in SDATA.glob("*")) / 1024:.0f} KB')
print(f'total: {total / 1024 / 1024:.2f} MB')
