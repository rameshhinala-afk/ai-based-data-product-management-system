"""Populate the DB with demo products and 90 days of synthetic sales."""
import os
import random
from datetime import date, timedelta

import db

PRODUCTS = [
    ("Wireless Bluetooth Headphones", "Over-ear noise cancelling headphones with mic", "Electronics", 89.0, 45.0, 120, 20),
    ("USB-C Fast Charger", "65W charger for phones and laptops", "Electronics", 29.0, 12.0, 300, 40),
    ("Smart LED TV 43 inch", "4K ultra HD television with streaming apps", "Electronics", 349.0, 240.0, 25, 8),
    ("Running Shoes", "Lightweight breathable shoes for jogging", "Sports", 59.0, 28.0, 80, 15),
    ("Yoga Mat", "Non-slip exercise mat for yoga and fitness", "Sports", 19.0, 7.0, 150, 25),
    ("Dumbbell Set 20kg", "Adjustable weights for strength training", "Sports", 75.0, 40.0, 30, 10),
    ("Organic Green Tea", "Box of 100 antioxidant tea bags", "Grocery", 12.0, 5.0, 400, 60),
    ("Almond Butter", "Natural creamy nut spread, no sugar added", "Grocery", 9.0, 4.0, 200, 30),
    ("Basmati Rice 5kg", "Premium long grain aromatic rice", "Grocery", 15.0, 9.0, 18, 30),
    ("Stainless Steel Water Bottle", "Insulated bottle keeps drinks cold 24 hours", "Home", 22.0, 9.0, 140, 20),
]


def seed():
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    db.init_db()
    random.seed(42)
    today = date.today()
    for name, desc, cat, price, cost, stock, reorder in PRODUCTS:
        pid = db.execute(
            "INSERT INTO products (name, description, category, price, cost, stock, reorder_level) VALUES (?,?,?,?,?,?,?)",
            (name, desc, cat, price, cost, stock, reorder),
        )
        base = random.randint(4, 18)
        trend = random.uniform(-0.03, 0.08)
        elasticity = random.uniform(-2.5, -0.6)
        for i in range(90):
            d = today - timedelta(days=89 - i)
            p = round(price * random.uniform(0.85, 1.15), 2)
            demand = base * (1 + trend * i / 10) * (p / price) ** elasticity
            qty = max(0, int(random.gauss(demand, demand * 0.15)))
            if random.random() < 0.03:                      # inject anomalies
                qty = int(qty * random.choice([0.1, 3]))
            db.execute("INSERT INTO sales (product_id, sale_date, qty, unit_price) VALUES (?,?,?,?)",
                       (pid, d.isoformat(), qty, p))
    print(f"Seeded {len(PRODUCTS)} products with 90 days of sales.")


if __name__ == "__main__":
    seed()
