# Яндекс Карты: выдача по запросам в Москве, перехват ответов поиска (search API) и текст списка.
import asyncio, sys, os, json, urllib.parse
from playwright.async_api import async_playwright
PROXY = {"server": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:39763")}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
OUT = sys.argv[1]; IMG = sys.argv[2]
QUERIES = ["заборы", "установка заборов", "откатные ворота", "забор под ключ"]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(proxy=PROXY)
        ctx = await b.new_context(user_agent=UA, viewport={"width": 1440, "height": 900}, locale="ru-RU")
        for qi, q in enumerate(QUERIES):
            pg = await ctx.new_page()
            caught = []
            async def on_resp(r):
                if "/maps/api/search" in r.url:
                    try:
                        caught.append(await r.json())
                    except Exception:
                        pass
            pg.on("response", on_resp)
            u = "https://yandex.ru/maps/213/moscow/search/" + urllib.parse.quote(q) + "/"
            await pg.goto(u, wait_until="domcontentloaded", timeout=60000)
            await pg.wait_for_timeout(8000)
            # прокрутка списка для подгрузки
            for _ in range(6):
                await pg.mouse.move(200, 500)
                await pg.mouse.wheel(0, 3000)
                await pg.wait_for_timeout(1500)
            # состояние страницы
            state = await pg.evaluate("""() => { const s=document.querySelector('script.state-view'); return s ? s.textContent : '' }""")
            txt = await pg.evaluate("document.body.innerText")
            slug = q.replace(' ', '_')
            open(f"{OUT}/ymaps_{slug}.txt", "w", encoding="utf-8").write(pg.url + "\n" + txt)
            open(f"{OUT}/ymaps_{slug}_state.json", "w", encoding="utf-8").write(state)
            json.dump(caught, open(f"{OUT}/ymaps_{slug}_api.json", "w", encoding="utf-8"), ensure_ascii=False)
            await pg.mouse.wheel(0, -30000); await pg.wait_for_timeout(1000)
            await pg.screenshot(path=f"{IMG}/yandex_maps_{slug}.png")
            print(q, len(state), len(caught), pg.url[:120])
            await pg.close()
        await b.close()
asyncio.run(main())
