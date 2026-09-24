import sys
import argparse
import json
from orchestrator.unlisted_country_researcher import unlisted_country_researcher

def main():
    parser = argparse.ArgumentParser(description="Autonomous Maritime Authority Web-Researcher & Verification Guide Generator")
    parser.add_argument("--country", required=True, help="Country or Nationality to research (e.g., 'Myanmar', 'Liberia', 'Vanuatu', 'Bahamas')")
    parser.add_argument("--name", help="Optional seafarer full name")
    parser.add_argument("--coc", help="Optional CoC certificate number")
    parser.add_argument("--cdc", help="Optional CDC / Seaman Book number")
    parser.add_argument("--dob", help="Optional Date of Birth (DD/MM/YYYY)")
    args = parser.parse_args()

    profile = None
    if args.name or args.coc or args.cdc or args.dob:
        profile = {
            "full_name": args.name,
            "coc_number": args.coc,
            "cdc_number": args.cdc,
            "dob": args.dob
        }

    print("=" * 65)
    print("  AUTONOMOUS MARITIME AUTHORITY RESEARCHER & SCRAPER")
    print("=" * 65)

    result = unlisted_country_researcher.research_country(args.country, seafarer_profile=profile)

    print("\n" + "=" * 30 + " SUMMARY " + "=" * 30)
    print(f"Country Researched   : {result.get('country')}")
    print(f"Official Authority   : {result.get('official_authority')}")
    print(f"Official Website     : {result.get('official_domain')}")
    print(f"Public Online Portal : {'YES -> ' + str(result.get('public_verification_url')) if result.get('has_public_online_verifier') else 'NO (Manual / Email Channel Only)'}")
    
    if result.get("manual_verification_procedure"):
        manual = result["manual_verification_procedure"]
        print(f"Verification Email   : {manual.get('contact_email')}")
        print(f"Turnaround / Fees    : {manual.get('fees_and_turnaround')}")

    print(f"Script Registered?   : {result.get('verifier_script_registered')}")
    print(f"Markdown Guide Saved : {result.get('report_markdown_path')}")
    print(f"JSON Output Saved    : {result.get('report_json_path')}")
    print("=" * 69 + "\n")

if __name__ == "__main__":
    main()
