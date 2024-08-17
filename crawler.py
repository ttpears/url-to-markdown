import asyncio
import os
import signal
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
import argparse
from urllib.parse import urljoin, urlparse

import aiolimiter
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup
import report_generator

VISITED_URLS = set()
TO_VISIT_URLS = []
DOMAIN = ""
LINK_LIMIT = 1000
RATE_LIMIT = aiolimiter.AsyncLimiter(1, 2)  # max concurrency: 1 request every 2 seconds
CONTEXT_MANAGER = None
PAGE = None
RUNNING = True
RESULTS = []
TOTAL_TESTED = 0
RETRY_LIMIT = 3
SITEMAP_URLS = []
CLEAR_COOKIES = False

# User-Agent for Google's web crawler
CRAWLER_USER_AGENT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"


def create_directory_structure(domain):
    base_path = f'/app/output/{domain.replace(":", "_").replace("/", "_")}'
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(f'{base_path}/screenshots', exist_ok=True)
    os.makedirs(f'{base_path}/videos', exist_ok=True)
    os.makedirs(f'{base_path}/reports', exist_ok=True)
    return base_path


def is_same_domain(url):
    return urlparse(url).netloc == DOMAIN


def normalize_url(base, link):
    return urljoin(base, link.split('#')[0]).rstrip('/')


def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for file in filenames:
            fp = os.path.join(dirpath, file)
            total_size += os.path.getsize(fp)
    # Return size in MB
    return total_size / (1024 * 1024)


async def extract_metrics(page, response, start_time, ttfb):
    content = await page.content()
    soup = BeautifulSoup(content, 'html.parser')
    assets_count = len(soup.find_all(['img', 'link', 'script']))
    load_time = time.time() - start_time
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


async def save_sitemap(file_path, urls):
    sitemap_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for url in urls:
        sitemap_lines.append(f"  <url><loc>{url}</loc></url>")
    sitemap_lines.append('</urlset>')

    with open(file_path, 'w') as f:
        f.write('\n'.join(sitemap_lines))


async def fetch_page(url, page, base_path):
    global VISITED_URLS, TOTAL_TESTED, SITEMAP_URLS, CLEAR_COOKIES

    VISITED_URLS.add(url)
    TOTAL_TESTED += 1
    SITEMAP_URLS.append(url)
    SITEMAP_URLS = sorted(set(SITEMAP_URLS))

    if CLEAR_COOKIES:
        await page.context.clear_cookies()

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

        ttfb_start_time = start_time
        response = await page.goto(url, wait_until="load", timeout=60000)
        ttfb = time.time() - ttfb_start_time

        if not response or response.status != 200:
            raise Exception(f"Non-200 or no response: {response}")

        await page.wait_for_selector("body", timeout=20000)

        screenshot_path = f'{base_path}/screenshots/{folder_name}.png'
        Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=screenshot_path)

        content, assets_count, load_time, ttfb = await extract_metrics(page, response, start_time, ttfb)
        links = await extract_links(content, url)

        content_length = len(content) / 1024  # Content length in KB

        result.update({
            "screenshot": screenshot_path,
            "status": "success",
            "response_code": response.status,
            "content_length": content_length,
            "assets_count": assets_count,
            "load_time": load_time,
            "ttfb": ttfb
        })

        sitemap_path = os.path.join(base_path, 'sitemap.xml')
        await save_sitemap(sitemap_path, SITEMAP_URLS)

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
        except Exception:
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
    global DOMAIN, CONTEXT_MANAGER, PAGE, RESULTS, RUNNING, TO_VISIT_URLS
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

        VIDEO_FOLDER = f"{base_path}/videos/"
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
                    TO_VISIT_URLS.extend(new_links - VISITED_URLS)

                    RESULTS.append(result)

                    elapsed_time = str(timedelta(seconds=int(time.time() - start_time)))
                    video_folder_size = get_folder_size(VIDEO_FOLDER)

                    output_string = (
                        f"\r🔗 Testing: {result.get('url', 'Unknown')[:40]:<40} | "
                        f"⏲️ Elapsed: {elapsed_time:<10} | "
                        f"📹 Video: {video_folder_size:.2f}MB"
                    )

                    print(output_string.ljust(100), end="", flush=True)

            await context.close()

            print("\r" + " " * 100, end="\r")

            print(f"Generating report in: {base_path}")
            report_generator.generate_report(RESULTS, base_path, VIDEO_FOLDER)
            await browser.close()
        except Exception as e:
            print(f"\nError during crawl: {e}")
            await handle_exit(None, None)

        return RESULTS


async def handle_exit(sig, frame):
    global CONTEXT_MANAGER, PAGE, RUNNING, RESULTS, DOMAIN, VIDEO_FOLDER
    RUNNING = False
    base_path = f'/app/output/{DOMAIN.replace(":", "_").replace("/", "_")}'
    if CONTEXT_MANAGER:
        await CONTEXT_MANAGER.close()
    report_generator.generate_report(RESULTS, base_path, VIDEO_FOLDER)
    sys.exit(0)


async def main():
    global CLEAR_COOKIES

    def signal_handler(sig, frame):
        asyncio.create_task(handle_exit(sig, frame))

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="A website crawler that generates reports and sitemaps.")
    parser.add_argument("start_url", help="The starting URL for the crawl.")
    parser.add_argument("--clear-cookies", action="store_true", help="Clear cookies between requests.")
    args = parser.parse_args()

    CLEAR_COOKIES = args.clear_cookies

    start_url = args.start_url
    await crawl(start_url)


if __name__ == "__main__":
    asyncio.run(main())
