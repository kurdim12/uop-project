---
title: Raw Smith Circle
emoji: ☕
colorFrom: yellow
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
short_description: Loyalty analytics & ML for Raw Smith Specialty Coffee
---

<!-- The block above is Hugging Face Space metadata (it configures the card and
     the Docker SDK). It is ignored on GitHub except as a small table. -->

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

## 3b. Deploy to PythonAnywhere (free tier, SQLite)

A fully free alternative with no credit card and **persistent** storage (so the
SQLite database survives restarts). No `gunicorn` / `render.yaml` are used here —
PythonAnywhere runs the app through a WSGI config file, and WhiteNoise serves the
static files.

**1. Create a free "Beginner" account** at <https://www.pythonanywhere.com>.

**2. Open a Bash console** (Consoles -> Bash) and set the project up:

```bash
git clone https://github.com/kurdim12/uop-project.git
cd uop-project
mkvirtualenv --python=/usr/bin/python3.10 rsc      # any Python 3.10+ is fine
pip install --no-cache-dir -r requirements.txt
```

**3. Create the production `.env`** in the project root (`nano .env`):

```
SECRET_KEY=PASTE_A_LONG_RANDOM_STRING
DEBUG=False
ALLOWED_HOSTS=USERNAME.pythonanywhere.com
```

Generate a secret key with:
`python -c "import secrets; print(secrets.token_urlsafe(50))"`

**4. Initialize the database and static files:**

```bash
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py load_data
```

**5. Web tab -> "Add a new web app" -> Manual configuration -> Python 3.10.**
Then in the Web tab set:

- **Virtualenv:** `/home/USERNAME/.virtualenvs/rsc`
- **WSGI configuration file** (click the link): replace its entire contents with
  the snippet below (change `USERNAME`):

```python
import os
import sys

project_home = "/home/USERNAME/uop-project"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Django reads SECRET_KEY / DEBUG / ALLOWED_HOSTS from the project's .env file.
os.environ["DJANGO_SETTINGS_MODULE"] = "raw_smith_circle.settings"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
```

- **Static files** (optional, recommended on PA): URL `/static/` ->
  Directory `/home/USERNAME/uop-project/staticfiles`. WhiteNoise also serves
  static, so the site works even without this mapping.

**6. Click "Reload"** and open `https://USERNAME.pythonanywhere.com`.

**Updating later:**

```bash
workon rsc && cd ~/uop-project
git pull
pip install --no-cache-dir -r requirements.txt   # only if requirements changed
python manage.py migrate && python manage.py collectstatic --noinput
# then click Reload in the Web tab
```

**Troubleshooting:**

- **Disk quota (free tier = 512 MB):** the ML stack (scikit-learn, pandas,
  numpy, scipy) is large. `--no-cache-dir` helps. If `pip` runs out of space,
  use the cheapest paid PA plan for more disk, or keep Render's free web service
  and point `DATABASE_URL` at a free Neon/Supabase Postgres instead.
- **400 Bad Request:** `ALLOWED_HOSTS` must equal exactly
  `USERNAME.pythonanywhere.com`.
- **Static files 404:** re-run `collectstatic` and Reload, or add the static
  mapping above.
- **Models won't load:** ensure `requirements.txt` installed cleanly — the
  committed `.joblib` models were built with the pinned `scikit-learn==1.5.2`
  and `numpy==2.1.3`.

## 3c. Deploy to Hugging Face Spaces (free, Docker)

Fully free, no credit card, and generous resources (16 GB RAM, ~50 GB disk) so
the ML libraries are never a problem. The included `Dockerfile` + `start.sh`
build the image, collect static, seed SQLite, and run Gunicorn on port 7860.
The Space front-matter at the top of this README configures it automatically.

**1. Create a free account** at <https://huggingface.co> and a **write
access token** (Settings -> Access Tokens).

**2. Create a new Space:** New -> Space -> **SDK: Docker -> Blank**, CPU basic
(free). Name it e.g. `raw-smith-circle`.

**3. Push this repo to the Space** (Spaces are git repos):

```bash
git remote add space https://huggingface.co/spaces/HF_USERNAME/raw-smith-circle
git push space claude/clever-sagan-T4ooK:main
# username = your HF username, password = your HF write token
```

**Alternative to step 3 (no git needed)** — run the bundled helper, which
creates the Space and uploads everything via the `huggingface_hub` library:

```bash
pip install huggingface_hub
export HF_TOKEN=your-write-token          # from HF Settings -> Access Tokens
python deploy_hf.py HF_USERNAME           # space name defaults to raw-smith-circle
```

Either way, the Space builds the Docker image and goes live at
`https://HF_USERNAME-raw-smith-circle.hf.space`.

**That's it** — no environment variables are required:
- `ALLOWED_HOSTS` is preset to `.hf.space` (matches any Space subdomain).
- `SECRET_KEY` is auto-generated at startup; *optionally* set a stable one under
  the Space's **Settings -> Variables and secrets** (secret named `SECRET_KEY`)
  if you want admin sessions to survive restarts.

The free tier sleeps after inactivity and wakes on the next visit (fine for a
demo). Storage is reset on rebuild, but `start.sh` re-seeds the data each boot.

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
