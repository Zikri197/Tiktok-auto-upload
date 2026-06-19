# ============================================================
# UPLOAD KE TIKTOK - TANPA PLAYWRIGHT
# ============================================================
import os, time, random, requests, hashlib, json
from pathlib import Path
from datetime import datetime

# ============================================================
# KONFIGURASI
# ============================================================
SESSION_ID = os.environ.get("TIKTOK_SESSION_ID", "")
MAX_UPLOAD = 5
DELAY_MIN = 80 * 60
DELAY_MAX = 100 * 60
MAX_RETRIES = 3
RATE_LIMIT_PAUSE = 30 * 60

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

CLIP_DIR = Path("clips")
LOG_FILE = Path("upload_log.txt")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def send_telegram(msg):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
                timeout=10
            )
        except:
            pass

# ============================================================
# UPLOAD VIA TIKTOK API (REQUESTS ONLY)
# ============================================================
def do_upload(video_path, caption):
    session = requests.Session()
    session.cookies.set("sessionid", SESSION_ID, domain=".tiktok.com")
    session.headers.update({"User-Agent": USER_AGENT})
    
    last_error = ""
    for attempt in range(1, MAX_RETRIES+1):
        try:
            # Step 1: Dapatkan upload URL
            video_size = os.path.getsize(video_path)
            video_name = video_path.name
            
            init_url = "https://www.tiktok.com/api/v1/video/upload/auth/"
            init_resp = session.post(init_url, json={
                "video_size": video_size,
                "video_name": video_name,
                "source": "tiktok_web"
            })
            
            if init_resp.status_code != 200:
                last_error = f"Init failed: {init_resp.text[:100]}"
                if "session" in last_error.lower():
                    return False, "SESSION_EXPIRED"
                continue
            
            init_data = init_resp.json()
            upload_url = init_data.get("upload_url", "")
            
            if not upload_url:
                last_error = "No upload URL"
                continue
            
            # Step 2: Upload video
            with open(video_path, "rb") as f:
                upload_resp = session.put(upload_url, data=f, headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(video_size)
                })
            
            if upload_resp.status_code not in [200, 201, 204]:
                last_error = f"Upload failed: {upload_resp.text[:100]}"
                continue
            
            # Step 3: Finalize
            finalize_url = "https://www.tiktok.com/api/v1/video/upload/finalize/"
            finalize_resp = session.post(finalize_url, json={
                "video_name": video_name,
                "video_size": video_size,
                "description": caption[:2200],
                "privacy_type": "public"
            })
            
            if finalize_resp.status_code == 200:
                print("   ✅ Upload berhasil!")
                return True, ""
            else:
                last_error = f"Finalize failed: {finalize_resp.text[:100]}"
                
        except Exception as e:
            last_error = str(e)
            print(f"   ❌ Attempt {attempt}: {last_error[:100]}")
        
        if "429" in last_error or "rate limit" in last_error.lower():
            print(f"   ⏳ Rate limit, jeda {RATE_LIMIT_PAUSE//60} menit...")
            send_telegram("⚠️ Rate limit, jeda 30 menit.")
            time.sleep(RATE_LIMIT_PAUSE)
            continue
        
        if "session" in last_error.lower() or "auth" in last_error.lower():
            return False, "SESSION_EXPIRED"
        
        if attempt < MAX_RETRIES:
            time.sleep(10)
    
    return False, last_error

# ============================================================
# MAIN
# ============================================================
if not CLIP_DIR.exists():
    print("❌ Folder clips tidak ada.")
    send_telegram("❌ Upload gagal: folder clips tidak ditemukan.")
    exit()

videos = sorted(CLIP_DIR.glob("*.mp4"))
if not videos:
    print("✅ Tidak ada video baru.")
    send_telegram("✅ Tidak ada video baru hari ini.")
    exit()

uploaded = set()
if LOG_FILE.exists():
    with open(LOG_FILE) as f:
        uploaded = set(line.strip() for line in f)

remaining = [v for v in videos if v.name not in uploaded]
if not remaining:
    print("✅ Semua sudah diupload.")
    exit()

to_upload = remaining[:MAX_UPLOAD]
print(f"📤 Upload {len(to_upload)} video hari ini.")
send_telegram(f"🚀 Mulai upload {len(to_upload)} video.")

for i, video_path in enumerate(to_upload, 1):
    txt_path = video_path.with_suffix(".txt")
    caption = ""
    if txt_path.exists():
        with open(txt_path) as f:
            content = f.read()
            if "=== CAPTION ===" in content:
                caption = content.split("=== CAPTION ===")[1].strip().split("\n\n")[0]
            else:
                caption = content.strip()
    
    if not caption:
        caption = video_path.stem
    if "#" not in caption:
        caption += " #fyp #viral"
    
    print(f"\n📤 {i}/{len(to_upload)}: {video_path.name}")
    print(f"   {datetime.now().strftime('%H:%M:%S')}")
    
    ok, err = do_upload(video_path, caption)
    
    if ok:
        print("   ✅ Berhasil!")
        send_telegram(f"✅ {video_path.name}")
        with open(LOG_FILE, "a") as f:
            f.write(video_path.name + "\n")
    else:
        print(f"   ❌ Gagal: {err[:100]}")
        send_telegram(f"❌ {video_path.name}: {err[:200]}")
        
        if err == "SESSION_EXPIRED":
            print("⛔ Session expired.")
            send_telegram("⛔ Session expired, upload dihentikan.")
            break
    
    if i < len(to_upload):
        delay = random.randint(DELAY_MIN, DELAY_MAX)
        print(f"   ⏳ Jeda {delay//60}m {delay%60}s...")
        time.sleep(delay)

print("\n✅ Sesi upload selesai.")
send_telegram("✅ Sesi upload selesai.")
