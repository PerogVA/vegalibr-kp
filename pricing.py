# -*- coding: utf-8 -*-
"""Правила расчёта цен калибров ВЕГАЛИБР"""

import re, math

NDS  = 0.22
DISC = 0.20   # скидка на товар (по умолчанию)

# Стандартный шаг метрической резьбы (ГОСТ 24705)
_STANDARD_PITCH = {
    1.0: 0.25, 1.1: 0.25, 1.2: 0.25, 1.4: 0.3,  1.6: 0.35, 1.8: 0.35,
    2.0: 0.4,  2.2: 0.45, 2.5: 0.45, 3.0: 0.5,  3.5: 0.6,
    4.0: 0.7,  4.5: 0.75, 5.0: 0.8,  6.0: 1.0,  7.0: 1.0,
    8.0: 1.25, 9.0: 1.25, 10.0: 1.5, 11.0: 1.5, 12.0: 1.75,
    14.0: 2.0, 16.0: 2.0, 18.0: 2.5, 20.0: 2.5, 22.0: 2.5,
    24.0: 3.0, 27.0: 3.0, 30.0: 3.5, 33.0: 3.5, 36.0: 4.0,
    39.0: 4.0, 42.0: 4.5, 45.0: 4.5, 48.0: 5.0, 52.0: 5.0,
    56.0: 5.5, 60.0: 5.5, 64.0: 6.0, 68.0: 6.0,
}

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
    """Цена скобы по таблице колец h8/h9+."""
    s = max(size, 2.001)
    for mn, mx, p67, p8 in _SKOBA_RANGES:
        if s > mn and s <= mx:
            return p8 if p8 is not None else p67
    return None

# ── Пробки гладкие (комплект ПР-НЕ, 10+ шт) ────────────────────────────────
_PROBA_NOT_IN_PRICE = {1.3}   # нестандарт, нет в прайсе → АА

def proba_price(size):
    if size < 1.0:   return None
    if size < 2.0:
        if round(size, 2) in _PROBA_NOT_IN_PRICE:
            return None   # нет в прайсе → АА
        return 5400.0
    if size <= 14.0:  return 4111.80
    if size <= 18.0:  return 4527.60
    if size <= 24.0:  return 4923.60
    if size <= 30.0:  return 5755.20
    if size <= 38.0:  return 6580.20
    if size <= 44.0:  return 8223.60
    if size <= 50.0:  return 9860.40
    if size <= 60.0:  return 20539.20
    if size <= 70.0:  return 23007.60
    if size <= 80.0:  return 26287.80
    if size <= 90.0:  return 28756.20
    if size <= 100.0: return 31224.60
    if size <= 110.0: return 31224.60
    if size <= 120.0: return 33679.80
    if size <= 130.0: return 36960.00
    if size <= 140.0: return 39428.40
    if size <= 150.0: return 45183.60
    if size <= 160.0: return 49288.80
    if size <= 170.0: return 52575.60
    if size <= 180.0: return 55855.80
    if size <= 190.0: return 61604.40
    if size <= 200.0: return 65716.20
    return None


# ── Кольца гладкие (ПР или НЕ, 1 шт) ───────────────────────────────────────
# Источник: прайс sheet3, колонки ПР / НЕ
_RING_SMOOTH_PR = [
    (5,   15120), (35,  3970),  (40,  9831),  (45,  10588),
    (50,  11344), (55,  12100), (60,  12855), (65,  13610),
    (70,  14365), (75,  15120), (80,  15876), (85,  16633),
    (90,  17389), (95,  18145), (100, 18750), (105, 19355),
    (110, 19960), (115, 20565), (120, 21170), (125, 23330),
    (130, 25490), (135, 27650), (140, 29810), (145, 31970),
    (150, 34130), (155, 36290), (160, 43010), (165, 49730),
    (170, 56450), (175, 63170), (180, 69890), (185, 76610),
    (190, 83330), (195, 90050), (200, 96770), (205, 99189),
    (210, 101608),(215, 104027),(220, 106446),(225, 108865),
    (230, 111284),(235, 113703),(240, 116122),(245, 118541),
    (250, 120960),
]
_RING_SMOOTH_NE = [
    (5,   15120), (35,  13970), (40,  9831),  (45,  10588),
    (50,  11344), (55,  12100), (60,  12855), (65,  13610),
    (70,  14365), (75,  15120), (80,  15876), (85,  16633),
    (90,  17389), (95,  18145), (100, 18750), (105, 19355),
    (110, 19960), (115, 20565), (120, 21170), (125, 23330),
    (130, 25490), (135, 27650), (140, 29810), (145, 31970),
    (150, 34130), (155, 36290), (160, 43010), (165, 49730),
    (170, 56450), (175, 63170), (180, 69890), (185, 76610),
    (190, 83330), (195, 90050), (200, 96770), (205, 99189),
    (210, 101608),(215, 104027),(220, 106446),(225, 108865),
    (230, 111284),(235, 113703),(240, 116122),(245, 118541),
    (250, 120960),
]

def ring_smooth_price(size, side='пр'):
    """Цена гладкого кольца (ПР или НЕ)."""
    table = _RING_SMOOTH_NE if side == 'не' else _RING_SMOOTH_PR
    for max_sz, price in table:
        if size <= max_sz:
            return float(price)
    return None


