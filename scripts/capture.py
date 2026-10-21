"""Съём посадочных: скриншоты (десктоп 1440x900, мобайл 390x844, полная страница),
текст, структура блоков, ссылки, метрики загрузки. Формы не отправляются, клики не делаются.
Запуск: python3 -I capture.py jobs.json [workers]
jobs.json: [{"slug":..., "url":..., "kind": "full|light|gates", "full": true/false}]
"""
import asyncio, json, sys, time, random, pathlib, datetime

ROOT = pathlib.Path('/home/claude/zabory')
IMG = ROOT / 'img' / 'sites'
RAW = ROOT / 'notes' / 'raw_sites'
IMG.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)
PROXY = {"server": "http://127.0.0.1:34453"}
UA_D = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36")
UA_M = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.5 Mobile/15E148 Safari/604.1")

PERF_INIT = """
window.__lcp = 0; window.__cls = 0;
try {
 new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lcp = e.startTime; })
   .observe({type: 'largest-contentful-paint', buffered: true});
 new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
   .observe({type: 'layout-shift', buffered: true});
} catch (e) {}
"""

OUTLINE_JS = r"""
() => {
  const vw = window.innerWidth;
  const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
     return r.height > 0 && r.width > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  // ищем контейнер, у которого больше всего полноширинных детей
  let best = document.body, bestN = 0;
  const all = document.querySelectorAll('body, body *');
  for (const el of all) {
    if (el.children.length < 3) continue;
    let n = 0;
    for (const c of el.children) { const r = c.getBoundingClientRect();
      if (r.width >= vw * 0.85 && r.height >= 80) n++; }
    if (n > bestN) { bestN = n; best = el; }
  }
  const blocks = [];
  for (const c of best.children) {
    const r = c.getBoundingClientRect();
    if (!(r.width >= vw * 0.85 && r.height >= 60) || !vis(c)) continue;
    const y = r.top + window.scrollY;
    const hs = [...c.querySelectorAll('h1,h2,h3,[class*=title],[class*=Title],[class*=head]')]
       .filter(vis).map(h => (h.innerText||'').trim().replace(/\s+/g,' ')).filter(t => t && t.length < 220);
    const btns = [...c.querySelectorAll('button,a[class*=btn],a[class*=button],input[type=submit],[class*=btn],[class*=button]')]
       .filter(vis).map(b => (b.innerText || b.value || '').trim().replace(/\s+/g,' ')).filter(t => t && t.length < 80);
    blocks.push({y: Math.round(y), h: Math.round(r.height), tag: c.tagName, cls: (c.className||'').toString().slice(0,80),
      id: c.id || '', headings: [...new Set(hs)].slice(0,8), buttons: [...new Set(btns)].slice(0,10),
      inputs: c.querySelectorAll('input:not([type=hidden]),textarea,select').length,
      forms: c.querySelectorAll('form').length, iframes: [...c.querySelectorAll('iframe')].map(f=>f.src.slice(0,120)),
      text: (c.innerText||'').replace(/\s+/g,' ').trim().slice(0, 1500)});
  }
  const h = [...document.querySelectorAll('h1,h2,h3')].filter(vis).map(e => ({tag: e.tagName,
     y: Math.round(e.getBoundingClientRect().top + window.scrollY), t: (e.innerText||'').trim().replace(/\s+/g,' ').slice(0,200)}));
  const links = [...document.querySelectorAll('a[href]')].map(a => [(a.innerText||'').trim().replace(/\s+/g,' ').slice(0,80), a.href]);
  const meta = {title: document.title, description: (document.querySelector('meta[name=description]')||{}).content || '',
     canonical: (document.querySelector('link[rel=canonical]')||{}).href || '', h1: [...document.querySelectorAll('h1')].map(e=>(e.innerText||'').trim()),
     height: document.documentElement.scrollHeight, container: best.tagName + '.' + (best.className||'').toString().slice(0,60), containerN: bestN,
     schema: [...document.querySelectorAll('script[type="application/ld+json"]')].map(s => s.innerText.slice(0,300)),
     messengers: [...document.querySelectorAll('a[href]')].map(a=>a.href).filter(u => /wa\.me|whatsapp|t\.me|telegram|vk\.com|max\.ru|viber|youtube|rutube|dzen/.test(u)).slice(0,40),
     tels: [...new Set([...document.querySelectorAll('a[href^="tel:"]')].map(a=>a.getAttribute('href')))].slice(0,5)};
  return {blocks, h, links, meta};
}
"""


async def autoscroll(page, step=700, pause=0.25, max_steps=120):
    last = -1
    for _ in range(max_steps):
        h = await page.evaluate("document.documentElement.scrollHeight")
        y = await page.evaluate("window.scrollY")
        if y + 900 >= h and last == h:
            break
        last = h
        await page.mouse.wheel(0, step)
        await asyncio.sleep(pause)
    await asyncio.sleep(1.2)


