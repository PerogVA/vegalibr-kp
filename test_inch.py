# -*- coding: utf-8 -*-
import sys, io, importlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
import pricing
importlib.reload(pricing)

sep = '=' * 60
print(sep)
print('ТЕСТ: UNF / UN / STUB ACME')
print(sep)

tests = [
    # UNF / UN — list price (без скидки, без поверки)
    ('Калибр-кольцо резьбовое ПР 1 1/8-12UNF 2A ASME B1.1',   1, 11900),
    ('Калибр-кольцо резьбовое НЕ 1 1/8-12UNF 2A ASME B1.1',   1,  8650),
    ('Калибр-кольцо резьбовое ПР 1 7/8-16UN 2A ASME B1.1',    1, 18400),
    ('Калибр-кольцо резьбовое НЕ 1 7/8-16UN 2A ASME B1.1',    1, 13525),
    ('Калибр-кольцо 1 1/16-14UNF-3А ПР и НЕ',                 1, 20025),
    ('Калибр-кольцо резьбовое ПР 1 7/8-12UN ASME B1.1',       1, 13836),
    ('Калибр-кольцо резьбовое НЕ 1 7/8-12UN ASME B1.1',       1, 13836),
    # STUB ACME
    ('Калибр-кольцо 4,377-8 STUB ACME-2G ПР',                 1, 195000),
    ('Калибр-кольцо 4,377-8 STUB ACME-2G НЕ',                 1, 182000),
    ('Калибр-кольцо 4,750-8 STUB ACME-2G LH ПР',              1, 228280),   # счёт 1352
    ('Калибр-кольцо 4,750-8 STUB ACME-2G LH НЕ',              1, 214500),   # счёт 1352
    ('Калибр-пробка 4,224-8 STUB ACME-2G ПР',                 1, 104000),
    ('Калибр-пробка 4,224-8 STUB ACME-2G НЕ',                 1,  91000),
]

passed = failed = 0
for name, qty, expected_price in tests:
    r = pricing.calc_item(name, qty, include_kalib=False, discount=0.0)
    got = r['price'] if r else None
    ok = (got == expected_price)
    if ok:
        passed += 1
        print(f'[PASS] {name}')
    else:
        failed += 1
        print(f'[FAIL] {name}')
        print(f'       Ожидалось: {expected_price}   Получено: {got}')
        if r is None:
            parsed = pricing.parse_caliber(name)
            print(f'       parse_caliber: {parsed}')

print(sep)
print(f'Итого: {passed} PASS, {failed} FAIL')
print(sep)