# ── Установочные кольца ──────────────────────────────────────────────────────
_USTANOV_RING = [
    (3.9,  12837.0), (5.9,   8800.0), (23.0,  7331.5),
    (39.0,  9168.5), (64.0, 12100.0), (79.0, 12837.0),
    (99.0, 14674.0), (109.0,14674.0), (119.0,16142.5),
    (129.0,20537.0), (139.0,25674.0), (149.0,30800.0),
    (159.0,36679.5), (169.0,51337.0), (179.0,58679.5),
    (189.0,66011.0), (199.0,73353.5), (229.0,95359.0),
    (259.0,117364.5),(309.0,183370.0),(359.0,220049.5),
]

def ustanov_ring_price(size):
    for max_sz, price in _USTANOV_RING:
        if size <= max_sz:
            return price
    return None

# ── Калибровка гладких ───────────────────────────────────────────────────────
def kalib_price(kind, size, name):
    if kind == "пробка":
        if size <= 18.0: return 910
        if size <= 60.0: return 850
        return 0   # >60мм — уточнять
    elif kind == "кольцо_гладкое":
        if size <= 18.0: return 910
        if size <= 60.0: return 850
        return 0
    elif kind == "установочное_кольцо":
        return 0   # поверка не включается
    elif kind == "скоба":
        # Граница по размеру (не по квалитету):
        # < 2 мм (листовые по ГОСТ 18358-93) → 970; ≥ 2 мм → 850
        if size < 2.0:
            return 970
        if size <= 60.0:
            return 850
    return 0

# ══════════════════════════════════════════════════════════════════════════════
# РЕЗЬБОВЫЕ КАЛИБРЫ
# Источник цен: «Прайс калибры (1).xlsx», лист «Метрическая резьба до 100»
# Столбцы: ПРОБКА ПР-НЕ (комплект), КОЛЬЦО ПР, КОЛЬЦО НЕ
#
# Правило «Жёлтый ценник» (М4–М22, цена кольца ≤ 5 000):
#   цена продажи кольца = base + round(plug_combo / 4)
#   (к цене кольца прибавляется 1 контрольная пробка)
#
# Поверка: кольцо = 880 р./шт; пробка ≤50 мм = 1 760 р./компл.;
#          кольцо/пробка >50 мм = 1 280 р./шт.
# ══════════════════════════════════════════════════════════════════════════════

# Базовые цены колец (прайс, до применения жёлтого ценника)
# (диаметр, шаг) → цена кольца (ПР = НЕ, если не указано иначе)
_RING_BASE = {
    (1.4,  0.3 ): 7667,
    (1.6,  0.35): 11011,
    (2.0,  0.4 ): 5577,
    (2.0,  0.25): 5577,
    (2.5,  0.45): 4543,
    (2.5,  0.35): 5577,
    (3.0,  0.5 ): 4543,
    (3.0,  0.35): 5577,
    (4.0,  0.7 ): 4180,
    (4.0,  0.5 ): 4180,
    (5.0,  0.8 ): 4180,
    (5.0,  0.5 ): 4180,
    (6.0,  1.0 ): 4180,
    (6.0,  0.75): 4180,
    (6.0,  0.5 ): 4180,
    (8.0,  1.25): 4180,
    (8.0,  1.0 ): 4180,
    (8.0,  0.75): 4180,
    (8.0,  0.5 ): 4180,
    (10.0, 1.5 ): 4180,
    (10.0, 1.25): 4180,
    (10.0, 1.0 ): 4180,
    (10.0, 0.75): 4180,
    (12.0, 1.75): 4180,
    (12.0, 1.5 ): 4180,
    (12.0, 1.25): 4180,
    (12.0, 1.0 ): 4180,
    (14.0, 2.0 ): 4180,
    (14.0, 1.5 ): 4180,
    (14.0, 1.25): 4180,
    (14.0, 1.0 ): 4180,
    (16.0, 2.0 ): 4180,
    (16.0, 1.5 ): 4180,
    (16.0, 1.25): 4202,
    (16.0, 1.0 ): 4180,
    (18.0, 2.5 ): 4543,
    (18.0, 2.0 ): 4543,
    (18.0, 1.5 ): 4543,
    (18.0, 1.0 ): 4884,
    (20.0, 2.5 ): 4884,
    (20.0, 2.0 ): 4884,
    (20.0, 1.5 ): 4180,
    (20.0, 1.0 ): 4884,
    (22.0, 2.5 ): 4884,
    (22.0, 2.0 ): 4884,
    (22.0, 1.5 ): 4884,
    (22.0, 1.0 ): 5577,
    (24.0, 3.0 ): 6281,
    (24.0, 2.5 ): 5995,
    (24.0, 2.0 ): 4884,
    (24.0, 1.5 ): 4884,
    (24.0, 1.0 ): 5577,
    (27.0, 3.0 ): 5929,
    (27.0, 2.0 ): 4884,
    (27.0, 1.5 ): 4884,
    (27.0, 1.0 ): 5577,
    (30.0, 3.5 ): 8712,
    (30.0, 3.0 ): 5577,
    (30.0, 2.0 ): 5577,
    (30.0, 1.5 ): 6974,
    (30.0, 1.0 ): 8371,
    (33.0, 3.5 ): 8712,
    (33.0, 3.0 ): 5577,
    (33.0, 2.0 ): 5577,
    (33.0, 1.5 ): 7326,
    (36.0, 4.0 ): 10109,
    (36.0, 3.0 ): 6622,
    (36.0, 2.0 ): 6622,
    (36.0, 1.5 ): 8712,
    (39.0, 4.0 ): 10450,
    (39.0, 3.0 ): 6622,
    (39.0, 2.0 ): 6622,
    (39.0, 1.5 ): 8712,
    (42.0, 4.5 ): 13937,
    (42.0, 4.0 ): 10450,
    (42.0, 3.0 ): 10450,
    (42.0, 2.0 ): 11847,
    (42.0, 1.5 ): 12551,
    (42.0, 1.0 ): 13937,
    (45.0, 4.5 ): 13937,
    (45.0, 4.0 ): 10450,
    (45.0, 3.0 ): 10450,
    (45.0, 2.0 ): 11847,
    (45.0, 1.5 ): 12551,
    (45.0, 1.0 ): 13937,
    (48.0, 5.0 ): 16038,
    (48.0, 4.0 ): 12199,
    (48.0, 3.0 ): 10450,
    (48.0, 2.0 ): 12551,
    (48.0, 1.5 ): 12892,
    (48.0, 1.0 ): 16038,
    (52.0, 5.0 ): 16038,
    (52.0, 4.0 ): 12199,
    (52.0, 3.0 ): 10450,
    (52.0, 2.0 ): 12551,
    (52.0, 1.5 ): 12892,
    (55.0, 0.5 ): 32500,   # нестандарт
    (56.0, 5.5 ): 18128,
    (56.0, 4.0 ): 12892,
    (56.0, 3.0 ): 12551,
    (56.0, 2.0 ): 12892,
    (56.0, 1.5 ): 27181,   # счёт 1324: 28461 − 1280 (kalib >50мм)
    (57.0, 0.5 ): 32500,   # нестандарт
    (60.0, 5.5 ): 20911,
    (60.0, 4.0 ): 16038,
    (60.0, 3.0 ): 14641,
    (60.0, 2.0 ): 14641,
    (64.0, 6.0 ): 27874,
    (64.0, 4.0 ): 19866,
    (64.0, 3.0 ): 18469,
    (64.0, 2.0 ): 19866,
    (68.0, 6.0 ): 29260,
    (68.0, 4.0 ): 22308,
    (68.0, 3.0 ): 19866,
    (68.0, 2.0 ): 20911,
}

