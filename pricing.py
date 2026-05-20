# -*- coding: utf-8 -*-
"""Правила расчёта цен калибров ВЕГАЛИБР"""

import re

NDS  = 0.22
DISC = 0.20   # скидка на товар

# ── Скобы: цены по таблице колец h8/h9+ ────────────────────────────────────
_SKOBA_RANGES = [
    # (min_excl, max_incl, price_h67, price_h8plus)
    (2.0,   3.0,  23700.0,  21700.0),
    (3.0,   5.0,  18740.0,  16740.0),
    (5.0,  60.0,  10757.0,   8667.0),
    (60.0,  80.0, 12841.5,  10757.0),
    (80.0, 101.0, 14937.0,  11450.0),
    (102.0,120.0, 20514.0,      None),
    (122.0,140.0, 25398.0,      None),
    (142.0,160.0, 30260.0,      None),
    (162.0,180.0, 34451.0,      None),
    (182.0,200.0, 39329.5,      None),
    (202.0,220.0, 42805.5,      None),
    (222.0,240.0, 49774.0,      None),
    (242.0,260.0, 69685.0,      None),
    (262.0,280.0, 69685.0,      None),
    (282.0,300.0, 84616.5,      None),
    (302.0,320.0,126422.0,      None),
    (322.0,340.0,154301.5,      None),
]

def skoba_price(size, name=""):
    """Цена скобы по таблице колец h8/h9+. Размеры < 2 мм → диапазон 2–3 мм."""
    s = max(size, 2.001)
    for mn, mx, p67, p8 in _SKOBA_RANGES:
        if s > mn and s <= mx:
            return p8 if p8 is not None else p67
    return None

# ── Пробки гладкие (комплект ПР-НЕ, 10+ шт) ────────────────────────────────
def proba_price(size):
    if size < 1.0:   return None       # <1мм — уточнить
    if size in (1.0, 1.2, 1.4, 1.5, 1.6): return 5400.0
    if size <= 1.6:  return 8797.80
    if size <= 14.0: return 4111.80
    if size <= 18.0: return 4527.60
    if size <= 24.0: return 4923.60
    if size <= 30.0: return 5755.20
    if size <= 38.0: return 6580.20
    return None   # >38мм — уточнить

# ── Калибровка ───────────────────────────────────────────────────────────────
def kalib_price(kind, size, name):
    if kind == "пробка":
        if size <= 18.0: return 910
        if size <= 60.0: return 850
    elif kind == "скоба":
        m = re.search(r'[a-zA-Z](\d+)', name.split('ГОСТ')[0])
        qual = int(m.group(1)) if m else 11
        if size <= 18.0:
            return 970 if qual <= 10 else 850
        if size <= 60.0:
            return 850
    return 0

# ── Парсинг наименования ─────────────────────────────────────────────────────
def parse_caliber(name):
    """
    Разбирает наименование калибра.
    Возвращает (kind, size) или None.
    kind: 'скоба' | 'пробка'
    """
    if not name:
        return None
    nl = name.lower().strip()

    # Скоба
    if 'скоба' in nl:
        m = re.search(r'скоба\s+(\d+[,.]?\d*)', nl)
        if m:
            size = float(m.group(1).replace(',', '.'))
            return ('скоба', size)

    # Пробка
    if 'пробка' in nl:
        m = re.search(r'пробка\s+(?:гладкая\s+)?(\d+[,.]?\d*)', nl)
        if m:
            size = float(m.group(1).replace(',', '.'))
            return ('пробка', size)

    return None

def calc_item(name, qty):
    """
    Считает одну позицию.
    Возвращает dict или None (если цена не определена).
    """
    parsed = parse_caliber(name)
    if parsed is None:
        return None

    kind, size = parsed
    if kind == 'скоба':
        price = skoba_price(size, name)
    else:
        price = proba_price(size)

    if price is None:
        return None

    kal   = kalib_price(kind, size, name)
    disc  = round(price * DISC, 2)
    price_d = round(price - disc, 2)
    summa   = round(qty * (price_d + kal), 2)
    nds_s   = round(summa * NDS, 2)
    itogo   = round(summa + nds_s, 2)

    return {
        'name':    name,
        'ed':      'шт.',
        'qty':     qty,
        'price':   price,
        'disc':    disc,
        'price_d': price_d,
        'kal':     kal,
        'summa':   summa,
        'nds':     nds_s,
        'itogo':   itogo,
    }
