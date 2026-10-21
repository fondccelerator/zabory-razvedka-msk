import asyncio, sys, os
from playwright.async_api import async_playwright
PROXY = {"server": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:39763")}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
OUT = sys.argv[1]
URLS = sys.argv[2:]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(proxy=PROXY)
        ctx = await b.new_context(user_agent=UA, viewport={"width": 1440, "height": 900}, locale="ru-RU")
        for i, u in enumerate(URLS):
            pg = await ctx.new_page()
            try:
                r = await pg.goto(u, wait_until="domcontentloaded", timeout=60000)
                await pg.wait_for_timeout(7000)
                t = await pg.evaluate("document.body.innerText")
                print("==", i, r.status if r else None, pg.url, await pg.title())
                print(t[:600].replace("\n", " | "))
                open(f"{OUT}/probe_{i}.txt", "w", encoding="utf-8").write(pg.url + "\n" + t)
                await pg.screenshot(path=f"{OUT}/probe_{i}.png")
            except Exception as e:
                print("ERR", u, e)
            await pg.close()
        await b.close()
asyncio.run(main())
