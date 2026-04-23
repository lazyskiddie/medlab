# MedLab — Medical Lab Report Analysis System

> Upload a lab report image or PDF → get a plain-English analysis, flagged values, detected conditions, and a downloadable PDF — all running **100% locally** with no external AI API.

---

## What it does

A patient uploads a photo of their blood test / lab report. Within ~30 seconds they receive:

- Every test value extracted from the image (OCR)
- Each value compared against clinical reference ranges (rule engine)
- An overall severity rating: Normal / Mild / Moderate / Severe
- A plain-English summary written by a local AI model (FLAN-T5)
- Detected conditions (anaemia, diabetes, thyroid issues, etc.)
- A downloadable PDF report with a colour-coded results table
- The system automatically seeds a training dataset from every upload and re-trains the local AI after every 50 new reports

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Web framework | Django 4.2 + Django REST Framework |
| Authentication | JWT (simplejwt) — 12h access token, 7d refresh |
| Database | SQLite (WAL mode — safe for concurrent reads/writes) |
| Task queue | Celery 5.6 + Redis (background analysis, training) |
| OCR | Tesseract 5 + OpenCV (preprocessing: denoise, deskew, upscale) |
| PDF extraction | pdfplumber (text PDFs) + pdf2image (scanned PDFs) |
| NLP / summarisation | FLAN-T5 base (HuggingFace, runs fully locally, CPU) |
| Named entity recognition | BiomedBERT (d4data/biomedical-ner-all, local) |
| PDF report generation | ReportLab |
| Fine-tuning | HuggingFace Seq2SeqTrainer (incremental, weighted sampling) |
| Frontend | Vanilla HTML/CSS/JS SPA (no framework, no build step) |
| Admin panel | Django Admin (custom dashboard with live stats) |

---

## Architecture

```
MEDLAB/
├── cloud_medi/          Django project config (settings, urls, celery)
├── accounts/            Custom User model (role: patient/doctor/admin)
├── reports/             LabReport + AnalysisResult models and API
├── analysis/            OCR → rules → NLP → PDF pipeline + Celery tasks
│   └── management/
│       └── commands/    setup_project, download_models, model_versions
├── training/            TrainingReport, FineTuningJob, AutoTrainingConfig
├── templates/
│   ├── frontend.html    Patient SPA (login, upload, results)
│   └── admin/
│       └── index.html   Custom admin dashboard with live stats
├── media/               Uploaded files, generated PDFs, training copies
├── ml_models/           Downloaded model weights (ner/, summarizer/)
├── logs/                Rotating log files
└── scripts/
    └── backup.sh        Backup DB + media + models
```

---

## How a report flows through the system

```
Patient uploads image/PDF
        │
        ▼
Django saves file → media/reports/
        │
        ▼
Celery fires run_analysis_pipeline task (background)
        │
        ├─► Step 1: OCR
        │     OpenCV preprocessing (grayscale → denoise → deskew → upscale)
        │     Tesseract reads all text from the image
        │
        ├─► Step 2: Rule engine
        │     Scans OCR text for 50+ known test names
        │     Compares each value to reference ranges (gender-aware)
        │     Flags each as normal / low / high / critical
        │     Determines severity: normal / mild / moderate / severe
        │
        ├─► Step 3: NLP (local FLAN-T5)
        │     Builds instruction prompt from flagged values
        │     Generates plain-English summary (no internet needed)
        │     Detects conditions: anaemia, diabetes, thyroid, kidney, liver, etc.
        │
        ├─► Step 4: PDF generation
        │     ReportLab builds colour-coded PDF
        │     Saved to media/output_reports/
        │
        ├─► Step 5: Save to SQLite
        │     AnalysisResult row created with all JSON fields
        │
        └─► Step 6: Seed training dataset
              File copied to media/training_data/user_uploads/
              TrainingReport row created (source=user_upload)
              If 50+ new samples → auto-trigger fine-tuning job
```

---

## Reference ranges covered

The rule engine covers 50+ blood tests including:

| Category | Tests |
|----------|-------|
| Complete blood count | Hemoglobin, WBC, RBC, Platelets, Hematocrit, MCV, MCH, MCHC |
| Blood glucose | Fasting glucose, HbA1c |
| Kidney function | Creatinine, BUN, Urea, Uric acid |
| Liver function | ALT/SGPT, AST/SGOT, ALP, Total bilirubin, Direct bilirubin, Albumin, Total protein |
| Thyroid | TSH, T3, T4, Free T3, Free T4 |
| Lipid profile | Total cholesterol, HDL, LDL, Triglycerides |
| Electrolytes | Sodium, Potassium, Chloride, Calcium, Magnesium |
| Iron studies | Serum iron, Ferritin |
| Vitamins | Vitamin D, Vitamin B12 |
| Inflammation | CRP, Troponin I |

