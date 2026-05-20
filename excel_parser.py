# -*- coding: utf-8 -*-
"""Парсер Excel-заявок для ВЕГАЛИБР"""

import re
import openpyxl


def parse_zaявka(filepath_or_stream):
    """
    Читает Excel-заявку. Возвращает (items, error).
    items = список (name, qty, price_no_kal, kalib)
      price_no_kal — цена из Excel без калибровки (или None)
      kalib        — стоимость калибровки из Excel (или None)
    """
    wb = openpyxl.load_workbook(filepath_or_stream, data_only=True)

    # Выбор листа
    ws = None
    for sname in wb.sheetnames:
        if 'заявк' in sname.lower():
            ws = wb[sname]
            break
    if ws is None:
        ws = wb.active

    # Поиск строки заголовков и колонок
    name_col      = None   # тип (Кольцо резьбовое / Калибр-скоба...)
    spec_col      = None   # обозначение / артикул (содержит М×шаг)
    qty_col       = None
    price_col     = None   # цена без калибровки
    price_kal_col = None   # цена с калибровкой
    header_row_idx = None

    for row in ws.iter_rows(min_row=1, max_row=30):
        for cell in row:
            if cell.value is None:
                continue
            val = str(cell.value).lower().strip()

            # Наименование/тип (НЕ "с калибровкой")
            if re.search(r'наим', val) and 'калибровк' not in val:
                if name_col is None:
                    name_col = cell.column
                    header_row_idx = cell.row

            # Обозначение / артикул (вторая колонка с описанием)
            if re.search(r'обозн|артикул', val):
                spec_col = cell.column
                header_row_idx = header_row_idx or cell.row

            # Кол-во
            if re.search(r'\bкол[\-\.]?во?\b|\bqty\b|\bcount\b', val) \
                    and '/' not in val and 'цена' not in val and 'руб' not in val:
                qty_col = cell.column

            # Цены — различаем "без калибровки" vs "с калибровкой"
            if ('цен' in val or 'руб' in val) and 'калибровк' in val:
                if 'без калибр' in val:
                    price_col = cell.column      # "цена без калибровки"
                elif 'с калибр' in val:
                    price_kal_col = cell.column  # "цена с калибровкой"

        if name_col and qty_col:
            break

    if name_col is None or qty_col is None:
        return [], "Не удалось найти колонки «Наименование» и «Кол-во»"

    # Если spec_col не нашли по заголовку — ищем по содержимому строк
    if spec_col is None and header_row_idx:
        for row in ws.iter_rows(min_row=header_row_idx + 1,
                                max_row=header_row_idx + 15):
            for cell in row:
                if cell.column == name_col or cell.column == qty_col:
                    continue
                if cell.value and re.search(
                        r'[МмMm]\s*\d+[,.]?\d*\s*[×xхХ\-]', str(cell.value)):
                    spec_col = cell.column
                    break
            if spec_col:
                break

    # Читаем строки данных
    items = []
    for row in ws.iter_rows(min_row=header_row_idx + 1):
        rv = {cell.column: cell.value for cell in row}

        type_name = str(rv.get(name_col) or '').strip()
        spec_name = str(rv.get(spec_col) or '').strip() if spec_col else ''

        if not type_name and not spec_name:
            continue

        # Полное наименование
        if spec_name and re.search(r'[Мм]\s*\d', spec_name):
            name = f"{type_name} {spec_name}".strip() if type_name else spec_name
        else:
            name = type_name or spec_name
        if not name or name.isdigit():
            continue

        # Количество
        try:
            qty = int(float(str(rv.get(qty_col) or '')))
        except (ValueError, TypeError):
            continue
        if qty <= 0:
            continue

        # Цены из Excel
        price_from_excel = None
        kalib_from_excel = None
        if price_col:
            try:
                price_from_excel = float(str(rv.get(price_col) or ''))
            except (ValueError, TypeError):
                pass
        if price_col and price_kal_col:
            try:
                p_no  = float(str(rv.get(price_col)     or ''))
                p_kal = float(str(rv.get(price_kal_col) or ''))
                kalib_from_excel = round(p_kal - p_no, 2)
            except (ValueError, TypeError):
                pass

        items.append((name, qty, price_from_excel, kalib_from_excel))

    if not items:
        return [], "Строки с данными не найдены"

    return items, None
