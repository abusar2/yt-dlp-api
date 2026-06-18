# استخدام نسخة بايثون خفيفة ومستقرة
FROM python:3.10-slim

# تثبيت ffmpeg والأدوات اللازمة للنظام لضمان عمل yt-dlp بدون مشاكل
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# تحديد مجلد العمل داخل الحاوية
WORKDIR /app

# نسخ وتثبيت مكتبات البايثون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع
COPY . .

# تشغيل السيرفر مع ربط المنفذ (Port) الديناميكي من Render تلقائياً
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
