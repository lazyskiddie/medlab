import cv2
import numpy as np
import pytesseract
import pdfplumber
from pdf2image import convert_from_path
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)


def _set_tesseract_cmd():
    """
    Set Tesseract path fresh every call.
    Priority:
      1. TESSERACT_CMD environment variable
      2. Django settings.TESSERACT_CMD
      3. Common Mac/Linux hardcoded paths
      4. Falls back to PATH
    """
    cmd = os.environ.get('TESSERACT_CMD', '').strip()

    if not cmd:
        try:
            from django.conf import settings
            cmd = str(getattr(settings, 'TESSERACT_CMD', '')).strip()
        except Exception:
            pass

    if not cmd:
        candidates = [
            '/opt/homebrew/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/usr/bin/tesseract',
        ]
        for p in candidates:
            if Path(p).exists():
                cmd = p
                break

    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
        logger.debug(f'Tesseract set to: {cmd}')


def preprocess_image(image_array: np.ndarray) -> np.ndarray:
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_array

    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh   = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 2
    )

    coords = np.column_stack(np.where(thresh > 0))
    if coords.size > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 0.5:
            (h, w) = thresh.shape
            M      = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            thresh = cv2.warpAffine(thresh, M, (w, h),
                                    flags=cv2.INTER_CUBIC,
                                    borderMode=cv2.BORDER_REPLICATE)

    h, w = thresh.shape
    if w < 1200:
        scale  = 1200 / w
        thresh = cv2.resize(thresh, None, fx=scale, fy=scale,
                            interpolation=cv2.INTER_CUBIC)
    return thresh


def ocr_from_image(file_path: str) -> str:
    _set_tesseract_cmd()
    try:
        img = cv2.imread(file_path)
        if img is None:
            raise ValueError(f'Could not read image: {file_path}')
        processed = preprocess_image(img)
        text      = pytesseract.image_to_string(processed, config=r'--oem 3 --psm 6')
        logger.info(f'OCR extracted {len(text)} chars from image')
        return text.strip()
    except Exception as e:
        logger.error(f'OCR image error: {e}')
        raise


def ocr_from_pdf(file_path: str) -> str:
    _set_tesseract_cmd()
    texts = []

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text)
    except Exception as e:
        logger.warning(f'pdfplumber failed, falling back to image OCR: {e}')

    if not texts:
        try:
            images = convert_from_path(file_path, dpi=300)
            for img in images:
                img_array = np.array(img)
                processed = preprocess_image(img_array)
                text      = pytesseract.image_to_string(processed,
                                                        config=r'--oem 3 --psm 6')
                if text.strip():
                    texts.append(text.strip())
        except Exception as e:
            logger.error(f'PDF image OCR failed: {e}')
            raise

    return '\n\n'.join(texts)


def extract_text(file_path: str, file_type: str) -> str:
    if file_type == 'pdf':
        return ocr_from_pdf(str(file_path))
    return ocr_from_image(str(file_path))