# Разные цены для НЕ (если ПР ≠ НЕ)
_RING_BASE_NE = {
    (55.0, 0.5): 29250,
    (57.0, 0.5): 29250,
}

# Комплектные цены пробок ПР-НЕ (прайс, ≤50 мм)
# Для >50 мм: цена за штуку = round((combo / 2) × 1,2)
_PLUG_COMBO = {
    (1.4,  0.3 ): 6281,
    (1.6,  0.35): 7667,
    (2.0,  0.4 ): 4543,
    (2.0,  0.25): 5577,
    (2.5,  0.45): 4543,
    (2.5,  0.35): 5577,
    (3.0,  0.5 ): 4543,
    (3.0,  0.35): 5577,
    (4.0,  0.7 ): 3487,
    (4.0,  0.5 ): 3487,
    (5.0,  0.8 ): 3487,
    (5.0,  0.5 ): 3487,
    (6.0,  1.0 ): 3487,
    (6.0,  0.75): 3487,
    (6.0,  0.5 ): 3487,
    (8.0,  1.25): 3487,
    (8.0,  1.0 ): 3487,
    (8.0,  0.75): 3487,
    (8.0,  0.5 ): 3487,
    (10.0, 1.5 ): 3487,
    (10.0, 1.25): 3487,
    (10.0, 1.0 ): 3487,
    (10.0, 0.75): 4180,
    (12.0, 1.75): 3487,
    (12.0, 1.5 ): 3487,
    (12.0, 1.25): 3487,
    (12.0, 1.0 ): 3839,
    (14.0, 2.0 ): 3487,
    (14.0, 1.5 ): 3487,
    (14.0, 1.25): 3487,
    (14.0, 1.0 ): 4180,
    (16.0, 2.0 ): 3487,
    (16.0, 1.5 ): 3487,
    (16.0, 1.25): 3949,
    (16.0, 1.0 ): 4180,
    (18.0, 2.5 ): 3487,
    (18.0, 2.0 ): 3487,
    (18.0, 1.5 ): 3487,
    (18.0, 1.0 ): 4180,
    (20.0, 2.5 ): 3487,
    (20.0, 2.0 ): 3487,
    (20.0, 1.5 ): 3487,
    (20.0, 1.0 ): 4180,
    (22.0, 2.5 ): 3487,
    (22.0, 2.0 ): 3487,
    (22.0, 1.5 ): 3487,
    (22.0, 1.0 ): 4180,
    (24.0, 3.0 ): 4543,
    (24.0, 2.5 ): 4543,
    (24.0, 2.0 ): 4543,
    (24.0, 1.5 ): 4543,
    (24.0, 1.0 ): 4543,
    (27.0, 3.0 ): 4543,
    (27.0, 2.0 ): 4180,
    (27.0, 1.5 ): 4180,
    (27.0, 1.0 ): 4180,
    (30.0, 3.5 ): 5577,
    (30.0, 3.0 ): 4543,
    (30.0, 2.0 ): 4180,
    (30.0, 1.5 ): 4884,
    (33.0, 3.5 ): 5225,
    (33.0, 3.0 ): 4543,
    (33.0, 2.0 ): 4180,
    (36.0, 4.0 ): 7667,
    (36.0, 3.0 ): 5929,
    (36.0, 2.0 ): 4884,
    (36.0, 1.5 ): 5225,
    (39.0, 4.0 ): 7667,
    (39.0, 3.0 ): 5929,
    (39.0, 2.0 ): 5577,
    (42.0, 4.5 ): 10109,
    (42.0, 4.0 ): 8712,
    (42.0, 3.0 ): 7667,
    (42.0, 2.0 ): 6974,
    (42.0, 1.5 ): 6974,
    (42.0, 1.0 ): 8712,
    (45.0, 4.5 ): 10109,
    (45.0, 4.0 ): 8712,
    (45.0, 3.0 ): 7667,
    (45.0, 2.0 ): 6974,
    (45.0, 1.5 ): 6974,
    (45.0, 1.0 ): 9416,
    (48.0, 5.0 ): 11154,
    (48.0, 4.0 ): 10109,
    (48.0, 3.0 ): 8712,
    (48.0, 2.0 ): 8008,
    (48.0, 1.5 ): 8008,
    (48.0, 1.0 ): 10109,
    (52.0, 5.0 ): 11154,
    (52.0, 4.0 ): 10109,
    (52.0, 3.0 ): 8712,
    (52.0, 2.0 ): 8008,
    (52.0, 1.5 ): 8008,
    # >50 мм — цена за штуку = round((combo/2)×1,2)
    (56.0, 5.5 ): 12199,
    (56.0, 4.0 ): 11154,
    (56.0, 3.0 ): 10109,
    (56.0, 2.0 ): 10109,
    (60.0, 5.5 ): 13937,
    (60.0, 4.0 ): 12551,
    (60.0, 3.0 ): 11495,
    (60.0, 2.0 ): 11495,
    (64.0, 6.0 ): 15686,
    (64.0, 4.0 ): 12551,
    (64.0, 3.0 ): 12551,
    (68.0, 6.0 ): 16038,
    (68.0, 4.0 ): 13244,
    (68.0, 3.0 ): 12551,
}

