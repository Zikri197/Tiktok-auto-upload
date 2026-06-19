# ============================================================
# UPLOAD KE TIKTOK (GITHUB ACTIONS) - TIKTOKAPI VERSION
# ============================================================
import os, time, random, requests, json
from pathlib import Path
from datetime import datetime
from TikTokApi import TikTokApi

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

def do_upload(video_path, caption):
    last_error = ""
    for attempt in range(1, MAX_RETRIES+1):
        try:
            api = TikTokApi.get_instance(custom_verifyFp="")
            api.upload_video(
                str(video_path),
                description=caption[:2200],
                session_id=SESSION_ID
            )
            return True, ""
        except Exception as e:
            last_error = str(e)
            print(f"   ❌ Attempt {attempt}: {last_error[:100]}")
            
            if "session" in last_error.lower() or "auth" in last_error.lower():
                return False, "SESSION_EXPIRED"
            
            if "429" in last_error.lower() or "rate limit" in last_error.lower():
                print(f"   ⏳ Rate limit, jeda {RATE_LIMIT_PAUSE//60} menit...")
                send_telegram("⚠️ Rate limit, jeda 30 menit.")
                time.sleep(RATE_LIMIT_PAUSE)
                continue
            
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
            break
    
    if i < len(to_upload):
        delay = random.randint(DELAY_MIN, DELAY_MAX)
        print(f"   ⏳ Jeda {delay//60}m...")
        time.sleep(delay)

print("\n✅ Selesai.")
send_telegram("✅ Sesi upload selesai.")
