from fastapi import FastAPI

from backend.config import settings

app = FastAPI(title=settings.APP_NAME)


@app.get("/")
def root():
    return {
        "message": "Vote App local backend is running",
        "mode": settings.APP_MODE,
        "database": settings.DATABASE_URL,
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "mode": settings.APP_MODE}
