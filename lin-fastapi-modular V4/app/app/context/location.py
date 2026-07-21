from app import config, db

def get_latest_location():
    if not config.ENABLE_LOCATION:
        return None
    cached = db.load_context("location")
    return cached["payload"] if cached else None
