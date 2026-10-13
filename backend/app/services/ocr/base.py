from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
from ...models.screenshot import OCRToken

class BaseOCREngine(ABC):
    @abstractmethod
    def extract_tokens(self, image_path: Path) -> List[OCRToken]:
        """Extracts OCR tokens with text, confidence, and bounding boxes."""
        pass
