import os
import json
import time
import subprocess
import yt_dlp
import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import quote

app = FastAPI()

# تفعيل الـ CORS لربط السيرفر بمدونة بلوجر بدون قيود
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# نظام الكاش للتوكن لضمان سرعة السيرفر
cached_token = None
cached_visitor_data = None
last_token_time = 0
TOKEN_EXPIRY = 3600  # تجديد التوكن كل ساعة

def get_live_po_token():
    """توليد توكن يوتيوب تلقائياً في الخلفية عبر Node.js"""
    global cached_token, cached_visitor_data, last_token_time
    current_time = time.time()
    
    if cached_token and cached_visitor_data and (current_time - last_token_time < TOKEN_EXPIRY):
        return cached_visitor_data, cached_token

    try:
        result = subprocess.run(
            ["youtube-po-token-generator"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        token_data = json.loads(result.stdout)
        cached_visitor_data = token_data.get("visitorData")
        cached_token = token_data.get("poToken")
        last_token_time = current_time
        print("🚀 [PoToken] Token updated successfully!")
        return cached_visitor_data, cached_token
    except Exception as e:
        print(f"❌ [PoToken Error]: {e}")
        if cached_token:
            return cached_visitor_data, cached_token
        raise Exception("Failed to generate PO Token.")

@app.get("/get-video")
async def get_video(url: str = Query(..., description="Social media video URL")):
    """المسار الأول: جلب معلومات الفيديو وصورة العرض والرابط المباشر"""
    try:
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
        }

        if "youtube.com" in url or "youtu.be" in url:
            visitor_data, po_token = get_live_po_token()
            ydl_opts['extractor_args'] = {
                'youtube': {
                    'po_token': [f'web+{po_token}', visitor_data],
                }
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            download_url = info.get('url')
            
            if not download_url and formats:
                suitable = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                download_url = suitable[-1].get('url') if suitable else formats[-1].get('url')

            # تنظيف اسم الفيديو لحمايته من المشاكل البرمجية
            title = info.get('title', 'video').replace('/', '_').replace('\\', '_')

            return {
                "title": title,
                "thumbnail": info.get('thumbnail', 'https://placehold.co/120x90?text=Ready'),
                "url": download_url
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/proxy-download")
async def proxy_download(url: str = Query(...), filename: str = Query("video.mp4")):
    """المسار الثاني والجديد: إجبار المتصفح على تحميل الفيديو فوراً بدلاً من تشغيله"""
    
    # التأكد من إضافة امتداد mp4 للملف
    if not filename.endswith(".mp4"):
        filename += ".mp4"
        
    async def stream_video():
        # استخدام httpx لعمل تحويل (Stream) لبيانات الفيديو مباشرة للمستخدم
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", url) as response:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 64): # 64KB chunks
                    yield chunk

    # تشفير اسم الملف ليدعم اللغة العربية بامتياز بدون رموز غريبة
    encoded_filename = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        "Content-Type": "video/mp4"
    }
    
    return StreamingResponse(stream_video(), headers=headers)
