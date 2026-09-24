import os
import importlib
from pathlib import Path
from typing import Dict, List, Optional
from core.schemas import SeafarerProfile, VerificationResult
from verifiers.base_verifier import BaseVerifier

VERIFIERS_DIR = Path(__file__).resolve().parent.parent / "verifiers"

class VerifierRegistryService:
    """Manages discovery, execution, and dynamic registration of country verifiers."""

    def __init__(self, verifiers_dir: Path = VERIFIERS_DIR):
        self.verifiers_dir = verifiers_dir
        self._verifiers: Dict[str, BaseVerifier] = {}
        self.refresh()

    def refresh(self):
        """Scans the verifiers directory and loads all verifier classes."""
        self._verifiers.clear()
        
        # Ensure base verifiers directory exists
        self.verifiers_dir.mkdir(parents=True, exist_ok=True)

        for file_path in self.verifiers_dir.glob("*_verifier.py"):
            if file_path.name == "base_verifier.py":
                continue
            module_name = f"verifiers.{file_path.stem}"
            try:
                module = importlib.import_module(module_name)
                # Reload to catch any newly registered files
                importlib.reload(module)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseVerifier)
                        and attr is not BaseVerifier
                    ):
                        instance = attr()
                        self._verifiers[instance.country.strip().lower()] = instance
            except Exception as e:
                print(f"[Registry] Error loading {module_name}: {e}")

    def has_verifier(self, country: str) -> bool:
        """Check if a verifier exists for this country."""
        return country.strip().lower() in self._verifiers

    def list_verifiers(self) -> List[str]:
        """Return list of countries with active verifiers."""
        return [v.country for v in self._verifiers.values()]

    def run_verifier(self, country: str, profile_data: dict, headless: bool = True, screencast=None) -> dict:
        """Run the cached verifier for the specified country."""
        key = country.strip().lower()
        if key not in self._verifiers:
            return {
                "status": "ERROR",
                "country": country,
                "error_message": f"No verifier registered for {country}. Inspection and script generation required."
            }

        profile = SeafarerProfile(**profile_data)
        verifier = self._verifiers[key]
        # Pass screencast broadcaster if verifier supports it
        try:
            import inspect
            sig = inspect.signature(verifier.verify)
            if "screencast" in sig.parameters:
                result: VerificationResult = verifier.verify(profile, headless=headless, screencast=screencast)
            else:
                result: VerificationResult = verifier.verify(profile, headless=headless)
        except Exception:
            result: VerificationResult = verifier.verify(profile, headless=headless)
        return result.model_dump()

    def register_verifier(self, country: str, python_code: str) -> dict:
        """Dynamically save a newly generated verifier script into the registry."""
        filename = f"{country.strip().lower()}_verifier.py"
        target_path = self.verifiers_dir / filename
        
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(python_code)
            
        self.refresh()
        return {
            "success": True,
            "country": country,
            "file_path": str(target_path),
            "message": f"Successfully registered verifier for {country}"
        }

# Global instance for in-process or MCP use
registry_service = VerifierRegistryService()
