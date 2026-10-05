"""AI / ML features: classification, forecasting, pricing, stock & anomaly insights."""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline

import db


# ---------- 1. Category classification (NLP) ----------
def classify_category(name: str, description: str = ""):
    """Predict a category from product text using TF-IDF + Logistic Regression
    trained on products that already have a category."""
    rows = db.query("SELECT name, description, category FROM products WHERE category != ''")
    categories = {r["category"] for r in rows}
    if len(rows) < 4 or len(categories) < 2:
        return {"category": None, "confidence": 0.0, "note": "Not enough labelled products to train."}

    texts = [f"{r['name']} {r['description']}" for r in rows]
    labels = [r["category"] for r in rows]
    model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), lowercase=True),
                          LogisticRegression(max_iter=1000))
    model.fit(texts, labels)

    probs = model.predict_proba([f"{name} {description}"])[0]
    best = int(np.argmax(probs))
    return {"category": model.classes_[best], "confidence": round(float(probs[best]), 3)}


# ---------- helpers ----------
def _daily_sales(product_id):
    return db.query(
        """SELECT sale_date, SUM(qty) AS qty, AVG(unit_price) AS price
           FROM sales WHERE product_id = ? GROUP BY sale_date ORDER BY sale_date""",
        (product_id,),
    )


# ---------- 2. Demand forecasting ----------
def forecast_demand(product_id, days=7):
    daily = _daily_sales(product_id)
    if len(daily) < 5:
        return {"forecast": [], "total": 0, "trend": "unknown", "note": "Need at least 5 days of sales."}

    y = np.array([d["qty"] for d in daily], dtype=float)
    X = np.arange(len(y)).reshape(-1, 1)
    model = LinearRegression().fit(X, y)

    future = np.arange(len(y), len(y) + days).reshape(-1, 1)
    preds = np.clip(model.predict(future), 0, None)
    slope = float(model.coef_[0])
    trend = "rising" if slope > 0.05 else "falling" if slope < -0.05 else "stable"
    return {
        "forecast": [round(float(p), 1) for p in preds],
        "total": round(float(preds.sum()), 1),
        "avg_daily": round(float(y.mean()), 2),
        "trend": trend,
    }


# ---------- 3. Price recommendation ----------
def recommend_price(product):
    """Estimate price elasticity with a log-log regression and suggest a
    profit-maximising price (clamped to +/-20% of the current price)."""
    daily = _daily_sales(product["id"])
    current = product["price"]
    cost = product["cost"]
    if len(daily) < 10:
        return {"suggested_price": current, "note": "Not enough sales history."}

    prices = np.array([d["price"] for d in daily])
    qty = np.array([max(d["qty"], 1) for d in daily], dtype=float)
    if prices.std() / prices.mean() < 0.02:
        return {"suggested_price": current, "note": "Price never varied; elasticity unknown."}

    model = LinearRegression().fit(np.log(prices).reshape(-1, 1), np.log(qty))
    elasticity = float(model.coef_[0])

    if elasticity < -1.05:
        optimal = cost * elasticity / (1 + elasticity)   # constant-elasticity markup rule
    elif elasticity >= -1.05:
        optimal = current * 1.1                          # inelastic demand -> room to raise
    optimal = min(max(optimal, current * 0.8), current * 1.2)
    optimal = max(optimal, cost * 1.05)                  # never sell below cost + 5%
    return {
        "suggested_price": round(float(optimal), 2),
        "elasticity": round(elasticity, 2),
        "note": "Elastic demand" if elasticity < -1 else "Inelastic demand",
    }


# ---------- 4. Stock insights ----------
def stock_insight(product, forecast):
    avg = forecast.get("avg_daily", 0) or 0
    cover = round(product["stock"] / avg, 1) if avg > 0 else None
    status, action = "ok", "Stock level is healthy."
    if product["stock"] <= product["reorder_level"] or (cover is not None and cover < 7):
        status = "low"
        need = max(int(forecast.get("total", 0) * 2 - product["stock"]), product["reorder_level"])
        action = f"Reorder about {need} units."
    elif cover is not None and cover > 90:
        status, action = "overstock", "Overstocked - consider a promotion."
    return {"days_of_cover": cover, "status": status, "action": action}


# ---------- 5. Anomaly detection ----------
def detect_anomalies(product_id, z_thresh=2.5):
    daily = _daily_sales(product_id)
    if len(daily) < 10:
        return []
    qty = np.array([d["qty"] for d in daily], dtype=float)
    std = qty.std()
    if std == 0:
        return []
    z = (qty - qty.mean()) / std
    return [
        {"date": d["sale_date"], "qty": int(d["qty"]), "z_score": round(float(zi), 2),
         "type": "spike" if zi > 0 else "drop"}
        for d, zi in zip(daily, z) if abs(zi) >= z_thresh
    ]


def full_insights(product_id):
    product = db.query("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
    if not product:
        return None
    forecast = forecast_demand(product_id)
    return {
        "product": product["name"],
        "forecast": forecast,
        "pricing": recommend_price(product),
        "stock": stock_insight(product, forecast),
        "anomalies": detect_anomalies(product_id),
    }
