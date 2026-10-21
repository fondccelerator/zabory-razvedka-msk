# 2ГИС: выдача по запросам в Москве, перехват ответов каталога (items) и скриншот.
import asyncio, sys, os, json, urllib.parse
from playwright.async_api import async_playwright
PROXY = {"server": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:39763")}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
OUT = sys.argv[1]; IMG = sys.argv[2]
QUERIES = sys.argv[3].split("|") if len(sys.argv) > 3 else ["заборы", "установка заборов", "откатные ворота", "забор под ключ"]
PAGES = (2, 3) if len(sys.argv) <= 3 else ()
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(proxy=PROXY)
        ctx = await b.new_context(user_agent=UA, viewport={"width": 1440, "height": 900}, locale="ru-RU")
        for q in QUERIES:
            pg = await ctx.new_page(); caught = []
            async def on_resp(r):
                ct = r.headers.get('content-type', '')
                if 'json' in ct and ('items' in r.url or 'catalog' in r.url or 'search' in r.url):
                    try: caught.append({'url': r.url.split('?')[0], 'json': await r.json()})
                    except Exception: pass
            pg.on("response", on_resp)
            await pg.goto("https://2gis.ru/moscow/search/" + urllib.parse.quote(q), wait_until="domcontentloaded", timeout=60000)
            await pg.wait_for_timeout(9000)
            txt = await pg.evaluate("document.body.innerText")
            slug = q.replace(' ', '_')
            await pg.screenshot(path=f"{IMG}/2gis_{slug}.png")
            # вторая страница выдачи
            for page in PAGES:
                try:
                    await pg.goto("https://2gis.ru/moscow/search/" + urllib.parse.quote(q) + f"/page/{page}", wait_until="domcontentloaded", timeout=60000)
                    await pg.wait_for_timeout(6000)
                    txt += "\n#### PAGE %d\n" % page + await pg.evaluate("document.body.innerText")
                except Exception as e:
                    print('page err', e)
            open(f"{OUT}/2gis_{slug}.txt", "w", encoding="utf-8").write(txt)
            json.dump(caught, open(f"{OUT}/2gis_{slug}_api.json", "w", encoding="utf-8"), ensure_ascii=False)
            print(q, len(txt), len(caught), [c['url'] for c in caught][:6])
            await pg.close()
        await b.close()
asyncio.run(main())
