import os
import json
import random
import shutil
import requests
from datetime import datetime
from openai import OpenAI

# 讀取設定檔
def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

config = load_config()

# Instagram API 設定
ACCESS_TOKEN = config["ACCESS_TOKEN"]
INSTAGRAM_BUSINESS_ID = config["INSTAGRAM_BUSINESS_ID"]
IMAGE_FOLDER = "/volume1/IG_Posts/pending/"
PUBLISHED_FOLDER = "/volume1/IG_Posts/published/"
LOG_FILE = "/volume1/IG_Posts/logs/post_log.txt"

# OpenAI 設定
OPENAI_API_KEY = config["OPENAI_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY)

def get_random_image():
    images = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith((".jpg", ".png"))]
    if not images:
        return None
    return random.choice(images)

def generate_caption(image_path):
    prompt = f"Analyze this image and generate a bilingual (Chinese & English) poetic or emotional caption with hashtags."
    response = client.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}],
        max_tokens=100
    )
    return response.choices[0].message["content"]

def post_to_instagram(image_path, caption):
    url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ID}/media"
    
    files = {"image_url": open(image_path, "rb")}
    data = {
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    
    response = requests.post(url, data=data, files=files)
    return response.json()

def log_message(message):
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now()} - {message}\n")

def main():
    image = get_random_image()
    if not image:
        log_message("No images found for posting.")
        return
    
    image_path = os.path.join(IMAGE_FOLDER, image)
    caption = generate_caption(image_path)
    
    result = post_to_instagram(image_path, caption)
    
    if "id" in result:
        shutil.move(image_path, os.path.join(PUBLISHED_FOLDER, image))
        log_message(f"Posted {image} successfully: {result['id']}")
    else:
        log_message(f"Failed to post {image}: {result}")

if __name__ == "__main__":
    main()
