from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_admin_user
from ..database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def admin_users(db: Session = Depends(get_db), _: models.User = Depends(get_admin_user)):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.get("/items")
def admin_items(db: Session = Depends(get_db), _: models.User = Depends(get_admin_user)):
    return {
        "lost_items": db.query(models.LostItem).order_by(models.LostItem.created_at.desc()).all(),
        "found_items": db.query(models.FoundItem).order_by(models.FoundItem.created_at.desc()).all(),
    }


@router.delete("/item/{id}")
def admin_delete_item(
    id: int,
    item_type: str = Query(default="lost"),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_admin_user),
):
    item = db.query(models.LostItem if item_type == "lost" else models.FoundItem).filter_by(id=id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"detail": "Item deleted"}


@router.post("/item/{item_type}/{id}/verify")
def admin_verify_item(
    item_type: str,
    id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_admin_user),
):
    model = models.LostItem if item_type == "lost" else models.FoundItem
    item = db.query(model).filter_by(id=id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.is_verified = True
    db.commit()
    return {"detail": "Item verified"}


@router.post("/categories")
def admin_create_category(name: str = Form(...), db: Session = Depends(get_db), _: models.User = Depends(get_admin_user)):
    exists = db.query(models.Category).filter(models.Category.name == name.strip()).first()
    if exists:
        raise HTTPException(status_code=400, detail="Category already exists")
    category = models.Category(name=name.strip())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category

