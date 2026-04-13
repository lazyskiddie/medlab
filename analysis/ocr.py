import cv2
import numpy as np
import pytesseract
import pdfplumber
from pdf2image import convert_from_path
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def preprocess_image(image_array: np.ndarray) -> np.ndarray:
    if len(image_array.shape) == 3:
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_array
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    thresh   = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
    coords = np.column_stack(np.where(thresh > 0))
    if coords.size > 0:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45: angle = -(90 + angle)
        else:           angle = -angle
        if abs(angle) > 0.5:
            (h, w) = thresh.shape
            M      = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
            thresh = cv2.warpAffine(thresh, M, (w, h),
                                    flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    h, w = thresh.shape
    if w < 1200:
        scale  = 1200 / w
        thresh = cv2.resize(thresh, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return thresh


def ocr_from_image(file_path: str) -> str:
    try:
        img = cv2.imread(file_path)
        if img is None:
            raise ValueError(f'Could not read image: {file_path}')
        processed = preprocess_image(img)
        return pytesseract.image_to_string(processed, config=r'--oem 3 --psm 6').strip()
    except Exception as e:
        logger.error(f'OCR image error: {e}')
        raise


def ocr_from_pdf(file_path: str) -> str:
    texts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: texts.append(t)
    except Exception as e:
        logger.warning(f'pdfplumber failed, trying image OCR: {e}')

    if not texts:
        try:
            images = convert_from_path(file_path, dpi=300)
            for img in images:
                processed = preprocess_image(np.array(img))
                t = pytesseract.image_to_string(processed, config=r'--oem 3 --psm 6')
                if t.strip(): texts.append(t.strip())
        except Exception as e:
            logger.error(f'PDF image OCR failed: {e}')
            raise
    return '\n\n'.join(texts)


def extract_text(file_path: str, file_type: str) -> str:
    if file_type == 'pdf':
        return ocr_from_pdf(str(file_path))
    return ocr_from_image(str(file_path))