import sys
import asyncio
from playwright.async_api import async_playwright, TimeoutError
import html2text
import os

async def url_to_markdown(url):
    try:
        async with async_playwright() as p:
            # Run browser in headful mode for more visibility
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},  # Update resolution
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0"
            )
            page = await context.new_page()

            # Log network requests
            page.on("request", lambda request: print(f"Request: {request.url}"))

            # Attempt to go to the URL
            try:
                await page.goto(url, wait_until="load", timeout=60000)  # 60 seconds timeout
            except TimeoutError:
                return f"Error: Timeout while loading the page."

            # Wait for a specific element to ensure content is loaded
            try:
                await page.wait_for_selector("body", timeout=20000)  # Wait up to 20 seconds for body to load
                await page.wait_for_timeout(5000)  # Extra wait time in milliseconds
            except TimeoutError:
                return f"Error: Timeout while waiting for page content."

            # Create a directory for the URL based on hostname and path
            folder_name = url.replace("://", "_").replace("/", "_")
            folder_path = f'/app/output/{folder_name}'
            os.makedirs(folder_path, exist_ok=True)

            # Take a screenshot for debugging purposes
            screenshot_path = f'{folder_path}/screenshot.png'
            await page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

            # Get the page content
            content = await page.content()
            await browser.close()

            # Convert to markdown
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
        print("Usage: python url-to-markdown.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    markdown, folder_path = await url_to_markdown(url)

    if folder_path:
        # Write markdown to file
        output_file = f'{folder_path}/content.md'
        with open(output_file, 'w') as f:
            f.write(markdown)

        print(f"Markdown saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
