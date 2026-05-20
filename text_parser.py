# -*- coding: utf-8 -*-
"""
Парсер текста/PDF для ВЕГАЛИБР.
Распознаёт строки с калибрами из:
  - PDF файлов (таблицы и текст)
  - Вставленного текста (из Word, письма, буфера обмена)
"""

import re
import io


# ── Ключевые слова для распознавания строки как калибра ──────────────────────
_CALIBER_KEYWORDS = [
    'калибр', 'скоба', 'пробка', 'кольцо', 'калибр-скоба',
    'калибр-пробка', 'калибр-кольцо', 'гост', 'пр-не', 'пр/не',
]

_SIZE_PATTERN = re.compile(
    r'(?:'
    r'[МMмm]\s*\d+[,.]?\d*\s*[×xхХ]'   # резьбовые М5х0,8
    r'|'
    r'\d+[,.]\d+\s*[hHhН]'              # гладкие 6,48 h11
    r'|'
    r'\d+[,.]\d+\s*[HНhн]\d+'           # пробки 2,0 H14
    r')'
)


def _is_caliber_line(text):
    """Строка похожа на наименование калибра?"""
    tl = text.lower()
    has_kw  = any(kw in tl for kw in _CALIBER_KEYWORDS)
    has_sz  = bool(_SIZE_PATTERN.search(text))
    return has_kw or has_sz


def _extract_qty(tokens):
    """Пытается найти количество в списке токенов (ищет целое число ≥1 ≤9999)."""
    for tok in tokens:
        tok = tok.replace(' ', '').replace('\xa0', '')
        try:
            v = int(float(tok.replace(',', '.')))
            if 1 <= v <= 9999:
                return v
        except ValueError:
            pass
    return None


def parse_text(raw_text):
    """
    Парсит произвольный текст (из буфера обмена, письма, Word).
    Возвращает (items, error).
    items = список (name, qty, None, None)
    """
    lines = raw_text.splitlines()
    items = []

    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue

        # Разбиваем по табуляциям, затем по нескольким пробелам
        parts = re.split(r'\t|  {2,}', line)
        parts = [p.strip() for p in parts if p.strip()]

        if not parts:
            continue

        # Первая часть — потенциальное наименование
        name_candidate = parts[0]

        # Пробуем все части как название (берём самую длинную похожую)
        name = None
        for p in parts:
            if _is_caliber_line(p) and len(p) > (len(name) if name else 0):
                name = p

        if not name:
            # Если явного калибра нет — проверяем первую часть на ключевые слова
            if _is_caliber_line(name_candidate):
                name = name_candidate
            else:
                continue

        # Ищем количество среди остальных токенов
        other_parts = [p for p in parts if p != name]
        qty = _extract_qty(other_parts)
        if qty is None:
            # Пробуем найти число в конце строки
            m = re.search(r'\b(\d{1,4})\s*шт', line, re.IGNORECASE)
            if m:
                qty = int(m.group(1))
        if qty is None:
            qty = 1   # если количество не найдено — ставим 1

        items.append((name, qty, None, None))

    if not items:
        return [], "Не удалось распознать калибры в тексте"
    return items, None


def parse_pdf(file_stream):
    """
    Парсит PDF файл.
    Возвращает (items, error).
    """
    try:
        import pdfplumber
    except ImportError:
        return [], "pdfplumber не установлен"

    try:
        data = file_stream.read() if hasattr(file_stream, 'read') else file_stream
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as e:
        return [], f"Не удалось открыть PDF: {e}"

    items = []

    for page in pdf.pages:
        # 1) Пробуем таблицы
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row:
                    continue
                cells = [str(c or '').strip() for c in row]
                cells = [c for c in cells if c]

                name = None
                for c in cells:
                    if _is_caliber_line(c) and len(c) > (len(name) if name else 0):
                        name = c
                if not name:
                    continue

                other = [c for c in cells if c != name]
                qty = _extract_qty(other)
                if qty is None:
                    qty = 1

                items.append((name, qty, None, None))

        # 2) Если таблиц нет — парсим текст построчно
        if not tables:
            text = page.extract_text() or ''
            page_items, _ = parse_text(text)
            items.extend(page_items)

    pdf.close()

    if not items:
        return [], "Не удалось найти калибры в PDF"
    return items, None