# Порог «жёлтого ценника»: если base ≤ этому значению — добавляем контр-пробку
_YELLOW_MAX = 5000


def _ring_selling(diam, pitch, side):
    """
    Цена продажи кольца (с учётом жёлтого ценника для base ≤ 5 000).
    """
    key = (float(diam), float(pitch))
    if side == 'не' and key in _RING_BASE_NE:
        base = _RING_BASE_NE[key]
    else:
        base = _RING_BASE.get(key)
    if base is None:
        return None
    if base <= _YELLOW_MAX:
        plug = _PLUG_COMBO.get(key)
        if plug is not None:
            addon = round(plug / 4)
            return base + addon
    return base


def _plug_selling(diam, pitch, is_combo):
    """
    Цена пробки.
    ≤50 мм: всегда цена комплекта ПР-НЕ (продаётся только комплектом).
    >50 мм: round((combo/2)×1,2) за штуку (ПР или НЕ).
    """
    key = (float(diam), float(pitch))
    combo = _PLUG_COMBO.get(key)
    if combo is None:
        return None
    if float(diam) > 50:
        return round((combo / 2) * 1.2)
    return combo   # ≤50мм — всегда комплект, ПР/НЕ/ПР-НЕ → одна цена


def _kalib_thread(kind, diam, is_combo):
    """Поверка резьбовых калибров."""
    d = float(diam)
    if kind == 'кольцо_резьбовое':
        return 1280 if d > 50 else 880
    elif kind == 'пробка_резьбовая':
        if d > 50:
            return 1280
        return 880  # ≤50мм: одна поверка на комплект ПР-НЕ
    return 0


# ── Парсинг наименования резьбового калибра ──────────────────────────────────
def parse_thread_ring(name):
    """
    Парсит наименование резьбового кольца/пробки.
    Возвращает (kind, diam, pitch, side, is_combo) или None.
    Если шаг не указан — берёт стандартный по ГОСТ 24705.
    """
    if not name:
        return None
    nl = name.lower()

    # Тип
    if 'кольцо' in nl:
        kind = 'кольцо_резьбовое'
    elif 'пробка' in nl and re.search(r'[мm]', nl):
        kind = 'пробка_резьбовая'
    else:
        return None

    # М<диаметр>×<шаг>
    m = re.search(r'м\s*(\d+[,.]?\d*)\s*[×xхХ]\s*(\d+[,.]?\d*)', nl)
    if m:
        diam  = float(m.group(1).replace(',', '.'))
        pitch = float(m.group(2).replace(',', '.'))
    else:
        # М<диаметр> без шага — пробуем стандартный шаг
        m2 = re.search(r'м\s*(\d+[,.]?\d*)', nl)
        if not m2:
            return None
        diam = float(m2.group(1).replace(',', '.'))
        pitch = _STANDARD_PITCH.get(diam)
        if pitch is None:
            return None   # нестандартный размер → в АА

    nu = name.upper()
    is_combo = ('ПР/НЕ' in nu or 'ПР-НЕ' in nu or 'PR/NE' in nu)
    if ' НЕ' in nu or nu.rstrip().endswith('НЕ'):
        side = 'не'
    else:
        side = 'пр'

    return (kind, diam, pitch, side, is_combo)


