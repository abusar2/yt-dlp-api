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
    allow_origins=["*"],  # يسمح لجميع النطاقات بالوصول، يمكنك تخصيصه لرابط مدونتك لاحقاً
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# الصفحة الرئيسية للسيرفر للتأكد من أنه يعمل
@app.get("/")
def read_root():
    return {"status": "alive", "message": "Universal Video Downloader API is running successfully!"}

# 2. مسار استخراج بيانات الفيديو (متوافق تماماً مع كود بلوجر الخاص بك)
@app.get("/get-video")
def get_video(url: str = Query(..., description="The URL of the social media video")):
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL parameter")
    
    # إعدادات أداة yt-dlp لجلب أفضل جودة بدون تحميلها على السيرفر
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'allowed_extractors': ['.*'],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # استخراج الرابط المباشر الفعلي للتحميل
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

# 3. مسار الوسيط (Proxy) لإجبار المتصفح على تحميل الفيديو فوراً بدلاً من تشغيله في صفحة جديدة
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
        
        # تنظيف اسم الملف من أي رموز غريبة
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

# 4. إعداد ربط المنفذ (Port Binding) الديناميكي المفروض من منصة Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
