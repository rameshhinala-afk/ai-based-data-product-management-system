# AI-Based Data Product Management System

A simple base project: product CRUD + sales tracking + machine-learning insights.

## Features
| Feature | Technique |
|---|---|
| Auto product categorisation | TF-IDF + Logistic Regression |
| 7-day demand forecast | Linear Regression on daily sales |
| Price recommendation | Log-log price elasticity + markup rule |
| Stock alerts / reorder qty | Forecast-based days-of-cover |
| Sales anomaly detection | Z-score |

## Run
```bash
pip install -r requirements.txt
python seed_data.py     # optional: demo data (auto-runs on first start)
python app.py           # open http://127.0.0.1:5000
```

## Structure
- `app.py` – Flask REST API + page
- `ai_engine.py` – all ML logic
- `db.py` – SQLite helpers
- `seed_data.py` – synthetic data
- `templates/index.html` – dashboard UI

## API
`GET/POST /api/products` · `PUT/DELETE /api/products/<id>` · `POST /api/products/<id>/sales`
`GET /api/products/<id>/insights` · `POST /api/ai/classify` · `GET /api/dashboard`

## Ideas to extend
Authentication, Prophet/ARIMA forecasting, LLM-generated product descriptions, charts (Chart.js), PostgreSQL.
