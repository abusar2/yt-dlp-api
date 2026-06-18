import os
import json
import time
import subprocess
import yt_dlp
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# تفعيل الـ CORS لكي يستقبل السيرفر طلبات من موقع بلوجر الخاص بك
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# متغيرات لتخزين التوكن في الذاكرة (Cache) لمنع بطء السيرفر
cached_token = None
cached_visitor_data = None
last_token_time = 0
TOKEN_EXPIRY = 3600  # تجديد التوكن تلقائياً كل ساعة (3600 ثانية)

def get_live_po_token():
    """تشغيل أداة Node.js في الخلفية وجلب توكن جديد كلياً"""
    global cached_token, cached_visitor_data, last_token_time
    
    current_time = time.time()
    # إذا كان التوكن موجوداً ولم تنتهِ صلاحيته بعد، استخدمه فوراً
    if cached_token and cached_visitor_data and (current_time - last_token_time < TOKEN_EXPIRY):
        return cached_visitor_data, cached_token

    try:
        # استدعاء أداة Node.js التي قمنا بتثبيتها في الـ Dockerfile
        result = subprocess.run(
            ["youtube-po-token-generator"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # تحويل المخرجات النصية إلى كائن JSON في بايثون
        token_data = json.loads(result.stdout)
        
        cached_visitor_data = token_data.get("visitorData")
        cached_token = token_data.get("poToken")
        last_token_time = current_time
        
        print("🚀 [PoToken System] New Token Generated Successfully!")
        return cached_visitor_data, cached_token
        
    except Exception as e:
        print(f"❌ [PoToken Error] Failed to generate token via node: {e}")
        # في حال فشل التوليد، قم بإرجاع التوكن القديم كخطة بديلة (Fallback)
        if cached_token:
            return cached_visitor_data, cached_token
        raise Exception("Could not generate YouTube PO Token.")

@app.get("/get-video")
async def get_video(url: str = Query(..., description="Video URL to extract")):
    try:
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
        }

        # إذا كان الرابط يخص يوتيوب، قم بحقن الـ PO Token المولد تلقائياً
        if "youtube.com" in url or "youtu.be" in url:
            visitor_data, po_token = get_live_po_token()
            ydl_opts['extractor_args'] = {
                'youtube': {
                    'po_token': [f'web+{po_token}', visitor_data],
                }
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # معالجة الروابط المباشرة بذكاء ودعم الصيغ المختلفة
            formats = info.get('formats', [])
            download_url = info.get('url')
            
            if not download_url and formats:
                # البحث عن أفضل رابط مباشر يدعم الفيديو والصوت معاً
                suitable_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
                if suitable_formats:
                    download_url = suitable_formats[-1].get('url')
                else:
                    download_url = formats[-1].get('url')

            return {
                "title": info.get('title', 'Social Media Video'),
                "thumbnail": info.get('thumbnail', 'https://placehold.co/120x90/0f172a/fff?text=Success'),
                "url": download_url
            }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
