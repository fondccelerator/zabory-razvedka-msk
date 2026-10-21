"""Этап seo, шаг 8: Playwright (мобильная эмуляция 390x844): скриншот первого экрана главной, время загрузки (load, DOMContentLoaded, LCP),
ширина контента против ширины экрана (горизонтальный скролл), число видео-iframe после рендера.
Выход: img/seo/<domain>_home_mobile.png, raw_seo/render.json"""
import os, sys, json, time
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/opt/pw-browsers')
from playwright.sync_api import sync_playwright

DOMS = sys.argv[1:]
OUT = '/home/claude/zabory/raw_seo/render.json'
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
JS = """() => new Promise(resolve => {
  let lcp = null;
  try { new PerformanceObserver(l => { const e = l.getEntries(); lcp = e[e.length-1].startTime; }).observe({type:'largest-contentful-paint', buffered:true}); } catch(e) {}
  setTimeout(() => {
    const t = performance.getEntriesByType('navigation')[0] || {};
    resolve({lcp_ms: lcp ? Math.round(lcp) : null, dcl_ms: Math.round(t.domContentLoadedEventEnd||0), load_ms: Math.round(t.loadEventEnd||0),
      transfer_kb: Math.round(performance.getEntriesByType('resource').reduce((a,r)=>a+(r.transferSize||0),0)/1024 + (t.transferSize||0)/1024),
      requests: performance.getEntriesByType('resource').length + 1,
      scroll_w: document.documentElement.scrollWidth, inner_w: window.innerWidth,
      iframes_video: [...document.querySelectorAll('iframe')].filter(f => /youtube|rutube|vk\\.com|vkvideo|dzen/.test(f.src||f.dataset.src||'')).length,
      video_tags: document.querySelectorAll('video').length});
  }, 2500);
})"""
with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    for d in DOMS:
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1',
                            locale='ru-RU')
        pg = ctx.new_page()
        rec = {'date': time.strftime('%Y-%m-%d')}
        try:
            t0 = time.time()
            pg.goto(f'https://{d}/', wait_until='load', timeout=60000)
            rec['wall_load_s'] = round(time.time() - t0, 1)
            rec.update(pg.evaluate(JS))
            pg.screenshot(path=f'/home/claude/zabory/img/seo/{d}_home_mobile.png')
        except Exception as e:
            rec['error'] = str(e)[:200]
        ctx.close()
        res[d] = rec
        print(d, rec)
        time.sleep(1.5)
    b.close()
json.dump(res, open(OUT, 'w'), ensure_ascii=False, indent=1)
