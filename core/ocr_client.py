import os
import requests
from pathlib import Path
from typing import Dict, Any, Union, Optional, Tuple
import time
from core.config import OCR_API_URL, OCR_TIMEOUT

class OCRClient:
    def __init__(self, endpoint_url: str = OCR_API_URL, default_timeout: int = OCR_TIMEOUT):
        self.endpoint_url = endpoint_url
        self.default_timeout = default_timeout

    def extract_document(self, file_path: Union[str, Path], timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Uploads a PDF/Image document to the OCR extraction endpoint.
        Fast-Fail Policy: Executes a request with configurable OCR_TIMEOUT (default 120s).
        """
        if timeout is None:
            timeout = self.default_timeout

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found at: {file_path}")

        filename = path.name
        content_type = "application/pdf" if path.suffix.lower() == ".pdf" else "image/png"
        t0 = time.time()
        print(f"[OCR] Starting extraction for '{filename}' ({path.stat().st_size // 1024} KB), timeout={timeout}s...")

        with open(path, "rb") as f:
            files = {
                "file": (filename, f, content_type)
            }
            response = requests.post(self.endpoint_url, files=files, timeout=timeout)

        elapsed = time.time() - t0
        response.raise_for_status()
        print(f"[OCR] Extracted '{filename}' in {elapsed:.1f}s")
        return response.json()

    def extract_document_safe(self, file_path: Union[str, Path], timeout: Optional[int] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Safe extraction wrapper.
        Returns: (data_dict, error_string)
        If extraction fails, returns (None, "Reason") without halting or looping.
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout
        try:
            data = self.extract_document(file_path, timeout=effective_timeout)
            return data, None
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "Error"
            print(f"[OCR] HTTP {status} error on {file_path}")
            return None, f"HTTP {status} Server Error"
        except requests.exceptions.Timeout:
            print(f"[OCR] Request timed out ({effective_timeout}s) on {file_path}")
            return None, f"OCR Request Timed Out ({effective_timeout}s)"
        except requests.exceptions.ConnectionError:
            print(f"[OCR] Server unreachable on {file_path}")
            return None, "OCR Server Unreachable"
        except Exception as e:
            print(f"[OCR] Unexpected error on {file_path}: {e}")
            return None, str(e)

ocr_client = OCRClient()