# ══════════════════════════════════════════════════════════════════════════════
# ДЮЙМОВЫЕ / ТРУБНЫЕ РЕЗЬБЫ
# Источник: «Прайс калибры (1) (1).xlsx»
# Ключ: нормализованный размер без дюймового знака ('1/4', '1 1/4', '1"' → '1')
# ══════════════════════════════════════════════════════════════════════════════

def _ns(s):
    """Нормализует дюймовый размер: '1/4"' → '1/4',  '1"' → '1'"""
    return re.sub(r'["\'\s]+$', '', str(s).strip().rstrip('"\''))

# ── NPT (American National Taper Pipe) ──────────────────────────────────────
# plug = Р-Р комплект, ring = Р-Р
_NPT = {
    '1/16': (10626, 28083), '1/8':  (6787,  18590), '1/4':  (6787,  18590),
    '3/8':  (6787,  18590), '1/2':  (9735,  24783), '3/4':  (9735,  24783),
    '1':    (12980, 30679), '1 1/4':(18887, 38346), '1 1/2':(20647, 41294),
    '2':    (22715, 45430), '2 1/2':(22715, 45430), '3':    (24783, 49555),
    '3 1/2':(26554, 51920), '4':    (28325, 56045),
}
# ── NPSM (American National Straight Mechanical) ────────────────────────────
# plug = ПР+НЕ комплект, ring = ПР+НЕ комплект
_NPSM = {
    '1/8':  (5577,  8151),  '1/4':  (5577,  8745),  '3/8':  (5577,  8745),
    '1/2':  (5577,  8745),  '3/4':  (6512,  9658),  '1':    (8371,  14784),
    '1 1/4':(13475, 21417), '1 1/2':(14410, 23529), '2':    (17193, 26235),
    '2 1/2':(23694, 57299), '3':    (29271, 66946),  '3 1/2':(36234, 81422),
    '4':    (72941, 124542),
}
# ── PT (British Standard Taper Pipe) ────────────────────────────────────────
# plug = Р-Р комплект, ring = Р-Р
_PT = {
    '1/16': (14410, 36234), '1/8':  (9757,  23232), '1/4':  (9757,  23232),
    '3/8':  (9757,  23232), '1/2':  (13013, 31592), '3/4':  (13013, 31592),
    '1':    (18590, 40887), '1 1/4':(26015, 50171), '1 1/2':(26015, 50171),
    '2':    (27874, 58069), '2 1/2':(29733, 60390), '3':    (33451, 64108),
    '3 1/2':(35310, 65967), '4':    (37169, 73403),
}
# ── G (BSP Parallel / Трубная цилиндрическая) ───────────────────────────────
# plug = ПР+НЕ комплект, ring_pr / ring_ne
_G = {
    'G 1/8':   (3487,  4961,  4961),  'G 1/4':   (3487,  4961,  4961),
    'G 3/8':   (3487,  5720,  5720),  'G 1/2':   (3916,  5720,  5720),
    'G 5/8':   (3916,  5929,  5929),  'G 3/4':   (4752,  6699,  6699),
    'G 7/8':   (4752,  6699,  6699),  'G 1':     (5302,  7590,  7590),
    'G 1 1/8': (5720,  7590,  7590),  'G 1 1/4': (6138,  10637, 10637),
    'G 1 3/8': (6138,  9900,  9900),  'G 1 1/2': (7535,  11011, 11011),
    'G 1 3/4': (8371,  11847, 11847), 'G 2':     (10186, 12760, 12760),
    'G 2 1/4': (13178, 16929, 16929), 'G 2 1/2': (19162, 19096, 19096),
    'G 2 3/4': (20559, 21956, 21956), 'G 3':     (20559, 29832, 29832),
    'G 4':     (52536, 47465, 47465), 'G 5':     (74360, 75955, 75955),
    'G 6':     (257202,215248,215248),
}
# ── BSW (British Standard Whitworth) ────────────────────────────────────────
# plug = ПР+НЕ комплект, ring_pr / ring_ne
_BSW = {
    'BSW 1/4':   (4807,  5852,  5852),  'BSW 5/16':  (5434,  6204,  6204),
    'BSW 3/8':   (5434,  6204,  6204),  'BSW 7/16':  (5434,  6204,  6204),
    'BSW 1/2':   (5643,  6413,  6413),  'BSW 9/16':  (5643,  6413,  6413),
    'BSW 5/8':   (6138,  6831,  6831),  'BSW 3/4':   (7040,  7667,  7667),
    'BSW 7/8':   (7249,  8371,  8371),  'BSW 1':     (8855,  8371,  8371),
    'BSW 1 1/8': (14289, 10736, 10736), 'BSW 1 1/4': (14641, 11022, 11022),
    'BSW 1 3/8': (16929, 13464, 13464), 'BSW 1 1/2': (17138, 13728, 13728),
    'BSW 1 5/8': (17138, 13728, 13728), 'BSW 1 3/4': (18678, 15752, 15752),
    'BSW 1 7/8': (20493, 17842, 17842), 'BSW 2':     (20911, 18051, 18051),
}

_INCH_KALIB = 2180   # поверка трубных / дюймовых калибров, руб./шт.

