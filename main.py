from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# السماح لمدونتك على Blogger بالاتصال بالسيرفر بدون مشاكل حظر (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

@app.post("/get-video")
def get_video_links(data: VideoRequest):
    ydl_opts = {
        'format': 'best',  # جلب أفضل جودة متاحة مدمجة
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(data.url, download=False)
            
            # استخراج الروابط المباشرة والمعلومات الأساسية
            formats_data = []
            if 'formats' in info:
                for f in info['formats']:
                    # تصفية الروابط التي تحتوي على فيديو وصوت معاً لسهولة التحميل
                    if f.get('acodec') != 'none' and f.get('vcodec') != 'none':
                        formats_data.append({
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'resolution': f.get('resolution') or f.get('format_note'),
                            'url': f.get('url') # هذا هو الرابط المباشر
                        })

            return {
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "links": formats_data
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))