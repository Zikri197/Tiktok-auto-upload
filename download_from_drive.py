# ============================================================
# DOWNLOAD VIDEO DARI GOOGLE DRIVE
# ============================================================
import io, os
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# Config
SCOPES = ['https://www.googleapis.com/auth/drive']
#SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_FILE = 'gdrive_credentials.json'
QUEUE_FOLDER_NAME = 'upload_queue'
UPLOADED_FOLDER_NAME = 'uploaded'
DRIVE_FOLDER = 'YT_Clips'
LOCAL_CLIP_DIR = Path('clips')

# Auth Google Drive
creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
service = build('drive', 'v3', credentials=creds)

def get_folder_id(name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = service.files().list(q=query, fields='files(id,name)').execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None

def list_files(folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields='files(id,name,mimeType)'
    ).execute()
    return results.get('files', [])

def download_file(file_id, file_name, dest_folder):
    request = service.files().get_media(fileId=file_id)
    dest_folder.mkdir(parents=True, exist_ok=True)
    file_path = dest_folder / file_name
    with open(file_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
    return file_path

# Main
print("🔍 Mencari folder di Google Drive...")
root_id = get_folder_id(DRIVE_FOLDER)
if not root_id:
    print(f"❌ Folder '{DRIVE_FOLDER}' tidak ditemukan.")
    exit()

queue_id = get_folder_id(QUEUE_FOLDER_NAME, root_id)
if not queue_id:
    print(f"❌ Folder '{QUEUE_FOLDER_NAME}' tidak ditemukan.")
    exit()

uploaded_id = get_folder_id(UPLOADED_FOLDER_NAME, root_id)

files = list_files(queue_id)
videos = [f for f in files if f['name'].endswith('.mp4')]
txts = [f for f in files if f['name'].endswith('.txt')]

print(f"📥 Download {len(videos)} video + {len(txts)} caption...")

LOCAL_CLIP_DIR.mkdir(parents=True, exist_ok=True)

for f in videos + txts:
    print(f"   ⬇️ {f['name']}")
    download_file(f['id'], f['name'], LOCAL_CLIP_DIR)
    # Pindahkan ke folder uploaded
    if uploaded_id:
        service.files().update(
            fileId=f['id'],
            addParents=uploaded_id,
            removeParents=queue_id
        ).execute()

print("✅ Download selesai.")