# ── UN / UNF / UNC (Unified Inch Threads) ────────────────────────────────────
# Ключ: 'nominal-TPI'  напр. '1 1/8-12', '1 7/8-16'
# Значение: (ring_pr, ring_ne, ring_combo, plug_pr, plug_ne, plug_combo)
# None = нет в прайсе → АА
_UNIFIED = {
    # (ring_pr, ring_ne, ring_combo, plug_pr, plug_ne, plug_combo)
    # Цены LIST (без скидки, без поверки)
    '1 1/16-14': (None,  None,  20025, None, None, None),   # UNF-3А комплект
    '1 1/8-12':  (11900, 8650,  None,  None, None, None),   # UNF 2A
    '1 7/8-16':  (18400, 13525, None,  None, None, None),   # UN  2A
    '1 7/8-12':  (13836, 13836, None,  None, None, None),   # UN  (счёт 1355)
}

# ── STUB ACME ─────────────────────────────────────────────────────────────────
# Ключ: 'diam_inch-TPI'  (запятую → точку),  LH-исполнение: + '-LH'
# Значение: (plug_pr, plug_ne, ring_pr, ring_ne)
_STUB_ACME = {
    '4.224-8':    (104000, 91000,  None,   None  ),
    '4.377-8':    (None,   None,   195000, 182000),
    '4.750-8-LH': (None,   None,   208000, 195000),
}


def _parse_inch_size(name_upper):
    """Извлекает нормализованный дюймовый размер из имени."""
    m = re.search(r'(\d+\s+\d+/\d+|\d+/\d+|\d+)\s*["\']?', name_upper)
    if not m:
        return None
    raw = m.group(1).strip()
    return raw  # например '1/4' или '1 1/4' или '1'


def parse_inch_thread(name):
    """
    Парсит дюймовые/трубные резьбовые калибры:
    NPT, NPSM, PT, G, BSW.
    Возвращает ('inch', type_code, is_plug, key, side) или None.
    type_code: 'npt'|'npsm'|'pt'|'g'|'bsw'
    key: ключ для поиска в соответствующем dict
    side: 'пр'|'не' (для G/BSW колец)
    """
    if not name:
        return None
    nu = name.upper().strip()
    nl = name.lower().strip()

    # Определяем тип
    if 'NPSM' in nu:
        tcode = 'npsm'
    elif 'NPT' in nu:
        tcode = 'npt'
    elif re.search(r'\bPT\b', nu) and 'G' not in nu and 'BSW' not in nu:
        tcode = 'pt'
    elif re.search(r'\bBSW\b', nu):
        tcode = 'bsw'
    elif re.search(r'\bG\s+\d', nu) or re.search(r'\bG\s+\d', nu):
        tcode = 'g'
    else:
        return None

    is_plug = 'пробк' in nl or 'plug' in nl or ('пробк' not in nl and 'кольц' not in nl and 'ring' not in nl)
    if 'кольц' in nl or 'ring' in nl:
        is_plug = False

    # Сторона для G/BSW колец
    if ' НЕ' in nu or nu.rstrip().endswith(' НЕ') or 'NOGO' in nu:
        side = 'не'
    else:
        side = 'пр'

    # Строим ключ поиска
    size = _parse_inch_size(nu)
    if size is None:
        return None

    if tcode == 'g':
        key = f'G {size}'
    elif tcode == 'bsw':
        key = f'BSW {size}'
    else:
        key = size

    return ('inch', tcode, is_plug, key, side)


def parse_unified_thread(name):
    """
    Парсит UN / UNF / UNC / UNO / UNS резьбовые калибры (дюймовые Unified).
    Форматы: '1 1/8-12UNF 2A', '1 7/8-16UN 2A', '1 1/16-14UNF-3А ПР и НЕ'
    Возвращает ('unified', is_plug, key, side, is_combo) или None.
    key: 'nominal-TPI'  напр. '1 1/8-12'
    """
    if not name:
        return None
    nu = name.upper()
    nl = name.lower()

    # Должно содержать UN (UNF, UNC, UN, UNO, UNS, UNR …)
    # Без \b перед UN — т.к. встречается в форме "12UNF" (цифра + буква)
    if not re.search(r'UNF|UNC|UNO|UNS|UNR|UN-|UN\b', nu):
        return None
    # Исключаем NPT/NPSM (тоже содержат N)
    if 'NPT' in nu or 'NPSM' in nu:
        return None

    is_plug  = 'пробк' in nl or 'plug' in nl
    is_ring  = 'кольц' in nl or 'ring' in nl
    if is_ring:
        is_plug = False

    # Комплект ПР и НЕ
    is_combo = bool(re.search(r'\bПР\s+[ИI]\s+НЕ\b', name, re.IGNORECASE))

    # Сторона
    if re.search(r'\bНЕ\b', name) and not is_combo:
        side = 'не'
    else:
        side = 'пр'

    # Извлекаем nominal-TPI: '1 1/8-12' из '1 1/8-12UNF'
    m = re.search(r'(\d+\s+\d+/\d+|\d+/\d+|\d+)\s*-\s*(\d+)\s*UN', nu)
    if not m:
        return None

    nominal = m.group(1).strip()
    tpi     = m.group(2)
    key     = f'{nominal}-{tpi}'

    return ('unified', is_plug, key, side, is_combo)


