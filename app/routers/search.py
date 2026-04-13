from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_
from sqlalchemy.orm import Session

from .. import models
from ..auth import get_optional_user
from ..database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/search")
def search_items(
    request: Request,
    q: str = Query(default=""),
    category: str = Query(default=""),
    location: str = Query(default=""),
    report_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=6, ge=1, le=24),
    db: Session = Depends(get_db),
):
    current_user = get_optional_user(request, db)
    if current_user and current_user.is_guest:
        return RedirectResponse(url="/dashboard?message=Guest+mode+cannot+access+search&msg_type=warning", status_code=303)

    lost_filters = []
    found_filters = []
    if q:
        lost_filters.append(models.LostItem.item_name.ilike(f"%{q}%"))
        found_filters.append(models.FoundItem.item_name.ilike(f"%{q}%"))
    if category:
        lost_filters.append(models.Category.name.ilike(f"%{category}%"))
        found_filters.append(models.Category.name.ilike(f"%{category}%"))
    if location:
        lost_filters.append(models.LostItem.location_lost.ilike(f"%{location}%"))
        found_filters.append(models.FoundItem.location_found.ilike(f"%{location}%"))
    if report_date:
        lost_filters.append(models.LostItem.date_lost == report_date)
        found_filters.append(models.FoundItem.date_found == report_date)

    lost_query = db.query(models.LostItem).join(models.Category)
    found_query = db.query(models.FoundItem).join(models.Category)
    if lost_filters:
        lost_query = lost_query.filter(and_(*lost_filters))
    if found_filters:
        found_query = found_query.filter(and_(*found_filters))

    lost_total = lost_query.count()
    found_total = found_query.count()
    total = lost_total + found_total
    pages = (total + size - 1) // size if total else 1

    lost_items = lost_query.order_by(models.LostItem.created_at.desc()).limit(size).all()
    found_items = found_query.order_by(models.FoundItem.created_at.desc()).offset(max(0, (page - 1) * size)).limit(size).all()

    return templates.TemplateResponse(
        request,
        "search.html",
        {
            "request": request,
            "current_user": current_user,
            "lost_items": lost_items,
            "found_items": found_items,
            "q": q,
            "category": category,
            "location": location,
            "report_date": report_date.isoformat() if report_date else "",
            "page": page,
            "pages": pages,
            "route": "/search",
            "message": request.query_params.get("message"),
            "message_type": request.query_params.get("msg_type", "success"),
        },
    )

