# -*- coding: utf-8 -*-
"""ВЕГАЛИБР — веб-калькулятор КП"""

import os
from flask import (Flask, render_template, request, session,
                   redirect, url_for, send_file, jsonify)
from pricing import calc_item, calc_item_from_excel
from parser import parse_zaявка
from doc_builder import build_kp

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

    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Файл не загружен"}), 400

    include_kalib = request.form.get("include_kalib", "true").lower() == "true"

    items_raw, err = parse_zaявка(f.stream)
    if err:
        return jsonify({"error": err}), 400

    result = []
    aa = []
    for name, qty, price_excel, kalib_excel in items_raw:
        # 1) Пробуем наш прайс
        row = calc_item(name, qty, include_kalib=include_kalib)
        if row:
            result.append(row)
            continue

        # 2) Если в Excel есть цена — используем её
        if price_excel is not None:
            kal = (kalib_excel or 0.0) if include_kalib else 0.0
            row = calc_item_from_excel(name, qty, price_excel, kal,
                                       include_kalib=include_kalib)
            row['source'] = 'excel'   # пометка что цена из заявки
            result.append(row)
            continue

        # 3) Не удалось — в АА
        aa.append({"name": name, "qty": qty})

    return jsonify({"items": result, "aa": aa})

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

    if not items:
        return jsonify({"error": "Нет позиций для КП"}), 400

    buf = build_kp(items, aa, customer=customer,
                   order_num=order_num, manager=manager)

    fname = f"КП_{order_num}.docx" if order_num else "КП_ВЕГАЛИБР.docx"
    return send_file(
        buf,
        as_attachment=True,
        download_name=fname,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
