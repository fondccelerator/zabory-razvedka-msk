import asyncio
from playwright.async_api import async_playwright
OUT = '/tmp/claude-0/-home-claude/97f9dc36-7fb1-518c-96b3-65ea34b0a075/scratchpad/raduga_reviews_raw.png'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(proxy={"server": "http://127.0.0.1:34453"})
        pg = await b.new_page(viewport={'width': 1440, 'height': 900}, locale='ru-RU')
        await pg.goto('https://raduga-zaborov.ru/', wait_until='load', timeout=60000)
        fr = pg.locator('iframe[src*="maps-reviews-widget"]')
        await fr.scroll_into_view_if_needed()
        await asyncio.sleep(12)
        await pg.evaluate("for (const e of document.querySelectorAll('body *')) { const p = getComputedStyle(e).position; if (p === 'fixed' || p === 'sticky') e.style.display = 'none'; }")
        await asyncio.sleep(1)
        box = await fr.bounding_box()
        print(box)
        sec = pg.locator('iframe[src*="maps-reviews-widget"]').locator('xpath=ancestor::section[1]')
        target = sec if await sec.count() else fr
        await target.screenshot(path=OUT)
        await b.close()
asyncio.run(main())