async def shoot(browser, job, log):
    slug, url = job['slug'], job['url']
    out = {'slug': slug, 'url': url, 'kind': job.get('kind'), 'date': datetime.date.today().isoformat()}
    # десктоп
    ctx = await browser.new_context(viewport={'width': 1440, 'height': 900}, user_agent=UA_D, locale='ru-RU')
    await ctx.add_init_script(PERF_INIT)
    page = await ctx.new_page()
    page.on('dialog', lambda d: asyncio.ensure_future(d.dismiss()))
    reqs = {'n': 0, 'bytes': 0}
    page.on('response', lambda r: reqs.__setitem__('n', reqs['n'] + 1))
    t0 = time.time()
    try:
        resp = await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        out['status'] = resp.status if resp else None
        out['final_url'] = page.url
        try:
            await page.wait_for_load_state('load', timeout=30000)
        except Exception:
            pass
        out['t_load_s'] = round(time.time() - t0, 1)
        await asyncio.sleep(3)
        if job.get('shot', True):
            await page.screenshot(path=str(IMG / f'{slug}_desktop.png'))
        perf = await page.evaluate("""() => { const n = performance.getEntriesByType('navigation')[0] || {};
            const res = performance.getEntriesByType('resource');
            return {ttfb: n.responseStart, dcl: n.domContentLoadedEventEnd, load: n.loadEventEnd,
              lcp: window.__lcp, cls: window.__cls, n_res: res.length,
              kb: Math.round(res.reduce((a, r) => a + (r.transferSize || 0), 0) / 1024 + (n.transferSize || 0) / 1024)}; }""")
        out['perf_desktop'] = perf
        if job.get('full', True):
            await autoscroll(page)
            await page.evaluate("window.scrollTo(0,0)")
            await asyncio.sleep(1.5)
            data = await page.evaluate(OUTLINE_JS)
            out.update(data)
            out['text'] = await page.evaluate("document.body.innerText")
            try:
                if job.get('fullshot', True):
                    await page.screenshot(path=str(IMG / f'{slug}_full.jpg'), full_page=True, type='jpeg', quality=60)
            except Exception as e:
                out['full_err'] = str(e)[:200]
        else:
            data = await page.evaluate(OUTLINE_JS)
            out.update(data)
            out['text'] = await page.evaluate("document.body.innerText")
    except Exception as e:
        out['error'] = str(e)[:300]
    await ctx.close()
    await asyncio.sleep(random.uniform(2, 3))
    # мобайл
    if job.get('mobile', True):
        ctx = await browser.new_context(viewport={'width': 390, 'height': 844}, user_agent=UA_M, is_mobile=True,
                                        has_touch=True, device_scale_factor=2, locale='ru-RU')
        await ctx.add_init_script(PERF_INIT)
        page = await ctx.new_page()
        try:
            t0 = time.time()
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            try:
                await page.wait_for_load_state('load', timeout=30000)
            except Exception:
                pass
            out['t_load_mobile_s'] = round(time.time() - t0, 1)
            await asyncio.sleep(3)
            await page.screenshot(path=str(IMG / f'{slug}_mobile.png'))
            out['perf_mobile'] = await page.evaluate("""() => { const n = performance.getEntriesByType('navigation')[0] || {};
               return {ttfb: n.responseStart, load: n.loadEventEnd, lcp: window.__lcp, cls: window.__cls,
               mobile_overflow: document.documentElement.scrollWidth > window.innerWidth + 5,
               sw: document.documentElement.scrollWidth}; }""")
        except Exception as e:
            out['mobile_error'] = str(e)[:300]
        await ctx.close()
    (RAW / f'{slug}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    log(f"{slug}: status={out.get('status')} err={out.get('error','')[:80]} blocks={len(out.get('blocks',[]))}")


async def worker(browser, q, log):
    while True:
        try:
            job = q.get_nowait()
        except asyncio.QueueEmpty:
            return
        try:
            log(f"start {job['slug']}")
            await asyncio.wait_for(shoot(browser, job, log), timeout=200)
        except Exception as e:
            log(f"{job['slug']}: FAIL {e}")
        await asyncio.sleep(random.uniform(2, 3))


async def main():
    jobs = json.load(open(sys.argv[1]))
    nw = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    q = asyncio.Queue()
    for j in jobs:
        q.put_nowait(j)
    log = lambda s: print(s, flush=True)
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(proxy=PROXY)
        await asyncio.gather(*[worker(b, q, log) for _ in range(nw)])
        await b.close()

asyncio.run(main())
