import os
import random
import shutil
from datetime import datetime

import cloudinary
import cloudinary.uploader
import openai
import requests

from .config_manager import load_config
from .database import SessionLocal, PostHistory
from .metadata_handler import read_metadata

CATEGORY_PROMPTS = {
    "poetic":       "請為這張圖片生成一段詩意的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。PS:請不要回應辨識到人臉",
    "humor":        "請為這張圖片生成一段幽默的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。PS:請不要回應辨識到人臉",
    "inspirational":"請為這張圖片生成一段勵志的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。PS:請不要回應辨識到人臉",
    "marketing":    "請為這張圖片生成一段行銷文案的 Instagram 貼文，中英文對照（繁體中文在前，英文在後），並附上適當的標籤。PS:請不要回應辨識到人臉",
}


def get_all_images(cfg: dict) -> list[dict]:
    result = []
    for category, folder in cfg.get("IMAGE_FOLDERS", {}).items():
        if not os.path.isdir(folder):
            continue
        for fname in sorted(os.listdir(folder)):
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            fp = os.path.join(folder, fname)
            meta = read_metadata(fp)
            result.append({
                "path": fp,
                "filename": fname,
                "category": category,
                "has_metadata": meta is not None,
                "metadata": meta or {},
            })
    return result


def get_random_image(cfg: dict) -> tuple[str | None, str | None]:
    available = {}
    for category, folder in cfg.get("IMAGE_FOLDERS", {}).items():
        if not os.path.isdir(folder):
            continue
        imgs = [f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if imgs:
            available[category] = (folder, imgs)

    if not available:
        return None, None

    category = random.choice(list(available.keys()))
    folder, imgs = available[category]
    return os.path.join(folder, random.choice(imgs)), category


async def do_post(log=None, post_type: str = "feed"):
    def emit(msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")
        if log:
            log(msg)

    cfg = load_config()
    db = SessionLocal()
    record = PostHistory(status="failed", image_filename="", category="",
                         image_url="", caption="", instagram_post_id="")
    try:
        emit("📸 選取圖片中...")
        image_path, category = get_random_image(cfg)
        if not image_path:
            emit("❌ 所有資料夾都沒有圖片，無法發文！")
            db.add(record)
            db.commit()
            return False

        record.image_filename = os.path.basename(image_path)
        record.category = category
        emit(f"📸 選取：{os.path.basename(image_path)}（{category}）")

        metadata = read_metadata(image_path)
        emit(f"📜 Metadata：{metadata}" if metadata else "⚠️ 沒有 Metadata，繼續...")

        emit("☁️ 上傳圖片至 Cloudinary...")
        cloudinary.config(
            cloud_name=cfg["CLOUDINARY_CLOUD_NAME"],
            api_key=cfg["CLOUDINARY_API_KEY"],
            api_secret=cfg["CLOUDINARY_API_SECRET"],
        )
        resp = cloudinary.uploader.upload(image_path)
        image_url = resp["secure_url"]
        record.image_url = image_url
        emit("✅ Cloudinary 上傳完成")

        is_story = (post_type == "story")

        if not is_story:
            emit("🤖 GPT-4o 生成文案中...")
            prompt = CATEGORY_PROMPTS.get(category, "請為這張圖片生成 Instagram 貼文。")
            if metadata:
                prompt += f"\n\n圖片描述：{metadata.get('description', '')}\n圖片標籤：{metadata.get('tags', [])}"

            client = openai.OpenAI(api_key=cfg["OPENAI_API_KEY"])
            ai_resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "你是 Instagram 貼文寫手，中英文對照（繁體中文在前，英文在後）。請不要回應辨識到人臉。"},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ]},
                ],
                max_tokens=300,
            )
            caption = ai_resp.choices[0].message.content.strip()
            record.caption = caption
            emit("📝 文案生成完成")
        else:
            caption = ""
            emit("📖 動態模式，跳過文案生成")

        type_label = "動態（Story）" if is_story else "貼文（Feed）"
        emit(f"📱 發佈至 Instagram {type_label}...")

        media_data = {"image_url": image_url, "access_token": cfg["ACCESS_TOKEN"]}
        if is_story:
            media_data["media_type"] = "STORIES"
        else:
            media_data["caption"] = caption

        media_r = requests.post(
            f"https://graph.facebook.com/v18.0/{cfg['INSTAGRAM_BUSINESS_ID']}/media",
            data=media_data,
        ).json()

        if "id" not in media_r:
            raise RuntimeError(f"媒體建立失敗：{media_r}")

        pub_r = requests.post(
            f"https://graph.facebook.com/v18.0/{cfg['INSTAGRAM_BUSINESS_ID']}/media_publish",
            data={"creation_id": media_r["id"], "access_token": cfg["ACCESS_TOKEN"]},
        ).json()

        if "id" not in pub_r:
            raise RuntimeError(f"發佈失敗：{pub_r}")

        record.instagram_post_id = pub_r["id"]
        record.status = "success"

        pub_folder = cfg.get("PUBLISHED_FOLDER", "")
        if pub_folder and os.path.isdir(pub_folder):
            shutil.move(image_path, os.path.join(pub_folder, os.path.basename(image_path)))
            emit("📁 圖片已移至已發佈資料夾")

        db.add(record)
        db.commit()
        emit(f"✅ 發文成功！Post ID：{pub_r['id']}")
        return True

    except Exception as e:
        record.error_message = str(e)
        record.status = "failed"
        db.add(record)
        db.commit()
        emit(f"❌ 發文失敗：{e}")
        return False
    finally:
        db.close()
