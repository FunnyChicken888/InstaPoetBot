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
from PIL import Image
import piexif

def get_root_dir():
    return os.path.abspath(os.sep)

def load_config():
    try:
        with open(get_root_dir()+"root/config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Error: config.json not found!")
        exit(1)
    except json.JSONDecodeError:
        print("❌ Error: config.json format is incorrect!")
        exit(1)

config = load_config()

ACCESS_TOKEN = config["ACCESS_TOKEN"]
INSTAGRAM_BUSINESS_ID = config["INSTAGRAM_BUSINESS_ID"]
LOG_FILE = get_root_dir()+config["LOG_FILE"]
PUBLISHED_FOLDER = get_root_dir()+config["PUBLISHED_FOLDER"]
IMAGE_FOLDERS = config["IMAGE_FOLDERS"]

cloudinary.config(
    cloud_name=config["CLOUDINARY_CLOUD_NAME"],
    api_key=config["CLOUDINARY_API_KEY"],
    api_secret=config["CLOUDINARY_API_SECRET"]
)

openai.api_key = config["OPENAI_API_KEY"]

def get_random_image():
    selected_category = random.choice(list(IMAGE_FOLDERS.keys()))
    folder_path = get_root_dir()+IMAGE_FOLDERS[selected_category]
    images = [f for f in os.listdir(folder_path) if f.endswith((".jpg", ".png"))]

    if not images:
        return None, None

    selected_image = random.choice(images)
    return os.path.join(folder_path, selected_image), selected_category

def get_exif_info(image_path):
    try:
        img = Image.open(image_path)
        exif_dict = piexif.load(img.info.get("exif", b""))
        json_data = exif_dict["0th"].get(piexif.ImageIFD.ImageDescription, b"").decode("utf-8")
        metadata = json.loads(json_data)
        return metadata
    except Exception as e:
        print(f"EXIF 讀取失敗或不存在: {e}")
        return None

def upload_image_to_cloudinary(image_path):
    response = cloudinary.uploader.upload(image_path)
    return response.get("secure_url")

def generate_caption(image_url, category, metadata):
    prompt_templates = {
        "poetic": "請為這張圖片生成一段詩意的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。",
        "humor": "請為這張圖片生成一段幽默的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。",
        "inspirational": "請為這張圖片生成一段勵志的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。",
        "marketing": "請為這張圖片生成一段行銷文案的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。"
    }

    prompt = prompt_templates.get(category, "請為這張圖片生成 Instagram 貼文。")

    if metadata:
        prompt += f"\n\n圖片描述：{metadata.get('description', '')}\n圖片標籤：{metadata.get('tags', [])}"

    client = openai.OpenAI(api_key=config["OPENAI_API_KEY"])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI that generates Instagram captions in Chinese first, followed by English."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]}
        ],
        max_tokens=200
    )

    return response.choices[0].message.content.strip()

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

def log_message(message):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - {message}\n")

def wait_until_5pm():
    while True:
        now = datetime.now()
        if now.hour == 17 and now.minute == 0:
            log_message("⏰ 到達 17:00，開始發文...")
            return
        time.sleep(30)

def main():
    while True:
        wait_until_5pm()

        image_path, category = get_random_image()
        image_path = os.path.normpath(image_path)
        if not image_path:
            log_message("❌ No images found for posting.")
            continue

        metadata = get_exif_info(image_path)

        image_url = upload_image_to_cloudinary(image_path)
        if not image_url:
            log_message("❌ 圖片上傳失敗")
            continue

        caption = generate_caption(image_url, category, metadata)

        result = post_to_instagram(image_url, caption)

        if "id" in result:
            shutil.move(image_path, os.path.join(PUBLISHED_FOLDER, os.path.basename(image_path)))
            log_message(f"✅ Posted {image_path} successfully: {result['id']}")
        else:
            log_message(f"❌ Failed to post {image_path}: {result}")

        log_message("🎉 發文完成，等待明天 17:00 再次發文...")
        time.sleep(43200)

if __name__ == "__main__":
    main()