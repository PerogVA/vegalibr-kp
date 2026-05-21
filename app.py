# -*- coding: utf-8 -*-
"""ВЕГАЛИБР — веб-калькулятор КП"""

import os
import re
from io import BytesIO
from flask import (Flask, render_template, request, session,
                   redirect, url_for, send_file, jsonify)
from pricing import calc_item, calc_item_from_excel, parse_caliber, _PLUG_COMBO, NDS
from excel_parser import parse_excel
from text_parser import parse_pdf, parse_text
from doc_builder import build_kp
from stock import lookup as stock_lookup
from drawing_parser import parse_drawing

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vegalibr-secret-2025")

APP_PASSWORD = os.environ.get("APP_PASSWORD", "vegalibr2025")

# ─────────────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if not session.get("auth"):
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["auth"] = True
            return redirect(url_for("index"))
        error = "Неверный пароль"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─────────────────────────────────────────────────────────────────────────────
@app.route("/parse", methods=["POST"])
def parse():
    """Парсит Excel-файл, возвращает JSON со списком позиций."""
    if not session.get("auth"):
        return jsonify({"error": "not_auth"}), 403

    include_kalib = request.form.get("include_kalib", "true").lower() == "true"
    try:
        discount = float(request.form.get("discount", "20")) / 100.0
        discount = max(0.0, min(0.99, discount))
    except ValueError:
        discount = 0.20

    # Текст из буфера обмена?
    raw_text = request.form.get("raw_text", "").strip()
    if raw_text:
        items_raw, err = parse_text(raw_text)
        if err:
            return jsonify({"error": err}), 400
    else:
        f = request.files.get("file")
        if not f:
            return jsonify({"error": "Загрузите файл или вставьте текст"}), 400

        fname = (f.filename or '').lower()
        file_buf = BytesIO(f.read())
        if fname.endswith('.pdf'):
            items_raw, err = parse_pdf(file_buf)
        else:
            items_raw, err = parse_excel(file_buf)
        if err:
            return jsonify({"error": err}), 400

    result = []
    aa = []
    for name, qty, price_excel, kalib_excel in items_raw:
        # 1) Пробуем наш прайс (с разбивкой ПР/НЕ если нужно)
        rows = _expand(name, qty, include_kalib, discount)
        if rows:
            result.extend(rows)
            continue

        # 2) Если в Excel есть цена — используем её (без разбивки)
        if price_excel is not None:
            kal = (kalib_excel or 0.0) if include_kalib else 0.0
            row = calc_item_from_excel(name, qty, price_excel, kal,
                                       include_kalib=include_kalib, discount=discount)
            row['source'] = 'excel'
            _add_stock(row)
            result.append(row)
            continue

        # 3) Не удалось — в АА
        aa.append({"name": name, "qty": qty})

    return jsonify({"items": result, "aa": aa})


