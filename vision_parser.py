# -*- coding: utf-8 -*-
"""
Распознавание технических чертежей через Google Gemini Vision API (бесплатно).
Возвращает:
  - drawing_title  — название чертежа (из основной надписи)
  - drawing_number — номер чертежа / обозначение
  - items          — список того что нужно изготовить [(наименование, примечание), ...]
"""

import os
import io
from typing import List, Tuple, Optional, Dict, Any

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

_PROMPT = """Ты — эксперт по метрологии и техническим чертежам деталей машин.

Проанализируй этот технический чертёж и определи:

1. НАЗВАНИЕ детали (из основной надписи / штампа — правый нижний угол)
2. ОБОЗНАЧЕНИЕ / номер чертежа (из основной надписи)
3. СПИСОК калибров, которые нужно ИЗГОТОВИТЬ для контроля этой детали:
   - Метрические резьбы (М10×1,5-6H → нужна пробка; М12-6g → нужно кольцо)
   - Гладкие отверстия с допуском H5-H11 → нужна пробка гладкая
   - Гладкие валы с допуском h/g/f/e/d → нужна скоба

Формат ответа — строго:
TITLE: <название детали>
NUMBER: <обозначение чертежа>
ITEM: <наименование калибра> | <обозначение с чертежа>
ITEM: <наименование калибра> | <обозначение с чертежа>
...

Правила наименования калибров:
- Резьба отверстие (H): "Калибр-пробка М{d}×{p} {допуск} ПР-НЕ"
- Резьба вал (h/g/f): "Калибр-кольцо М{d}×{p} {допуск} ПР-НЕ"
- Гладкое отверстие: "Калибр-пробка ⌀{d} {допуск}"
- Гладкий вал: "Калибр-скоба ⌀{d} {допуск}"
- Если шаг не указан — подставь стандартный по ГОСТ 24705

Если калибры не требуются — напиши NONE вместо ITEM-строк.
Не добавляй лишних слов — только строки в указанном формате.
"""


def _to_pil_image(file_bytes: bytes, filename: str):
    """Конвертирует файл в PIL Image для Gemini."""
    from PIL import Image

    fname = filename.lower()

    if fname.endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()
            return img, None
        except ImportError:
            return None, "Для PDF установите pymupdf"
        except Exception as e:
            return None, str(e)

    try:
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        return img, None
    except Exception as e:
        return None, str(e)


def _resize_image(img, max_px: int = 3000):
    """Уменьшает если слишком большое."""
    w, h = img.size
    if max(w, h) > max_px:
        scale = max_px / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)))
    return img


def analyze_drawing(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Анализирует чертёж через Google Gemini Vision.
    Возвращает dict: {title, number, items, error}
    """
    result: Dict[str, Any] = {'title': '', 'number': '', 'items': [], 'error': None}

    if not GOOGLE_API_KEY:
        result['error'] = "GOOGLE_API_KEY не задан"
        return result

    try:
        import google.generativeai as genai
    except ImportError:
        result['error'] = "Библиотека google-generativeai не установлена"
        return result

    try:
        from PIL import Image
    except ImportError:
        result['error'] = "Pillow не установлен"
        return result

    img, err = _to_pil_image(file_bytes, filename)
    if img is None:
        result['error'] = err
        return result

    img = _resize_image(img)

    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content([_PROMPT, img])
        text = response.text or ""
    except Exception as e:
        result['error'] = f"Ошибка Gemini API: {e}"
        return result

    # Парсим ответ
    items: List[Tuple[str, str]] = []
    seen: set = set()

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("TITLE:"):
            result['title'] = line[6:].strip()
        elif line.startswith("NUMBER:"):
            result['number'] = line[7:].strip()
        elif line.startswith("ITEM:"):
            parts = line[5:].split("|", 1)
            name = parts[0].strip()
            hint = parts[1].strip() if len(parts) > 1 else ""
            key = name.lower()
            if key not in seen and name:
                seen.add(key)
                items.append((name, hint))

    result['items'] = items
    return result


# Обратная совместимость с drawing_parser.py
def parse_drawing_vision(file_bytes: bytes, filename: str) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    r = analyze_drawing(file_bytes, filename)
    return r['items'], r.get('error')
