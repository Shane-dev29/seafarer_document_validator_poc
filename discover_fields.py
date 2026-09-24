import sys
import json
from playwright.sync_api import sync_playwright

def scrape_any_form(url):
    with sync_playwright() as p:
        # Launch Playwright Chromium
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"[Playwright] Navigating to: {url}")
        page.goto(url, wait_until="networkidle")

        # Playwright dynamically locates all interactive form fields on the page
        field_elements = page.locator(
            "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='reset']), textarea, select"
        ).all()

        discovered_fields = []
        for el in field_elements:
            if not el.is_visible():
                continue

            # Playwright evaluates DOM properties to extract the label and metadata
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
                    label: labelText || e.getAttribute('aria-label') || e.getAttribute('name') || e.id || 'Unnamed'
                };
            }""")
            discovered_fields.append((el, meta))

        print(f"\n[Playwright] Discovered {len(discovered_fields)} input fields on the live page:\n")
        for i, (_, meta) in enumerate(discovered_fields, 1):
            print(f"  Field {i}:")
            print(f"    - Label      : {meta['label']}")
            print(f"    - Element Tag: <{meta['tag']}>")
            print(f"    - Input Type : {meta['type']}")
            print(f"    - ID / Name  : {meta['id']} / {meta['name']}")

        browser.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://results.unigoa.ac.in/result_be.php?exam=eyJleGFtIjoiQmFjaGVsb3Igb2YgRW5naW5lZXJpbmcgKFNlbWVzdGVyIFZJKSIsImpzb24iOiJCRV9KdW5lMjZfU2VtVkkifQ=="
    scrape_any_form(url)
