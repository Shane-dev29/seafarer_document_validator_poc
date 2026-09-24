import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from orchestrator.state import VerificationWorkflowState
from core.ocr_client import ocr_client
from local_llm.extractor import extractor
from local_llm.multi_doc_classifier import multi_doc_classifier
from registry.excel_registry import registry
from mcp_server.registry_service import registry_service
from orchestrator.auto_scraper_agent import auto_scraper_agent
from orchestrator.unlisted_country_researcher import unlisted_country_researcher

def ingestion_and_ocr_node(state: VerificationWorkflowState) -> dict:
    """Step 1: Ingests documents (either single PDF or entire folder) with fast-fail OCR."""
    folder_path_str = state.get("folder_path")
    pdf_path_str = state.get("pdf_path")

    # 1. Folder Ingestion Mode
    if folder_path_str:
        fpath = Path(folder_path_str)
        if fpath.exists() and fpath.is_dir():
            print(f"\n[LangGraph] [Step 1/5] Ingesting seafarer folder: {fpath.name}...")
            all_files = list(fpath.iterdir())
            profile, doc_matrix = multi_doc_classifier.consolidate_seafarer_folder(all_files)
            
            return {
                "batch_name": fpath.name,
                "document_matrix": doc_matrix,
                "seafarer_profile": profile.model_dump(),
                "current_step": "Documents Scanned & Classified",
                "step_progress": 1,
                "status": "INGESTED"
            }

    # 2. Single PDF Mode
    if pdf_path_str:
        p = Path(pdf_path_str)
        print(f"\n[LangGraph] [Step 1/5] Ingesting single document: {p.name}...")
        ocr_data, ocr_error = ocr_client.extract_document_safe(p)
        doc_matrix = [{
            "file_name": p.name,
            "file_size": p.stat().st_size if p.exists() else 0,
            "status": "SUCCESS" if ocr_data else "OCR_FAILED",
            "error": ocr_error,
            "doc_type": "PDF",
            "extracted_data": ocr_data
        }]
        
        if ocr_error:
            return {
                "batch_name": p.stem,
                "document_matrix": doc_matrix,
                "current_step": "OCR Failed on Document",
                "step_progress": 1,
                "error": f"OCR Failed: {ocr_error}",
                "status": "ERROR"
            }

        return {
            "batch_name": p.stem,
            "document_matrix": doc_matrix,
            "raw_document_text": json.dumps(ocr_data) if isinstance(ocr_data, dict) else str(ocr_data),
            "current_step": "OCR Extraction Complete",
            "step_progress": 1,
            "status": "OCR_DONE"
        }

    return {
        "current_step": "Using pre-supplied profile",
        "step_progress": 1,
        "status": "PROFILE_READY"
    }

def extract_profile_node(state: VerificationWorkflowState) -> dict:
    """Step 2: Synthesize SeafarerProfile using local LLM (AI_Local) if not already extracted."""
    if state.get("status") == "ERROR":
        return {}

    if state.get("seafarer_profile"):
        profile_data = state["seafarer_profile"]
        name = profile_data.get("full_name", "Unknown")
        nat = profile_data.get("nationality", "Unknown")
        print(f"[LangGraph] [Step 2/5] Consolidated Profile: {name} | {nat} | CoC: {profile_data.get('coc_number')} | CDC: {profile_data.get('cdc_number')}")
        return {
            "current_step": f"Entity Synthesis: {name} ({nat})",
            "step_progress": 2,
            "status": "PROFILE_READY"
        }

    raw_text = state.get("raw_document_text")
    if not raw_text:
        return {
            "error": "No document text or profile available for entity extraction.",
            "status": "ERROR"
        }

    print("[LangGraph] [Step 2/5] Local Model (AI_Local) extracting Seafarer Profile...")
    try:
        profile = extractor.extract_profile(raw_text)
        return {
            "seafarer_profile": profile.model_dump(),
            "current_step": f"Extracted: {profile.full_name} ({profile.nationality})",
            "step_progress": 2,
            "status": "PROFILE_READY"
        }
    except Exception as e:
        return {
            "error": f"Local model extraction failed: {str(e)}",
            "status": "ERROR"
        }

