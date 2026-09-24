import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from playwright.sync_api import sync_playwright
from google import genai
from core.config import GEMINI_API_KEY, LLM_URL, LLM_MODEL, LLM_API_KEY
from orchestrator.auto_scraper_agent import auto_scraper_agent

BASE_DIR = Path(__file__).resolve().parent.parent
RESEARCH_REPORTS_DIR = BASE_DIR / "verified_reports" / "research_reports"
RESEARCH_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

RESEARCH_PROMPT_TEMPLATE = """You are an elite International Maritime Organization (IMO) and STCW regulatory expert.
Research and provide an authoritative, comprehensive validation guide for verifying seafarer documents (Certificate of Competency - CoC, Seaman's Book / Continuous Discharge Certificate - CDC, Flag State Endorsements - FOC, and STCW modular certificates) for: **{country}**.

Provide your analysis in the following structured JSON format ONLY (no conversational preamble or codeblock wrapper):
{{
  "country": "{country}",
  "official_authority": "Exact name of maritime authority / administration",
  "official_domain": "https://...",
  "has_public_online_verifier": true/false,
  "public_verification_url": "https://... (or null if none)",
  "online_verification_fields": ["List of input fields required e.g., Certificate No, DOB, Issue Date"],
  "has_captcha_or_auth": "Details regarding CAPTCHA, login, or public access",
  "manual_verification_procedure": {{
    "contact_email": "Official verification email(s)",
    "department": "Specific department handling verification",
    "phone": "Official phone with country code",
    "postal_address": "Headquarters address",
    "required_documents": ["List of documents required to submit for verification e.g., Certificate scan, Seafarer consent letter"],
    "fees_and_turnaround": "Standard turnaround time and fee requirements"
  }},
  "document_security_features": [
    "Security features to inspect on physical/PDF documents (e.g., QR code, watermark, hologram, serial number format)"
  ],
  "validation_recommendation_steps": [
    "Step 1: ...",
    "Step 2: ...",
    "Step 3: ..."
  ]
}}
"""

