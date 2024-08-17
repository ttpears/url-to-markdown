import sys
import asyncio
from playwright.async_api import async_playwright, TimeoutError
import html2text
import os

async def url_to_markdown(url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0"
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="load", timeout=60000)
            except TimeoutError:
                return f"Error: Timeout while loading the page."

            try:
                await page.wait_for_selector("body", timeout=20000)
                await page.wait_for_timeout(5000)
            except TimeoutError:
                return f"Error: Timeout while waiting for page content."

            folder_name = url.replace("://", "_").replace("/", "_")
            folder_path = f'/app/output/{folder_name}'
            os.makedirs(folder_path, exist_ok=True)

            screenshot_path = f'{folder_path}/screenshot.png'
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

            content = await page.content()
            await browser.close()

            h = html2text.HTML2Text()
            h.ignore_links = False
            markdown = h.handle(content)

            return markdown.strip(), folder_path
    except TimeoutError as e:
        return f"Error: {e}", None
    except Exception as e:
        return f"General Error: {e}", None

async def main():
    if len(sys.argv) < 2:
        print("Usage: python converter.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    markdown, folder_path = await url_to_markdown(url)

    if folder_path:
        output_file = f'{folder_path}/content.md'
        with open(output_file, 'w') as f:
            f.write(markdown)

        print(f"Markdown saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