def lookup_portal_node(state: VerificationWorkflowState) -> dict:
    """Step 3: Resolve official national maritime authority portal from Excel database."""
    if state.get("status") == "ERROR":
        return {}

    profile = state.get("seafarer_profile") or {}
    nationality = profile.get("nationality", "")

    portal = registry.lookup(nationality)
    if not portal or not portal.url:
        country_name = portal.country if portal else nationality
        print(f"[LangGraph] [Step 3/5] No confirmed online portal in Excel for '{nationality}'. Routing to Autonomous Maritime Researcher...")
        return {
            "portal_entry": portal.model_dump() if portal else None,
            "country_resolved": country_name,
            "has_cached_verifier": False,
            "current_step": f"Unlisted Country: {country_name} -> Autonomous Research",
            "step_progress": 3,
            "status": "UNLISTED_COUNTRY"
        }

    print(f"[LangGraph] [Step 3/5] Resolved Maritime Authority: {portal.country} -> {portal.url}")
    return {
        "portal_entry": portal.model_dump(),
        "country_resolved": portal.country,
        "current_step": f"Resolved Portal: {portal.country}",
        "step_progress": 3,
        "error": None,
        "status": "LOOKUP_DONE"
    }

def research_unlisted_country_node(state: VerificationWorkflowState) -> dict:
    """Step 3B: Autonomously searches official channels for unlisted administration."""
    country = state.get("country_resolved", "Unknown")
    profile = state.get("seafarer_profile")

    print(f"\n[LangGraph] Autonomous Frontier Agent researching verification procedures for {country}...")
    research_res = unlisted_country_researcher.research_country(country, seafarer_profile=profile)

    if research_res.get("verifier_script_registered"):
        print(f"[LangGraph] Researcher discovered active online portal and registered verifier for {country}!")
        return {
            "has_cached_verifier": True,
            "current_step": f"Discovered & Registered Verifier for {country}",
            "step_progress": 3,
            "status": "VERIFIER_GENERATED"
        }
    else:
        print(f"[LangGraph] Official manual/email validation guide generated for {country}.")
        return {
            "has_cached_verifier": False,
            "current_step": f"Manual Verification Guide Generated for {country}",
            "step_progress": 5,
            "status": "MANUAL_VERIFICATION_REQUIRED",
            "error": f"Official verification guide generated: {research_res.get('report_markdown_path')}"
        }

def check_cached_verifier_node(state: VerificationWorkflowState) -> dict:
    """Step 4: Check if MCP Verifier Registry has a cached verifier."""
    if state.get("status") in ("ERROR", "UNLISTED_COUNTRY"):
        return {}

    country = state.get("country_resolved", "")
    has_script = registry_service.has_verifier(country)
    return {
        "has_cached_verifier": has_script
    }

def auto_generate_verifier_node(state: VerificationWorkflowState) -> dict:
    """Step 4B: Generate a new Playwright verifier on the fly if cache miss."""
    country = state.get("country_resolved", "")
    portal = state.get("portal_entry") or {}
    portal_url = portal.get("url")

    print(f"\n[LangGraph] Cache Miss: Autonomous Agent inspecting {country} at {portal_url}...")
    success = auto_scraper_agent.generate_and_register_verifier(country, portal_url)

    if success:
        print(f"[LangGraph] Successfully generated and registered verifier for {country}!")
        return {
            "has_cached_verifier": True,
            "current_step": f"Built & Registered Verifier for {country}",
            "step_progress": 4,
            "status": "VERIFIER_GENERATED"
        }
    else:
        return {
            "has_cached_verifier": False,
            "current_step": f"Could not build verifier for {country}",
            "status": "ERROR",
            "error": f"Failed to autonomously build verifier for {country}."
        }

def execute_verifier_node(state: VerificationWorkflowState) -> dict:
    """Step 5: Run the Playwright browser automation against the official portal."""
    country = state.get("country_resolved", "")
    profile = state.get("seafarer_profile") or {}
    headless = state.get("headless", True) if state.get("headless") is not None else True
    screencast = state.get("screencast")  # ScreencastBroadcaster or None

    print(f"\n[LangGraph] [Step 4/5] Executing Browser Automation for {country} (headless={headless}, streaming={screencast is not None})...")
    if screencast:
        screencast.set_label(f"Playwright connecting to {country} portal...")

    result = registry_service.run_verifier(country, profile, headless=headless, screencast=screencast)
    
    return {
        "verification_result": result,
        "current_step": f"Browser Verification Result: {result.get('status', 'DONE')}",
        "step_progress": 4,
        "status": result.get("status", "ERROR"),
        "error": result.get("error_message")
    }

