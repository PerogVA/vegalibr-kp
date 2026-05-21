# -*- coding: utf-8 -*-
"""
Парсер технических чертежей для ВЕГАЛИБР.

Распознаёт на чертеже:
  - Метрические резьбы: М10×1,5-6H / М10-7H / М12×1,75-6g
  - Гладкие отверстия: ∅25H7 / Ø45H8 / 25H7
  - Гладкие валы: ∅45h6 / 30g6

Возвращает список предложений: (name, hint)
  name  — наименование калибра для калькулятора
  hint  — «откуда взято» (для отображения пользователю)

Поддерживает:
  • PDF с текстом (pdfplumber)
  • PDF-сканы и изображения (tesseract OCR, если установлен)
"""

import re
import io
from typing import List, Tuple, Optional

# ---------------------------------------------------------------------------
# Стандартный шаг ГОСТ 24705 (для восстановления шага если не указан)
# ---------------------------------------------------------------------------
_STD_PITCH = {
    1: 0.25, 1.1: 0.25, 1.2: 0.25, 1.4: 0.3, 1.6: 0.35,
    1.8: 0.35, 2: 0.4, 2.2: 0.45, 2.5: 0.45, 3: 0.5,
    3.5: 0.6, 4: 0.7, 5: 0.8, 6: 1.0, 7: 1.0, 8: 1.25,
    9: 1.25, 10: 1.5, 11: 1.5, 12: 1.75, 14: 2.0, 16: 2.0,
    18: 2.5, 20: 2.5, 22: 2.5, 24: 3.0, 27: 3.0, 30: 3.5,
    33: 3.5, 36: 4.0, 39: 4.0, 42: 4.5, 45: 4.5, 48: 5.0,
    52: 5.0, 56: 5.5, 60: 5.5, 64: 6.0, 68: 6.0,
}

def _std_pitch(diam: float) -> Optional[float]:
    return _STD_PITCH.get(int(diam)) or _STD_PITCH.get(diam)


# ---------------------------------------------------------------------------
# Регулярные выражения
# ---------------------------------------------------------------------------

# Любой символ диаметра: ∅ Ø ⌀ ф Ф D Д (OCR иногда даёт разные варианты)
_DIAM_SIGN = r'[∅Ø⌀фФDДdд]'

# Метрическая резьба: М10×1,5-6H или М10-7H или M16x2-6g
# Группы: 1=диаметр, 2=шаг (опц.), 3=поле допуска
_THREAD_RE = re.compile(
    r'(?<![/\d])'                              # не часть дроби
    r'[МMмm]\s*'                               # М (кириллица или латиница)
    r'(\d{1,3}(?:[,\.]\d+)?)'                  # диаметр
    r'(?:\s*[×xхХ\*]\s*(\d{1,2}[,\.]\d+))?'   # × шаг (необязательно)
    r'\s*[-–—]\s*'                              # разделитель
    r'(\d{1,2}[A-Za-zА-Яа-яЁё]{1,4})',         # поле допуска (6H, 6g, 7H, 5H6H…)
    re.UNICODE | re.IGNORECASE
)

# Гладкие: ∅25H7 / Ø45h6 / 25H7 / ф30H8 / D50h6
# Группы: 1=диаметр, 2=поле допуска (H7, h6, G6, g6 …)
_SMOOTH_RE = re.compile(
    r'(?:'
        + _DIAM_SIGN + r'\s*'                  # знак диаметра (опц.)
    r')?'
    r'(\d{1,4}(?:[,\.]\d+)?)'                  # значение диаметра
    r'\s*'
    r'([A-HJ-Za-hj-z][5-9](?:[A-Ha-h](?:\d+)?)?)',  # поле допуска H7, h6, js6…
    re.UNICODE
)

