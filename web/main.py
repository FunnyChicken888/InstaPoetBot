import asyncio
import json
import os
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from werkzeug.utils import secure_filename

from .config_manager import load_config, save_config
from .database import PostHistory, SessionLocal, init_db
from .metadata_handler import read_metadata, write_metadata
from .poster import do_post, get_all_images
from . import scheduler as sched

STATIC_DIR = Path(__file__).parent / "static"
ALLOWED_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    sched.start()
    yield
    sched.stop()


app = FastAPI(title="InstaPoetBot", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Root ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


# ── Dashboard ───────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
async def get_dashboard():
    db = SessionLocal()
    try:
        total   = db.query(PostHistory).count()
        success = db.query(PostHistory).filter(PostHistory.status == "success").count()
        failed  = db.query(PostHistory).filter(PostHistory.status == "failed").count()
        recent  = (
            db.query(PostHistory)
            .order_by(PostHistory.created_at.desc())
            .limit(5).all()
        )
        return {
            "total_posts":       total,
            "success_posts":     success,
            "failed_posts":      failed,
            "scheduler_running": sched.scheduler.running,
            "next_run":          sched.get_next_run(),
            "logs":              list(sched.log_buffer)[-80:],
            "recent_posts": [
                {
                    "id":             p.id,
                    "created_at":     p.created_at.strftime("%Y-%m-%d %H:%M"),
                    "category":       p.category,
                    "image_filename": p.image_filename,
                    "status":         p.status,
                }
                for p in recent
            ],
        }
    finally:
        db.close()


@app.get("/api/logs/stream")
async def stream_logs():
    async def generator():
        last = 0
        while True:
            logs = list(sched.log_buffer)
            if len(logs) > last:
                for entry in logs[last:]:
                    yield f"data: {json.dumps({'log': entry})}\n\n"
                last = len(logs)
            await asyncio.sleep(1)

    return StreamingResponse(generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/post-now")
async def post_now(background_tasks: BackgroundTasks):
    async def run():
        sched.add_log("📢 手動觸發發文...")
        await do_post(log=sched.add_log)

    background_tasks.add_task(run)
    return {"message": "發文任務已啟動"}


# ── Config ──────────────────────────────────────────────────────────────────

@app.get("/api/config")
async def get_config():
    return load_config()


@app.post("/api/config")
async def update_config(config: dict):
    save_config(config)
    sched.update_schedule()
    return {"message": "設定已儲存"}


# ── Images ──────────────────────────────────────────────────────────────────

@app.get("/api/images")
async def list_images():
    cfg = load_config()
    images = get_all_images(cfg)
    for img in images:
        img["thumb_url"] = f"/api/images/file?path={img['path']}"
    return images


@app.get("/api/images/file")
async def serve_image(path: str = Query(...)):
    if not os.path.exists(path):
        raise HTTPException(404, "圖片不存在")
    if Path(path).suffix.lower() not in ALLOWED_EXTS:
        raise HTTPException(400, "不支援的檔案類型")
    return FileResponse(path)


@app.post("/api/images/upload")
async def upload_image(file: UploadFile = File(...), category: str = "poetic"):
    cfg = load_config()
    folder = cfg.get("IMAGE_FOLDERS", {}).get(category)
    if not folder:
        raise HTTPException(400, "無效的分類")
    os.makedirs(folder, exist_ok=True)
    safe_name = secure_filename(file.filename)
    dest = os.path.join(folder, safe_name)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"message": "上傳成功", "path": dest, "filename": safe_name}


@app.post("/api/images/metadata")
async def save_image_metadata(data: dict):
    path = data.get("path")
    metadata = data.get("metadata")
    if not path or metadata is None or not os.path.exists(path):
        raise HTTPException(400, "無效的請求")
    write_metadata(path, metadata)
    return {"message": "Metadata 已儲存"}


@app.delete("/api/images")
async def delete_image(data: dict):
    path = data.get("path")
    if not path or not os.path.exists(path):
        raise HTTPException(400, "檔案不存在")
    os.remove(path)
    return {"message": "已刪除"}


# ── History ─────────────────────────────────────────────────────────────────

@app.get("/api/history")
async def get_history(page: int = 1, limit: int = 20):
    db = SessionLocal()
    try:
        total = db.query(PostHistory).count()
        posts = (
            db.query(PostHistory)
            .order_by(PostHistory.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "page":  page,
            "posts": [
                {
                    "id":                 p.id,
                    "created_at":         p.created_at.strftime("%Y-%m-%d %H:%M"),
                    "category":           p.category,
                    "image_filename":     p.image_filename,
                    "image_url":          p.image_url,
                    "caption":            p.caption,
                    "instagram_post_id":  p.instagram_post_id,
                    "status":             p.status,
                    "error_message":      p.error_message,
                }
                for p in posts
            ],
        }
    finally:
        db.close()
