import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(proxy={"server":"http://127.0.0.1:34453"})
        pg = await b.new_page(viewport={"width":1440,"height":900}, ignore_https_errors=False)
        r = await pg.goto("https://zaborkin.ru/", wait_until="domcontentloaded", timeout=60000)
        print(r.status, await pg.title())
        await b.close()
asyncio.run(main())
