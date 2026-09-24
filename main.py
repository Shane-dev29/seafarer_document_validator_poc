import sys
import json
import argparse
from pathlib import Path
from orchestrator.workflow import run_seafarer_verification

def main():
    parser = argparse.ArgumentParser(description="Automated Maritime Seafarer Credential Verification System (LangGraph)")
    parser.add_argument("--folder", help="Path to Seafarer document folder to ingest (scans all PDFs/Images)")
    parser.add_argument("--pdf", help="Path to single Seafarer document PDF to ingest via OCR")
    parser.add_argument("--nationality", help="Seafarer nationality (e.g., Indian, Myanmar, Indonesia)")
    parser.add_argument("--name", help="Seafarer full name")
    parser.add_argument("--dob", help="Date of Birth (DD/MM/YYYY)")
    parser.add_argument("--coc", help="CoC / INDoS / Blanko number")
    parser.add_argument("--cdc", help="CDC / Seaman Book number")
    parser.add_argument("--visible", action="store_true", help="Launch real visible browser window on screen")
    args = parser.parse_args()

    folder_path = None
    pdf_path = None
    profile = None

    if args.folder:
        f = Path(args.folder)
        if not f.exists() or not f.is_dir():
            print(f"Error: Folder '{args.folder}' not found.")
            sys.exit(1)
        folder_path = str(f.resolve())
        print(f"\n[Master Pipeline] Ingesting Folder: {folder_path}")
    elif args.pdf:
        p = Path(args.pdf)
        if not p.exists():
            print(f"Error: PDF file '{args.pdf}' not found.")
            sys.exit(1)
        pdf_path = str(p.resolve())
        print(f"\n[Master Pipeline] Ingesting Single PDF: {pdf_path}")
    else:
        profile = {
            "full_name": args.name or "ANUP KAMBOJ",
            "nationality": args.nationality or "Indian",
            "dob": args.dob or "07/09/1992",
            "coc_number": args.coc or "09NL5250",
            "cdc_number": args.cdc or ""
        }
        print(f"\n[Master Pipeline] Starting from Manual Profile: {profile['full_name']} ({profile['nationality']})")

    print("=" * 65)
    print("  EXECUTING AUTONOMOUS LANGGRAPH VERIFICATION PIPELINE")
    print("=" * 65)

    final_state = run_seafarer_verification(
        folder_path=folder_path,
        pdf_path=pdf_path,
        profile=profile,
        headless=not args.visible
    )

    print("\n" + "=" * 25 + " FINAL RESULTS " + "=" * 25)
    print(f"Final Status     : {final_state.get('status')}")
    
    if final_state.get("seafarer_profile"):
        prof = final_state["seafarer_profile"]
        print(f"Seafarer Name    : {prof.get('full_name')}")
        print(f"Nationality      : {prof.get('nationality')}")
        print(f"CoC / Serial No. : {prof.get('coc_number')}")
        print(f"CDC Number       : {prof.get('cdc_number')}")
        print(f"Date of Birth    : {prof.get('dob')}")

    print(f"Country Resolved : {final_state.get('country_resolved')}")

    if final_state.get("document_matrix"):
        matrix = final_state["document_matrix"]
        print(f"\nDocument Ingestion Matrix ({len(matrix)} files):")
        for item in matrix:
            st = item.get("status")
            fn = item.get("file_name")
            err = f" - Error: {item.get('error')}" if item.get("error") else ""
            print(f"  [{st}] {fn}{err}")

    if final_state.get("verification_result"):
        res = final_state["verification_result"]
        print(f"\nPortal Verification Status: {res.get('status')}")
        if res.get("screenshot_path"):
            print(f"Verification Screenshot   : {res.get('screenshot_path')}")

    if final_state.get("audit_report_path"):
        print(f"Saved Audit Report JSON   : {final_state.get('audit_report_path')}")

    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
