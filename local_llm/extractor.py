import json
import re
import requests
from typing import Dict, Any, Optional
from core.config import LLM_URL, LLM_MODEL, LLM_API_KEY
from core.schemas import SeafarerProfile

SYSTEM_PROMPT = """You are an expert maritime document intelligence model.
Given raw OCR text from a seafarer's document (such as CDC, COC, Passport, or Certificate of Competency), extract the following key entities:
1. full_name: The full legal name of the seafarer.
2. nationality: The country or nationality of the seafarer (e.g., India, Panama, Philippines).
3. dob: Date of birth formatted as DD/MM/YYYY.
4. cdc_number: Continuous Discharge Certificate or Seaman Book number.
5. coc_number: Certificate of Competency or INDoS number.
6. foc_number: Flag of Convenience / Endorsement number if applicable.

Return ONLY a valid JSON object matching this schema. Do not include markdown explanation, code blocks, or extra text:
{
  "full_name": "...",
  "nationality": "...",
  "dob": "DD/MM/YYYY",
  "cdc_number": "...",
  "coc_number": "...",
  "foc_number": "..."
}"""

class EntityExtractor:
    def __init__(self, url: str = LLM_URL, model: str = LLM_MODEL, api_key: str = LLM_API_KEY):
        self.url = url
        self.model = model
        self.api_key = api_key

    def extract_profile(self, document_text_or_json: Any) -> SeafarerProfile:
        """Invokes the local model to extract SeafarerProfile from OCR content."""
        if isinstance(document_text_or_json, dict):
            content = json.dumps(document_text_or_json, indent=2)
        else:
            content = str(document_text_or_json)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Document OCR Content:\n{content[:4000]}"}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }

        response = requests.post(self.url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        raw_content = response.json()["choices"][0]["message"]["content"].strip()

        # Clean markdown wrappers if model enclosed in ```json ... ```
        clean_json = re.sub(r"^```(?:json)?\s*", "", raw_content, flags=re.MULTILINE)
        clean_json = re.sub(r"```\s*$", "", clean_json, flags=re.MULTILINE).strip()

        data = json.loads(clean_json)
        return SeafarerProfile(**data)

extractor = EntityExtractor()
