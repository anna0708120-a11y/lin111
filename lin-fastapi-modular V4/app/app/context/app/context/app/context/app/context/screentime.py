from app import config, db

def get_screentime():
    if not config.ENABLE_SCREENTIME:
        return None
    cached = db.load_context("screentime")
    return cached["payload"] if cached else None
