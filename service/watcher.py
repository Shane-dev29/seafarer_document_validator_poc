import time
import json
import shutil
import csv
from pathlib import Path
from datetime import datetime
from orchestrator.workflow import run_seafarer_verification

BASE_DIR = Path(__file__).resolve().parent.parent
INCOMING_DIR = BASE_DIR / "incoming_docs"
PROCESSED_DIR = BASE_DIR / "processed_docs"
REPORTS_DIR = BASE_DIR / "verified_reports"

INCOMING_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

AUDIT_CSV = REPORTS_DIR / "audit_summary.csv"

def init_audit_log():
    if not AUDIT_CSV.exists():
        with open(AUDIT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "Batch / Folder", "Seafarer Name", "Nationality",
                "CoC No", "CDC No", "Status", "Records Found", "Report Path"
            ])

def log_audit(batch_name: str, profile: dict, result: dict, report_path: str):
    with open(AUDIT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            batch_name,
            profile.get("full_name", "Unknown"),
            profile.get("nationality", "Unknown"),
            profile.get("coc_number", ""),
            profile.get("cdc_number", ""),
            result.get("status", "ERROR") if result else "ERROR",
            len(result.get("records", [])) if result else 0,
            report_path
        ])

def process_seafarer_batch(batch_folder_or_files):
    """Processes a batch of documents (COC, CDC, FOC) for one seafarer via LangGraph."""
    if isinstance(batch_folder_or_files, Path) and batch_folder_or_files.is_dir():
        batch_dir = batch_folder_or_files
        folder_path = str(batch_dir.resolve())
        pdf_path = None
        batch_name = batch_dir.name
    else:
        batch_dir = None
        folder_path = None
        pdf_path = str(batch_folder_or_files.resolve())
        batch_name = batch_folder_or_files.stem

    print("\n" + "#" * 60)
    print(f"  WATCHER DETECTED ARRIVAL: {batch_name}")
    print("#" * 60)

    # Run unified LangGraph pipeline
    final_state = run_seafarer_verification(
        folder_path=folder_path,
        pdf_path=pdf_path,
        headless=True
    )

    profile = final_state.get("seafarer_profile") or {}
    result = final_state.get("verification_result") or {}
    report_path = final_state.get("audit_report_path", "")

    # Log to CSV audit trail
    log_audit(batch_name, profile, result, report_path)

    # Move processed documents to processed_docs/
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_processed_dir = PROCESSED_DIR / f"{batch_name}_{timestamp_str}"
    
    try:
        if batch_dir and batch_dir.exists():
            shutil.move(str(batch_dir), str(target_processed_dir))
        elif pdf_path and Path(pdf_path).exists():
            target_processed_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(pdf_path, str(target_processed_dir / Path(pdf_path).name))
    except Exception as e:
        print(f"[Watcher Notice] Archiving document notice: {e}")

def run_watcher(poll_interval: int = 5):
    """Continuously monitors incoming_docs/ and processes new seafarer arrivals."""
    init_audit_log()
    print("=" * 60)
    print("  MARITIME SEAFARER DROPZONE WATCHER ACTIVE (LangGraph Integrated)")
    print(f"  Drop seafarer folders or PDFs into:")
    print(f"  -> {INCOMING_DIR.resolve()}")
    print("=" * 60)

    while True:
        try:
            # Check for subdirectories (seafarer folders)
            subdirs = [p for p in INCOMING_DIR.iterdir() if p.is_dir()]
            for sd in subdirs:
                process_seafarer_batch(sd)

            # Check for loose PDFs in incoming_docs root
            loose_pdfs = list(INCOMING_DIR.glob("*.pdf")) + list(INCOMING_DIR.glob("*.jpg"))
            for doc in loose_pdfs:
                process_seafarer_batch(doc)

            time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\n[Watcher] Stopped by user.")
            break
        except Exception as e:
            print(f"[Watcher Error]: {e}")
            time.sleep(poll_interval)

if __name__ == "__main__":
    run_watcher()