Critical thresholds trigger **SEVERE** severity immediately regardless of total abnormal count.

---

## Self-training pipeline

```
Every successful analysis
        │
        ▼
TrainingReport created (source=user_upload, is_doctor_reviewed=False)
AI's own output used as initial labels (correct_summary, correct_severity)
        │
        ▼
Admin panel: Training Reports
Doctor opens record → corrects any wrong labels → clicks "Mark as reviewed"
Reviewed records get weight 1.0 in training
Unreviewed records get weight 0.5 (configurable)
        │
        ▼
When 50+ new samples accumulated (configurable threshold):
FineTuningJob created → Celery runs Seq2SeqTrainer
FLAN-T5 weights updated → saved to ml_models/summarizer_finetuned/
        │
        ▼
Every subsequent analysis uses the improved model
Model gets smarter with every upload
```

---

## Setup — from zero to running

### Prerequisites (install once)

```bash
# Mac
brew install tesseract redis poppler
brew services start redis

# Ubuntu
sudo apt install tesseract-ocr redis-server poppler-utils libgl1 libglib2.0-0
sudo systemctl start redis
```

### Install and run

```bash
# 1. Clone / download the project
cd MEDLAB

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install Python packages
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Open .env and set:
#   TESSERACT_CMD=/opt/homebrew/bin/tesseract   (Mac)
#   TESSERACT_CMD=/usr/bin/tesseract            (Linux)

# 5. First-time setup (migrations + admin user + folders)
python manage.py setup_project

# 6. Download AI models (~700MB, runs once)
python manage.py download_models
```

### Run (3 terminals)

```bash
# Terminal 1 — Django web server
python manage.py runserver

# Terminal 2 — Celery worker (runs analysis in background)
celery -A cloud_medi worker --loglevel=info

# Terminal 3 — Celery beat (auto-training scheduler)
celery -A cloud_medi beat --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Open in browser

| URL | What it is |
|-----|-----------|
| `http://localhost:8000/` | Patient app — login, upload, results |
| `http://localhost:8000/admin/` | Admin panel — admin / admin1234 |
| `http://localhost:8000/api/health/` | System health JSON |

---

## Admin panel guide

### Reports → Lab reports
- See all uploaded reports and their status
- Use **"Re-run analysis pipeline"** action to retry failed reports
- Click any report to see the inline analysis result

### Reports → Analysis results
- Full detail of every analysis: raw OCR text, extracted values, flagged items
- Auto-populated — you never need to create these manually

### Training → Training reports
- Auto-populated from every successful analysis
- **Your job:** open each record, check if the AI labels are correct, fix any mistakes, click **"Mark as doctor-reviewed"**
- Reviewed records carry double weight in the next training run

### Training → Auto-training config
- 1 row only — click it to change settings
- `new_samples_threshold`: how many new uploads trigger auto-training (default 50)
- `include_unreviewed`: whether unreviewed uploads count toward training (default True)
- `unreviewed_weight`: how much unreviewed samples count vs reviewed (default 0.5)

### Training → Fine tuning jobs
- Auto-created when threshold is reached
- You can also manually create one here and click **"Start fine-tuning"**
- Watch the `logs` field to see training progress

### Periodic tasks → Periodic tasks
- Daily auto-training check, weekly force-training, 6h stale cleanup
- These run automatically in Celery beat — no action needed

---

## API reference

### Authentication
```
POST /api/auth/token/           Body: {username, password}  → {access, refresh}
POST /api/auth/token/refresh/   Body: {refresh}             → {access}
```

### Accounts
```
POST /api/accounts/register/    Body: {username, email, password, password2, ...}
GET  /api/accounts/profile/     Header: Authorization: Bearer <token>
PATCH /api/accounts/profile/    Update name, phone, gender, date_of_birth
```

### Reports
```
POST /api/reports/upload/       Multipart: file (JPG/PNG/PDF, max 20MB)
POST /api/reports/bulk-upload/  Multipart: files[] (multiple)
GET  /api/reports/              List (patients see own; staff see all)
GET  /api/reports/<uuid>/       Full detail including analysis result
DELETE /api/reports/<uuid>/     Delete report and file
```

### Analysis
```
GET  /api/analysis/status/<uuid>/     Poll analysis progress
POST /api/analysis/retrigger/<uuid>/  Admin only — re-run pipeline
```

