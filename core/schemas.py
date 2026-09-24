from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SeafarerProfile(BaseModel):
    full_name: Optional[str] = Field(None, description="Full name of seafarer")
    nationality: str = Field(..., description="Nationality / issuing state (e.g., India, Panama, Philippines)")
    dob: Optional[str] = Field(None, description="Date of birth formatted as DD/MM/YYYY or DD-MMM-YYYY")
    cdc_number: Optional[str] = Field(None, description="Continuous Discharge Certificate / Seaman Book number")
    coc_number: Optional[str] = Field(None, description="Certificate of Competency / INDoS number")
    foc_number: Optional[str] = Field(None, description="Flag State Endorsement / FOC number")

class PortalEntry(BaseModel):
    country: str = Field(..., description="Country name")
    url: Optional[str] = Field(None, description="Official verification URL")
    verification_type: str = Field(..., description="Verification type (e.g. OPEN PUBLIC, RESTRICTED, etc.)")
    supports_coc: bool = Field(False, description="Whether CoC verification is supported")
    supports_cdc: bool = Field(False, description="Whether CDC verification is supported")
    has_captcha: bool = Field(False, description="Whether portal requires CAPTCHA resolution")
    authority: Optional[str] = Field(None, description="Official maritime authority / administration")
    notes: Optional[str] = Field(None, description="Operational notes")

class VerificationResult(BaseModel):
    status: str = Field(..., description="Status: VERIFIED, NOT_FOUND, EXPIRED, ERROR")
    country: str
    seafarer_name: Optional[str] = None
    dob: Optional[str] = None
    records: List[Any] = Field(default_factory=list, description="Extracted certificate/verification rows")
    raw_text: Optional[str] = None
    screenshot_path: Optional[str] = None
    error_message: Optional[str] = None
