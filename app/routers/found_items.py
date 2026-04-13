from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_current_user, get_optional_user, save_upload_file
from ..database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/report-found")
def report_found_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_optional_user(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    if current_user.is_guest:
        return RedirectResponse(url="/dashboard?message=Guest+mode+cannot+create+reports&msg_type=warning", status_code=303)
    categories = db.query(models.Category).order_by(models.Category.name.asc()).all()
    return templates.TemplateResponse(
        request,
        "report_found.html",
        {
            "request": request,
            "categories": categories,
            "current_user": current_user,
            "message": request.query_params.get("message"),
            "message_type": request.query_params.get("msg_type", "success"),
        },
    )


@router.post("/found-item")
async def create_found_item(
    request: Request,
    item_name: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    date_found: date = Form(...),
    location_found: str = Form(...),
    finder_contact: str = Form(...),
    image_upload: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.is_guest:
        return RedirectResponse(url="/dashboard?message=Guest+mode+cannot+create+reports&msg_type=warning", status_code=303)
    image_path = None
    if image_upload and image_upload.filename:
        file_bytes = await image_upload.read()
        image_path = save_upload_file("app/uploads", image_upload.filename, file_bytes)
    item = models.FoundItem(
        item_name=item_name.strip(),
        description=description.strip(),
        category_id=category_id,
        date_found=date_found,
        location_found=location_found.strip(),
        finder_contact=finder_contact.strip(),
        image_path=image_path,
        user_id=current_user.id,
    )
    db.add(item)
    db.add(models.Notification(user_id=current_user.id, message=f"Found item report submitted: {item_name.strip()}"))
    db.commit()
    return RedirectResponse(url="/my-reports?message=Found+report+created&msg_type=success", status_code=303)


@router.get("/found-item/{item_id}/edit")
def edit_found_item_page(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.is_guest:
        return RedirectResponse(url="/dashboard?message=Guest+mode+cannot+edit+reports&msg_type=warning", status_code=303)
    item = db.query(models.FoundItem).filter(models.FoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Found item not found")
    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can edit only your own reports")
    categories = db.query(models.Category).order_by(models.Category.name.asc()).all()
    return templates.TemplateResponse(
        request,
        "report_found.html",
        {
            "request": request,
            "current_user": current_user,
            "categories": categories,
            "report": item,
            "form_title": "Edit Found Item",
            "submit_label": "Update Found Report",
            "form_action": f"/found-item/{item_id}/edit",
            "message": request.query_params.get("message"),
            "message_type": request.query_params.get("msg_type", "success"),
        },
    )


@router.post("/found-item/{item_id}/edit")
async def edit_found_item(
    item_id: int,
    request: Request,
    item_name: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    date_found: date = Form(...),
    location_found: str = Form(...),
    finder_contact: str = Form(...),
    image_upload: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.is_guest:
        return RedirectResponse(url="/dashboard?message=Guest+mode+cannot+edit+reports&msg_type=warning", status_code=303)
    item = db.query(models.FoundItem).filter(models.FoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Found item not found")
    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can edit only your own reports")

    item.item_name = item_name.strip()
    item.description = description.strip()
    item.category_id = category_id
    item.date_found = date_found
    item.location_found = location_found.strip()
    item.finder_contact = finder_contact.strip()

    if image_upload and image_upload.filename:
        file_bytes = await image_upload.read()
        item.image_path = save_upload_file("app/uploads", image_upload.filename, file_bytes)

    db.add(models.Notification(user_id=current_user.id, message=f"Found item report updated: {item.item_name}"))
    db.commit()
    return RedirectResponse(url="/my-reports?message=Found+report+updated&msg_type=success", status_code=303)


@router.post("/found-item/{item_id}/delete")
def delete_found_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if current_user.is_guest:
        return RedirectResponse(url="/dashboard?message=Guest+mode+cannot+delete+reports&msg_type=warning", status_code=303)
    item = db.query(models.FoundItem).filter(models.FoundItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Found item not found")
    if item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can delete only your own reports")
    db.delete(item)
    db.add(models.Notification(user_id=current_user.id, message=f"Found item report deleted: {item.item_name}"))
    db.commit()
    return RedirectResponse(url="/my-reports?message=Found+report+deleted&msg_type=success", status_code=303)


@router.get("/found-items")
def list_found_items(
    request: Request,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=6, ge=1, le=24),
    db: Session = Depends(get_db),
):
    current_user = get_optional_user(request, db)
    if current_user and current_user.is_guest:
        return RedirectResponse(url="/dashboard?message=Guest+mode+cannot+access+search&msg_type=warning", status_code=303)
    total = db.query(models.FoundItem).count()
    items = (
        db.query(models.FoundItem)
        .order_by(models.FoundItem.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    pages = (total + size - 1) // size if total else 1
    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "request": request,
            "current_user": current_user,
            "lost_items": [],
            "found_items": items,
            "q": "",
            "category": "",
            "location": "",
            "report_date": "",
            "page": page,
            "pages": pages,
            "route": "/found-items",
            "message": request.query_params.get("message"),
            "message_type": request.query_params.get("msg_type", "success"),
        },
    )

