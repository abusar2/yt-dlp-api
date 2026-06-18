import os
import uvicorn
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp

app = FastAPI(title="Stable Video Downloader API")

# 1. تفعيل الـ CORS لمنع حظر مدونة بلوجر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "alive", "message": "Stable API is running perfectly without YouTube/Proxy!"}

# 2. مسار جلب الفيديو
@app.get("/get-video")
def get_video(url: str = Query(..., description="The URL of the video")):
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL parameter")
    
    # إعدادات قياسية وسريعة جداً للمنصات المدعومة
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'allowed_extractors': ['.*'],
        'nocheckcertificate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
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
        raise HTTPException(status_code=500, detail=f"Extraction Error: {str(e)}")

# 3. مسار التحميل المباشر القسري (الوسيط المستقر)
@app.get("/proxy-download")
async def proxy_download(url: str = Query(..., description="The direct video URL"), filename: str = "video"):
    try:
        # إضافة ترويسات تحاكي المتصفح لتجاوز حظر 403 الخاص بتيك توك ومنصات البث
        headers_waterfall = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://www.tiktok.com/"
        }

        async def video_streamer():
            # اتصال مباشر مع الترويسات الجديدة لتجاوز الفلترة
            async with httpx.AsyncClient(timeout=None, headers=headers_waterfall) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch video source, status: {response.status_code}")
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        yield chunk
        
        # تنظيف العنوان: الإبقاء فقط على الحروف الإنجليزية والأرقام والمسافات ASCII لمنع خطأ latin-1
        safe_filename = "".join([c for c in filename if c.isalnum() and c.isascii() or c == ' ']).strip()
        
        # إذا أصبح العنوان فارغاً (مثلاً كان يحتوي على عربية فقط)، نضع اسماً افتراضياً آمناً
        if not safe_filename:
            safe_filename = "video"

        headers = {
            "Content-Disposition": f'attachment; filename="{safe_filename}.mp4"',
            "Content-Type": "video/mp4"
        }
        return StreamingResponse(video_streamer(), media_type="video/mp4", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
