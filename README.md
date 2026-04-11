# MedLab — Medical Lab Report Analyser

Zero external LLM API. Everything runs locally on your server.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Django 4.2 + Django REST Framework |
| Auth | JWT via `djangorestframework-simplejwt` |
| Async queue | Celery + Redis |
| OCR | Tesseract 5 + OpenCV + pdfplumber |
| Rule engine | Pure Python reference ranges |
| NLP (local) | FLAN-T5 + BiomedBERT via Hugging Face |
| Fine-tuning | Hugging Face Trainer (runs on your server) |
| PDF reports | ReportLab |
| Database | SQLite (dev) / PostgreSQL (prod) |

---

## Setup

### 1. Clone and create virtual environment
```bash
cd MEDLAB
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Install system dependencies

**macOS**
```bash
brew install tesseract redis
brew services start redis
```

**Ubuntu / Debian**
```bash
sudo apt update
sudo apt install tesseract-ocr redis-server poppler-utils
sudo systemctl start redis
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env — at minimum set TESSERACT_CMD to your tesseract binary path
```

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Create a superuser (admin)
```bash
python manage.py createsuperuser
```

### 7. Download AI models to local disk (one-time, needs internet)
```bash
python manage.py download_models
```
After this, the server never needs internet access for analysis.

### 8. Create required directories
```bash
mkdir -p media/output_reports ml_models static
```

---

## Running the server

You need **3 terminal windows**:

**Terminal 1 — Django**
```bash
source venv/bin/activate
python manage.py runserver
```

**Terminal 2 — Celery worker**
```bash
source venv/bin/activate
celery -A cloud_medi worker --loglevel=info
```

**Terminal 3 — Redis** (if not running as a service)
```bash
redis-server
```

---

## API Endpoints

### Auth
| Method | URL | Description |
|---|---|---|
| POST | `/api/auth/token/` | Get JWT token (login) |
| POST | `/api/auth/token/refresh/` | Refresh token |
| POST | `/api/accounts/register/` | Register new user |
| GET/PATCH | `/api/accounts/profile/` | View/edit profile |

### Reports (patient)
| Method | URL | Description |
|---|---|---|
| POST | `/api/reports/upload/` | Upload a lab report (image or PDF) |
| GET | `/api/reports/` | List your reports |
| GET | `/api/reports/<id>/` | Get report detail + analysis result |
| GET | `/api/analysis/status/<id>/` | Poll analysis status |

### Training (admin only)
| Method | URL | Description |
|---|---|---|
| POST | `/api/training/data/` | Upload annotated training report |
| GET | `/api/training/data/` | List training reports |
| POST | `/api/training/jobs/` | Create a fine-tuning job |
| POST | `/api/training/jobs/<id>/start/` | Start fine-tuning |
| GET | `/api/training/stats/` | Dashboard stats |

### Admin panel
```
http://localhost:8000/admin/
```

---

## How it works

```
User uploads image/PDF
        ↓
Django saves file → fires Celery task
        ↓
[Celery Worker]
  1. OCR (Tesseract + OpenCV preprocessing)
  2. Rule engine (compare values to reference ranges)
  3. Local FLAN-T5 → generate plain-English summary
  4. Condition detection (rule-based from flagged values)
  5. PDF report generation (ReportLab)
        ↓
Result saved to DB → user can poll /status/ or fetch /reports/<id>/
```

---

## Admin fine-tuning workflow

1. Go to **Admin panel → Training Reports → Add**
2. Upload a lab report image + fill in the correct summary and severity
3. OCR runs automatically in background
4. Once you have 5+ processed reports, go to **Fine-tuning Jobs → Add**
5. Select the base model and click **Start fine-tuning**
6. The fine-tuned model weights are saved to `ml_models/summarizer_finetuned/`
7. Restart Celery workers to load the new model

---

## Project structure

```
MEDLAB/
├── cloud_medi/          # Django project config
│   ├── settings.py
│   ├── celery.py
│   └── urls.py
├── accounts/            # Custom User model + auth
├── reports/             # LabReport + AnalysisResult models + APIs
├── analysis/            # OCR, rule engine, NLP, PDF generator, Celery task
│   ├── ocr.py
│   ├── rules.py         ← reference ranges live here
│   ├── nlp.py           ← local model inference, no API
│   ├── pdf_report.py
│   └── tasks.py
├── training/            # Admin fine-tuning pipeline
│   ├── models.py
│   ├── finetuning.py
│   ├── admin.py         ← bulk upload UI
│   └── tasks.py
├── ml_models/           # Downloaded model weights (git-ignored)
├── media/               # Uploaded files + generated PDFs
├── requirements.txt
└── .env.example
```

---

## Adding more lab tests

Open `analysis/rules.py` and add to `REFERENCE_RANGES`:

```python
'test_name': {
    'male':   (low, high),   # or 'all': (low, high)
    'female': (low, high),
    'unit': 'unit_string',
    'full_name': 'Human Readable Name',
},
```

That's it — the rule engine picks it up automatically.