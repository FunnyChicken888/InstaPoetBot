import os
import json
import random
import shutil
import requests
import time
from datetime import datetime, timedelta
import openai
import cloudinary
import cloudinary.uploader
from PIL import Image
import piexif

def get_root_dir():
    """Return the absolute path to the project root directory."""
    return os.path.dirname(os.path.abspath(__file__))

def load_config():
    try:
        config_path = os.path.join(get_root_dir(), "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
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
LOG_FILE = config["LOG_FILE"]
if not os.path.isabs(LOG_FILE):
    LOG_FILE = os.path.join(get_root_dir(), LOG_FILE)

PUBLISHED_FOLDER = config["PUBLISHED_FOLDER"]
if not os.path.isabs(PUBLISHED_FOLDER):
    PUBLISHED_FOLDER = os.path.join(get_root_dir(), PUBLISHED_FOLDER)

IMAGE_FOLDERS = config["IMAGE_FOLDERS"]

cloudinary.config(
    cloud_name=config["CLOUDINARY_CLOUD_NAME"],
    api_key=config["CLOUDINARY_API_KEY"],
    api_secret=config["CLOUDINARY_API_SECRET"]
)

openai.api_key = config["OPENAI_API_KEY"]

def get_random_image():
    available_folders = {}

    for category, relative_path in IMAGE_FOLDERS.items():
        if os.path.isabs(relative_path):
            folder_path = os.path.normpath(relative_path)
        else:
            folder_path = os.path.normpath(os.path.join(get_root_dir(), relative_path))

        images = [f for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if images:
            available_folders[category] = (folder_path, images)

    if not available_folders:
        log_message("❌ 所有資料夾都沒有圖片，無法發文！")
        return None, None

    selected_category = random.choice(list(available_folders.keys()))
    folder_path, images = available_folders[selected_category]
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
        "poetic": "請為這張圖片生成一段詩意的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。PS:請不要回應辨識到人臉",
        "humor": "請為這張圖片生成一段幽默的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。PS:請不要回應辨識到人臉",
        "inspirational": "請為這張圖片生成一段勵志的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。PS:請不要回應辨識到人臉",
        "marketing": "請為這張圖片生成一段行銷文案的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。PS:請不要回應辨識到人臉"
    }

    prompt = prompt_templates.get(category, "請為這張圖片生成 Instagram 貼文。")

    if metadata:
        prompt += f"\n\n圖片描述：{metadata.get('description', '')}\n圖片標籤：{metadata.get('tags', [])}"

    client = openai.OpenAI(api_key=config["OPENAI_API_KEY"])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。PS:請不要回應辨識到人臉"},
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

def wait_next_post(wait_days, post_time):
    wait_days = max(wait_days, 1)  # 強制至少等一天
    global config
    now = datetime.now()
    post_hour, post_minute = map(int, post_time.split(':'))
    next_post_time = now + timedelta(days=wait_days)
    next_post_time = next_post_time.replace(hour=post_hour, minute=post_minute, second=0, microsecond=0)
    log_message(f'下一次發文時間設定為 {next_post_time}')
    while True:
        config = load_config()
        now = datetime.now()
        
        if now >= next_post_time:
            log_message(f"⏰ 到達 {next_post_time}，開始發文...")

            return
        elif config["POST_NOW"] == "YES":

            log_message("📢 POST_NOW is YES, returning immediately.")
            config["POST_NOW"] = "NO"
            config_path = os.path.join(get_root_dir(), "config.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return

        # print(f'wait_next_post wait 30 sec config["POST_NOW"] = {config["POST_NOW"]}')
        time.sleep(30)

def main():
    while True:
        wait_next_post(config["WAIT_DAYS"], config["POST_TIME"])
        
        # 1️⃣ 選取圖片
        image_path, category = get_random_image()
        if image_path == None:
            log_message("❌ No images found for posting.")
            continue
        image_path = os.path.normpath(image_path)
   
        log_message(f"📸 選取的圖片: {image_path} (類別: {category})")

        # 2️⃣ 讀取 Metadata
        metadata = get_exif_info(image_path)
        log_message(f"📜 讀取到的 Metadata: {metadata}" if metadata else "⚠️ 該圖片沒有 Metadata")

        # 3️⃣ 上傳圖片到 Cloudinary
        image_url = upload_image_to_cloudinary(image_path)
        if not image_url:
            log_message("❌ 圖片上傳失敗")
            continue
        log_message(f"✅ 圖片已上傳至 Cloudinary: {image_url}")

        # 4️⃣ 產生 GPT 貼文內容
        try:
            caption = generate_caption(image_url, category, metadata)
            log_message(f"📝 GPT 生成的貼文內容:\n{caption}")
        except Exception as e:
            log_message(f"❌ GPT 生成貼文內容失敗: {e} 本日停更")
            continue
                        

        # 5️⃣ 發佈到 Instagram
        result = post_to_instagram(image_url, caption)

        if "id" in result:
            shutil.move(image_path, os.path.join(PUBLISHED_FOLDER, os.path.basename(image_path)))
            log_message(f"✅ Instagram 發文成功！圖片已移動至已發佈資料夾: {result['id']}")
        else:
            log_message(f"❌ Instagram 發文失敗: {result}")

        # 6️⃣ 休眠至明天
        time.sleep(43200)
        log_message("🎉 發文完成，等待明天 17:00 再次發文...")

   

if __name__ == "__main__":
    main()
