"""AI-Based Data Product Management System - Flask API + web UI."""
import os
from datetime import date

from flask import Flask, jsonify, render_template, request

import ai_engine
import db

app = Flask(__name__)
db.init_db()


@app.route("/")
def index():
    return render_template("index.html")


# ---------- Products CRUD ----------
@app.get("/api/products")
def list_products():
    return jsonify(db.query("SELECT * FROM products ORDER BY id DESC"))


@app.post("/api/products")
def create_product():
    d = request.get_json(force=True)
    if not d.get("name") or d.get("price") in (None, ""):
        return jsonify(error="name and price are required"), 400
    category = d.get("category", "")
    if not category:  # AI auto-categorisation when left blank
        category = ai_engine.classify_category(d["name"], d.get("description", "")).get("category") or ""
    pid = db.execute(
        "INSERT INTO products (name, description, category, price, cost, stock, reorder_level) VALUES (?,?,?,?,?,?,?)",
        (d["name"], d.get("description", ""), category, float(d["price"]),
         float(d.get("cost") or 0), int(d.get("stock") or 0), int(d.get("reorder_level") or 10)),
    )
    return jsonify(db.query("SELECT * FROM products WHERE id=?", (pid,), one=True)), 201


@app.put("/api/products/<int:pid>")
def update_product(pid):
    d = request.get_json(force=True)
    allowed = ["name", "description", "category", "price", "cost", "stock", "reorder_level"]
    fields = {k: d[k] for k in allowed if k in d}
    if not fields:
        return jsonify(error="nothing to update"), 400
    sets = ", ".join(f"{k}=?" for k in fields)
    db.execute(f"UPDATE products SET {sets} WHERE id=?", (*fields.values(), pid))
    return jsonify(db.query("SELECT * FROM products WHERE id=?", (pid,), one=True))


@app.delete("/api/products/<int:pid>")
def delete_product(pid):
    db.execute("DELETE FROM sales WHERE product_id=?", (pid,))
    db.execute("DELETE FROM products WHERE id=?", (pid,))
    return jsonify(deleted=pid)


# ---------- Sales ----------
@app.post("/api/products/<int:pid>/sales")
def record_sale(pid):
    d = request.get_json(force=True)
    product = db.query("SELECT * FROM products WHERE id=?", (pid,), one=True)
    if not product:
        return jsonify(error="product not found"), 404
    qty = int(d.get("qty", 1))
    if qty > product["stock"]:
        return jsonify(error="insufficient stock"), 400
    db.execute("INSERT INTO sales (product_id, sale_date, qty, unit_price) VALUES (?,?,?,?)",
               (pid, d.get("date", date.today().isoformat()), qty, float(d.get("price", product["price"]))))
    db.execute("UPDATE products SET stock = stock - ? WHERE id=?", (qty, pid))
    return jsonify(ok=True), 201


# ---------- AI endpoints ----------
@app.post("/api/ai/classify")
def classify():
    d = request.get_json(force=True)
    return jsonify(ai_engine.classify_category(d.get("name", ""), d.get("description", "")))


@app.get("/api/products/<int:pid>/insights")
def insights(pid):
    result = ai_engine.full_insights(pid)
    return (jsonify(result) if result else (jsonify(error="not found"), 404))


@app.get("/api/dashboard")
def dashboard():
    products = db.query("SELECT * FROM products")
    alerts = []
    for p in products:
        info = ai_engine.stock_insight(p, ai_engine.forecast_demand(p["id"]))
        if info["status"] != "ok":
            alerts.append({"id": p["id"], "name": p["name"], **info})
    return jsonify(
        total_products=len(products),
        inventory_value=round(sum(p["price"] * p["stock"] for p in products), 2),
        alerts=alerts,
    )


if __name__ == "__main__":
    if not os.path.exists(db.DB_PATH) or not db.query("SELECT 1 FROM products LIMIT 1"):
        import seed_data
        seed_data.seed()
    app.run(debug=True)
