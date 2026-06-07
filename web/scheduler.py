from collections import deque
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .config_manager import load_config
from .database import SessionLocal, PostHistory
from .poster import do_post

scheduler = AsyncIOScheduler(timezone="Asia/Taipei")
log_buffer: deque[str] = deque(maxlen=300)
_posting = False


def add_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    log_buffer.append(f"[{ts}] {msg}")


async def scheduled_job():
    global _posting
    if _posting:
        add_log("⚠️ 上一次發文仍在進行中，跳過本次排程")
        return

    cfg = load_config()
    wait_days = max(int(cfg.get("WAIT_DAYS", 1)), 1)

    db = SessionLocal()
    try:
        last = (
            db.query(PostHistory)
            .filter(PostHistory.status == "success")
            .order_by(PostHistory.created_at.desc())
            .first()
        )
        if last and (datetime.now() - last.created_at) < timedelta(days=wait_days):
            add_log(f"⏭️ 距離上次發文不足 {wait_days} 天，跳過")
            return
    finally:
        db.close()

    _posting = True
    add_log("⏰ 排程觸發，開始發文流程...")
    try:
        await do_post(log=add_log)
    finally:
        _posting = False


def get_next_run() -> str | None:
    job = scheduler.get_job("main_post")
    if job and job.next_run_time:
        return job.next_run_time.strftime("%Y-%m-%d %H:%M")
    return None


def update_schedule():
    cfg = load_config()
    post_time = cfg.get("POST_TIME", "17:00")
    hour, minute = post_time.split(":")

    if scheduler.get_job("main_post"):
        scheduler.remove_job("main_post")

    scheduler.add_job(
        scheduled_job,
        CronTrigger(hour=int(hour), minute=int(minute), timezone="Asia/Taipei"),
        id="main_post",
        replace_existing=True,
    )
    add_log(f"📅 排程已更新：每天 {post_time} 自動檢查並發文")


def start():
    update_schedule()
    if not scheduler.running:
        scheduler.start()
    add_log("🚀 InstaPoetBot 已啟動，排程器運行中")


def stop():
    if scheduler.running:
        scheduler.shutdown(wait=False)