class UnlistedCountryResearcher:
    def __init__(self, api_key: str = GEMINI_API_KEY):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key) if api_key else None

    def research_country(self, country: str, seafarer_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Researches maritime verification methods for a country whose portal is not in the database.
        Probes live URLs with Playwright if found, generates an automated verifier if feasible,
        and saves a comprehensive verification guide report.
        """
        print(f"\n[Researcher] Initiating maritime intelligence research for: {country}...")

        # 1. Query Gemini Frontier Model
        prompt = RESEARCH_PROMPT_TEMPLATE.format(country=country)
        raw_text = ""
        if self.client:
            print("[Researcher] Querying Gemini Frontier Intelligence...")
            response = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )
            raw_text = response.text.strip()
        else:
            print("[Researcher] GEMINI_API_KEY not configured. Returning fallback structure.")
            return {"error": "GEMINI_API_KEY missing"}

        # 2. Parse Structured JSON
        clean_json_str = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        clean_json_str = re.sub(r"```\s*$", "", clean_json_str, flags=re.MULTILINE).strip()

        try:
            research_data = json.loads(clean_json_str)
        except Exception as e:
            print(f"[Researcher] Error parsing JSON response: {e}. Raw response snippet: {raw_text[:200]}")
            research_data = {
                "country": country,
                "official_authority": "Maritime Administration",
                "has_public_online_verifier": False,
                "raw_intelligence": raw_text
            }

        # 3. If a public verification URL is discovered, probe live DOM with Playwright
        portal_url = research_data.get("public_verification_url")
        verifier_registered = False

        if portal_url and research_data.get("has_public_online_verifier"):
            print(f"[Researcher] Candidate online verifier found at: {portal_url}")
            print(f"[Researcher] Launching Playwright to probe live DOM and test form accessibility...")
            try:
                dom_result = auto_scraper_agent.inspect_portal_dom(portal_url)
                inputs_found = len(dom_result.get("elements", []))
                print(f"[Researcher] Live DOM inspection successful: Found {inputs_found} interactive elements.")
                
                # Check if we should auto-generate a verifier script
                if inputs_found > 0:
                    print(f"[Researcher] Auto-generating and registering Playwright verifier for {country}...")
                    verifier_registered = auto_scraper_agent.generate_and_register_verifier(country, portal_url)
            except Exception as e:
                print(f"[Researcher] Playwright live probing warning: {e}")

        # 4. Generate Markdown Verification Guide Report
        report_md_path, report_json_path = self._save_reports(country, research_data, verifier_registered, seafarer_profile)
        
        research_data["report_markdown_path"] = str(report_md_path)
        research_data["report_json_path"] = str(report_json_path)
        research_data["verifier_script_registered"] = verifier_registered

        print(f"\n[Researcher] Comprehensive verification report generated:")
        print(f"  -> Markdown Guide: {report_md_path}")
        print(f"  -> JSON Data:     {report_json_path}")
        return research_data

    def _save_reports(self, country: str, data: dict, verifier_registered: bool, profile: Optional[dict]) -> tuple:
        safe_country = country.replace(" ", "_").replace("/", "_").lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        md_file = RESEARCH_REPORTS_DIR / f"{safe_country}_verification_guide_{timestamp}.md"
        json_file = RESEARCH_REPORTS_DIR / f"{safe_country}_verification_guide_{timestamp}.json"

        # Build Markdown content
        md_lines = [
            f"# Maritime Seafarer Document Verification Guide: {data.get('country', country).upper()}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | **Source:** Autonomous Maritime Researcher (Gemini 3.6 Flash & Playwright)",
            "",
            "---",
            "",
            "## 1. Official Maritime Administration",
            f"- **Authority Name:** {data.get('official_authority', 'Not specified')}",
            f"- **Official Website:** [{data.get('official_domain', 'N/A')}]({data.get('official_domain', '#')})",
            f"- **Online Verification Portal Status:** {'✅ AVAILABLE' if data.get('has_public_online_verifier') else '❌ MANUAL / EMAIL ONLY'}",
            "",
        ]

        if data.get("has_public_online_verifier") and data.get("public_verification_url"):
            md_lines.extend([
                "## 2. Public Online Verification Portal",
                f"- **Portal URL:** [{data.get('public_verification_url')}]({data.get('public_verification_url')})",
                f"- **Required Lookup Fields:** {', '.join(data.get('online_verification_fields', []))}",
                f"- **Authentication / CAPTCHA:** {data.get('has_captcha_or_auth', 'None observed')}",
                f"- **Automated Playwright Script:** {'✅ Generated and registered in MCP Registry' if verifier_registered else '⚠️ Manual verification recommended'}",
                ""
            ])

        manual = data.get("manual_verification_procedure", {})
        if manual:
            md_lines.extend([
                "## 3. Official Manual / Email Verification Channel",
                f"- **Responsible Department:** {manual.get('department', 'Seafarer Certification Department')}",
                f"- **Contact Email:** `{manual.get('contact_email', 'N/A')}`",
                f"- **Contact Phone:** `{manual.get('phone', 'N/A')}`",
                f"- **Office Address:** {manual.get('postal_address', 'N/A')}",
                f"- **Turnaround Time & Fees:** {manual.get('fees_and_turnaround', 'N/A')}",
                "",
                "### Required Documents for Email Verification Request:",
            ])
            for doc in manual.get("required_documents", []):
                md_lines.append(f"- [ ] {doc}")
            md_lines.append("")

        security = data.get("document_security_features", [])
        if security:
            md_lines.extend([
                "## 4. Document Authenticity & Security Features",
            ])
            for feat in security:
                md_lines.append(f"- 🛡️ {feat}")
            md_lines.append("")

        steps = data.get("validation_recommendation_steps", [])
        if steps:
            md_lines.extend([
                "## 5. Step-by-Step Verification Protocol for Crew Operations",
            ])
            for idx, step in enumerate(steps, 1):
                md_lines.append(f"{idx}. {step}")
            md_lines.append("")

        if profile:
            md_lines.extend([
                "---",
                "## 6. Contextual Seafarer Profile Evaluated",
                f"- **Seafarer Name:** {profile.get('full_name', 'N/A')}",
                f"- **DOB:** {profile.get('dob', 'N/A')}",
                f"- **CoC Number:** {profile.get('coc_number', 'N/A')}",
                f"- **CDC Number:** {profile.get('cdc_number', 'N/A')}",
                f"- **FOC Number:** {profile.get('foc_number', 'N/A')}",
                ""
            ])

        with open(md_file, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return md_file, json_file

unlisted_country_researcher = UnlistedCountryResearcher()
