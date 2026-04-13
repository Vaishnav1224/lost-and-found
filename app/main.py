from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models
from .auth import get_optional_user, hash_password
from .database import SessionLocal, engine
from .routers import admin, auth_routes, found_items, lost_items, search

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Digital Lost and Found Management System")
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / "uploads")), name="uploads")

app.include_router(auth_routes.router)
app.include_router(lost_items.router)
app.include_router(found_items.router)
app.include_router(search.router)
app.include_router(admin.router)


def seed_categories():
    db: Session = SessionLocal()
    try:
        names = ["Electronics", "Documents", "Bags", "Clothing", "Accessories", "Other"]
        for name in names:
            if not db.query(models.Category).filter(models.Category.name == name).first():
                db.add(models.Category(name=name))
        admin_user = db.query(models.User).filter(models.User.email == "admin@lostfound.local").first()
        if not admin_user:
            db.add(
                models.User(
                    full_name="System Admin",
                    email="admin@lostfound.local",
                    hashed_password=hash_password("admin123"),
                    is_admin=True,
                )
            )
        elif not admin_user.hashed_password.startswith("pbkdf2_sha256$"):
            admin_user.hashed_password = hash_password("admin123")
        db.commit()
    finally:
        db.close()


def migrate_schema():
    with engine.begin() as conn:
        columns = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        column_names = {row[1] for row in columns}
        if "is_guest" not in column_names:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_guest BOOLEAN NOT NULL DEFAULT 0"))


@app.on_event("startup")
def startup_event():
    (BASE_DIR / "uploads").mkdir(parents=True, exist_ok=True)
    migrate_schema()
    seed_categories()


@app.get("/")
def home(request: Request):
    db = SessionLocal()
    try:
        current_user = get_optional_user(request, db)
        recent_lost = db.query(models.LostItem).order_by(models.LostItem.created_at.desc()).limit(6).all()
        recent_found = db.query(models.FoundItem).order_by(models.FoundItem.created_at.desc()).limit(6).all()
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "request": request,
                "current_user": current_user,
                "recent_lost": recent_lost,
                "recent_found": recent_found,
                "message": request.query_params.get("message"),
                "message_type": request.query_params.get("msg_type", "success"),
            },
        )
    finally:
        db.close()


@app.get("/dashboard")
def dashboard(request: Request):
    db = SessionLocal()
    try:
        current_user = get_optional_user(request, db)
        if not current_user:
            return RedirectResponse(url="/login", status_code=303)
        lost_total = db.query(models.LostItem).filter(models.LostItem.user_id == current_user.id).count()
        found_total = db.query(models.FoundItem).filter(models.FoundItem.user_id == current_user.id).count()
        recent_reports = (
            db.query(models.LostItem)
            .filter(models.LostItem.user_id == current_user.id)
            .order_by(models.LostItem.created_at.desc())
            .limit(3)
            .all()
        )
        recent_found = (
            db.query(models.FoundItem)
            .filter(models.FoundItem.user_id == current_user.id)
            .order_by(models.FoundItem.created_at.desc())
            .limit(3)
            .all()
        )
        notifications = (
            db.query(models.Notification)
            .filter(models.Notification.user_id == current_user.id)
            .order_by(models.Notification.created_at.desc())
            .limit(8)
            .all()
        )
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {
                "request": request,
                "current_user": current_user,
                "lost_total": lost_total,
                "found_total": found_total,
                "recent_reports": recent_reports,
                "recent_found": recent_found,
                "notifications": notifications,
                "message": request.query_params.get("message"),
                "message_type": request.query_params.get("msg_type", "success"),
            },
        )
    finally:
        db.close()


@app.get("/my-reports")
def my_reports(
    request: Request,
    report_type: str = Query(default="all"),
    status: str = Query(default="all"),
    q: str = Query(default=""),
):
    db = SessionLocal()
    try:
        current_user = get_optional_user(request, db)
        if not current_user:
            return RedirectResponse(url="/login", status_code=303)
        if current_user.is_guest:
            return RedirectResponse(url="/dashboard?message=Guest+mode+cannot+access+My+Reports&msg_type=warning", status_code=303)

        lost_query = db.query(models.LostItem).filter(models.LostItem.user_id == current_user.id)
        found_query = db.query(models.FoundItem).filter(models.FoundItem.user_id == current_user.id)

        clean_q = q.strip()
        if clean_q:
            lost_query = lost_query.filter(models.LostItem.item_name.ilike(f"%{clean_q}%"))
            found_query = found_query.filter(models.FoundItem.item_name.ilike(f"%{clean_q}%"))

        if status == "verified":
            lost_query = lost_query.filter(models.LostItem.is_verified.is_(True))
            found_query = found_query.filter(models.FoundItem.is_verified.is_(True))
        elif status == "pending":
            lost_query = lost_query.filter(models.LostItem.is_verified.is_(False))
            found_query = found_query.filter(models.FoundItem.is_verified.is_(False))

        lost_items = []
        found_items = []
        if report_type in {"all", "lost"}:
            lost_items = lost_query.order_by(models.LostItem.created_at.desc()).all()
        if report_type in {"all", "found"}:
            found_items = found_query.order_by(models.FoundItem.created_at.desc()).all()

        return templates.TemplateResponse(
            request,
            "my_reports.html",
            {
                "request": request,
                "current_user": current_user,
                "lost_items": lost_items,
                "found_items": found_items,
                "report_type": report_type,
                "status": status,
                "q": clean_q,
                "message": request.query_params.get("message"),
                "message_type": request.query_params.get("msg_type", "success"),
            },
        )
    finally:
        db.close()

