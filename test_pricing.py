# -*- coding: utf-8 -*-
"""10 тестов для ВЕГАЛИБР pricing"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, '.')
from pricing import calc_item, parse_caliber
from app import _clean_name, _infer_caliber_type

sep = '=' * 55
passed = 0
failed = 0

def check(tid, result, expected, desc):
    global passed, failed
    ok = (result == expected)
    if ok:
        passed += 1
        print(f'[PASS] {desc}')
    else:
        failed += 1
        print(f'[FAIL] {desc}')
        print(f'       Expected: {expected!r}')
        print(f'       Got:      {result!r}')

print(sep)
print('ТЕСТЫ ВЕГАЛИБР')
print(sep)

# 1. Кольцо М10×1,5 ПР — жёлтый ценник (price > базовой 4178)
r = calc_item('Калибр-кольцо М10×1,5 ПР', 1, include_kalib=False, discount=0.0)
check('t1', r is not None, True, 'Кольцо М10×1,5 ПР — найдено в прайсе')
if r:
    check('t1b', r['price'] > 4178.0, True, 'Кольцо М10×1,5 ПР — жёлтый ценник применён')

# 2a. Пробка М10×1,5 ПР ≤50мм → всегда цена комплекта 3487
r = calc_item('Калибр-пробка М10×1,5 ПР', 1, include_kalib=False, discount=0.0)
check('t2a', r['price'] if r else None, 3487.0, 'Пробка М10×1,5 ПР ≤50мм → цена комплекта 3487')

# 2b. Пробка М10×1,5 ПР-НЕ комплект ≤50мм → combo = 3487
r = calc_item('Калибр-пробка М10×1,5 ПР-НЕ', 1, include_kalib=False, discount=0.0)
check('t2b', r['price'] if r else None, 3487.0, 'Пробка М10×1,5 ПР-НЕ (комплект) → 3487')

# 3. Пробка М56×5,5 ПР — штучно >50мм = 7319
r = calc_item('Калибр-пробка М56×5,5 ПР', 1, include_kalib=False, discount=0.0)
check('t3', r['price'] if r else None, 7319.0, 'Пробка М56×5,5 ПР — штучно >50мм = 7319')

# 4. _clean_name нормализация
r4 = _clean_name('Кольцо резьбовое М12×1,75 6g ГОСТ 17758-72 ×5шт')
check('t4', r4, 'Калибр-кольцо М12×1,75 6g', '_clean_name: Кольцо резьбовое + ГОСТ + кол-во')

# 5. _infer_caliber_type: H → пробка
r5 = _infer_caliber_type('Калибр М16×2-6H')
check('t5', r5, 'Калибр-пробка М16×2-6H', '_infer_caliber_type: 6H → пробка')

# 6. _infer_caliber_type: g → кольцо
r6 = _infer_caliber_type('Калибр М16×2-6g')
check('t6', r6, 'Калибр-кольцо М16×2-6g', '_infer_caliber_type: 6g → кольцо')

# 7a. Гладкая пробка 1,3мм → АА (нет в прайсе)
r = calc_item('Калибр-пробка гладкая 1,3 ПР', 1, include_kalib=False, discount=0.0)
check('t7a', r, None, 'Гладкая пробка 1,3мм → АА (нет в прайсе)')

# 7b. Гладкая пробка 1,2мм → 5400 (есть в прайсе)
r = calc_item('Калибр-пробка гладкая 1,2 ПР', 1, include_kalib=False, discount=0.0)
check('t7b', r['price'] if r else None, 5400.0, 'Гладкая пробка 1,2мм → 5400 (есть в прайсе)')

# 8. Гладкая пробка 45мм → 9860.40
r = calc_item('Калибр-пробка гладкая 45 ПР', 1, include_kalib=False, discount=0.0)
check('t8', r['price'] if r else None, 9860.40, 'Гладкая пробка 45мм → 9860.40')

# 9. Конический Rc кольцо 1/2" → 27874
r = calc_item('Калибр-кольцо конусное Rc 1/2"', 1, include_kalib=False, discount=0.0)
check('t9', r['price'] if r else None, 27874.0, 'Конический Rc кольцо 1/2" → 27874')

# 10. NPT пробка 3/4" → 9735
r = calc_item('Калибр-пробка NPT 3/4"', 1, include_kalib=False, discount=0.0)
check('t10', r['price'] if r else None, 9735.0, 'NPT пробка 3/4" → 9735')

print(sep)
print(f'Итого: {passed} PASS, {failed} FAIL из {passed + failed}')
print(sep)
