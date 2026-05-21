# -*- coding: utf-8 -*-
"""
Распознавание технических чертежей через Google Gemini Vision API.
Использует прямой HTTP-запрос (requests) — без google-generativeai SDK.
"""

import os
import io
import json
import base64
import urllib.request
import urllib.error
from typing import List, Tuple, Optional, Dict, Any

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent?key={key}"
)

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

Правила наименования калибров:
- Резьба отверстие (H): "Калибр-пробка М{d}×{p} {допуск} ПР-НЕ"
- Резьба вал (h/g/f): "Калибр-кольцо М{d}×{p} {допуск} ПР-НЕ"
- Гладкое отверстие: "Калибр-пробка ⌀{d} {допуск}"
- Гладкий вал: "Калибр-скоба ⌀{d} {допуск}"
- Если шаг не указан — подставь стандартный по ГОСТ 24705

Если калибры не требуются — напиши NONE вместо ITEM-строк.
Не добавляй лишних слов — только строки в указанном формате.
"""


def _to_png_b64(file_bytes: bytes, filename: str) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Конвертирует файл в base64 PNG.
    Возвращает (b64_string, mime_type, error_or_None).
    """
    fname = filename.lower()

    if fname.endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img_bytes = pix.tobytes("png")
            doc.close()
            return base64.b64encode(img_bytes).decode(), "image/png", None
        except ImportError:
            return None, "", "Для PDF установите pymupdf"
        except Exception as e:
            return None, "", str(e)

    # Изображения — при необходимости конвертируем в PNG
    if fname.endswith((".tif", ".tiff", ".bmp")):
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode(), "image/png", None
        except Exception as e:
            return None, "", str(e)

    if fname.endswith(".png"):
        return base64.b64encode(file_bytes).decode(), "image/png", None

    if fname.endswith((".jpg", ".jpeg")):
        return base64.b64encode(file_bytes).decode(), "image/jpeg", None

    return None, "", f"Неподдерживаемый формат: {filename}"


def _resize_b64(b64: str, mime: str, max_bytes: int = 4_000_000) -> str:
    """Уменьшает изображение если слишком большое."""
    raw = base64.b64decode(b64)
    if len(raw) <= max_bytes:
        return b64
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(raw))
        w, h = img.size
        img = img.resize((w // 2, h // 2))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return b64


def analyze_drawing(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Анализирует чертёж через Gemini Vision REST API.
    Возвращает: {title, number, items, error}
    """
    result: Dict[str, Any] = {"title": "", "number": "", "items": [], "error": None}

    if not GOOGLE_API_KEY:
        result["error"] = "GOOGLE_API_KEY не задан"
        return result

    b64, mime, err = _to_png_b64(file_bytes, filename)
    if b64 is None:
        result["error"] = err
        return result

    b64 = _resize_b64(b64, mime)

    payload = {
        "contents": [{
            "parts": [
                {"text": _PROMPT},
                {"inline_data": {"mime_type": mime, "data": b64}},
            ]
        }]
    }

    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _GEMINI_URL.format(key=GOOGLE_API_KEY),
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        result["error"] = f"Gemini API ошибка {e.code}: {e.read().decode()[:200]}"
        return result
    except Exception as e:
        result["error"] = f"Ошибка запроса: {e}"
        return result

    # Парсим ответ
    items: List[Tuple[str, str]] = []
    seen: set = set()

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("TITLE:"):
            result["title"] = line[6:].strip()
        elif line.startswith("NUMBER:"):
            result["number"] = line[7:].strip()
        elif line.startswith("ITEM:"):
            parts = line[5:].split("|", 1)
            name = parts[0].strip()
            hint = parts[1].strip() if len(parts) > 1 else ""
            key = name.lower()
            if key not in seen and name:
                seen.add(key)
                items.append((name, hint))

    result["items"] = items
    return result


def parse_drawing_vision(file_bytes: bytes, filename: str) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """Обратная совместимость с drawing_parser.py"""
    r = analyze_drawing(file_bytes, filename)
    return r["items"], r.get("error")
