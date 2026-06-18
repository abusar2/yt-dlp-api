from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# 1. تفعيل الـ CORS للسماح لمدونتك على بلوجر بالاتصال بالسيرفر بدون حظر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # النجمة تعني السماح لجميع النطاقات، وهو المطلوب لموقعك
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

# لتجنب خطأ الـ 404 عند فتح الرابط المباشر للسيرفر
@app.get("/")
def read_root():
    return {"status": "API is running successfully!", "tool": "yt-dlp-api"}

# الدالة المشتركة لاستخراج الروابط باستخدام yt-dlp
def extract_video_info(url: str):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
        # إضافة إعدادات لتخطي حظر بعض المنصات كـ تيك توك وانستغرام
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # ترتيب البيانات لتطابق ما ينتظره كود الجافا سكريبت في بلوجر
            return {
                "title": info.get("title", "Social Media Video"),
                "url": info.get("url"),
                "thumbnail": info.get("thumbnail", "https://placehold.co/120x90/0f172a/fff?text=Success")
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# دعم طريقة الـ GET التقليدية
@app.get("/get-video")
def get_video(url: str = Query(..., description="The video URL from TikTok, FB, IG, or YT")):
    return extract_video_info(url)

# دعم طريقة الـ POST الاحتياطية
@app.post("/get-video")
def post_video(request: VideoRequest):
    return extract_video_info(request.url)
