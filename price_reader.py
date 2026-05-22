# -*- coding: utf-8 -*-
"""
Читает прайс-лист калибров из Excel без openpyxl (ZIP/XML).
Кешируется по mtime файла — обновляется автоматически при замене файла.
"""

import os
import re
import zipfile
import xml.etree.ElementTree as ET

_WNS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
_RNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

_PRICE_FILE = 'Прайс калибры.xlsx'

_cache = {
    'mtime': None,
    'plug_combo':  {},   # (diam, pitch) → цена комплекта ПР-НЕ (≤100 мм)
    'ring_pr':     {},   # (diam, pitch) → кольцо ПР
    'ring_ne':     {},   # (diam, pitch) → кольцо НЕ
    'plug_pr_big': {},   # (diam, pitch) → пробка ПР  (>100 мм)
    'plug_ne_big': {},   # (diam, pitch) → пробка НЕ  (>100 мм)
    'ring_pr_big': {},   # (diam, pitch) → кольцо ПР  (>100 мм)
    'ring_ne_big': {},   # (diam, pitch) → кольцо НЕ  (>100 мм)
    'loaded': False,
}


def _find_file():
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.path.dirname(here)):
        p = os.path.join(base, _PRICE_FILE)
        if os.path.exists(p):
            return p
    return None


def _parse_size(s):
    """'М12×1,5' / 'M2×0.4' → (12.0, 1.5) или None."""
    m = re.search(r'[МмMm]\s*(\d+[,.]?\d*)\s*[×xхХ]\s*(\d+[,.]?\d*)', str(s))
    if m:
        return (round(float(m.group(1).replace(',', '.')), 3),
                round(float(m.group(2).replace(',', '.')), 3))
    return None


def _parse_val(s):
    if not s:
        return None
    try:
        return float(str(s).strip().replace('\xa0', '').replace(' ', '').replace(',', '.'))
    except (ValueError, TypeError):
        return None


def _read_sst(z):
    sst = {}
    if 'xl/sharedStrings.xml' in z.namelist():
        for i, si in enumerate(ET.parse(z.open('xl/sharedStrings.xml')).getroot()
                               .findall(f'{_WNS}si')):
            sst[i] = ''.join(t.text or '' for t in si.iter(f'{_WNS}t'))
    return sst


def _cell_val(c, sst):
    t = c.get('t', '')
    v_el = c.find(f'{_WNS}v')
    if v_el is None:
        return ''
    v = v_el.text or ''
    if t == 's' and v:
        return sst.get(int(v), v)
    return v


def _col(ref):
    return ''.join(ch for ch in (ref or '') if ch.isalpha())


def _iter_rows(z, fpath, sst):
    root = ET.parse(z.open(fpath)).getroot()
    for row in root.iter(f'{_WNS}row'):
        cells = {}
        for c in row.findall(f'{_WNS}c'):
            cells[_col(c.get('r', ''))] = _cell_val(c, sst)
        yield int(row.get('r', 0)), cells


