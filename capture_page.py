import sys
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def capture_website(url: str, output_image: str = "website_screenshot.png"):
    """
    Renders a website, captures a full-page screenshot via Playwright,
    and parses page structure/text using BeautifulSoup.
    
    Note: BeautifulSoup parses HTML/DOM text, while Playwright provides
    the browser rendering engine needed to generate visual screenshots.
    """
    print("=" * 60)
    print("  WEBSITE SCREENSHOT & BEAUTIFULSOUP PARSER")
    print("=" * 60)
    print(f"Target URL   : {url}")
    print(f"Output Image : {output_image}")
    print("-" * 60)

    with sync_playwright() as p:
        print("[1/3] Launching headless browser to render page...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[Warning] Navigation error: {e}")

        # 1. Capture visual screenshot
        print(f"[2/3] Capturing full-page screenshot to '{output_image}'...")
        page.screenshot(path=output_image, full_page=True)

        # 2. Get rendered HTML and parse with BeautifulSoup
        print("[3/3] Parsing rendered HTML with BeautifulSoup...")
        html_content = page.content()
        soup = BeautifulSoup(html_content, "html.parser")

        browser.close()

    # Extract structured metadata with BeautifulSoup
    title = soup.title.string.strip() if soup.title else "No title"
    headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"])[:5]]
    links_count = len(soup.find_all("a"))
    images_count = len(soup.find_all("img"))

    print("\n" + "=" * 25 + " BEAUTIFULSOUP SUMMARY " + "=" * 25)
    print(f"Page Title   : {title}")
    print(f"Total Links  : {links_count}")
    print(f"Total Images : {images_count}")
    print(f"Top Headings :")
    for idx, h in enumerate(headings, 1):
        print(f"  {idx}. {h}")
    print("=" * 60)
    print(f"\n[+] Screenshot saved successfully at: {Path(output_image).resolve()}\n")

def main():
    parser = argparse.ArgumentParser(description="Capture website screenshot and parse structure with BeautifulSoup")
    parser.add_argument("--url", help="Target website URL (e.g., https://example.com)")
    parser.add_argument("--output", default="website_screenshot.png", help="Output PNG file path")
    args = parser.parse_args()

    url = args.url
    if not url:
        url = input("Enter Website URL (e.g., https://example.com): ").strip()

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    capture_website(url, args.output)

if __name__ == "__main__":
    main()
