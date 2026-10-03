import os
import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Post, User
from app.posts.schemas import PostResponse, PostUpdate

router = APIRouter(prefix="/posts", tags=["posts"])

def save_image(file: UploadFile) -> str:
    if file.size > settings.MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large (max 5MB)")
    
    ext = file.filename.split(".")[-1]
    filename = f"{uuid4()}.{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return filepath

@router.post("/", response_model=PostResponse, status_code=201)
def create_post(
    title: str = Form(...),
    content: str = Form(...),
    image: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    image_path = save_image(image) if image else None
    
    post = Post(
        title=title,
        content=content,
        image_path=image_path,
        user_id=current_user.id
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    
    return {
        **post.__dict__,
        "image_url": f"/uploads/{os.path.basename(image_path)}" if image_path else None
    }

@router.get("/", response_model=list[PostResponse])
def get_posts(
    skip: int = 0,
    limit: int = 10,
    user_id: int | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Post)
    if user_id:
        query = query.filter(Post.user_id == user_id)
    
    posts = query.offset(skip).limit(limit).all()
    
    return [
        {
            **post.__dict__,
            "image_url": f"/uploads/{os.path.basename(post.image_path)}" if post.image_path else None
        }
        for post in posts
    ]

@router.get("/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        **post.__dict__,
        "image_url": f"/uploads/{os.path.basename(post.image_path)}" if post.image_path else None
    }

@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_update: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if post_update.title:
        post.title = post_update.title
    if post_update.content:
        post.content = post_update.content
    
    db.commit()
    db.refresh(post)
    
    return {
        **post.__dict__,
        "image_url": f"/uploads/{os.path.basename(post.image_path)}" if post.image_path else None
    }

@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if post.image_path and os.path.exists(post.image_path):
        os.remove(post.image_path)
    
    db.delete(post)
    db.commit()

@router.get("/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(user_id: int, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.user_id == user_id).offset(skip).limit(limit).all()
    
    return [
        {
            **post.__dict__,
            "image_url": f"/uploads/{os.path.basename(post.image_path)}" if post.image_path else None
        }
        for post in posts
    ]
