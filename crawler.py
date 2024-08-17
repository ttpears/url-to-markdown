import sys
import signal
import asyncio
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse
from aiolimiter import AsyncLimiter
from datetime import datetime, timedelta
from pathlib import Path
import time
import json
import report_generator

VISITED_URLS = set()
TO_VISIT_URLS = []
DOMAIN = ""
LINK_LIMIT = 1000
RATE_LIMIT = AsyncLimiter(1, 2)  # max concurrency is 1 request every 2 seconds
CONTEXT_MANAGER = None
VIDEO_PATH = None
PAGE = None
RUNNING = True
RESULTS = []
TOTAL_TESTED = 0
RETRY_LIMIT = 3

# Use a well-known User-Agent string for Google's web crawler
CRAWLER_USER_AGENT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

def create_directory_structure(domain):
    base_path = f'/app/output/{domain.replace(":", "_").replace("/", "_")}'  # Updated path
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(f'{base_path}/screenshots', exist_ok=True)
    os.makedirs(f'{base_path}/videos', exist_ok=True)
    os.makedirs(f'{base_path}/reports', exist_ok=True)
    return base_path

def is_same_domain(url):
    return urlparse(url).netloc == DOMAIN

def normalize_url(base, link):
    return urljoin(base, link.split('#')[0]).rstrip('/')

async def extract_metrics(page, response, start_time):
    content = await page.content()
    soup = BeautifulSoup(content, 'html.parser')
    assets_count = len(soup.find_all(['img', 'link', 'script']))
    load_time = time.time() - start_time
    ttfb = response.headers.get("x-timing-request-start")
    return content, assets_count, load_time, ttfb

async def extract_links(page_content, base_url):
    soup = BeautifulSoup(page_content, 'html.parser')
    links = set()
    for link_tag in soup.find_all('a', href=True):
        link = link_tag['href']
        full_url = normalize_url(base_url, link)
        if is_same_domain(full_url) and full_url not in VISITED_URLS:
            links.add(full_url)
    return links

async def fetch_page(url, page, base_path):
    global VISITED_URLS, TOTAL_TESTED
    VISITED_URLS.add(url)
    TOTAL_TESTED += 1

    result = {
        "url": url,
        "screenshot": None,
        "video": None,
        "status": "fail",
        "response_code": None,
        "content_length": "Unknown",
        "assets_count": 0,
        "load_time": 0,
        "ttfb": 0
    }

    try:
        folder_name = url.replace("://", "_").replace("/", "_")
        start_time = time.time()
        response = await page.goto(url, wait_until="networkidle", timeout=60000)

        if not response or response.status != 200:
            raise Exception(f"Non-200 or no response: {response}")

        await page.wait_for_selector("body", timeout=20000)
        screenshots_path = f'{base_path}/screenshots/{folder_name}.png'

        # Ensure directory exists before saving the screenshot
        Path(screenshots_path).parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=screenshots_path)

        content, assets_count, load_time, ttfb = await extract_metrics(page, response, start_time)
        links = await extract_links(content, url)

        content_length = len(content) / 1024  # Content length in KB

        result.update({
            "screenshot": screenshots_path,
            "status": "success",
            "response_code": response.status,
            "content_length": content_length,
            "assets_count": assets_count,
            "load_time": load_time,
            "ttfb": ttfb
        })

        return links, result

    except TimeoutError:
        return [], result
    except Exception as e:
        result["error"] = str(e)
        return [], result

async def retry_fetch_page(url, page, base_path, retries=RETRY_LIMIT):
    for attempt in range(retries):
        try:
            return await fetch_page(url, page, base_path)
        except Exception as e:
            if attempt == retries - 1:
                VISITED_URLS.remove(url)
                return [], {
                    "url": url,
                    "screenshot": None,
                    "video": None,
                    "status": "fail",
                    "response_code": "Error",
                    "content_length": "Unknown",
                    "assets_count": 0,
                    "load_time": 0,
                    "ttfb": 0
                }

