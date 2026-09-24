import sys
import json
from playwright.sync_api import sync_playwright

def scrape_any_website(url=None):
    if not url:
        url = input("Enter target website URL: ").strip()
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    with sync_playwright() as p:
        # Launch browser in visible headed mode so the user sees Playwright in action
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"\n[Playwright] Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

        # 1. Playwright dynamically scans the DOM for all visible, interactable input fields
        selector = (
            "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='reset']), "
            "textarea, select"
        )
        fields = page.locator(selector).all()

        discovered = []
        for el in fields:
            if not el.is_visible():
                continue

            meta = el.evaluate("""(e) => {
                let labelText = '';
                if (e.id) {
                    const l = document.querySelector(`label[for="${e.id}"]`);
                    if (l) labelText = l.innerText.trim();
                }
                if (!labelText) {
                    const parent = e.closest('label');
                    if (parent) labelText = parent.innerText.trim();
                }
                return {
                    tag: e.tagName.toLowerCase(),
                    type: e.getAttribute('type') || 'text',
                    id: e.id || '',
                    name: e.getAttribute('name') || '',
                    placeholder: e.getAttribute('placeholder') || '',
                    label: labelText || e.getAttribute('aria-label') || e.getAttribute('placeholder') || e.getAttribute('name') || e.id || 'Unnamed Field'
                };
            }""")
            discovered.append((el, meta))

        print(f"\n[Playwright] Found {len(discovered)} field(s) on the page to fill:\n" + "-"*50)

        # 2. Interactively ask user for each field found by Playwright
        for idx, (el, meta) in enumerate(discovered, 1):
            tag = meta['tag']
            input_type = meta['type']
            label = meta['label']

            if tag == "select":
                options = el.locator("option").all_inner_texts()
                print(f"[{idx}] (Dropdown) {label}")
                print(f"    Options: {', '.join(options)}")
                user_val = input("    Enter choice: ").strip()
                if user_val:
                    try:
                        el.select_option(label=user_val)
                    except Exception:
                        el.select_option(value=user_val)
            elif input_type in ["checkbox", "radio"]:
                user_val = input(f"[{idx}] ({input_type.title()}) Check '{label}'? (y/N): ").strip().lower()
                if user_val in ['y', 'yes']:
                    el.check()
            else:
                user_val = input(f"[{idx}] Enter '{label}': ")
                el.fill(user_val)

        print("-" * 50)

        # 3. Playwright dynamically finds and triggers submission
        submit_btn = page.locator(
            "button[type='submit'], input[type='submit'], button:has-text('Get Result'), button:has-text('Submit'), button:has-text('Search')"
        ).first

        print("\n[Playwright] Submitting form...")
        if submit_btn.count() > 0 and submit_btn.is_visible():
            submit_btn.click()
        else:
            page.keyboard.press("Enter")

        # 4. Wait for response or DOM changes
        print("[Playwright] Waiting for response data...")
        page.wait_for_timeout(3000)

        # 5. Playwright extracts the scraped results
        print("\n" + "="*25 + " EXTRACTED DATA " + "="*25)

        # Attempt to find main result container or tables
        result_container = page.locator("#marksContainer, table, main, article").first
        if result_container.count() > 0:
            extracted_text = result_container.inner_text().strip()
        else:
            extracted_text = page.locator("body").inner_text().strip()

        print(extracted_text)
        print("="*66)

        # Save screenshot
        page.screenshot(path="extracted_result.png")
        print("\n[+] Saved page screenshot to 'extracted_result.png'")

        input("\nPress Enter to exit and close the browser...")
        browser.close()

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://results.unigoa.ac.in/result_be.php?exam=eyJleGFtIjoiQmFjaGVsb3Igb2YgRW5naW5lZXJpbmcgKFNlbWVzdGVyIFZJKSIsImpzb24iOiJCRV9KdW5lMjZfU2VtVkkifQ=="
    scrape_any_website(target_url)
