# Digital Lost and Found Management System

FastAPI + SQLite web application for reporting and searching lost/found items with admin controls.

## Features
- User registration, login, logout with bcrypt + JWT cookie auth
- Lost and found item reporting with image uploads
- Search by item name, category, location, and date
- Dashboard with totals, recent reports, and notifications
- Admin APIs for users/items, delete fake reports, verify items, and manage categories
- Pagination and image preview before upload

## Project Structure
```text
lost_found_system/
  app/
    main.py
    database.py
    models.py
    schemas.py
    auth.py
    routers/
      auth_routes.py
      lost_items.py
      found_items.py
      search.py
      admin.py
    templates/
      base.html
      index.html
      login.html
      register.html
      dashboard.html
      report_lost.html
      report_found.html
      search.html
    static/
      css/style.css
      js/app.js
      images/
    uploads/
  requirements.txt
  README.md
```

## Setup
1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open `http://127.0.0.1:8000`.

### Default Admin
- Email: `admin@lostfound.local`
- Password: `admin123`

## API Endpoints
- `POST /register`
- `POST /login`
- `POST /lost-item`
- `GET /lost-items`
- `POST /found-item`
- `GET /found-items`
- `GET /search`
- `GET /admin/users`
- `GET /admin/items`
- `DELETE /admin/item/{id}`

## Security Notes
- Passwords are hashed with PBKDF2-SHA256.
- Auth uses JWT (HTTP-only cookie by default).
- SQLAlchemy ORM helps prevent SQL injection via parameterized queries.
- File uploads are validated for extension and size.

## Deploy on Render (Free Web Service)

This repository is now ready for Render deployment with `render.yaml` and `Procfile`.

### Option 1: Blueprint Deploy (recommended)
1. Push this project to GitHub.
2. In Render, click **New +** -> **Blueprint**.
3. Connect your repository and select this project.
4. Render will read `render.yaml` automatically.
5. Click **Apply** to create the web service.

### Option 2: Manual Web Service
1. In Render, click **New +** -> **Web Service**.
2. Connect your repository.
3. Use:
  - Build Command: `pip install -r requirements.txt`
  - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
  - `SECRET_KEY` = a long random secret value
  - `ACCESS_TOKEN_EXPIRE_MINUTES` = `480`
  - `DATABASE_URL` = `sqlite:///./lost_found.db` (free, non-persistent)

### Optional: Render Postgres (recommended for persistence)
1. Create a **PostgreSQL** service in Render.
2. Copy its **External Database URL**.
3. Set web service `DATABASE_URL` to that value.
4. Redeploy the web service.

No code changes are required: the app auto-detects SQLite vs Postgres, and also handles `postgres://` URL format automatically.

### Important Free-Tier Note
- SQLite and uploaded files are stored on the web service filesystem.
- On free web services, storage is ephemeral, so data may reset after restarts/redeploys.
- For persistent production data, use a managed database (for example Render Postgres) and object storage for uploads.

