import os
import json
import random
import shutil
import requests
import time
from datetime import datetime
import openai
import cloudinary
import cloudinary.uploader

def get_root_dir():
    # 取得目前磁碟機的根目錄
    return os.path.abspath(os.sep)
# 讀取設定檔
def load_config():
    try:
        print(get_root_dir()+"root/config.json")
        with open(get_root_dir()+"root/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Error: config.json not found!")
        exit(1)
    except json.JSONDecodeError:
        print("❌ Error: config.json format is incorrect!")
        exit(1)

config = load_config()

# 讀取 API 設定
ACCESS_TOKEN = config["ACCESS_TOKEN"]
INSTAGRAM_BUSINESS_ID = config["INSTAGRAM_BUSINESS_ID"]
LOG_FILE =  get_root_dir()+config["LOG_FILE"]
PUBLISHED_FOLDER =  get_root_dir()+config["PUBLISHED_FOLDER"]
IMAGE_FOLDERS =  config["IMAGE_FOLDERS"]

# Cloudinary 設定
cloudinary.config( 
  cloud_name = config["CLOUDINARY_CLOUD_NAME"],  
  api_key = config["CLOUDINARY_API_KEY"],  
  api_secret = config["CLOUDINARY_API_SECRET"]  
)

# OpenAI 設定
openai.api_key = config["OPENAI_API_KEY"]

# ✅ 從 `config.json` 設定的資料夾隨機選取一張圖片
def get_random_image():
    available_folders = {k: v for k, v in IMAGE_FOLDERS.items() if os.listdir(v)}
    
    if not available_folders:
        log_message("❌ 所有資料夾都沒有圖片，無法發文！")
        return None, None
    
    selected_category = random.choice(list(available_folders.keys()))
    folder_path = available_folders[selected_category]
    images = [f for f in os.listdir(folder_path) if f.endswith((".jpg", ".png"))]

    if not images:
        log_message(f"❌ {selected_category} 資料夾沒有可用圖片")
        return None, None

# ✅ 上傳圖片到 Cloudinary 並取得 URL
def upload_image_to_cloudinary(image_path):
    response = cloudinary.uploader.upload(image_path)
    return response.get("secure_url")

# ✅ GPT 生成 Instagram 貼文（中文在前，英文在後）
def generate_caption(image_url, category):
    prompt_templates = {
        "poetic": "請為這張圖片生成一段詩意的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。",
        "humor": "請為這張圖片生成一段幽默的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。",
        "inspirational": "請為這張圖片生成一段勵志的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。",
        "marketing": "請為這張圖片生成一段行銷文案的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。"
    }

    prompt = prompt_templates.get(category, "請為這張圖片生成 Instagram 貼文。")

    client = openai.OpenAI(api_key=config["OPENAI_API_KEY"])  

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI that generates Instagram captions in Chinese first, followed by English.請不要輸出多餘的通知文字，辨識到人臉也不要回應到字串內"},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ],
        max_tokens=200
    )

    return response.choices[0].message.content.strip()

# ✅ 發佈 Instagram 貼文
def post_to_instagram(image_url, caption):
    upload_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ID}/media"
    data = {
        "image_url": image_url,  
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    
    upload_response = requests.post(upload_url, data=data).json()
    
    if "id" not in upload_response:
        return {"error": "❌ 無法上傳到 Instagram", "details": upload_response}
    
    media_id = upload_response["id"]
    
    publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ID}/media_publish"
    publish_response = requests.post(publish_url, data={"creation_id": media_id, "access_token": ACCESS_TOKEN}).json()
    
    return publish_response

# ✅ 記錄日誌
def log_message(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - {message}\n")

# ✅ 等待到每天 17:00 再執行
def wait_until_5pm():
    while True:
        now = datetime.now()
        if now.hour == 17 and now.minute == 0:
            log_message("⏰ 到達 17:00，開始發文...")
            return
        time.sleep(30)  # 每 30 秒檢查一次時間

# ✅ 主流程
def main():
    while True:
        wait_until_5pm()  # 等待到 17:00 再發文
        
        image_path, category = get_random_image()
        image_path = os.path.normpath(image_path)
        if not image_path:
            log_message("❌ No images found for posting.")
            continue

        # 1️⃣ 上傳圖片到 Cloudinary
        image_url = upload_image_to_cloudinary(image_path)
        if not image_url:
            log_message("❌ 圖片上傳失敗")
            continue

        # 2️⃣ 使用 GPT 生成 Instagram 貼文
        caption = generate_caption(image_url, category)

        # 3️⃣ 發佈到 Instagram
        result = post_to_instagram(image_url, caption)

        if "id" in result:
            shutil.move(image_path, os.path.join(PUBLISHED_FOLDER, os.path.basename(image_path)))
            log_message(f"✅ Posted {image_path} successfully: {result['id']}")
        else:
            log_message(f"❌ Failed to post {image_path}: {result}")

        # 等待到明天 5 點
        log_message("🎉 發文完成，等待明天 17:00 再次發文...")
        time.sleep(82800)  # 等待 23 小時再執行wait_until_5pm（避免重複發文）

if __name__ == "__main__":
    main()
