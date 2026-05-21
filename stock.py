# -*- coding: utf-8 -*-
"""Остатки склада ВЕГАЛИБР — читает СКЛАД ВЕГАЛИБР (1).xlsx напрямую как ZIP/XML."""

import re
import os
import zipfile
import xml.etree.ElementTree as ET

_STOCK  = {}   # key → (price, qty)
_LOADED = False
_WNS    = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


# ── Загрузка ──────────────────────────────────────────────────────────────────

def _load():
    global _STOCK, _LOADED
    if _LOADED:
        return
    _LOADED = True

    here = os.path.dirname(os.path.abspath(__file__))
    candidates = []
    for fname in ('СКЛАД ВЕГАЛИБР (1).xlsx', 'СКЛАД ВЕГАЛИБР.xlsx'):
        candidates.append(os.path.join(here, fname))
        candidates.append(os.path.join(os.path.dirname(here), fname))

    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        return

    try:
        with zipfile.ZipFile(path) as z:
            sst = _read_sst(z)
            rid_map = _read_rels(z)
            sheet_map = _read_sheet_names(z, rid_map)

            for name, fpath in sheet_map.items():
                nl = name.lower()
                if 'кольц' in nl:
                    _parse_rings(z, fpath, sst)
                elif 'пробк' in nl:
                    _parse_plugs(z, fpath, sst)
    except Exception:
        pass


def _read_sst(z):
    """Читает таблицу общих строк SharedStrings."""
    sst = {}
    if 'xl/sharedStrings.xml' not in z.namelist():
        return sst
    for i, si in enumerate(ET.parse(z.open('xl/sharedStrings.xml')).getroot().findall(f'{_WNS}si')):
        sst[i] = ''.join(t.text or '' for t in si.iter(f'{_WNS}t'))
    return sst


def _read_rels(z):
    rns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
    rels = ET.parse(z.open('xl/_rels/workbook.xml.rels')).getroot()
    return {r.get('Id'): r.get('Target') for r in rels}


def _read_sheet_names(z, rid_map):
    rns = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
    wb = ET.parse(z.open('xl/workbook.xml')).getroot()
    result = {}
    for sh in wb.iter(f'{_WNS}sheet'):
        rid  = sh.get(f'{rns}id') or sh.get('r:id') or ''
        path = rid_map.get(rid, '')
        if path:
            result[sh.get('name', '')] = 'xl/' + path
    return result


def _cell_val(c, sst):
    t    = c.get('t', '')
    v_el = c.find(f'{_WNS}v')
    if v_el is None:
        return ''
    v = v_el.text or ''
    if t == 's' and v:
        return sst.get(int(v), v)
    return v


def _col(ref):
    return ''.join(ch for ch in (ref or '') if ch.isalpha())


def _to_float(s):
    """Парсит число: '5 995', '9 500,00', '5995' → float."""
    if not s:
        return None
    s = str(s).replace('\xa0', '').replace(' ', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def _parse_rings(z, fpath, sst):
    """Кольца: A=имя, C=цена, D=остаток."""
    root = ET.parse(z.open(fpath)).getroot()
    for row in root.iter(f'{_WNS}row'):
        cells = {_col(c.get('r','')): _cell_val(c, sst) for c in row.findall(f'{_WNS}c')}
        name  = str(cells.get('A', '')).strip()
        price = _to_float(cells.get('C'))
        qty   = _to_float(cells.get('D'))
        if not name or price is None or qty is None:
            continue
        k = _make_key(name, 'к')
        if k:
            _STOCK[k] = (price, int(qty))


def _parse_plugs(z, fpath, sst):
    """Пробки: B=имя, D=цена, E=остаток."""
    root = ET.parse(z.open(fpath)).getroot()
    for row in root.iter(f'{_WNS}row'):
        cells = {_col(c.get('r','')): _cell_val(c, sst) for c in row.findall(f'{_WNS}c')}
        name  = str(cells.get('B', '')).strip()
        price = _to_float(cells.get('D'))
        qty   = _to_float(cells.get('E'))
        if not name or price is None or qty is None:
            continue
        k = _make_key(name, 'п')
        if k:
            _STOCK[k] = (price, int(qty))


# ── Ключ для поиска ───────────────────────────────────────────────────────────

def _make_key(name, default_kind='к'):
    nl = name.lower()

    if 'кольцо' in nl:
        kind = 'к'
    elif 'пробка' in nl or (default_kind == 'п' and re.search(r'[мm]\s*\d', nl)):
        kind = 'п'
    else:
        return None

    m = re.search(r'[мm]\s*(\d+[,.]?\d*)\s*[×xхХ]\s*(\d+[,.]?\d*)', nl)
    if not m:
        return None

    diam  = round(float(m.group(1).replace(',', '.')), 3)
    pitch = round(float(m.group(2).replace(',', '.')), 3)

    qm   = re.search(r'\b(\d+[hHgGeE](?:\d+[hHgGeE])?)\b', name)
    qual = qm.group(1).lower() if qm else ''

    nu = name.upper()
    if re.search(r'\bНЕ\b', nu) and 'ПР' not in nu:
        side = 'не'
    elif 'ПР-НЕ' in nu or 'ПР/НЕ' in nu:
        side = 'пр-не'
    else:
        side = 'пр'

    return (kind, diam, pitch, qual, side)


# ── Публичный API ─────────────────────────────────────────────────────────────

def lookup(name):
    """
    Ищет позицию в складе.
    Возвращает (price, qty) или None.
    """
    _load()
    if not _STOCK:
        return None

    k = _make_key(name)
    if not k:
        return None

    r = _STOCK.get(k)
    if r:
        return r

    # Без учёта квалитета
    kind, diam, pitch, qual, side = k
    if qual:
        for (kk, kd, kp, kq, ks), v in _STOCK.items():
            if kk == kind and abs(kd - diam) < 0.02 and abs(kp - pitch) < 0.02 and ks == side:
                return v

    return None
