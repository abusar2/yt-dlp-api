# 1. استخدام نسخة بايثون خفيفة ومستقرة
FROM python:3.10-slim

# 2. تثبيت عُقدة Node.js و npm داخل السيرفر
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

# 3. تثبيت أداة توليد التوكن اليوتيوب بشكل عالمي داخل السيرفر
RUN npm install -g youtube-po-token-generator

# 4. إعداد مجلد العمل الخاص بالبايثون
WORKDIR /app

# 5. تثبيت مكتبات البايثون (FastAPI, yt-dlp, uvicorn)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. نسخ باقي ملفات المشروع إلى السيرفر
COPY . .

# 7. الأمر التشغيلي للسيرفر
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]