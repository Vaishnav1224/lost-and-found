import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import create_access_token, get_optional_user, hash_password, verify_password
from ..database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/register")
def register_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "request": request,
            "current_user": get_optional_user(request, db),
            "message": request.query_params.get("message"),
            "message_type": request.query_params.get("msg_type", "success"),
        },
    )


@router.get("/register-guest")
def guest_register_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "register_guest.html",
        {
            "request": request,
            "current_user": get_optional_user(request, db),
            "message": request.query_params.get("message"),
            "message_type": request.query_params.get("msg_type", "success"),
        },
    )


@router.post("/register-guest")
def register_guest(request: Request, full_name: str = Form(...), db: Session = Depends(get_db)):
    clean_name = full_name.strip()
    if len(clean_name) < 2:
        return templates.TemplateResponse(
            request,
            "register_guest.html",
            {"request": request, "error": "Guest name must be at least 2 characters.", "current_user": get_optional_user(request, db)},
            status_code=400,
        )
    guest_email = f"guest_{uuid.uuid4().hex[:12]}@guest.local"
    user = models.User(
        full_name=clean_name,
        email=guest_email,
        hashed_password=hash_password(uuid.uuid4().hex),
        is_guest=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.email)
    response = RedirectResponse(url="/dashboard?message=Guest+mode+enabled&msg_type=success", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response


@router.post("/register")
def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        payload = schemas.UserCreate(full_name=full_name.strip(), email=email.strip().lower(), password=password)
    except ValidationError:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "request": request,
                "error": "Please enter a valid name, email, and password (minimum 6 characters).",
                "current_user": get_optional_user(request, db),
            },
            status_code=400,
        )
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"request": request, "error": "Email already exists.", "current_user": get_optional_user(request, db)},
            status_code=400,
        )
    user = models.User(full_name=payload.full_name, email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.email)
    response = RedirectResponse(url="/dashboard?message=Registration+successful&msg_type=success", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response


@router.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "current_user": get_optional_user(request, db),
            "message": request.query_params.get("message"),
            "message_type": request.query_params.get("msg_type", "success"),
        },
    )


@router.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "Invalid credentials.", "current_user": get_optional_user(request, db)},
            status_code=400,
        )
    token = create_access_token(user.email)
    response = RedirectResponse(url="/dashboard?message=Welcome+back&msg_type=success", status_code=303)
    response.set_cookie("access_token", token, httponly=True, samesite="lax")
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response

