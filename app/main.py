from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.auth.routes import router as auth_router
from app.users.routes import router as users_router
from app.posts.routes import router as posts_router
from app.config import settings
import os

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Social Media API")

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(posts_router)

@app.get("/")
def root():
    return {"message": "Social Media API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}