# Фильтр: допуски, которые требуют калибров (иначе слишком много шума)
_HOLE_TOLERANCES  = {'H5','H6','H7','H8','H9','H10','H11','H6H','H7H'}
_SHAFT_TOLERANCES = {'h5','h6','h7','h8','h9','g5','g6','f7','e8','d9','js5','js6',
                     'k5','k6','m5','m6','n5','n6','p5','p6','r5','r6','s6','u6'}


# ---------------------------------------------------------------------------
# Парсинг текста
# ---------------------------------------------------------------------------

def _parse_text(text: str) -> List[Tuple[str, str]]:
    """
    Извлекает из текста чертежа обозначения резьб и допусков.
    Возвращает [(name, hint), …]
    """
    suggestions = []
    seen: set[str] = set()

    # Нормализация: заменяем «умные» кавычки, лишние пробелы
    text = text.replace(' ', ' ').replace('\r', '\n')

    # ── Метрические резьбы ────────────────────────────────────────────────
    for m in _THREAD_RE.finditer(text):
        raw_diam  = m.group(1).replace(',', '.')
        raw_pitch = (m.group(2) or '').replace(',', '.')
        tolerance = m.group(3)

        try:
            diam = float(raw_diam)
        except ValueError:
            continue

        # Определяем шаг (если не указан — берём стандартный)
        if raw_pitch:
            pitch = float(raw_pitch)
        else:
            pitch = _std_pitch(diam)
            if pitch is None:
                continue

        # Определяем тип калибра по полю допуска
        # Прописная → отверстие → пробка; строчная → вал → кольцо
        tol_letter = ''
        for ch in tolerance:
            if ch.isalpha():
                tol_letter = ch
                break

        if tol_letter.isupper():
            kind = 'Калибр-пробка'
        else:
            kind = 'Калибр-кольцо'

        # Форматируем название
        pitch_str = str(pitch).rstrip('0').rstrip('.')
        if '.' in pitch_str:
            pitch_str = pitch_str.replace('.', ',')
        diam_str = raw_diam.replace('.', ',').rstrip(',0')

        name = f'{kind} М{diam_str}×{pitch_str} {tolerance} ПР-НЕ'
        hint = m.group(0).strip()

        key = name.lower()
        if key not in seen:
            seen.add(key)
            suggestions.append((name, hint))

    # ── Гладкие поверхности ───────────────────────────────────────────────
    for m in _SMOOTH_RE.finditer(text):
        raw_diam  = m.group(1).replace(',', '.')
        tolerance = m.group(2)

        # Отфильтровываем случайные совпадения
        tol_upper = tolerance.upper()
        if (tolerance not in _HOLE_TOLERANCES
                and tolerance not in _SHAFT_TOLERANCES
                and tol_upper not in _HOLE_TOLERANCES):
            continue

        try:
            diam = float(raw_diam)
        except ValueError:
            continue

        if diam < 1 or diam > 500:
            continue

        tol_letter = tolerance[0]
        if tol_letter.isupper():
            kind = 'Калибр-пробка гладкая'
        else:
            kind = 'Скоба листовая'   # вал → скоба

        diam_disp = raw_diam.replace('.', ',')
        name = f'{kind} {diam_disp} {tolerance}'
        hint = m.group(0).strip()

        key = name.lower()
        if key not in seen:
            seen.add(key)
            suggestions.append((name, hint))

    return suggestions


# ---------------------------------------------------------------------------
# PDF (текстовый)
# ---------------------------------------------------------------------------

def parse_drawing_pdf_text(file_bytes: bytes) -> Tuple[List[Tuple[str,str]], Optional[str]]:
    """
    Извлекает текст из PDF через pdfplumber, ищет обозначения.
    Возвращает (suggestions, error_or_None).
    """
    try:
        import pdfplumber
    except ImportError:
        return [], 'pdfplumber не установлен'

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                t = page.extract_text() or ''
                pages_text.append(t)
            full_text = '\n'.join(pages_text)
    except Exception as e:
        return [], f'Не удалось открыть PDF: {e}'

    if not full_text.strip():
        return [], None   # Пустой — нужен OCR (сигнал для вызывающего)

    return _parse_text(full_text), None


