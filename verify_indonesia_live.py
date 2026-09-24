import sys
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from core.schemas import SeafarerProfile, VerificationResult
from local_llm.extractor import extractor
from frontier_llm.gemini_client import frontier_client
from core.page_recorder import PageRecorder

# Sample Indonesian Seafarer Document text for local LLM extraction
SAMPLE_INDONESIAN_DOC_TEXT = """
REPUBLIK INDONESIA
KEMENTERIAN PERHUBUNGAN
DIREKTORAT JENDERAL PERHUBUNGAN LAUT
SERTIFIKAT KEAHLIAN PELAUT (CERTIFICATE OF COMPETENCY)
STCW 1978 AS AMENDED

NAMA PELAUT (NAME OF SEAFARER): AGUS PRATAMA
TEMPAT & TANGGAL LAHIR (POB & DOB): SURABAYA, 14/08/1990
WARGANEGARA (NATIONALITY): INDONESIA
KODE PELAUT (SEAFARER CODE): 6201994520
NOMOR SERTIFIKAT / BLANKO (CERTIFICATE BLANKO NO): 6201994520
JABATAN (CAPACITY): OFFICER IN CHARGE OF NAVIGATIONAL WATCH (OOW)
REGULATION: II/1
TANGGAL TERBIT (DATE OF ISSUE): 10/05/2022
BERLAKU HINGGA (VALID UNTIL): 10/05/2027
"""

def ensure_sample_pdf() -> str:
    """Creates a minimal valid 1-page PDF for upload verification."""
    pdf_path = Path("sample_certificate.pdf")
    if not pdf_path.exists():
        with open(pdf_path, "wb") as f:
            f.write(
                b"%PDF-1.4\n"
                b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
                b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
                b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000098 00000 n\n"
                b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"
            )
    return str(pdf_path.resolve())

def verify_indonesia_reference(profile: SeafarerProfile, visible: bool = True, screencast=None):
    """
    Reference Implementation:
    Demonstrates how to handle:
    1. Input field population (Seafarer Code & Blanko Code)
    2. File attachment (input[type='file'])
    3. Visual CAPTCHA screenshot capture & Frontier Gemini vision decoding
    4. Form submission
    """
    target_url = "https://pelaut.dephub.go.id/index.php/verifikasi"
    upload_doc = ensure_sample_pdf()

    seafarer_code = profile.coc_number or profile.cdc_number or "6201994520"
    blanko_code = profile.coc_number or profile.cdc_number or "6201994520"

    print("\n" + "=" * 65)
    print("  REFERENCE PORTAL AUTOMATION (CAPTCHA + FILE UPLOAD)")
    print("=" * 65)
    print(f"Target URL   : {target_url}")
    print(f"Seafarer Code: {seafarer_code}")
    print(f"Blanko Code  : {blanko_code}")
    print(f"Upload Doc   : {upload_doc}")
    print("-" * 65)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not visible, slow_mo=700 if visible else 0)
        context = browser.new_context()
        raw_page = context.new_page()

        # Wrap with PageRecorder for live streaming if screencast is available
        if screencast:
            page = PageRecorder(raw_page, screencast)
        else:
            page = raw_page

        try:
            print("[Step 1] Opening portal...")
            if screencast:
                page.goto(target_url, label="Opening Indonesia Dephub portal...",
                          wait_until="domcontentloaded", timeout=35000)
                raw_page.wait_for_timeout(2000)
            else:
                page.goto(target_url, wait_until="domcontentloaded", timeout=35000)
                page.wait_for_timeout(2000)

            # 1. Fill Text Inputs
            print(f"[Step 2] Filling SEAFARE_CODE: {seafarer_code}...")
            if screencast:
                page.fill("#SEAFARE_CODE, input[name='SEAFARE_CODE']", seafarer_code,
                          label=f"Filling Seafarer Code: {seafarer_code}")
            else:
                page.locator("#SEAFARE_CODE, input[name='SEAFARE_CODE']").fill(seafarer_code)

            print(f"[Step 2] Filling BLANKO_DISPLAY_CODE: {blanko_code}...")
            if screencast:
                page.fill("#BLANKO_DISPLAY_CODE, input[name='BLANKO_DISPLAY_CODE']", blanko_code,
                          label=f"Filling Blanko Code: {blanko_code}")
            else:
                page.locator("#BLANKO_DISPLAY_CODE, input[name='BLANKO_DISPLAY_CODE']").fill(blanko_code)

            # 2. Attach File
            print(f"[Step 3] Uploading certificate file to #DOKUMEN_SERTIFIKAT...")
            if screencast:
                page.set_input_files("#DOKUMEN_SERTIFIKAT, input[name='DOKUMEN_SERTIFIKAT']", upload_doc,
                                     label="Attaching certificate PDF...")
            else:
                page.set_input_files("#DOKUMEN_SERTIFIKAT, input[name='DOKUMEN_SERTIFIKAT']", upload_doc)

            # 3. Handle Live CAPTCHA
            print("[Step 4] Detecting & Capturing live CAPTCHA image element...")
            captcha_elem = raw_page.locator(".captcha img, img[src*='captcha']").first
            
            if captcha_elem.is_visible():
                captcha_path = "reference_captcha.png"
                captcha_elem.screenshot(path=captcha_path)
                print(f"  [+] CAPTCHA image saved to: {captcha_path}")
                if screencast:
                    screencast.push_frame_from_path(captcha_path, label="Reading CAPTCHA...")

                print("  [+] Decoding CAPTCHA using Frontier Gemini Vision (solve_captcha)...")
                try:
                    captcha_text = frontier_client.solve_captcha(captcha_path)
                    print(f"  [+] Decoded CAPTCHA: '{captcha_text}'")
                    if screencast:
                        page.fill("#captcha, input[name='captcha']", captcha_text,
                                  label=f"Entering CAPTCHA: {captcha_text}")
                    else:
                        page.locator("#captcha, input[name='captcha']").fill(captcha_text)
                except Exception as ce:
                    print(f"  [!] CAPTCHA decode notice: {ce}")

            raw_page.wait_for_timeout(1000)

            # 4. Submit
            print("[Step 5] Submitting form (Cek | Check)...")
            submit_btn = raw_page.locator("button[type='submit'], button:has-text('Cek')").first
            if submit_btn.is_visible():
                if screencast:
                    page.click("button[type='submit'], button:has-text('Cek')",
                               label="Submitting verification form...")
                    raw_page.wait_for_timeout(4000)
                else:
                    submit_btn.click()
                    page.wait_for_timeout(4000)

            screenshot_out = "reference_verification_result.png"
            raw_page.screenshot(path=screenshot_out, full_page=True)
            if screencast:
                screencast.push_frame_from_path(screenshot_out, label="✅ Verification result loaded!")
            print(f"\n[Step 6] Verification completed! Result screenshot: {screenshot_out}")

        finally:
            if visible:
                raw_page.wait_for_timeout(4000)
            browser.close()

def main():
    parser = argparse.ArgumentParser(description="Reference Script: Handling CAPTCHA and File Upload with Playwright")
    parser.add_argument("--visible", action="store_true", default=True, help="Open visible browser window")
    parser.add_argument("--headless", action="store_true", help="Run in background headless mode")
    args = parser.parse_args()
    
    print("\n[Reference] Extracting Seafarer Profile using Local Model (AI_Local)...")
    profile = extractor.extract_profile(SAMPLE_INDONESIAN_DOC_TEXT)
    verify_indonesia_reference(profile, visible=not args.headless)

if __name__ == "__main__":
    main()
