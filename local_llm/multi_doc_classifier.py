import json
import re
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from core.config import LLM_URL, LLM_MODEL, LLM_API_KEY
from core.schemas import SeafarerProfile
from core.ocr_client import ocr_client

CLASSIFIER_PROMPT = """You are an expert maritime document classifier and entity extractor.
Analyze the following document content.
Your tasks:
1. Determine the document category: 'COC' (Certificate of Competency), 'CDC' (Continuous Discharge Certificate / Seaman Book), 'PASSPORT', 'FOC' (Flag State Endorsement / Flag of Convenience), or 'OTHER'.
2. Extract the key metadata:
   - doc_type: 'COC', 'CDC', 'PASSPORT', 'FOC', or 'OTHER'
   - doc_number: The primary document or certificate serial number.
   - indos_number: The INDoS number if visible (Indian seafarers only, format like 09NL5250).
   - passport_number: Passport number if visible.
   - full_name: The seafarer's full legal name.
   - nationality: Country or issuing authority of the seafarer.
   - dob: Date of birth (DD/MM/YYYY).
   - issue_date: Date of issue if visible.
   - expiry_date: Date of expiry if visible.

Return ONLY a valid JSON object matching this schema. No markdown wrappers or explanation:
{
  "doc_type": "COC|CDC|PASSPORT|FOC|OTHER",
  "doc_number": "...",
  "indos_number": "...",
  "passport_number": "...",
  "full_name": "...",
  "nationality": "...",
  "dob": "DD/MM/YYYY",
  "issue_date": "...",
  "expiry_date": "..."
}"""

PRIORITY_KEYWORDS = ["coc", "cdc", "passport", "foc", "indos", "competency", "discharge", "chief mate", "aio", "sid", "seaman"]

def _priority_sort_key(path: Path) -> int:
    name_lower = path.stem.lower()
    for kw in PRIORITY_KEYWORDS:
        if kw in name_lower:
            return 0
    return 1

class MultiDocClassifier:
    def __init__(self, url: str = LLM_URL, model: str = LLM_MODEL, api_key: str = LLM_API_KEY):
        self.url = url
        self.model = model
        self.api_key = api_key

    def classify_text_content(self, filename: str, text_or_json: Any) -> Dict[str, Any]:
        """Classifies document text using the local LLM."""
        content_str = json.dumps(text_or_json) if isinstance(text_or_json, dict) else str(text_or_json)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": CLASSIFIER_PROMPT},
                {"role": "user", "content": f"Document Filename: {filename}\nContent:\n{content_str[:4000]}"}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }

        response = requests.post(self.url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        raw = response.json()["choices"][0]["message"]["content"].strip()
        clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        clean = re.sub(r"```\s*$", "", clean, flags=re.MULTILINE).strip()
        
        data = json.loads(clean)
        data["file_name"] = filename
        return data

    def consolidate_seafarer_folder(self, file_paths: List[Path], on_progress=None) -> Tuple[SeafarerProfile, List[Dict[str, Any]]]:
        """
        Ingests all documents in folder with fast-fail OCR policy.
        Documents that fail OCR are recorded in document_matrix without halting the pipeline.
        Returns: (consolidated_profile, document_matrix)
        """
        valid_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
        docs = [p for p in file_paths if p.suffix.lower() in valid_extensions]
        docs.sort(key=lambda p: (_priority_sort_key(p), p.name.lower()))

        total = len(docs)
        doc_matrix = []
        parsed_results = []

        for idx, path in enumerate(docs, 1):
            if on_progress:
                on_progress(f"Scanning document ({idx}/{total}): {path.name}")
            print(f"[MultiDoc] [{idx}/{total}] Ingesting {path.name}...")

            # Fast-Fail OCR Attempt (Zero retry delays)
            ocr_data, ocr_error = ocr_client.extract_document_safe(path)

            if ocr_error or not ocr_data:
                print(f"  [!] OCR failed for {path.name}: {ocr_error}")
                doc_matrix.append({
                    "file_name": path.name,
                    "file_size": path.stat().st_size if path.exists() else 0,
                    "status": "OCR_FAILED",
                    "error": ocr_error or "Unknown OCR Error",
                    "doc_type": "UNREADABLE",
                    "extracted_data": None
                })
                continue

            # Classify with Local Model
            try:
                classified = self.classify_text_content(path.name, ocr_data)
                parsed_results.append(classified)
                dtype = classified.get("doc_type", "OTHER")
                dnum = classified.get("doc_number", "None")
                indos = classified.get("indos_number")
                extra = f" | INDoS: {indos}" if indos else ""
                print(f"  [+] Identified as [{dtype}]: No. {dnum}{extra}")

                doc_matrix.append({
                    "file_name": path.name,
                    "file_size": path.stat().st_size if path.exists() else 0,
                    "status": "SUCCESS",
                    "error": None,
                    "doc_type": dtype,
                    "extracted_data": classified
                })
            except Exception as e:
                print(f"  [!] Classification error on {path.name}: {e}")
                doc_matrix.append({
                    "file_name": path.name,
                    "file_size": path.stat().st_size if path.exists() else 0,
                    "status": "PARSE_ERROR",
                    "error": str(e),
                    "doc_type": "UNKNOWN",
                    "extracted_data": None
                })

        # Consolidate into unified SeafarerProfile
        full_name = None
        nationality = None
        dob = None
        coc_number = None
        cdc_number = None
        foc_number = None
        indos_number = None
        passport_number = None

        for doc in parsed_results:
            d_type = doc.get("doc_type", "").upper()
            d_num = doc.get("doc_number")

            if not full_name and doc.get("full_name"):
                full_name = doc.get("full_name")
            if not nationality and doc.get("nationality"):
                nationality = doc.get("nationality")
            if not dob and doc.get("dob"):
                dob = doc.get("dob")
            if not passport_number and doc.get("passport_number"):
                passport_number = doc.get("passport_number")

            if doc.get("indos_number"):
                indos_number = doc.get("indos_number")

            if d_type == "COC" and d_num:
                coc_number = d_num
            elif d_type == "CDC" and d_num:
                cdc_number = d_num
            elif d_type == "FOC" and d_num:
                foc_number = d_num

        # Indian Seafarers use INDoS as primary CoC search key
        nat_lower = (nationality or "").lower()
        if "india" in nat_lower and indos_number:
            print(f"[MultiDoc] Indian seafarer detected — using INDoS '{indos_number}' as CoC key")
            coc_number = indos_number

        profile = SeafarerProfile(
            full_name=full_name or "Unknown Seafarer",
            nationality=nationality or "Unknown",
            dob=dob,
            coc_number=coc_number,
            cdc_number=cdc_number,
            foc_number=foc_number
        )

        return profile, doc_matrix

multi_doc_classifier = MultiDocClassifier()
