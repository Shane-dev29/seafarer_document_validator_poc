import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from core.schemas import SeafarerProfile, VerificationResult
from verifiers.base_verifier import BaseVerifier
from frontier_llm.gemini_client import frontier_client


class IndonesiaVerifier(BaseVerifier):
    @property
    def country(self) -> str:
        return "Indonesia"

    def _ensure_sample_pdf(self) -> str:
        sample_path = Path("sample_certificate.pdf")
        if not sample_path.exists():
            with open(sample_path, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n")
        return str(sample_path.resolve())

    def verify(self, profile: SeafarerProfile, headless: bool = True, screencast = None) -> VerificationResult:
        os.makedirs("screenshots", exist_ok=True)
        screenshot_path = f"screenshots/{self.country.lower()}_result.png"

        target_url = "https://pelaut.dephub.go.id/index.php/verifikasi"
        upload_doc = self._ensure_sample_pdf()

        # Resolve seafarer / blanko code
        seafarer_code = profile.coc_number or profile.cdc_number or ""
        blanko_code = profile.coc_number or profile.cdc_number or ""

        records = []
        raw_text = ""
        status = "UNVERIFIED"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            raw_page = browser.new_page()

            if screencast:
                from core.page_recorder import PageRecorder
                page = PageRecorder(raw_page, screencast)
            else:
                page = raw_page

            try:
                if screencast:
                    page.goto(target_url, label="Opening Indonesia Dephub portal...", timeout=35000)
                else:
                    page.goto(target_url, timeout=35000)
                raw_page.wait_for_load_state("domcontentloaded")
                raw_page.wait_for_timeout(1500)

                # 1. Fill Text Inputs
                if seafarer_code:
                    if screencast:
                        page.fill("#SEAFARE_CODE, input[name='SEAFARE_CODE']", seafarer_code,
                                  label=f"Filling Seafarer Code: {seafarer_code}")
                    else:
                        page.locator("#SEAFARE_CODE, input[name='SEAFARE_CODE']").fill(seafarer_code)

                if blanko_code:
                    if screencast:
                        page.fill("#BLANKO_DISPLAY_CODE, input[name='BLANKO_DISPLAY_CODE']", blanko_code,
                                  label=f"Filling Blanko Code: {blanko_code}")
                    else:
                        page.locator("#BLANKO_DISPLAY_CODE, input[name='BLANKO_DISPLAY_CODE']").fill(blanko_code)

                # 2. Attach File
                if screencast:
                    page.set_input_files("#DOKUMEN_SERTIFIKAT, input[name='DOKUMEN_SERTIFIKAT']", upload_doc,
                                         label="Attaching certificate PDF...")
                else:
                    page.set_input_files("#DOKUMEN_SERTIFIKAT, input[name='DOKUMEN_SERTIFIKAT']", upload_doc)

                # 3. Handle CAPTCHA with Vision AI
                captcha_elem = raw_page.locator(".captcha img, img[src*='captcha']").first
                if captcha_elem.is_visible():
                    captcha_temp = "screenshots/temp_indonesia_captcha.png"
                    captcha_elem.screenshot(path=captcha_temp)
                    if screencast:
                        screencast.push_frame_from_path(captcha_temp, label="Decoding visual CAPTCHA...")

                    try:
                        captcha_text = frontier_client.solve_captcha(captcha_temp)
                        print(f"[IndonesiaVerifier] Decoded CAPTCHA: '{captcha_text}'")
                        if screencast:
                            page.fill("#captcha, input[name='captcha']", captcha_text,
                                      label=f"Entering CAPTCHA: {captcha_text}")
                        else:
                            page.locator("#captcha, input[name='captcha']").fill(captcha_text)
                    except Exception as ce:
                        print(f"[IndonesiaVerifier] CAPTCHA decode warning: {ce}")

                raw_page.wait_for_timeout(1000)

                # 4. Submit
                submit_btn = raw_page.locator("button[type='submit'], button:has-text('Cek')").first
                if submit_btn.is_visible():
                    if screencast:
                        page.click("button[type='submit'], button:has-text('Cek')",
                                   label="Submitting verification form...")
                    else:
                        submit_btn.click()
                    raw_page.wait_for_timeout(4000)

                # 5. Extract results
                raw_text = raw_page.inner_text("body")
                
                tables = raw_page.query_selector_all("table")
                for table in tables:
                    rows = table.query_selector_all("tr")
                    for row in rows:
                        cols = [c.inner_text().strip() for c in row.query_selector_all("th, td")]
                        if any(cols):
                            records.append(cols)

                if "Data Tidak ditemukan" in raw_text or "Tidak Ditemukan" in raw_text:
                    status = "NOT_FOUND"
                elif records or "Valid" in raw_text or "Sertifikat Ditemukan" in raw_text:
                    status = "VERIFIED"
                else:
                    status = "COMPLETED"

            except Exception as e:
                print(f"[IndonesiaVerifier] Error during verification: {e}")
                status = "ERROR"
            finally:
                raw_page.screenshot(path=screenshot_path, full_page=True)
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