async def crawl(start_url):
    global DOMAIN, CONTEXT_MANAGER, PAGE, RESULTS, VIDEO_PATH, RUNNING, TO_VISIT_URLS
    DOMAIN = urlparse(start_url).netloc
    base_path = create_directory_structure(DOMAIN)
    TO_VISIT_URLS = [normalize_url('', start_url)]
    VISITED_URLS.clear()
    RESULTS = []

    start_time = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 1024},
            user_agent=CRAWLER_USER_AGENT,
            record_video_dir=f"{base_path}/videos/",
            record_video_size={"width": 1280, "height": 1024}
        )
        PAGE = await context.new_page()

        VIDEO_PATH = f"{base_path}/videos/{DOMAIN}.webm"
        CONTEXT_MANAGER = context

        try:
            while TO_VISIT_URLS and len(VISITED_URLS) < LINK_LIMIT:
                if not RUNNING:
                    break
                current_url = TO_VISIT_URLS.pop(0)
                if current_url in VISITED_URLS:
                    continue

                async with RATE_LIMIT:
                    new_links, result = await retry_fetch_page(current_url, PAGE, base_path)
                    for link in new_links:
                        if link not in VISITED_URLS and link not in TO_VISIT_URLS:
                            TO_VISIT_URLS.append(link)
                    RESULTS.append(result)

                    elapsed_time = str(timedelta(seconds=int(time.time() - start_time)))
                    estimated_size = os.path.getsize(VIDEO_PATH) / (1024 * 1024) if os.path.exists(VIDEO_PATH) else 0

                    output_string = (
                        f"\r🔗 Testing: {result.get('url', 'Unknown')[:40]:<40} | "
                        f"⏲️ Elapsed: {elapsed_time:<10} | "
                        f"📹 Video: {estimated_size:.2f}MB"
                    )

                    # Ensure fixed length for line clearing by adding spaces to the end
                    print(output_string.ljust(100), end="", flush=True)

            await context.close()

            # Clear line after completion
            print("\r" + " " * 100, end="\r")

            # Rename the created video file to the meaningful name
            for file in os.listdir(f"{base_path}/videos/"):
                full_path = os.path.join(f"{base_path}/videos/", file)
                if file.endswith(".webm") and os.path.exists(full_path):
                    os.rename(full_path, VIDEO_PATH)
                    print(f"Video saved: {VIDEO_PATH}")
                    break

            print(f"Generating report in: {base_path}")
            report_generator.generate_report(RESULTS, base_path, VIDEO_PATH if os.path.exists(VIDEO_PATH) else None)
            await browser.close()
        except Exception as e:
            print(f"\nError during crawl: {e}")
            await handle_exit(None, None)

        return RESULTS

async def handle_exit(sig, frame):
    global CONTEXT_MANAGER, PAGE, RUNNING, RESULTS, DOMAIN, VIDEO_PATH
    RUNNING = False
    base_path = f'/app/output/{DOMAIN.replace(":", "_").replace("/", "_")}'  # Updated path
    if CONTEXT_MANAGER:
        await CONTEXT_MANAGER.close()
    if PAGE and VIDEO_PATH:
        for file in os.listdir(f"{base_path}/videos/"):
            full_path = os.path.join(f"{base_path}/videos/", file)
            if file.endswith(".webm") and os.path.exists(full_path):
                os.rename(full_path, VIDEO_PATH)
                print(f"Video saved during exit: {VIDEO_PATH}")
                break
    report_generator.generate_report(RESULTS, base_path, VIDEO_PATH if os.path.exists(VIDEO_PATH) else None)
    sys.exit(0)

async def main():
    def signal_handler(sig, frame):
        asyncio.create_task(handle_exit(sig, frame))

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if len(sys.argv) < 2:
        print("Usage: python crawler.py <START_URL>")
        sys.exit(1)

    start_url = sys.argv[1]
    await crawl(start_url)

if __name__ == "__main__":
    asyncio.run(main())
