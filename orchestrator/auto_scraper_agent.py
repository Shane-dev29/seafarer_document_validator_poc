import re
import requests
from playwright.sync_api import sync_playwright
from core.config import LLM_URL, LLM_MODEL, LLM_API_KEY, GEMINI_API_KEY
from mcp_server.registry_service import registry_service
from frontier_llm.gemini_client import frontier_client

class AutoScraperAgent:
    def __init__(self):
        self.local_url = LLM_URL
        self.local_model = LLM_MODEL
        self.local_key = LLM_API_KEY

    def inspect_portal_dom(self, portal_url: str) -> dict:
        """Navigates to the portal using Playwright and extracts the live form structure."""
        print(f"[AutoScraper] Frontier Agent inspecting live DOM at: {portal_url}...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(portal_url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(1500)
            except Exception as e:
                print(f"[AutoScraper] Navigation warning: {e}")

            # Extract inputs and metadata
            form_info = page.evaluate("""() => {
                const inputs = Array.from(document.querySelectorAll("input, select, textarea, button"));
                return inputs.map(el => {
                    let label = '';
                    if (el.id) {
                        const l = document.querySelector(`label[for="${el.id}"]`);
                        if (l) label = l.innerText.trim();
                    }
                    if (!label && el.closest('label')) {
                        label = el.closest('label').innerText.trim();
                    }
                    return {
                        tag: el.tagName.toLowerCase(),
                        type: el.getAttribute('type') || el.tagName.toLowerCase(),
                        name: el.getAttribute('name') || '',
                        id: el.id || '',
                        value: el.getAttribute('value') || '',
                        label: label || el.getAttribute('placeholder') || el.getAttribute('aria-label') || el.name || el.id || ''
                    };
                });
            }""")

            body_snippet = page.locator("body").inner_text()[:1500]
            browser.close()

            return {
                "url": portal_url,
                "elements": form_info,
                "page_text_snippet": body_snippet
            }

    def generate_and_register_verifier(self, country: str, portal_url: str) -> bool:
        """Inspects portal, uses Frontier Gemini model to generate verifier, and registers it in MCP."""
        try:
            # 1. Scrape live DOM
            dom_data = self.inspect_portal_dom(portal_url)

            # 2. Generate Python verifier script
            print(f"[AutoScraper] Calling AI Model to generate verifier script for {country}...")
            clean_code = None
            if GEMINI_API_KEY:
                try:
                    print("[AutoScraper] Using Google Gemini to write Playwright verifier...")
                    clean_code = frontier_client.generate_verifier_script(
                        country=country,
                        portal_url=portal_url,
                        dom_elements=dom_data["elements"],
                        text_preview=dom_data["page_text_snippet"]
                    )
                except Exception as e:
                    print(f"[AutoScraper] Gemini generation error ({e}), falling back to in-house LLM...")

            if not clean_code:
                print("[AutoScraper] Using in-house LiteLLM model for script generation...")
                headers = {"Authorization": f"Bearer {self.local_key}", "Content-Type": "application/json"}
                payload = {
                    "model": self.local_model,
                    "messages": [
                        {"role": "user", "content": f"Write BaseVerifier for {country} at {portal_url}. Elements: {dom_data['elements']}"}
                    ]
                }
                resp = requests.post(self.local_url, headers=headers, json=payload, timeout=90)
                code_raw = resp.json()["choices"][0]["message"]["content"].strip()
                clean_code = re.sub(r"^```(?:python)?\s*", "", code_raw, flags=re.MULTILINE)
                clean_code = re.sub(r"```\s*$", "", clean_code, flags=re.MULTILINE).strip()

            if not clean_code:
                print(f"[AutoScraper] No code generated for {country}")
                return False

            # 3. Register into MCP server
            reg_result = registry_service.register_verifier(country, clean_code)
            print(f"[AutoScraper] Registered verifier: {reg_result['message']}")
            return True
        except Exception as e:
            print(f"[AutoScraper] Error generating/registering verifier for {country}: {e}")
            return False

auto_scraper_agent = AutoScraperAgent()
