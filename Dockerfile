FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

RUN mkdir -p media/reports media/training_data/user_uploads \
    media/output_reports ml_models/ner ml_models/summarizer \
    staticfiles static logs

ENV DJANGO_SETTINGS_MODULE=cloud_medi.settings \
    PYTHONUNBUFFERED=1 \
    TESSERACT_CMD=/usr/bin/tesseract

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]