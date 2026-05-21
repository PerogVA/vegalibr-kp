# -*- coding: utf-8 -*-
"""
Распознавание технических чертежей через Claude Vision API.
Возвращает список калибров в том же формате что и drawing_parser.
"""

import os
import io
import base64
from typing import List, Tuple, Optional

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

_PROMPT = """Ты — эксперт по метрологии и техническим чертежам.
Проанализируй чертёж и найди ВСЕ поверхности, для которых нужны калибры:

1. Метрические резьбы: М10×1,5-6H, М12-7h, M16x2-6g и т.п.
2. Гладкие отверстия с допуском: ∅25H7, ∅45H8, 30H7 и т.п.
3. Гладкие валы с допуском: ∅30h6, 45g6, 50f7 и т.п.

Для каждой найденной поверхности верни строку в формате:
CALIBER|<наименование калибра>|<что нашёл на чертеже>

Правила формирования наименования:
- Метрическая резьба, отверстие (H): "Калибр-пробка М{диам}×{шаг} {допуск} ПР-НЕ"
- Метрическая резьба, вал (h/g/d/e/f): "Калибр-кольцо М{диам}×{шаг} {допуск} ПР-НЕ"
- Гладкое отверстие (H7,H8…): "Калибр-пробка {диам} {допуск}"
- Гладкий вал (h6,g6,f7…): "Калибр-скоба {диам} {допуск}"
- Если шаг резьбы не указан — используй стандартный по ГОСТ 24705

Если калибры не нужны или ничего не найдено — верни строку: NONE

Не добавляй пояснений — только строки CALIBER|...|... или NONE.
"""


def _pdf_to_png_bytes(file_bytes: bytes) -> Optional[bytes]:
    """Конвертирует первую страницу PDF в PNG для отправки в Vision."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")
    except Exception:
        pass
    try:
        import pdfplumber
        # Нет fitz — пробуем через Pillow если pdfplumber умеет
        pass
    except Exception:
        pass
    return None


def _resize_if_needed(img_bytes: bytes, max_bytes: int = 4_500_000) -> bytes:
    """Уменьшает изображение если оно слишком большое для API."""
    if len(img_bytes) <= max_bytes:
        return img_bytes
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        # Уменьшаем до 50%
        w, h = img.size
        img = img.resize((w // 2, h // 2), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return img_bytes


def parse_drawing_vision(file_bytes: bytes, filename: str) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """
    Отправляет чертёж в Claude Vision и возвращает список калибров.
    Формат возврата: ([(name, hint), ...], error_or_None)
    """
    if not ANTHROPIC_API_KEY:
        return [], "ANTHROPIC_API_KEY не задан"

    try:
        import anthropic
    except ImportError:
        return [], "Библиотека anthropic не установлена"

    # Подготавливаем изображение
    fname = filename.lower()
    if fname.endswith(".pdf"):
        img_bytes = _pdf_to_png_bytes(file_bytes)
        if img_bytes is None:
            # Попробуем просто передать PDF как есть — но Vision не принимает PDF,
            # поэтому возвращаем ошибку
            return [], "Для PDF-сканов требуется PyMuPDF (pip install pymupdf)"
        media_type = "image/png"
    elif fname.endswith((".jpg", ".jpeg")):
        img_bytes = file_bytes
        media_type = "image/jpeg"
    elif fname.endswith(".png"):
        img_bytes = file_bytes
        media_type = "image/png"
    elif fname.endswith((".tif", ".tiff", ".bmp")):
        # Конвертируем в PNG
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            media_type = "image/png"
        except Exception as e:
            return [], f"Не удалось конвертировать изображение: {e}"
    else:
        return [], f"Неподдерживаемый формат: {filename}"

    img_bytes = _resize_if_needed(img_bytes)
    b64_data = base64.standard_b64encode(img_bytes).decode("utf-8")

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": _PROMPT,
                        },
                    ],
                }
            ],
        )
    except Exception as e:
        return [], f"Ошибка Claude API: {e}"

    response_text = message.content[0].text if message.content else ""

    # Парсим ответ
    suggestions: List[Tuple[str, str]] = []
    seen: set = set()

    for line in response_text.splitlines():
        line = line.strip()
        if line.startswith("CALIBER|"):
            parts = line.split("|", 2)
            if len(parts) == 3:
                name = parts[1].strip()
                hint = parts[2].strip()
                key = name.lower()
                if key not in seen and name:
                    seen.add(key)
                    suggestions.append((name, hint))
        elif line == "NONE":
            break

    return suggestions, None