def parse_stub_acme(name):
    """
    Парсит STUB ACME калибры.
    Форматы: '4,377-8 STUB ACME-2G ПР', '4,750-8 STUB ACME-2G LH НЕ'
    Возвращает ('stub_acme', is_plug, key, side) или None.
    key: 'diam_inch-TPI' напр. '4.377-8'; левая резьба: '4.750-8-LH'
    """
    if not name:
        return None
    nu = name.upper()
    nl = name.lower()

    if 'ACME' not in nu:
        return None

    is_plug = 'пробк' in nl or 'plug' in nl
    if 'кольц' in nl or 'ring' in nl:
        is_plug = False

    is_combo = bool(re.search(r'\bПР\s+[ИI]\s+НЕ\b', name, re.IGNORECASE))
    if re.search(r'\bНЕ\b', name) and not is_combo:
        side = 'не'
    else:
        side = 'пр'

    # Диаметр и TPI: '4,377-8' или '4.377-8'
    m = re.search(r'(\d+[,\.]\d+)-(\d+)', name)
    if not m:
        return None

    diam = m.group(1).replace(',', '.')
    tpi  = m.group(2)
    key  = f'{diam}-{tpi}'

    if 'LH' in nu:   # левая резьба
        key += '-LH'

    return ('stub_acme', is_plug, key, side, is_combo)


# ── Конические резьбовые калибры ГОСТ 6485-69 ────────────────────────────────
# Цены: кольцо Р-Р / пробка Р-Р; поверка 2 180 р./шт.
_CONICAL_RING  = {
    # Rc (ГОСТ 6485-69 / ГОСТ 6211-81) — Кольцо Р-Р
    '1/16"': 31592,
    '1/8"':  20911,
    '1/4"':  20911,
    '3/8"':  20911,
    '1/2"':  27874,
    '3/4"':  27874,
    '1"':    34518,
    '1 1/4"': 43142,
    '1 1/2"': 46464,
    '2"':    51106,
    '2 1/2"': 51106,
    '3"':    55748,
}
_CONICAL_PLUG  = {
    # Rc (ГОСТ 6485-69 / ГОСТ 6211-81) — Пробка Р-Р (комплект ПР+НЕ)
    '1/16"': 11946,
    '1/8"':  7634,
    '1/4"':  7634,
    '3/8"':  7634,
    '1/2"':  10956,
    '3/4"':  10956,
    '1"':    14608,
    '1 1/4"': 21241,
    '1 1/2"': 23232,
    '2"':    25553,
    '2 1/2"': 25553,
    '3"':    27874,
}
_CONICAL_KALIB = 2180   # поверка за штуку


def parse_conical(name):
    """
    Парсит конические калибры: 'Калибр-кольцо конусное 1/4"', 'Калибр-пробка конусная 3/8"'.
    Возвращает ('конус_кольцо', size_str) / ('конус_пробка', size_str) или None.
    """
    if not name:
        return None
    nl = name.lower()
    if 'конус' not in nl:
        return None
    # Размер: 1/8", 1/4", 3/8", 1/2", 3/4", 1", 1 1/4", 1 1/2", 2"
    # Паттерн: целое[пробел дробь] | дробь  — перед кавычкой
    m = re.search(r'(\d+\s+\d+/\d+|\d+/\d+|\d+)\s*"', name)
    if not m:
        return None
    size = m.group(1).strip() + '"'    # например '1/4"' или '1 1/4"'
    size = re.sub(r'\s+', ' ', size).strip()
    if 'кольцо' in nl:
        return ('конус_кольцо', size)
    if 'пробка' in nl:
        return ('конус_пробка', size)
    return None


# ── Парсинг гладкого калибра ─────────────────────────────────────────────────
def parse_caliber(name):
    """
    Разбирает наименование гладкого или резьбового калибра.
    Возвращает (kind, ...) или None.
    """
    if not name:
        return None
    nl = name.lower().strip()

    # Конические резьбовые калибры (до метрических, чтобы не перепутать)
    if 'конус' in nl or re.search(r'\bRc\b', name, re.I):
        return parse_conical(name)

    # Дюймовые / трубные резьбы (NPT, NPSM, PT, G, BSW)
    inch = parse_inch_thread(name)
    if inch:
        return inch

    # Unified inch threads (UN / UNF / UNC …)
    unified = parse_unified_thread(name)
    if unified:
        return unified

    # STUB ACME
    stub = parse_stub_acme(name)
    if stub:
        return stub

    # Резьбовое кольцо/пробка (с шагом или без)
    if re.search(r'м\s*\d+[,.]?\d*\s*[×xхХ]', nl):
        return parse_thread_ring(name)
    if re.search(r'м\s*\d+', nl) and ('кольцо' in nl or 'пробка' in nl):
        return parse_thread_ring(name)

    # Скоба гладкая
    if 'скоба' in nl:
        m = re.search(r'скоба\s+(\d+[,.]?\d*)', nl)
        if m:
            return ('скоба', float(m.group(1).replace(',', '.')))

    # Пробка гладкая
    if 'пробка' in nl:
        m = re.search(r'пробка\s+(?:гладкая\s+)?(\d+[,.]?\d*)', nl)
        if m:
            return ('пробка', float(m.group(1).replace(',', '.')))

    # Установочное кольцо (до кольца гладкого — специфичнее)
    if 'установочн' in nl and 'кольц' in nl:
        m = re.search(r'(\d+[,.]?\d*)', nl)
        if m:
            return ('установочное_кольцо', float(m.group(1).replace(',', '.')))

    # Кольцо гладкое (не резьбовое и не конусное)
    if 'кольцо' in nl and 'резьб' not in nl and 'конус' not in nl:
        # Определяем сторону: ПР или НЕ
        nu = name.upper()
        if ' НЕ' in nu or nu.rstrip().endswith('НЕ') or 'NOGO' in nu:
            side = 'не'
        else:
            side = 'пр'
        m = re.search(r'(\d+[,.]?\d*)', nl)
        if m:
            return ('кольцо_гладкое', float(m.group(1).replace(',', '.')), side)

    return None


