from typing import TypedDict, Optional, Dict, Any, List

class VerificationWorkflowState(TypedDict):
    """Shared state for the Maritime Verification LangGraph pipeline."""
    # Folder & Document Ingestion
    folder_path: Optional[str]
    batch_name: Optional[str]
    pdf_path: Optional[str]
    raw_document_text: Optional[str]
    document_matrix: Optional[List[Dict[str, Any]]] # List of {file_name, status, error, doc_type}
    
    # Entity Extraction
    seafarer_profile: Optional[Dict[str, Any]]
    
    # Registry Lookup
    portal_entry: Optional[Dict[str, Any]]
    country_resolved: Optional[str]
    
    # MCP Verifier Check
    has_cached_verifier: Optional[bool]
    
    # Execution & Result
    headless: Optional[bool]
    screencast: Optional[Any]   # ScreencastBroadcaster instance for live WebSocket streaming
    verification_result: Optional[Dict[str, Any]]
    audit_report_path: Optional[str]
    error: Optional[str]
    
    # Progress & State
    current_step: Optional[str]
    step_progress: Optional[int] # e.g. 1 to 5
    status: str # INGESTING, EXTRACTING, LOOKUP_DONE, VERIFYING, COMPLETED, ERROR, MANUAL_VERIFICATION_REQUIRED
