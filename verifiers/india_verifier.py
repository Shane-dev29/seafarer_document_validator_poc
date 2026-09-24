import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from core.schemas import SeafarerProfile, VerificationResult
from verifiers.base_verifier import BaseVerifier


class IndiaVerifier(BaseVerifier):
    @property
    def country(self) -> str:
        return "India"

    def verify(self, profile: SeafarerProfile, headless: bool = True, screencast = None) -> VerificationResult:
        os.makedirs("screenshots", exist_ok=True)
        screenshot_path = f"screenshots/{self.country.lower()}_result.png"

        records = []
        raw_text = ""
        status = "UNVERIFIED"

        # Resolve INDoS and DOB
        indos_no = profile.coc_number or profile.cdc_number or ""
        # Clean special chars from INDoS if any
        indos_no = indos_no.replace(" ", "").upper()
        
        dob_str = profile.dob or ""
        # Ensure format DD/MM/YYYY
        if dob_str and "-" in dob_str:
            dob_str = dob_str.replace("-", "/")

        url = "http://220.156.189.33/esamudraUI/jsp/examination/checker/COCSearch.jsp?hidProcessId=COC"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            
            if screencast:
                from core.page_recorder import PageRecorder
                page = PageRecorder(browser.new_page(), screencast)
            else:
                page = browser.new_page()

            try:
                page.goto(url, timeout=35000)
                page.wait_for_load_state("domcontentloaded")

                # Fill INDoS Number
                if indos_no:
                    page.fill("input[name='txtNo']", indos_no)

                # Fill Date of Birth (remove readonly attribute for robust input)
                if dob_str:
                    page.evaluate(f"""() => {{
                        const el = document.querySelector("input[name='txtDob']");
                        if (el) {{
                            el.removeAttribute('readonly');
                            el.value = '{dob_str}';
                        }}
                    }}""")

                # Click Search button
                page.click("input[name='btnNext']")
                page.wait_for_timeout(3500)

                # Extract result content
                raw_text = page.inner_text("body")
                
                # Extract structured table records
                tables = page.query_selector_all("table")
                for table in tables:
                    rows = table.query_selector_all("tr")
                    for row in rows:
                        cols = [c.inner_text().strip() for c in row.query_selector_all("th, td")]
                        if any(cols) and len(cols) >= 3:
                            records.append(cols)

                if "Master of a Foreign Going Ship" in raw_text or "Verified" in raw_text or "Valid" in raw_text or "First Mate" in raw_text:
                    status = "VERIFIED"
                elif "No Record Found" in raw_text or "Invalid" in raw_text:
                    status = "NOT_FOUND"
                else:
                    status = "COMPLETED"

            except Exception as e:
                print(f"[IndiaVerifier] Error during automation: {e}")
                status = "ERROR"
            finally:
                page.screenshot(path=screenshot_path)
                browser.close()

        return VerificationResult(
            status=status,
            country=self.country,
            seafarer_name=profile.full_name,
            dob=profile.dob,
            records=records,
            raw_text=raw_text,
            screenshot_path=screenshot_path
        )