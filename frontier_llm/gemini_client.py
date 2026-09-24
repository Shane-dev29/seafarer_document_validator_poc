import os
import re
from pathlib import Path
from google import genai
from core.config import GEMINI_API_KEY

FRONTIER_VERIFIER_PROMPT = """You are a Senior Browser Automation Engineer writing Playwright Python integration classes.
Your task is to write a Python verification class for automated portal lookup.

Requirements:
1. Inherit from `BaseVerifier` in `verifiers.base_verifier`.
2. Implement `@property def country(self) -> str:` returning the exact country name.
3. Implement `def verify(self, profile: SeafarerProfile, headless: bool = True, screencast = None) -> VerificationResult:`
4. The method must:
   - Launch Playwright Chromium (`headless=headless`).
   - Wrap page with PageRecorder if screencast provided:
     ```python
     if screencast:
         from core.page_recorder import PageRecorder
         page = PageRecorder(browser.new_page(), screencast, interval_sec=0.4)
     else:
         page = browser.new_page()
     ```
   - Navigate to the target portal URL.
   - Fill inputs matching the seafarer's `coc_number`, `cdc_number`, or `dob`.
   - Click search/submit button.
   - Wait for results table to load.
   - Save screenshot to `screenshots/{country.lower()}_result.png`.
   - Return `VerificationResult(status='VERIFIED' or 'COMPLETED', country=self.country, records=[...], raw_text=..., screenshot_path=...)`.
5. Return ONLY valid, executable Python code. Do not include markdown conversational explanations.

Imports to include:
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from core.schemas import SeafarerProfile, VerificationResult
from verifiers.base_verifier import BaseVerifier
"""

class GeminiFrontierClient:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if not self._client:
            key = self.api_key or os.environ.get("GEMINI_API_KEY", "")
            if not key:
                raise ValueError("GEMINI_API_KEY not configured in .env!")
            self._client = genai.Client(api_key=key)
        return self._client

    def generate_verifier_script(self, country: str, portal_url: str, dom_elements: list, text_preview: str) -> str:
        """Uses Gemini Frontier model to write a full Playwright verification script."""
        user_prompt = f"""Target Country: {country}
Portal URL: {portal_url}

Live Form Elements Discovered on Page:
{dom_elements}

Page Text Preview:
{text_preview}
"""
        response = self.client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[FRONTIER_VERIFIER_PROMPT, user_prompt]
        )
        code_text = response.text.strip()
        clean_code = re.sub(r"^```(?:python)?\s*", "", code_text, flags=re.MULTILINE)
        clean_code = re.sub(r"```\s*$", "", clean_code, flags=re.MULTILINE).strip()

        # Validate that response is actually Python code
        if not ("class " in clean_code and "def verify" in clean_code):
            raise ValueError(f"AI response did not contain valid Verifier class: {clean_code[:120]}")

        # Test compile
        compile(clean_code, "<string>", "exec")
        return clean_code

    def solve_captcha(self, image_path: str) -> str:
        """Uses Gemini Multimodal Vision to decode CAPTCHA images."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"CAPTCHA image not found: {image_path}")

        with open(path, "rb") as f:
            img_bytes = f.read()

        response = self.client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                "Return ONLY the exact alphanumeric characters visible in this CAPTCHA image. Do not include spaces, quotes, or explanation.",
                genai.types.Part.from_bytes(data=img_bytes, mime_type="image/png")
            ]
        )
        return response.text.strip()

frontier_client = GeminiFrontierClient()
