"""Пересъёмка скриншотов без перекрытий: принять cookies / согласие, закрыть попапы крестиком,
скрыть оставшиеся фиксированные оверлеи (кроме шапки сайта). Формы не отправляются.
Запуск: python3 -I shoot_clean.py jobs.json [workers]
jobs: [{"slug", "url", "full": bool}]  → img/sites/<slug>_desktop.png, _mobile.png, (_full.jpg)
Журнал: notes/raw_sites/reshoot/<slug>.json
"""
import asyncio, json, sys, random, pathlib, datetime

ROOT = pathlib.Path('/home/claude/zabory')
IMG = ROOT / 'img' / 'sites'
LOG = ROOT / 'notes' / 'raw_sites' / 'reshoot'
LOG.mkdir(parents=True, exist_ok=True)
import os
PROXY = {"server": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:34453")}
UA_D = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36")
UA_M = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.5 Mobile/15E148 Safari/604.1")

# 1) согласие с cookies: кнопка с текстом согласия внутри блока, где упоминаются cookie / персональные данные
ACCEPT_JS = r"""
() => {
  const ok = /^(принять|принимаю|принять все|принять всё|согласен|согласна|согласиться|я согласен|ok|ок|хорошо|понятно|понятно!|accept|accept all|got it|закрыть)$/i;
  const ctx = /cookie|куки|cookies|персональн|конфиденциальн|соглашаетесь|метаданн/i;
  const out = [];
  for (const el of document.querySelectorAll('button, a, div[role=button], span, input[type=button], input[type=submit], div')) {
    const t = (el.innerText || el.value || '').trim();
    if (!t || t.length > 25) continue;
    let cityYes = false;
    if (/^да$/i.test(t)) { for (let p = el.parentElement, i = 0; p && i < 4; p = p.parentElement, i++) { if (/Ваш (город|регион)/i.test(p.innerText || '')) { cityYes = true; break; } } }
    if (!ok.test(t) && !cityYes) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (el.closest('form') && el.closest('form').querySelector('input[type=tel],input[name*=phone],input[type=text]')) continue;
    let p = el, hit = cityYes;
    for (let i = 0; i < 6 && p; i++, p = p.parentElement) { if (ctx.test(p.innerText || '')) { hit = true; break; } }
    if (!hit) continue;
    if (el.children.length > 2) continue;
    el.click(); out.push('принято: ' + t);
  }
  return out;
}
"""

# 2) закрыть попапы крестиком: кнопки закрытия внутри фиксированных/модальных контейнеров
CLOSE_JS = r"""
() => {
  const out = [];
  const isOverlay = el => { for (let p = el, i = 0; p && i < 10; p = p.parentElement, i++) {
      const s = getComputedStyle(p); if (s.position === 'fixed' || p.getAttribute('role') === 'dialog' || /modal|popup|popap|overlay|fancybox|quiz|marquiz|callback|widget/i.test(p.className || '')) return true; } return false; };
  const sel = '[class*=close], [class*=Close], [aria-label*=lose], [aria-label*=акрыть], [title*=акрыть], .mfp-close, .fancybox-close-small, .t-popup__close, .modal__close, button';
  for (const el of document.querySelectorAll(sel)) {
    const r = el.getBoundingClientRect(); if (r.width === 0 || r.height === 0 || r.width > 80 || r.height > 80) continue;
    const t = (el.innerText || '').trim();
    const cls = (el.className && el.className.toString()) || '';
    const looksClose = /close|закрыть/i.test(cls + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '')) || /^[×✕✖x]$/i.test(t);
    if (!looksClose || !isOverlay(el)) continue;
    if (/search|menu|nav|toggle|dropdown|bx-aside|e-n-menu/i.test(cls)) continue;  // не трогать поиск и меню
    if (el.closest('[class*=search], [class*=Search], [class*=menu], nav, [class*=pv_]') || /close_ico/.test(cls)) continue;
    try { el.click(); out.push('закрыто: ' + (cls.slice(0, 40) || t)); } catch (e) {}
  }
  return out;
}
"""

# 3) скрыть оставшиеся фиксированные оверлеи, кроме шапки у верхнего края
HIDE_JS = r"""
(mobile) => {
  const out = [], vw = innerWidth, vh = innerHeight;
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if (s.position !== 'fixed') continue;
    if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) continue;
    let r = el.getBoundingClientRect();
    if (r.width < 10 || r.height < 10) {  // нулевой контейнер с видимыми потомками (чат-виджеты)
      let big = null; let n = 0;
      for (const c of el.querySelectorAll('*')) { if (++n > 300) break; const cr = c.getBoundingClientRect(); if (cr.width > 50 && cr.height > 50) { big = cr; break; } }
      if (!big) continue; r = big;
    }
    const txt = ((el.innerText || el.textContent || '') + '').replace(/\s+/g, ' ').trim();
    const cookieBar = /используем (файлы )?cookie|обрабатываем cookie|cookie-файл|файлы cookie/i.test(txt.slice(0, 150)) && r.height < 300;
    const header = r.top <= 5 && r.height < (mobile ? 170 : 360) && r.width >= vw * 0.9 && !cookieBar;
    if (header) continue;
    if (el.parentElement && getComputedStyle(el.parentElement).position === 'fixed') continue;
    el.setAttribute('data-hidden-by-shoot', '1'); el.style.setProperty('display', 'none', 'important');
    if (r.width * r.height > vw * vh * 0.5) el.remove();  // крупные оверлеи удаляем, чтобы скрипт сайта не показал их снова
    out.push(`скрыт ${s.position} ${Math.round(r.width)}×${Math.round(r.height)} @${Math.round(r.top)}: ${txt.slice(0, 60)}`);
  }
  for (const el of document.querySelectorAll('.popover.show, [class*=geo-popup], [class*=city-confirm]')) { el.style.setProperty('display', 'none', 'important'); out.push('скрыт попап выбора региона'); }
  for (const el of document.querySelectorAll('.pv_wrap, [class*=venyoo]')) { el.remove(); out.push('удалён чат Venyoo'); }
  // чат-виджеты и кнопки обратного звонка, которые живут во вложенных fixed-контейнерах нулевого размера
  const W = 'jdiv, [id*=jivo], [class*=jivo], [id^=jvlabel], .b24-widget-button-wrapper, [class*=callback], [id*=callback], [class*=widget-button], [class*=envybox], [class*=roistat], [class*=chat-widget], [class*=chatra], [id*=chatra], [class*=wa-widget], [class*=whatsapp-widget], [class*=pulse], [class*=phone-widget], [class*=call-btn], [class*=uis-]';
  for (const el of document.querySelectorAll(W)) {
    let top = null; for (let p = el; p && p !== document.body; p = p.parentElement) { if (getComputedStyle(p).position === 'fixed') top = p; }
    if (!top || top.style.display === 'none') continue;
    const tr = top.getBoundingClientRect();
    if (tr.top <= 2 && tr.width >= vw * 0.9 && tr.height < (mobile ? 170 : 360)) continue;  // шапка сайта
    if (tr.width >= vw * 0.9 && tr.height >= vh * 0.5) continue;  // крупные контейнеры не трогаем
    top.style.setProperty('display', 'none', 'important'); out.push(`скрыт виджет ${Math.round(tr.width)}×${Math.round(tr.height)}: ` + ((top.id || top.className || top.tagName) + '').slice(0, 40));
  }
  for (const e of [document.documentElement, document.body]) { if (e.style.overflow === 'hidden') e.style.overflow = ''; }  // снять блокировку прокрутки от модалок
  return out;
}
"""


async def clean(page, mobile, log):
    for step in range(2):
        try:
            log += await page.evaluate(ACCEPT_JS)
        except Exception as e:
            log.append(f'accept err {str(e)[:60]}')
        await asyncio.sleep(0.8)
        try:
            log += await page.evaluate(CLOSE_JS)
        except Exception as e:
            log.append(f'close err {str(e)[:60]}')
        try:
            await page.keyboard.press('Escape')
        except Exception:
            pass
        await asyncio.sleep(random.uniform(2, 3))
    try:
        log += await page.evaluate(HIDE_JS, mobile)
    except Exception as e:
        log.append(f'hide err {str(e)[:60]}')
    await asyncio.sleep(0.5)


async def autoscroll(page):
    last = -1
    for _ in range(120):
        h = await page.evaluate("document.documentElement.scrollHeight")
        y = await page.evaluate("window.scrollY")
        if y + 900 >= h and last == h:
            break
        last = h
        await page.mouse.wheel(0, 700)
        await asyncio.sleep(0.25)
    await asyncio.sleep(1.5)


async def shoot(browser, job):
    slug, url = job['slug'], job['url']
    rec = {'slug': slug, 'url': url, 'date': datetime.date.today().isoformat(), 'desktop': [], 'mobile': [], 'full': []}
    for mode in ('desktop', 'mobile'):
        kw = dict(viewport={'width': 1440, 'height': 900}, user_agent=UA_D, locale='ru-RU') if mode == 'desktop' else \
            dict(viewport={'width': 390, 'height': 844}, user_agent=UA_M, is_mobile=True, has_touch=True, device_scale_factor=2, locale='ru-RU')
        ctx = await browser.new_context(**kw)
        page = await ctx.new_page()
        page.on('dialog', lambda d: asyncio.ensure_future(d.dismiss()))
        for pat in job.get('block', []):  # не загружать сторонний чат-виджет, который нельзя закрыть
            await page.route(pat, lambda route: route.abort())
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            try:
                await page.wait_for_load_state('load', timeout=30000)
            except Exception:
                pass
            await asyncio.sleep(job.get('wait', 3))
            await clean(page, mode == 'mobile', rec[mode])
            await page.evaluate("window.scrollTo(0,0)")
            await asyncio.sleep(2.5)
            rec[mode] += await page.evaluate(HIDE_JS, mode == 'mobile')  # виджеты, загрузившиеся с задержкой
            await page.add_style_tag(content='[class^="pv_"], [class*=" pv_"], jdiv, .popover.show {display: none !important}')
            await asyncio.sleep(0.5)
            rec[mode] += await page.evaluate(HIDE_JS, mode == 'mobile')
            await page.screenshot(path=str(IMG / f'{slug}_{mode}.png'))
            if mode == 'desktop' and job.get('full'):
                await autoscroll(page)
                await clean(page, False, rec['full'])  # попапы по прокрутке
                await page.evaluate("window.scrollTo(0,0)")
                await asyncio.sleep(1.5)
                await page.screenshot(path=str(IMG / f'{slug}_full.jpg'), full_page=True, type='jpeg', quality=60)
        except Exception as e:
            rec[mode].append('ОШИБКА ' + str(e)[:200])
        await ctx.close()
        await asyncio.sleep(random.uniform(2, 3))
    (LOG / f'{slug}.json').write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print(slug, 'D', len(rec['desktop']), 'M', len(rec['mobile']), 'F', len(rec['full']), flush=True)


async def worker(b, q):
    while not q.empty():
        job = q.get_nowait()
        try:
            await asyncio.wait_for(shoot(b, job), timeout=300)
        except Exception as e:
            print(job['slug'], 'FAIL', e, flush=True)


async def main():
    jobs = json.load(open(sys.argv[1]))
    q = asyncio.Queue()
    for j in jobs:
        q.put_nowait(j)
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(proxy=PROXY)
        await asyncio.gather(*[worker(b, q) for _ in range(int(sys.argv[2]) if len(sys.argv) > 2 else 3)])
        await b.close()

asyncio.run(main())