### Training
```
GET  /api/training/data/              List training reports (admin only)
POST /api/training/data/              Upload new training record (admin)
POST /api/training/data/<uuid>/review/ Mark as doctor-reviewed
GET  /api/training/jobs/              List fine-tuning jobs
POST /api/training/jobs/              Create new job
POST /api/training/jobs/<uuid>/start/ Queue a job
GET  /api/training/stats/             Full dashboard stats
```

---

## Model management

```bash
# Save current fine-tuned model as a new version
python manage.py model_versions --snapshot

# List all saved versions
python manage.py model_versions

# Activate a specific version
python manage.py model_versions --activate 2

# Roll back to the previous version
python manage.py model_versions --rollback

# Show which version is active
python manage.py model_versions --info
```

---

## Backup

```bash
# Full backup (DB + media + model weights)
./scripts/backup.sh

# DB only (fast — good for daily cron)
./scripts/backup.sh --db

# Restore from a DB backup
./scripts/backup.sh --restore backups/db/db_2026-04-15_01-00-00.sqlite3.gz
```

Add to crontab for daily automated backup:
```
0 1 * * * /path/to/MEDLAB/scripts/backup.sh >> /path/to/logs/backup.log 2>&1
```

---

## Improvement roadmap

### Already working
- [x] OCR with image preprocessing (denoise, deskew, upscale)
- [x] 50+ reference ranges with gender-aware thresholds
- [x] Critical value detection (glucose <40, K <2.5, Hb <7.0, etc.)
- [x] Local FLAN-T5 summarisation (no API needed)
- [x] Automatic training dataset seeding from every upload
- [x] Weighted fine-tuning (reviewed samples count more)
- [x] Model versioning with snapshot/rollback
- [x] Auto-training trigger after configurable threshold
- [x] Weekly force-training via Celery Beat
- [x] PDF report with colour-coded results table
- [x] JWT authentication with token refresh
- [x] Admin dashboard with live system stats

### Suggested improvements

#### Accuracy improvements
- **More reference ranges** — add HbA1c trends, ferritin, folate, PSA, cortisol
- **Age-specific ranges** — children and elderly have different normal ranges
- **Unit conversion** — some labs report in mmol/L vs mg/dL; auto-detect and convert
- **Multi-language OCR** — add Hindi, Tamil, Telugu language packs to Tesseract for Indian lab reports
- **Better image preprocessing** — add brightness/contrast normalisation for dark phone photos

#### Features to add
- **Trend graphs** — show how values change across multiple uploads over time
- **Doctor portal** — separate login for doctors to review all patient reports
- **Email notifications** — email patient when analysis is complete or critical values found
- **Report comparison** — side-by-side view of two reports to see changes
- **Bulk import** — admin can upload a folder of lab reports at once for training
- **DICOM support** — some labs export DICOM format, not just JPEG/PDF

#### Performance improvements
- **GPU inference** — if a GPU is available, FLAN-T5 runs 10× faster
- **Model quantisation** — use int8 quantised FLAN-T5 for lower RAM usage (from ~3GB to ~1GB)
- **Async PDF generation** — move ReportLab to a separate Celery task so it doesn't block the main pipeline
- **PostgreSQL** — swap SQLite for PostgreSQL for multi-user production deployments
- **Redis Sentinel** — make Redis highly available for production

#### Security improvements
- **File type verification** — verify magic bytes, not just content-type header
- **Rate limiting per IP** — add nginx-level rate limiting for the upload endpoint
- **Audit log** — record every admin action (who reviewed what, when)
- **Data encryption at rest** — encrypt media files using Django-encrypted-files

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Analysis shows FAILED | Tesseract not found | `which tesseract` then hardcode path in `ocr.py` |
| Celery worker not picking up tasks | Redis not running | `brew services start redis` |
| Models not loading | download_models not run | `python manage.py download_models` |
| Admin stats show 401 | Admin dashboard JS using session auth | Normal — stats require JWT which admin doesn't have |
| OCR text is empty | Image too dark/blurry | Improve preprocessing or use a clearer photo |
| Training not triggering | Threshold not reached | Lower threshold in Auto-training config admin |

---

## Environment variables reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | insecure default | Django secret key — change in production |
| `DEBUG` | True | Set False in production |
| `ALLOWED_HOSTS` | `*` | Comma-separated allowed hostnames |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `TESSERACT_CMD` | `/usr/bin/tesseract` | Full path to Tesseract binary |
| `NER_MODEL_NAME` | `d4data/biomedical-ner-all` | HuggingFace NER model |
| `SUMMARIZER_MODEL_NAME` | `google/flan-t5-base` | HuggingFace summariser model |

---

## Licence

MIT — free to use, modify and distribute.