def compile_audit_report_node(state: VerificationWorkflowState) -> dict:
    """Step 6: Consolidate verification result, document matrix, and save audit report JSON."""
    batch_name = state.get("batch_name") or "SEAFARER"
    profile = state.get("seafarer_profile") or {}
    name_clean = (profile.get("full_name") or batch_name).upper().replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report_dir = Path("verified_reports") / f"{name_clean}_{timestamp}"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_payload = {
        "timestamp": datetime.now().isoformat(),
        "batch_name": batch_name,
        "consolidated_profile": profile,
        "document_matrix": state.get("document_matrix") or [],
        "country_resolved": state.get("country_resolved"),
        "verification_status": state.get("status"),
        "verification_result": state.get("verification_result"),
        "error": state.get("error")
    }

    report_file = report_dir / "verification_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    print(f"\n============================================================")
    print(f"  VERIFICATION COMPLETE FOR: {name_clean}")
    print(f"  Final Status: {state.get('status')}")
    print(f"  Saved Audit Report: {report_file.resolve()}")
    print(f"============================================================\n")

    return {
        "audit_report_path": str(report_file.resolve()),
        "current_step": "Verification Complete & Audit Report Saved",
        "step_progress": 5,
        "status": state.get("status")
    }

# Conditional Routers
def route_after_lookup(state: VerificationWorkflowState) -> str:
    if state.get("status") == "ERROR":
        return "compile_audit_report"
    if state.get("status") == "UNLISTED_COUNTRY":
        return "research_unlisted_country"
    return "check_cached_verifier"

def route_verifier_availability(state: VerificationWorkflowState) -> str:
    if state.get("status") in ("ERROR", "MANUAL_VERIFICATION_REQUIRED"):
        return "compile_audit_report"
    if state.get("has_cached_verifier"):
        return "execute_verifier"
    else:
        return "auto_generate_verifier"

# Assemble the Graph
builder = StateGraph(VerificationWorkflowState)

builder.add_node("ingestion_and_ocr", ingestion_and_ocr_node)
builder.add_node("extract_profile", extract_profile_node)
builder.add_node("lookup_portal", lookup_portal_node)
builder.add_node("research_unlisted_country", research_unlisted_country_node)
builder.add_node("check_cached_verifier", check_cached_verifier_node)
builder.add_node("auto_generate_verifier", auto_generate_verifier_node)
builder.add_node("execute_verifier", execute_verifier_node)
builder.add_node("compile_audit_report", compile_audit_report_node)

builder.set_entry_point("ingestion_and_ocr")
builder.add_edge("ingestion_and_ocr", "extract_profile")
builder.add_edge("extract_profile", "lookup_portal")

builder.add_conditional_edges(
    "lookup_portal",
    route_after_lookup,
    {
        "check_cached_verifier": "check_cached_verifier",
        "research_unlisted_country": "research_unlisted_country",
        "compile_audit_report": "compile_audit_report"
    }
)

builder.add_conditional_edges(
    "research_unlisted_country",
    lambda s: "execute_verifier" if s.get("has_cached_verifier") else "compile_audit_report",
    {
        "execute_verifier": "execute_verifier",
        "compile_audit_report": "compile_audit_report"
    }
)

builder.add_conditional_edges(
    "check_cached_verifier",
    route_verifier_availability,
    {
        "execute_verifier": "execute_verifier",
        "auto_generate_verifier": "auto_generate_verifier",
        "compile_audit_report": "compile_audit_report"
    }
)

builder.add_conditional_edges(
    "auto_generate_verifier",
    lambda s: "execute_verifier" if s.get("has_cached_verifier") else "compile_audit_report",
    {
        "execute_verifier": "execute_verifier",
        "compile_audit_report": "compile_audit_report"
    }
)

builder.add_edge("execute_verifier", "compile_audit_report")
builder.add_edge("compile_audit_report", END)

verification_graph = builder.compile()

def run_seafarer_verification(
    folder_path: str = None,
    pdf_path: str = None,
    profile: dict = None,
    headless: bool = True,
    screencast=None
) -> dict:
    """Master helper to run the LangGraph pipeline synchronously."""
    initial_state = {
        "folder_path": folder_path,
        "pdf_path": pdf_path,
        "seafarer_profile": profile,
        "headless": headless,
        "screencast": screencast,   # ScreencastBroadcaster instance or None
        "status": "STARTING",
        "step_progress": 0,
        "current_step": "Initializing LangGraph Pipeline"
    }
    return verification_graph.invoke(initial_state)
