import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        for ch in [None,"chromium"]:
            try:
                b = await p.chromium.launch(proxy={"server":"http://127.0.0.1:34453"}, channel=ch) if ch else await p.chromium.launch(proxy={"server":"http://127.0.0.1:34453"})
                ctx = await b.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36", locale="ru-RU", extra_http_headers={"Accept-Language":"ru-RU,ru;q=0.9"})
                pg = await ctx.new_page()
                r = await pg.goto("https://zaboroff.ru/", wait_until="domcontentloaded", timeout=60000)
                print(ch, r.status, (await pg.content())[:300])
                await b.close()
            except Exception as e: print(ch, 'ERR', e)
asyncio.run(main())
