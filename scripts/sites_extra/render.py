import asyncio, json, sys, os, pathlib, re
from playwright.async_api import async_playwright
OUT = pathlib.Path('/home/claude/zabory/notes/raw_sites/trust_rendered'); OUT.mkdir(exist_ok=True)
JS = """() => { const r=[]; document.querySelectorAll('img').forEach(i=>r.push(['img', i.currentSrc||i.src||'', i.getAttribute('data-src')||i.getAttribute('data-lazy-src')||'', i.alt||'', i.naturalWidth])); 
document.querySelectorAll('a[href]').forEach(a=>{ if(/\\.(jpe?g|png|webp|pdf)(\\?|$)/i.test(a.href)) r.push(['a', a.href, '', (a.innerText||a.title||'').slice(0,80), 0]);});
document.querySelectorAll('*').forEach(e=>{const b=getComputedStyle(e).backgroundImage; if(b && b.startsWith('url(')) r.push(['bg', b.slice(5,-2), '', (e.className||'').toString().slice(0,60), 0]);});
document.querySelectorAll('iframe').forEach(f=>r.push(['iframe', f.src,'',f.title||'',0])); return r; }"""
async def main():
    jobs=[l.split() for l in open(sys.argv[1]) if l.strip()]
    async with async_playwright() as p:
        b = await p.chromium.launch(proxy={"server":os.environ['HTTPS_PROXY']})
        ctx = await b.new_context(viewport={"width":1440,"height":900}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
        for dom,url in jobs:
            pg = await ctx.new_page()
            try:
                r = await pg.goto(url, wait_until="domcontentloaded", timeout=60000)
                await pg.wait_for_timeout(4000)
                for k in range(12):
                    await pg.mouse.wheel(0,1500); await pg.wait_for_timeout(500)
                await pg.wait_for_timeout(2000)
                items = await pg.evaluate(JS)
                txt = await pg.evaluate("() => document.body.innerText")
                slug = dom+'__'+re.sub(r'[^a-zA-Z0-9]+','_',url.split('://',1)[1].split('/',1)[1] if '/' in url.split('://',1)[1] else '').strip('_')
                json.dump(dict(url=url,status=r.status if r else None,items=items,text=txt),open(OUT/f'{slug}.json','w'),ensure_ascii=False)
                print(slug, r.status if r else None, len(items), len(txt), flush=True)
            except Exception as e:
                print(dom, url, 'ERR', str(e)[:200], flush=True)
            await pg.close()
        await b.close()
asyncio.run(main())
