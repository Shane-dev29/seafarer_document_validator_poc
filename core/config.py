import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file manually if python-dotenv is not installed
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

LLM_URL = os.environ.get("EDOT_LLM_URL", "https://ai.edot-solutions.com/v1/chat/completions")
LLM_MODEL = os.environ.get("EDOT_LLM_MODEL", "AI_Local")
LLM_API_KEY = os.environ.get("EDOT_API_KEY", "")

OCR_API_URL = os.environ.get("OCR_API_URL", "http://192.168.1.34:8007/api/extract?mode=structured")
OCR_TIMEOUT = int(os.environ.get("OCR_TIMEOUT", "120"))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

EXCEL_PATH = str(BASE_DIR / os.environ.get("EXCEL_REGISTRY_PATH", "IMO_STCW_Seafarer_Verification.xlsx"))
VERIFIERS_DIR = str(BASE_DIR / "verifiers")
