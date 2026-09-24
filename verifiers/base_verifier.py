from abc import ABC, abstractmethod
from core.schemas import SeafarerProfile, VerificationResult

class BaseVerifier(ABC):
    @property
    @abstractmethod
    def country(self) -> str:
        """The country this verifier handles (e.g. 'India', 'Panama')."""
        pass

    @abstractmethod
    def verify(self, profile: SeafarerProfile, headless: bool = True) -> VerificationResult:
        """Execute browser verification for this seafarer and return structured result."""
        pass
