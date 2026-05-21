# -*- coding: utf-8 -*-
"""
Распознавание технических чертежей через Claude Vision API.
Возвращает:
  - drawing_title  — название чертежа (из основной надписи)
  - drawing_number — номер чертежа / обозначение
  - items          — список того что нужно изготовить [(наименование, примечание), ...]
"""

import os
import io
import base64
from typing import List, Tuple, Optional, Dict, Any

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

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


def _to_png_bytes(file_bytes: bytes, filename: str) -> Tuple[Optional[bytes], str]:
    """Конвертирует файл в PNG-байты для Vision API."""
    fname = filename.lower()

    if fname.endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            return pix.tobytes("png"), "image/png"
        except ImportError:
            return None, "Для PDF-сканов установите pymupdf"
        except Exception as e:
            return None, str(e)

    if fname.endswith((".tif", ".tiff", ".bmp")):
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue(), "image/png"
        except Exception as e:
            return None, str(e)

    if fname.endswith(".png"):
        return file_bytes, "image/png"
    if fname.endswith((".jpg", ".jpeg")):
        return file_bytes, "image/jpeg"

    return None, f"Неподдерживаемый формат: {filename}"


def _resize(img_bytes: bytes, max_bytes: int = 4_500_000) -> bytes:
    if len(img_bytes) <= max_bytes:
        return img_bytes
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        img = img.resize((w // 2, h // 2), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return img_bytes


def analyze_drawing(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Анализирует чертёж через Claude Vision.
    Возвращает dict:
      {
        'title':  str,                         # название детали
        'number': str,                         # обозначение
        'items':  [(name, hint), ...],         # калибры
        'error':  str or None
      }
    """
    result = {'title': '', 'number': '', 'items': [], 'error': None}

    if not ANTHROPIC_API_KEY:
        result['error'] = "ANTHROPIC_API_KEY не задан"
        return result

    try:
        import anthropic
    except ImportError:
        result['error'] = "Библиотека anthropic не установлена"
        return result

    img_bytes, media_type = _to_png_bytes(file_bytes, filename)
    if img_bytes is None:
        result['error'] = media_type
        return result

    img_bytes = _resize(img_bytes)
    b64 = base64.standard_b64encode(img_bytes).decode("utf-8")

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
        )
    except Exception as e:
        result['error'] = f"Ошибка Claude API: {e}"
        return result

    text = msg.content[0].text if msg.content else ""
    items = []
    seen = set()

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
