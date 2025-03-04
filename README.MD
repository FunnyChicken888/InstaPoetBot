# 📸 InstaPoetBot - 自動化 IG 發文機器人

🚀 **InstaPoetBot** 是一個基於 **OpenAI + Cloudinary + Instagram API** 的自動化發文機器人，能夠每天自動上傳 **不同風格的圖片**，並透過 **GPT-4o 產生中英對照的 Instagram 貼文**！🔥

---
## **🌟 功能特色**
✅ **每天晚上 5 點 (17:00) 自動發文**  
✅ **從不同資料夾隨機挑選圖片**（詩意 / 幽默 / 勵志 / 行銷）  
✅ **將圖片上傳到 Cloudinary，並使用 GPT-4o 生成貼文內容**  
✅ **發佈到 Instagram 並將已發佈圖片移動到 `published` 資料夾**  
✅ **可透過 `Docker` 在 NAS 或伺服器上持續運行**  

---

## **📥 安裝方式**
### **🔹 1. 克隆專案**
```bash
git clone https://github.com/yourusername/InstaPoetBot.git
cd InstaPoetBot
```

### **🔹 2. 安裝 Python 依賴**
確保已安裝 **Python 3.9+**，然後安裝套件：
```bash
pip install -r requirements.txt
```

### **🔹 3. 設定 `config.json`**
在 `InstaPoetBot` 目錄內建立 **`config.json`**：
```json
{
    "ACCESS_TOKEN": "your_instagram_access_token",
    "INSTAGRAM_BUSINESS_ID": "your_instagram_business_id",
    "OPENAI_API_KEY": "your_openai_api_key",
    "CLOUDINARY_CLOUD_NAME": "your_cloudinary_cloud_name",
    "CLOUDINARY_API_KEY": "your_cloudinary_api_key",
    "CLOUDINARY_API_SECRET": "your_cloudinary_api_secret",
    "LOG_FILE": "image/post_log.txt",
    "PUBLISHED_FOLDER": "image/published",
    "IMAGE_FOLDERS": {
        "poetic": "image/poetic",
        "humor": "image/humor",
        "inspirational": "image/inspirational",
        "marketing": "image/marketing"
    }
}
```
📌 **請填入你的 Instagram API & Cloudinary API 金鑰！**

---

## **🚀 執行方式**
### **🔹 方法 1：直接運行**
```bash
python InstaPoetBot.py
```
📌 **程式會每天等到 `17:00` 自動發文一次！**

### **🔹 方法 2：使用 `Docker` 部署**
如果你想在 **NAS 或伺服器** 運行，可以使用 Docker：

#### **1️⃣ 建立 `Dockerfile`**
```dockerfile
FROM python:3.9
WORKDIR /app

# 複製並安裝依賴
COPY requirements.txt ./
RUN pip install -r requirements.txt

# 複製所有程式碼
COPY . .

CMD ["python", "InstaPoetBot.py"]
```

#### **2️⃣ 建置 Docker Image**
```bash
docker build -t ig_auto_post .
```

#### **3️⃣ 運行容器**
```bash
docker run -d --name insta_bot ig_auto_post
```
📌 **這樣 InstaPoetBot 會每天自動運行！**

---

## **📌 常見問題**
### **1️⃣ Instagram API Access Token 如何取得？**
你需要：
1. 建立 **Facebook 開發者帳號** 👉 [點這裡](https://developers.facebook.com/)
2. 建立 **應用程式** 並申請 **Instagram Graph API 權限**
3. 透過 **Graph API 測試工具** 取得 `ACCESS_TOKEN`

📌 **Instagram API 權限需要 `instagram_content_publish` 才能發佈貼文！**

---

### **2️⃣ Cloudinary 如何設定？**
1. **註冊 Cloudinary** 👉 [點這裡](https://cloudinary.com/)
2. **取得 API 金鑰**（`CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`）
3. **填入 `config.json`**

📌 **Cloudinary 用於存放圖片，IG 需要公開的 URL！**

---

### **3️⃣ 如何確認 InstaPoetBot 是否正常運行？**
你可以檢查 **發文日誌**：
```bash
cat image/post_log.txt
```
✅ **如果發文成功，會顯示：**
```
2025-02-14 17:00:00 - ✅ Posted image/poetic/image1.jpg successfully: 1234567890
```

---

## **👨‍💻 貢獻者**
🛠 **開發者：FunnyChicken**  
📧 **聯絡方式：funnychicken888@gmail.com**  
🌐 **GitHub Repo：[Your GitHub](https://github.com/yourusername/InstaPoetBot)**  

---
## **⭐ 如果這個專案對你有幫助，請記得點擊 `Star`！**
