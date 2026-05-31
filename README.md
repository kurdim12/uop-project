---
title: Raw Smith Circle
emoji: ☕
colorFrom: orange
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Loyalty analytics & ML for Raw Smith Specialty Coffee
---

<!-- The block above is Hugging Face Space metadata: it configures the Space
     card and the Docker SDK. On GitHub it renders as a small table. -->

# Raw Smith Circle

> Loyalty analytics and machine-learning platform for **Raw Smith Specialty
> Coffee** (Amman, Jordan). Phase 3 of the course project for *606315
> Programming for Data Science* — University of Petra, Dr. Mohammad Arafah.

A production-ready Django web app that turns three phases of anonymized
loyalty data into an interactive product: an analytics dashboard, two trained
scikit-learn models served through both web forms and a REST API, the Django
admin, and a one-command cloud deployment.

**Live demo:** _set after deployment_ — e.g.
`https://YOUR_HF_USER-raw-smith-circle.hf.space`

---

## Contents

1. [Features](#1-features)
2. [Model results](#2-model-results)
3. [Local quickstart](#3-local-quickstart)
4. [Training the models](#4-training-the-models)
5. [Deployment](#5-deployment)
   - [5.1 Hugging Face Spaces (free, recommended)](#51-hugging-face-spaces-free-recommended)
   - [5.2 Render (Blueprint)](#52-render-blueprint)
   - [5.3 PythonAnywhere (free tier, SQLite)](#53-pythonanywhere-free-tier-sqlite)
6. [REST API](#6-rest-api)
7. [Environment variables](#7-environment-variables)
8. [Project structure](#8-project-structure)
9. [Tech stack](#9-tech-stack)
10. [Endpoints reference](#10-endpoints-reference)
11. [Phase deliverable mapping](#11-phase-deliverable-mapping)
12. [Credits](#12-credits)

---

## 1. Features

- **Dashboard** (`/dashboard/`) — Chart.js charts powered entirely by Django
  ORM aggregations: tier distribution (doughnut), monthly point flow
  (dual-axis line), points by earn source (horizontal bar), daily transactions
  with a 7-day rolling average, top-10 customers table, and a four-card stat
  row.
- **Tier classifier** (`/predict/tier/`) — predicts a customer's loyalty tier
  (bronze / silver / gold) from five behavioural features, with class
  probabilities and a targeted marketing recommendation.
- **Daily-volume regressor** (`/predict/volume/`) — forecasts daily loyalty
  points, expected transactions, and a reward-inventory suggestion from
  weather, day-of-week, month, and the prevailing Arabica coffee price.
- **REST API** (`/api/...`) — JSON endpoints for both predictions and the
  dashboard aggregates, with DRF input validation.
- **Django admin** (`/admin/`) — every prediction made through a form or the
  API is persisted and auditable here.
- **Production polish**: WhiteNoise for static, env-driven settings (SQLite
  or Postgres), idempotent data loader, branded 404 / 500 pages, sitemap,
  Open Graph tags, print-friendly stylesheet.

## 2. Model results

Both models are trained from the anonymized Phase 1 / 2 data via two
standalone scripts; the trained `*.joblib` and a metrics JSON are committed
so the deployed app serves predictions without retraining.

| Model | Pipeline | Train / Test | Result |
|-------|----------|-------------:|--------|
| Tier classifier | `StandardScaler` → `RandomForestClassifier` (balanced) | 107 / 47 | **Accuracy 0.957**, weighted F1 **0.955** |
| Volume regressor | `ColumnTransformer` (`StandardScaler` + `OneHotEncoder`) → `RandomForestRegressor` | 269 / 116 | RMSE **76.0**, MAE **46.0**, R² **−0.07** |

The near-zero R² of the volume model is itself a finding: daily total points
are dominated by program events (welcome bonuses, admin adjustments,
referrals) that are unrelated to weather, so weather and coffee features
explain very little of the day-to-day variance. Full confusion matrices and
feature importances are saved to `circle/ml/*_metrics.json`.

## 3. Local quickstart

```bash
git clone https://github.com/kurdim12/uop-project.git
cd uop-project

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit SECRET_KEY / DEBUG if needed
python manage.py migrate
python manage.py load_data         # seeds from data/*.csv
python manage.py runserver
```

Open <http://localhost:8000/>. `load_data` and both training scripts find the
CSVs in either `data/` or the repo root, so it does not matter which one you
drop new files into.

## 4. Training the models

Each script reads from `data/` (or the repo root), builds features, trains on
a 70 / 30 split with `random_state=42`, evaluates, and writes the model plus
a metrics JSON into `circle/ml/`:

```bash
python circle/ml/train_tier_model.py     # -> tier_model.joblib   + metrics
python circle/ml/train_volume_model.py   # -> volume_model.joblib + metrics
```

Commit the resulting `*.joblib` and `*_metrics.json` so deployments serve
predictions without retraining.

## 5. Deployment

The app is host-agnostic: it falls back to SQLite when `DATABASE_URL` is
unset and serves its own static files through WhiteNoise. Three options
below, in order of recommendation.

### 5.1 Hugging Face Spaces (free, recommended)

Fully free, no credit card, with generous resources (16 GB RAM, ~50 GB disk),
so the ML libraries never hit a quota wall. The bundled `Dockerfile` and
`start.sh` build the image, collect static, seed SQLite, and run Gunicorn on
port 7860. The Space front-matter at the top of this README configures
everything else automatically.

1. Sign in at <https://huggingface.co>, then create a **Write** access token
   at **Settings → Access Tokens** (it will look like `hf_...`).
2. Deploy with the included helper — no git remote setup needed:
   ```bash
   pip install huggingface_hub
   export HF_TOKEN=hf_xxxxxxxx
   python deploy_hf.py YOUR_HF_USERNAME      # space defaults to raw-smith-circle
   ```
3. The build takes about 3 – 5 minutes. The app goes live at
   `https://YOUR_HF_USERNAME-raw-smith-circle.hf.space`.

Prefer git? Create the Space manually
(**New → Space → SDK: Docker → Blank**, CPU basic) and push from this
checkout:

```bash
git remote add space https://huggingface.co/spaces/YOUR_HF_USERNAME/raw-smith-circle
git push -f space HEAD:main
# username = HF username, password = HF Write token
```

No environment variables are required: `ALLOWED_HOSTS` is preset to
`.hf.space`, `SECRET_KEY` auto-generates at startup, and `start.sh` re-seeds
the SQLite database on each boot. To make admin sessions survive restarts,
set a stable `SECRET_KEY` under the Space's
**Settings → Variables and secrets**.

### 5.2 Render (Blueprint)

Push the repo to GitHub, then in Render choose **New → Blueprint** and point
it at the repository. `render.yaml` provisions a free web service and a
managed PostgreSQL database; `build.sh` runs `pip install`, `collectstatic`,
`migrate`, then `load_data`, and Gunicorn starts automatically.

After deployment, confirm:
- the assigned hostname matches `ALLOWED_HOSTS` (`render.yaml` ships with
  `raw-smith-circle.onrender.com`; update the env var if Render assigned a
  different name);
- the build log shows the data and models loaded.

If Render's free PostgreSQL expires (90 days), point `DATABASE_URL` at a
free **Neon** or **Supabase** Postgres connection string and keep using the
free web service.

### 5.3 PythonAnywhere (free tier, SQLite)

No credit card and persistent disk, but the 512 MB free quota is tight for
the ML stack — `--no-cache-dir` gives the best chance of fitting; fall back
to options 5.1 / 5.2 if `pip` runs out of space.

In a Bash console:

```bash
git clone https://github.com/kurdim12/uop-project.git
cd uop-project
mkvirtualenv --python=/usr/bin/python3.10 rsc
pip install --no-cache-dir -r requirements.txt
```

Create the production `.env` (`nano .env`):

```
SECRET_KEY=paste-a-long-random-string
DEBUG=False
ALLOWED_HOSTS=USERNAME.pythonanywhere.com
```

Generate the key with:
`python -c "import secrets; print(secrets.token_urlsafe(50))"`.

Initialize the database and static files:

```bash
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py load_data
```

In the **Web** tab, **Add a new web app → Manual configuration → Python
3.10**. Set the virtualenv to `/home/USERNAME/.virtualenvs/rsc` and replace
the generated WSGI file with:

```python
import os, sys

project_home = "/home/USERNAME/uop-project"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ["DJANGO_SETTINGS_MODULE"] = "raw_smith_circle.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Click **Reload** and open `https://USERNAME.pythonanywhere.com`. To update
later: `git pull`, optionally reinstall requirements,
`python manage.py migrate && python manage.py collectstatic --noinput`, then
Reload from the Web tab.

## 6. REST API

```bash
# Tier prediction
curl -X POST http://localhost:8000/api/predict/tier/ \
  -H 'Content-Type: application/json' \
  -d '{"total_points_earned":250,"transaction_count":30,"drink_purchase_ratio":0.3,"days_since_signup":60,"avg_points_per_transaction":8.3}'

# Volume forecast
curl -X POST http://localhost:8000/api/predict/volume/ \
  -H 'Content-Type: application/json' \
  -d '{"forecast_date":"2026-06-01","temperature_max":31,"temperature_min":19,"precipitation":0,"coffee_price_usd":2.35}'

# Dashboard aggregates
curl http://localhost:8000/api/stats/
```

Both prediction endpoints return `503` with a clear message if the
corresponding model has not been trained yet; invalid input returns `400`
with field-level errors from DRF.

## 7. Environment variables

| Variable | Local default | Production |
|----------|---------------|------------|
| `SECRET_KEY` | `dev-secret-key-change-me` | required — Render auto-generates; HF auto-generates at boot |
| `DEBUG` | `True` (from `.env`) | `False` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | host-specific (e.g. `.hf.space`, `USERNAME.pythonanywhere.com`, `raw-smith-circle.onrender.com`) |
| `DATABASE_URL` | *unset → SQLite* | Postgres connection string (Render) |
| `SECURE_SSL_REDIRECT` | n/a | defaults to `True`; set `False` on hosts that terminate TLS themselves (HF Spaces) to avoid redirect loops |

## 8. Project structure

```
uop-project/
├── manage.py
├── requirements.txt / runtime.txt
├── Dockerfile / start.sh / .dockerignore      # Hugging Face Spaces image
├── deploy_hf.py                               # one-command HF deploy helper
├── render.yaml / build.sh / .env.example      # Render Blueprint
├── raw_smith_circle/                          # settings, urls, wsgi, asgi
├── circle/                                    # main Django app
│   ├── models.py            # Customer, Transaction, TierPrediction, VolumeForecast
│   ├── views.py             # 5 page views + dashboard payload
│   ├── forms.py
│   ├── api_views.py / serializers.py / api_urls.py
│   ├── urls.py / admin.py / apps.py / sitemaps.py
│   ├── ml/                  # training scripts + predictor + serialized models
│   ├── management/commands/load_data.py
│   ├── static/circle/       # css, js, svg
│   └── templates/circle/    # base.html + pages + partials
└── data/                                      # anonymized CSVs (see data/README.md)
```

## 9. Tech stack

| Layer | Choice |
|-------|--------|
| Backend | Django 5.0 |
| API | Django REST Framework 3.15 |
| ML | scikit-learn 1.5 (RandomForest pipelines), joblib |
| Frontend | Django templates · Tailwind (Play CDN) · Chart.js |
| Static files | WhiteNoise |
| Server | Gunicorn |
| Database | SQLite (dev) · PostgreSQL (Render prod) |
| Hosting | Hugging Face Spaces · Render · PythonAnywhere |
| Language | Python 3.12 (works on 3.10+) |

## 10. Endpoints reference

| Path | Description |
|------|-------------|
| `/` | Landing page |
| `/dashboard/` | Charts, top-10 customers, stat cards |
| `/predict/tier/` | Tier classifier form + result panel |
| `/predict/volume/` | Daily-volume forecast form + result panel |
| `/about/` | Project overview and tech stack |
| `/admin/` | Django admin |
| `/api/predict/tier/` | Tier prediction API (POST) |
| `/api/predict/volume/` | Volume forecast API (POST) |
| `/api/stats/` | Dashboard aggregates (GET) |
| `/sitemap.xml` | Sitemap |

## 11. Phase deliverable mapping

- **Phase 1** — NumPy + Pandas EDA across five anonymized tables
  (transactions, customers, rewards, redemptions, menu).
- **Phase 2** — multithreaded CSV loader, Open-Meteo weather API (Amman
  daily weather), ICO Arabica coffee prices, all merged into a single
  enriched dataset.
- **Phase 3 (this repository)** — Django web application, two scikit-learn
  models, Chart.js dashboard, Django REST Framework API, cloud deployment.

## 12. Credits

Abdelrahman Elkurdi · Student ID 202410905 · Data Science & AI, University
of Petra. Built for *606315 Programming for Data Science*, taught by
Dr. Mohammad Arafah. All data used with permission and anonymized.