def _load(path):
    global _cache
    plug_combo  = {}
    ring_pr     = {}
    ring_ne     = {}
    plug_pr_big = {}
    plug_ne_big = {}
    ring_pr_big = {}
    ring_ne_big = {}

    try:
        with zipfile.ZipFile(path) as z:
            sst = _read_sst(z)
            rels = ET.parse(z.open('xl/_rels/workbook.xml.rels')).getroot()
            rid_map = {r.get('Id'): r.get('Target') for r in rels}
            wb = ET.parse(z.open('xl/workbook.xml')).getroot()
            sheet_map = {}
            for sh in wb.iter(f'{_WNS}sheet'):
                rid  = sh.get(f'{_RNS}id') or sh.get('r:id') or ''
                name = sh.get('name', '')
                tgt  = rid_map.get(rid, '')
                if tgt:
                    sheet_map[name] = 'xl/' + tgt

            # ── Метрическая до 100 мм ──────────────────────────────────────
            # Колонки: A=размер, C=пробка_комплект, D=кольцо_ПР, E=кольцо_НЕ
            sh = next((v for k, v in sheet_map.items() if 'до 100' in k), None)
            if sh:
                for rn, cells in _iter_rows(z, sh, sst):
                    if rn < 5:
                        continue
                    key = _parse_size(cells.get('A', ''))
                    if key is None:
                        continue
                    pc = _parse_val(cells.get('C'))
                    rp = _parse_val(cells.get('D'))
                    rn_val = _parse_val(cells.get('E'))
                    if pc and pc > 0:
                        plug_combo[key] = pc
                    if rp and rp > 0:
                        ring_pr[key] = rp
                    if rn_val and rn_val > 0:
                        ring_ne[key] = rn_val

            # ── Метрическая от 100 мм ──────────────────────────────────────
            # Колонки: A=размер, C=пробка_ПР, D=пробка_НЕ, E=кольцо_ПР, F=кольцо_НЕ
            sh = next((v for k, v in sheet_map.items() if 'от 100' in k), None)
            if sh:
                for rn, cells in _iter_rows(z, sh, sst):
                    if rn < 6:
                        continue
                    key = _parse_size(cells.get('A', ''))
                    if key is None:
                        continue
                    pp = _parse_val(cells.get('C'))
                    pn = _parse_val(cells.get('D'))
                    rp = _parse_val(cells.get('E'))
                    rn_val = _parse_val(cells.get('F'))
                    if pp and pp > 0:
                        plug_pr_big[key] = pp
                    if pn and pn > 0:
                        plug_ne_big[key] = pn
                    if rp and rp > 0:
                        ring_pr_big[key] = rp
                    if rn_val and rn_val > 0:
                        ring_ne_big[key] = rn_val

    except Exception:
        pass  # если файл недоступен — вернём пустые таблицы

    _cache.update({
        'mtime':       os.path.getmtime(path),
        'plug_combo':  plug_combo,
        'ring_pr':     ring_pr,
        'ring_ne':     ring_ne,
        'plug_pr_big': plug_pr_big,
        'plug_ne_big': plug_ne_big,
        'ring_pr_big': ring_pr_big,
        'ring_ne_big': ring_ne_big,
        'loaded':      True,
    })


def _ensure():
    """Загружает/обновляет кеш если файл изменился."""
    path = _find_file()
    if not path:
        return
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return
    if _cache['mtime'] != mtime:
        _load(path)


# ── Публичный API ──────────────────────────────────────────────────────────────

def plug_combo(diam, pitch):
    """Цена комплекта пробок ПР-НЕ для резьбы ≤100 мм или None."""
    _ensure()
    return _cache['plug_combo'].get((round(float(diam), 3), round(float(pitch), 3)))


def ring_pr(diam, pitch):
    """Цена кольца ПР ≤100 мм или None."""
    _ensure()
    return _cache['ring_pr'].get((round(float(diam), 3), round(float(pitch), 3)))


def ring_ne(diam, pitch):
    """Цена кольца НЕ ≤100 мм или None."""
    _ensure()
    return _cache['ring_ne'].get((round(float(diam), 3), round(float(pitch), 3)))


def plug_big(diam, pitch, side='пр'):
    """Цена пробки (ПР или НЕ) для резьбы >100 мм или None."""
    _ensure()
    k = (round(float(diam), 3), round(float(pitch), 3))
    if side == 'не':
        return _cache['plug_ne_big'].get(k)
    return _cache['plug_pr_big'].get(k)


def ring_big(diam, pitch, side='пр'):
    """Цена кольца (ПР или НЕ) для резьбы >100 мм или None."""
    _ensure()
    k = (round(float(diam), 3), round(float(pitch), 3))
    if side == 'не':
        return _cache['ring_ne_big'].get(k)
    return _cache['ring_pr_big'].get(k)


def available_sizes():
    """Возвращает set всех (diam, pitch) из прайса (для отладки)."""
    _ensure()
    return set(_cache['plug_combo']) | set(_cache['ring_pr']) | \
           set(_cache['plug_pr_big']) | set(_cache['ring_pr_big'])