# ── Калькулятор одной позиции ────────────────────────────────────────────────
def calc_item_from_excel(name, qty, base_price, kal, include_kalib=True, discount=None):
    """Расчёт по ценам из Excel."""
    d = discount if discount is not None else DISC
    disc    = round(base_price * d, 2)
    price_d = round(base_price - disc, 2)
    kal_use = kal if (include_kalib and kal is not None) else 0.0
    summa   = round(qty * (price_d + kal_use), 2)
    nds_s   = round(summa * NDS, 2)
    itogo   = round(summa + nds_s, 2)
    return {
        'name':    name,
        'ed':      'шт.',
        'qty':     qty,
        'price':   base_price,
        'disc':    disc,
        'price_d': price_d,
        'kal':     kal_use,
        'summa':   summa,
        'nds':     nds_s,
        'itogo':   itogo,
    }


def calc_item(name, qty, include_kalib=True, discount=None):
    """
    Считает одну позицию.
    Возвращает dict или None (если цена не определена).
    """
    parsed = parse_caliber(name)
    if parsed is None:
        return None

    kind = parsed[0]

    # ── Резьбовые кольца / пробки ──────────────────────────────────────────
    if kind in ('кольцо_резьбовое', 'пробка_резьбовая'):
        _, diam, pitch, side, is_combo = parsed

        if kind == 'кольцо_резьбовое':
            price = _ring_selling(diam, pitch, side)
            kal_full = _kalib_thread(kind, diam, False)
        else:
            price = _plug_selling(diam, pitch, is_combo)
            kal_full = _kalib_thread(kind, diam, is_combo)

        if price is None:
            return None

    # ── Дюймовые / трубные (NPT, NPSM, PT, G, BSW) ────────────────────────
    elif kind == 'inch':
        _, tcode, is_plug, key, side = parsed
        _MAP = {'npt': _NPT, 'npsm': _NPSM, 'pt': _PT, 'g': _G, 'bsw': _BSW}
        tbl = _MAP.get(tcode)
        if tbl is None:
            return None
        entry = tbl.get(key)
        if entry is None:
            return None
        if is_plug:
            price = float(entry[0])
        elif len(entry) == 3:   # G/BSW: (plug, pr, ne)
            price = float(entry[2] if side == 'не' else entry[1])
        else:                   # NPT/NPSM/PT: (plug, ring)
            price = float(entry[1])
        if price is None:
            return None
        kal_full = _INCH_KALIB

    # ── Unified inch (UN / UNF / UNC) ──────────────────────────────────────
    elif kind == 'unified':
        _, is_plug, key, side, is_combo = parsed
        entry = _UNIFIED.get(key)
        if entry is None:
            return None
        ring_pr, ring_ne, ring_combo, plug_pr, plug_ne, plug_combo = entry
        if is_combo:
            price = plug_combo if is_plug else ring_combo
        elif is_plug:
            price = plug_pr if side == 'пр' else plug_ne
        else:
            price = ring_pr if side == 'пр' else ring_ne
        if price is None:
            return None
        kal_full = _INCH_KALIB

    # ── STUB ACME ───────────────────────────────────────────────────────────
    elif kind == 'stub_acme':
        _, is_plug, key, side, is_combo = parsed
        entry = _STUB_ACME.get(key)
        if entry is None:
            return None
        plug_pr, plug_ne, ring_pr, ring_ne = entry
        if is_combo:
            price = (plug_pr or 0) + (plug_ne or 0) if is_plug else (ring_pr or 0) + (ring_ne or 0)
        elif is_plug:
            price = plug_pr if side == 'пр' else plug_ne
        else:
            price = ring_pr if side == 'пр' else ring_ne
        if price is None:
            return None
        kal_full = _INCH_KALIB

    # ── Конические резьбовые калибры ───────────────────────────────────────
    elif kind in ('конус_кольцо', 'конус_пробка'):
        _, size_str = parsed
        if kind == 'конус_кольцо':
            price = _CONICAL_RING.get(size_str)
        else:
            price = _CONICAL_PLUG.get(size_str)
        if price is None:
            return None
        kal_full = _CONICAL_KALIB

    # ── Гладкие / установочные ─────────────────────────────────────────────
    else:
        if kind == 'кольцо_гладкое':
            _, size, side = parsed
            price = ring_smooth_price(size, side)
        elif kind == 'установочное_кольцо':
            _, size = parsed
            price = ustanov_ring_price(size)
        elif kind == 'скоба':
            _, size = parsed
            price = skoba_price(size, name)
        else:  # пробка
            _, size = parsed
            price = proba_price(size)
        if price is None:
            return None
        kal_full = kalib_price(kind, size, name)

    kal = kal_full if include_kalib else 0.0
    d = discount if discount is not None else DISC
    disc    = round(price * d, 2)
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
