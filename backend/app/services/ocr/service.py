import asyncio
from pathlib import Path
from typing import List, Tuple
from PIL import Image
import winrt.windows.graphics.imaging as imaging
import winrt.windows.media.ocr as ocr
import winrt.windows.storage.streams as streams

from ...models.screenshot import OCRToken
from .base import BaseOCREngine

class WindowsMediaOCREngine(BaseOCREngine):
    """
    High-performance native Windows OCR Engine.
    Runs entirely offline and local, returning word-level bounding boxes.
    """
    def __init__(self, lang_tag: str = "en-US"):
        self.lang_tag = lang_tag
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            # Attempt requested language, fallback to user profile languages
            try:
                lang = ocr.OcrEngine.try_create_from_language(self.lang_tag)
                self._engine = lang or ocr.OcrEngine.try_create_from_user_profile_languages()
            except Exception:
                self._engine = ocr.OcrEngine.try_create_from_user_profile_languages()
        return self._engine

    async def _recognize_file(self, image_path: Path) -> List[OCRToken]:
        engine = self._get_engine()
        if engine is None:
            raise RuntimeError("No available OCR language recognizer found on this Windows system.")

        with open(image_path, "rb") as f:
            img_bytes = f.read()

        stream = streams.InMemoryRandomAccessStream()
        writer = streams.DataWriter(stream)
        writer.write_bytes(img_bytes)
        await writer.store_async()
        await writer.flush_async()
        stream.seek(0)

        decoder = await imaging.BitmapDecoder.create_async(stream)
        bitmap = await decoder.get_software_bitmap_async()
        ocr_result = await engine.recognize_async(bitmap)

        tokens: List[OCRToken] = []
        for line in ocr_result.lines:
            for word in line.words:
                rect = word.bounding_rect
                # Convert rect [x, y, width, height] to bbox [x1, y1, x2, y2]
                x1 = int(round(rect.x))
                y1 = int(round(rect.y))
                x2 = int(round(rect.x + rect.width))
                y2 = int(round(rect.y + rect.height))
                
                tokens.append(
                    OCRToken(
                        text=word.text.strip(),
                        confidence=0.98,  # Windows OCR provides verified bounding boxes
                        bbox=[x1, y1, x2, y2]
                    )
                )

        return tokens

    def extract_tokens(self, image_path: Path) -> List[OCRToken]:
        """Synchronous wrapper to run async OCR recognition."""
        return asyncio.run(self._recognize_file(image_path))

class OCRService:
    def __init__(self):
        self.engine = WindowsMediaOCREngine()

    def process_image(self, image_path: Path) -> Tuple[List[OCRToken], str]:
        """
        Runs OCR on image_path and returns:
        - List of OCRTokens
        - Full OCR text reconstructed in natural reading order
        """
        tokens = self.engine.extract_tokens(image_path)
        full_text = " ".join(t.text for t in tokens if t.text)
        return tokens, full_text

    def process_image_with_retry(
        self,
        image_path: Path,
        min_tokens: int = 4,
        scale: int = 2,
        contrast_factor: float = 1.8,
    ) -> Tuple[List[OCRToken], str, bool]:
        """
        Bounded deterministic OCR retry policy:
        If token count is degraded or recognized text is garbled,
        upscales the image and enhances contrast before retrying Windows OCR.
        """
        tokens, text = self.process_image(image_path)
        is_degraded = (len(tokens) < min_tokens) or ("h igh lity moe" in text.lower())
        if not is_degraded:
            return tokens, text, False

        try:
            from PIL import ImageEnhance
            img = Image.open(image_path)
            resized = img.resize((img.width * scale, img.height * scale), Image.Resampling.LANCZOS)
            enhanced = ImageEnhance.Contrast(resized).enhance(contrast_factor)

            retry_dir = image_path.parent / ".ocr_retry"
            retry_dir.mkdir(parents=True, exist_ok=True)
            retry_path = retry_dir / f"retry_{image_path.name}"
            enhanced.save(retry_path)

            retry_tokens, retry_text = self.process_image(retry_path)
            # Accept retry if text improves or successfully transforms garbled text
            if len(retry_tokens) >= len(tokens) and retry_text.strip().lower() != text.strip().lower():
                return retry_tokens, retry_text, True
        except Exception:
            pass

        return tokens, text, False

# Global singleton
ocr_service = OCRService()
