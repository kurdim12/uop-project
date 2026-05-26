# Raw Smith Circle — Phase 3

A Django web application for the loyalty program of **Raw Smith Specialty
Coffee** (Amman, Jordan). Phase 3 of the course project for *606315 Programming
for Data Science* (University of Petra, Dr. Mohammad Arafah).

It turns the Phase 1 EDA and Phase 2 enrichment work into a live product:

- An analytics **dashboard** (Chart.js) powered entirely by the Django ORM.
- Two **scikit-learn models** served from serialized joblib pipelines:
  - a **tier classifier** (predicts bronze / silver / gold), and
  - a **daily-volume regressor** (predicts points issued from weather + coffee price).
- A **REST API** (Django REST Framework).
- A **cloud deployment** on Render with PostgreSQL and WhiteNoise.

## Live demo

`https://raw-smith-circle.onrender.com` *(set once deployed)*

---

## 1. Local setup

```bash
git clone https://github.com/kurdim12/uop-project.git
cd uop-project

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit SECRET_KEY / DEBUG if you like

python manage.py migrate
python manage.py load_data       # loads data/*.csv (see data/README.md)
python manage.py runserver
```

Open <http://localhost:8000/>.

> The repository ships **without** the anonymized data. Put the CSVs and the
> Phase 2 enrichment files in `data/` first (schema in `data/README.md`).
> Until then the app runs fine: the dashboard shows an empty state and the
> prediction pages prompt you to train the models.

## 2. Training the models

Each script reads from `data/`, trains, evaluates, and writes the model plus a
metrics JSON into `circle/ml/`:

```bash
python circle/ml/train_tier_model.py     # -> tier_model.joblib   + metrics
python circle/ml/train_volume_model.py   # -> volume_model.joblib + metrics
```

Commit the resulting `*.joblib` and `*_metrics.json` so the deployed app can
serve predictions (the Render build does not retrain).

## 3. Deployment to Render

1. Push this repository to GitHub.
2. In Render, **New +  ->  Blueprint** and point it at the repo. `render.yaml`
   provisions a free web service and a managed PostgreSQL database.
3. Render runs `build.sh` (install, `collectstatic`, `migrate`, `load_data`)
   and starts Gunicorn.
4. Confirm the environment variables below, then open the `*.onrender.com` URL
   and capture a screenshot for the report.

`build.sh` is already executable and idempotent.

## 4. Environment variables

| Variable | Dev default | Production (Render) |
|----------|-------------|---------------------|
| `SECRET_KEY` | `dev-secret-key-change-me` | auto-generated |
| `DEBUG` | `True` (set in `.env`) | `False` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | `raw-smith-circle.onrender.com` |
| `DATABASE_URL` | *(unset -> SQLite)* | from the managed database |
| `PYTHON_VERSION` | — | `3.12.7` |

## 5. REST API

```bash
# Tier prediction
curl -X POST http://localhost:8000/api/predict/tier/ \
  -H "Content-Type: application/json" \
  -d '{"total_points_earned":250,"transaction_count":30,"drink_purchase_ratio":0.3,"days_since_signup":60,"avg_points_per_transaction":8.3}'

# Volume forecast
curl -X POST http://localhost:8000/api/predict/volume/ \
  -H "Content-Type: application/json" \
  -d '{"forecast_date":"2026-06-01","temperature_max":31,"temperature_min":19,"precipitation":0,"coffee_price_usd":2.35}'

# Dashboard stats
curl http://localhost:8000/api/stats/
```

## 6. Project structure

```
uop-project/
├── manage.py
├── requirements.txt / runtime.txt
├── build.sh / render.yaml / .env.example
├── raw_smith_circle/        # settings, urls, wsgi, asgi
├── circle/                  # main app
│   ├── models.py            # Customer, Transaction, TierPrediction, VolumeForecast
│   ├── views.py             # 5 page views + dashboard payload
│   ├── api_views.py / serializers.py / api_urls.py
│   ├── forms.py
│   ├── ml/                  # training scripts + predictor + serialized models
│   ├── management/commands/load_data.py
│   ├── static/circle/       # css, js, svg
│   └── templates/circle/    # base.html + pages + partials
└── data/                    # anonymized CSVs (you provide)
```

## 7. Tech stack

| Layer | Choice |
|-------|--------|
| Backend | Django 5.0 |
| API | Django REST Framework |
| ML | scikit-learn (RandomForest), joblib |
| Frontend | Django templates, Tailwind (CDN), Chart.js |
| Static | WhiteNoise |
| Server | Gunicorn |
| DB | SQLite (dev) / PostgreSQL (prod) |
| Host | Render |

## 8. Phase deliverable mapping

- **Phase 1** — NumPy + Pandas EDA across five anonymized tables.
- **Phase 2** — multithreaded loader, Open-Meteo weather, ICO coffee prices.
- **Phase 3** — this app: Django + 2 ML models + Chart.js + REST API + Render.

## 9. Endpoints

| Path | Description |
|------|-------------|
| `/` | Landing page |
| `/dashboard/` | Charts + top customers |
| `/predict/tier/` | Tier classifier form |
| `/predict/volume/` | Volume regressor form |
| `/about/` | Project + stack |
| `/admin/` | Django admin |
| `/api/...` | REST API (see §5) |
| `/sitemap.xml` | Sitemap |

## 10. Credits

Abdelrahman Elkurdi · ID 202410905 · Data Science & AI, University of Petra.
Built for 606315 Programming for Data Science. All data used with permission and
anonymized.