# ---------------------------------------------------------------------------
# OCR (сканы + image-PDF)
# ---------------------------------------------------------------------------

def _ocr_image(img) -> str:
    """
    Запускает Tesseract на PIL Image. Возвращает текст или ''.
    Если tesseract не установлен — возвращает ''.
    """
    try:
        import pytesseract
    except ImportError:
        return ''

    # Пробуем rus+eng; если пакет языка не установлен — только eng
    for lang in ('rus+eng', 'eng'):
        try:
            text = pytesseract.image_to_string(img, lang=lang,
                                               config='--psm 11')
            if text.strip():
                return text
        except Exception:
            continue
    return ''


def parse_drawing_image(file_bytes: bytes) -> Tuple[List[Tuple[str,str]], Optional[str]]:
    """
    OCR изображения (PNG/JPG/TIFF/BMP).
    Возвращает (suggestions, error_or_None).
    """
    try:
        from PIL import Image
    except ImportError:
        return [], 'Pillow не установлен (pip install Pillow)'

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img = img.convert('L')   # grayscale — лучше для OCR
    except Exception as e:
        return [], f'Не удалось открыть изображение: {e}'

    text = _ocr_image(img)
    if not text.strip():
        return [], 'OCR не дал результата (Tesseract не установлен или пустой скан)'

    return _parse_text(text), None


def parse_drawing_pdf_ocr(file_bytes: bytes) -> Tuple[List[Tuple[str,str]], Optional[str]]:
    """
    Конвертирует PDF в изображения и OCR-ит каждую страницу.
    Требует PyMuPDF (pymupdf).
    """
    try:
        import fitz   # PyMuPDF
    except ImportError:
        return [], 'PyMuPDF не установлен (pip install pymupdf)'

    try:
        from PIL import Image
    except ImportError:
        return [], 'Pillow не установлен'

    try:
        doc = fitz.open(stream=file_bytes, filetype='pdf')
    except Exception as e:
        return [], f'Не удалось открыть PDF: {e}'

    all_suggestions: List[Tuple[str,str]] = []
    seen: set[str] = set()

    for page_num in range(len(doc)):
        page = doc[page_num]
        mat  = fitz.Matrix(2.0, 2.0)   # 2× масштаб для лучшего OCR
        pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        img  = Image.frombytes('L', [pix.width, pix.height], pix.samples)

        text = _ocr_image(img)
        for s in _parse_text(text):
            key = s[0].lower()
            if key not in seen:
                seen.add(key)
                all_suggestions.append(s)

    doc.close()
    return all_suggestions, None


# ---------------------------------------------------------------------------
# Главная точка входа
# ---------------------------------------------------------------------------

def parse_drawing(file_bytes: bytes, filename: str) -> Tuple[List[Tuple[str,str]], Optional[str]]:
    """
    Универсальный парсер чертежа.
    filename используется для определения типа файла.
    Возвращает (suggestions, error_or_None).
    """
    fname = filename.lower()

    if fname.endswith('.pdf'):
        # Сначала пробуем текст
        suggestions, err = parse_drawing_pdf_text(file_bytes)
        if err:
            return [], err
        if suggestions:
            return suggestions, None
        # Текст пустой — пробуем OCR через PyMuPDF
        suggestions, err = parse_drawing_pdf_ocr(file_bytes)
        if err:
            # PyMuPDF не установлен или другая ошибка — сообщаем
            return [], f'PDF не содержит текста. Для OCR-сканов установите pymupdf: {err}'
        return suggestions, None

    # Изображения
    if any(fname.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp')):
        return parse_drawing_image(file_bytes)

    return [], f'Неподдерживаемый формат файла: {filename}'
