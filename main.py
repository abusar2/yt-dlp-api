import os
import uvicorn
import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp

app = FastAPI(title="Universal Video Downloader API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "alive", "message": "Radical TV-Spoofing API is running!"}

@app.get("/get-video")
def get_video(url: str = Query(..., description="The URL of the video")):
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL parameter")
    
    # الإعداد الجذري: التظاهر بأننا شاشة تلفزيون ذكية أو تطبيق iOS
    # هذا يمنع يوتيوب من طلب "تسجيل الدخول" أو فحص البوتات
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        'allowed_extractors': ['.*'],
        'nocheckcertificate': True,
        'geo_bypass': True,
        
        # الخدعة هنا: استخدام مشغلات التلفزيون والـ iOS المدمجة وتخطي فحص الويب المعتاد
        'extractor_args': {
            'youtube': {
                'player_client': ['tvembedded', 'ios'],
                'skip': ['webpage', 'authcheck']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (SmartHub; SMART-TV; Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) SmartTV Safari/537.36',
        }
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
        raise HTTPException(status_code=500, detail=f"Error extracting video: {str(e)}")

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
