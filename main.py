import os
import uvicorn
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp

app = FastAPI(title="Universal Video Downloader API")

# 1. تفعيل الـ CORS لحل مشكلة الحظر والسماح لمدونة بلوجر بالاتصال بالسيرفر بحرية
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# الصفحة الرئيسية للسيرفر للتأكد من أنه يعمل ومستيقظ
@app.get("/")
def read_root():
    return {"status": "alive", "message": "Dockerized yt-dlp API is running smoothly with Android spoofing!"}

# 2. مسار استخراج بيانات الفيديو (المتوافق مع كود التمرير في بلوجر)
@app.get("/get-video")
def get_video(url: str = Query(..., description="The URL of the video")):
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL parameter")
    
    # مسار ملف الكوكيز (اختياري، يعمل تلقائياً إذا تم رفعه للمستودع)
    cookie_path = "cookies.txt"
    
    # الإعدادات المتقدمة جداً لتخطي حظر وفلترة يوتيوب للسيرفرات
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'allowed_extractors': ['.*'],
        'nocheckcertificate': True,  # تخطي فحص الشهادات الأمنية
        'geo_bypass': True,          # تخطي الحظر الجغرافي
        
        # التمويه المتقدم: إيهام يوتيوب أن الطلب قادم من تطبيق أندرويد/آيفون رسمي وليس سيرفر ويب
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
            }
        },
        'http_headers': {
            'User-Agent': 'com.google.android.youtube/19.05.36 (Linux; U; Android 11; en_US; Pixel 5 Build/RD1A.201105.003.C1)',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    
    # إذا قمت برفع ملف cookies.txt إلى المستودع، سيقوم الكود بدمجه تلقائياً لضمان تخطي حظر 403
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # استخراج الرابط المباشر الفعلي للفيديو
            video_url = info.get('url') or (info.get('formats')[-1].get('url') if info.get('formats') else None)
            title = info.get('title', 'Video successfully fetched')
            thumbnail = info.get('thumbnail', '')
            
            if not video_url:
                raise HTTPException(status_code=404, detail="Could not extract direct download URL")
                
            return {
                "url": video_url,
                "title": title,
                "thumbnail": thumbnail
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting video: {str(e)}")

# 3. مسار الوسيط (Proxy) لإجبار المتصفح على تحميل الفيديو فوراً بدلاً من تشغيله
@app.get("/proxy-download")
async def proxy_download(url: str = Query(..., description="The direct video URL"), filename: str = "video"):
    try:
        async def video_streamer():
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        raise HTTPException(status_code=response.status_code, detail="Failed to fetch video source")
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        yield chunk
        
        # تنظيف اسم الملف من أي رموز قد تسبب مشاكل في التحميل
        safe_filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        if not safe_filename:
            safe_filename = "video"

        headers = {
            "Content-Disposition": f'attachment; filename="{safe_filename}.mp4"',
            "Content-Type": "video/mp4"
        }
        return StreamingResponse(video_streamer(), media_type="video/mp4", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

# 4. إعداد ربط المنفذ (Port Binding) الديناميكي لمنصة Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