def _extract_qty_from_name(name):
    """Извлекает кол-во, вписанное в наименование (напр. 'ПР12шт' → 12). None если нет."""
    m = re.search(r'[-×х]?\s*(\d+)\s*шт\.?', name, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


def _infer_caliber_type(name):
    """
    Если имя начинается с 'Калибр М...' (без кольцо/пробка) или просто 'М...',
    пытается определить тип по квалитету:
      H/Н (прописные) → пробка (отверстие)
      g/e/f/r/d (строчные) → кольцо (вал)
    Возвращает нормализованное имя или исходное если определить не удалось.
    """
    # Голое «М4×0,7-6g» (без типа калибра) — инферим тип и добавляем префикс
    if re.match(r'^[МмMm]\s*\d', name):
        nl = name.lower()
        if 'кольцо' in nl or 'пробка' in nl or 'калибр' in nl:
            return name  # уже есть тип
        m = re.search(
            r'[МмMm]\s*\d+[,.]?\d*\s*[×xхХ]?\s*\d*[,.]?\d*\s*-\s*([A-Za-zА-Яа-яЁё0-9]+)',
            name)
        if m:
            qual = m.group(1)
            if re.search(r'[gefdr]', qual):
                return 'Калибр-кольцо ' + name
            if re.search(r'[HН]', qual):
                return 'Калибр-пробка ' + name
        return name

    # Работаем только с «Калибр М...»
    if not re.match(r'^Калибр\s+[МмMm]\s*\d', name, flags=re.IGNORECASE):
        return name
    # Уже есть тип — не трогаем
    nl = name.lower()
    if 'кольцо' in nl or 'пробка' in nl:
        return name

    # Ищем квалитет после дефиса: -5Н6Н, -6g, -6eR и т.п.
    m = re.search(r'[МмMm]\s*\d+[,.]?\d*\s*[×xхХ]?\s*\d*[,.]?\d*\s*-\s*([A-Za-zА-Яа-яЁё0-9]+)', name)
    if m:
        qual = m.group(1)
        # Если есть строчные латинские (g, e, f, d, r) → кольцо (вал)
        if re.search(r'[gefdr]', qual):
            suffix = name[len('калибр'):].strip() if name.lower().startswith('калибр') else name
            return 'Калибр-кольцо ' + suffix
        # Если есть прописные H/Н → пробка (отверстие)
        if re.search(r'[HН]', qual):
            suffix = name[len('калибр'):].strip() if name.lower().startswith('калибр') else name
            return 'Калибр-пробка ' + suffix
    return name


def _clean_name(name):
    """Убирает служебные аннотации и нормализует наименование к стандарту ВЕГАЛИБР."""
    # ГОСТ ссылки: ГОСТ 17758-72
    name = re.sub(r'\s*ГОСТ\s*\d+[\.\-–]\d+', '', name, flags=re.IGNORECASE)
    # Артикулы: 8221-3013, 8221-3013-6Н и подобные
    name = re.sub(r'\b\d{3,}[\-–]\d{3,}[\-–]?\w*\b', '', name)
    # >50мм / > 50 мм / более 50мм
    name = re.sub(r'\s*>?\s*50\s*мм\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*более\s*\d+\s*мм?\b', '', name, flags=re.IGNORECASE)
    # Кол-во в имени: ×12шт / 12шт / 12 шт. / -12шт
    name = re.sub(r'\s*[-×х]?\s*\d+\s*шт\.?', '', name, flags=re.IGNORECASE)
    # Нормализация типа
    name = re.sub(r'^Кольцо\s+резьбовое\b', 'Калибр-кольцо', name, flags=re.IGNORECASE)
    name = re.sub(r'^Кольцо\b', 'Калибр-кольцо', name, flags=re.IGNORECASE)
    name = re.sub(r'^Пробка\s+резьбовая\b', 'Калибр-пробка', name, flags=re.IGNORECASE)
    name = re.sub(r'^Пробка\b', 'Калибр-пробка', name, flags=re.IGNORECASE)
    name = re.sub(r'^Скоба\b', 'Калибр-скоба', name, flags=re.IGNORECASE)
    # Символ ⌀ для скобы и пробки гладкой: «Калибр-скоба 1,2» → «Калибр-скоба ⌀1,2»
    name = re.sub(r'(Калибр-скоба|Калибр-пробка)\s+(?!⌀)(\d)', r'\1 ⌀\2', name, flags=re.IGNORECASE)
    # «Калибр М...» без типа — определяем по квалитету
    name = _infer_caliber_type(name)
    return ' '.join(name.split())


def _spec_part(name):
    """Вырезает 'М10×1,5 6g' из 'Калибр-кольцо М10×1,5 6g ПР'."""
    s = re.sub(r'^(Калибр-кольцо|Калибр-пробка|Кольцо|Пробка)\s*', '', name, flags=re.IGNORECASE)
    s = re.sub(r'\s+(ПР-НЕ|ПР|НЕ)\s*$', '', s, flags=re.IGNORECASE)
    return s.strip()


def _control_rows(ring_name, diam, pitch, ring_side, qty, include_kalib, discount):
    """
    Генерирует строки контрольных калибров-пробок для кольца.
    ring_side: 'ПР' → КПР-ПР, КПР-НЕ; 'НЕ' → КНЕ-ПР, КНЕ-НЕ
    """
    combo = _PLUG_COMBO.get((float(diam), float(pitch)))
    if not combo:
        return []
    tag = 'КПР' if ring_side == 'ПР' else 'КНЕ'
    spec = _spec_part(ring_name)
    d = discount if discount is not None else 0.0
    kal = 1760 if include_kalib else 0
    rows = []
    for ctrl_side in ('ПР', 'НЕ'):
        ctrl_name = f"Контрольный калибр-пробка {spec} {tag}-{ctrl_side}"
        disc    = round(combo * d, 2)
        price_d = round(combo - disc, 2)
        summa   = round(qty * (price_d + kal), 2)
        nds_s   = round(summa * NDS, 2)
        rows.append({
            'name': ctrl_name, 'ed': 'шт.', 'qty': qty,
            'price': combo, 'disc': disc, 'price_d': price_d,
            'kal': kal, 'summa': summa, 'nds': nds_s,
            'itogo': round(summa + nds_s, 2),
            'stock': None, 'stock_price': None,
            'source': 'control',
        })
    return rows


def _add_stock(row):
    """Добавляет информацию о складе в строку результата."""
    s = stock_lookup(row['name'])
    row['stock'] = s[1] if s else None
    row['stock_price'] = s[0] if s else None


def _needs_split(name):
    """
    Нужно ли разбивать позицию на ПР и НЕ.
    Кольца: всегда. Пробки резьбовые >50мм: да. Пробки ≤50мм: нет (цена комплекта).
    """
    nu = name.upper()
    if 'ПР-НЕ' not in nu and 'ПР/НЕ' not in nu:
        return False
    parsed = parse_caliber(name)
    if not parsed:
        return False
    kind = parsed[0]
    if kind == 'кольцо_резьбовое':
        return True
    if kind == 'пробка_резьбовая':
        diam = parsed[1]
        return float(diam) > 50
    return False


def _replace_pr_ne(name, side):
    """Заменяет ПР-НЕ / ПР/НЕ на ПР или НЕ, сохраняя регистр остальной части."""
    for combo in ('ПР-НЕ', 'ПР/НЕ'):
        idx = name.upper().find(combo)
        if idx >= 0:
            return name[:idx] + side + name[idx + len(combo):]
    return name


def _expand(name, qty, include_kalib, discount):
    """
    Считает одну или две позиции (при разбивке ПР/НЕ).
    Возвращает список dict-ов (1 или 2 элемента).
    """
    # Кол-во, вписанное в наименование, имеет приоритет
    qty_in_name = _extract_qty_from_name(name)
    if qty_in_name is not None:
        qty = qty_in_name

    if _needs_split(name):
        rows = []
        for side in ('ПР', 'НЕ'):
            n = _clean_name(_replace_pr_ne(name, side))
            r = calc_item(n, qty, include_kalib=include_kalib, discount=discount)
            if r:
                r['name'] = n
                _add_stock(r)
                rows.append(r)
                # Контрольные калибры для колец ≤36мм и шаг ≤1,5мм
                parsed = parse_caliber(n)
                if parsed and parsed[0] == 'кольцо_резьбовое':
                    d, p = parsed[1], parsed[2]
                    if float(d) <= 36 and float(p) <= 1.5:
                        rows.extend(_control_rows(n, d, p, side, qty,
                                                  include_kalib, discount))
        return rows

    clean = _clean_name(name)
    r = calc_item(clean, qty, include_kalib=include_kalib, discount=discount)
    if r:
        r['name'] = clean
        _add_stock(r)
        return [r]
    return []

# ─────────────────────────────────────────────────────────────────────────────
@app.route("/generate", methods=["POST"])
def generate():
    """Генерирует Word КП по данным формы."""
    if not session.get("auth"):
        return jsonify({"error": "not_auth"}), 403

    data = request.get_json(force=True)
    items     = data.get("items", [])
    aa        = [(x["name"], x["qty"]) for x in data.get("aa", [])]
    customer  = data.get("customer", "")
    order_num = data.get("order_num", "")
    manager   = data.get("manager", "Перог Вадим Александрович")
    try:
        discount = float(data.get("discount", 20)) / 100.0
        discount = max(0.0, min(0.99, discount))
    except (ValueError, TypeError):
        discount = 0.20

    if not items:
        return jsonify({"error": "Нет позиций для КП"}), 400

    buf = build_kp(items, aa, customer=customer,
                   order_num=order_num, manager=manager, discount=discount)

    fname = f"КП_{order_num}.docx" if order_num else "КП_ВЕГАЛИБР.docx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=fname,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# ─────────────────────────────────────────────────────────────────────────────
@app.route("/calc-single", methods=["POST"])
def calc_single():
    """Считает одну позицию по наименованию (ручное добавление)."""
    if not session.get("auth"):
        return jsonify({"error": "not_auth"}), 403

    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    try:
        qty = max(1, int(data.get("qty", 1)))
    except (ValueError, TypeError):
        qty = 1
    include_kalib = bool(data.get("include_kalib", True))
    try:
        discount = float(data.get("discount", 20)) / 100.0
        discount = max(0.0, min(0.99, discount))
    except (ValueError, TypeError):
        discount = 0.20

    if not name:
        return jsonify({"error": "Укажите наименование"}), 400

    rows = _expand(name, qty, include_kalib, discount)
    if rows:
        return jsonify({"items": rows})

    return jsonify({"aa": {"name": name, "qty": qty}})


# ─────────────────────────────────────────────────────────────────────────────
@app.route("/parse-drawing", methods=["POST"])
def parse_drawing_route():
    """Принимает чертёж (PDF/PNG/JPG), возвращает список найденных калибров."""
    if not session.get("auth"):
        return jsonify({"error": "not_auth"}), 403

    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Файл не загружен"}), 400

    file_bytes = f.read()
    filename   = f.filename or ""

    suggestions, err = parse_drawing(file_bytes, filename)
    if err and not suggestions:
        return jsonify({"error": err}), 400

    return jsonify({"suggestions": [{"name": n, "hint": h} for n, h in suggestions]})


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
