# Ez-Task: Secure File-Sharing System

## Overview
A secure file-sharing system built with Django (no DRF, no Django admin) and MySQL, supporting two user types: Ops and Client. Features email verification, role-based access, secure file upload/download, and encrypted download links.

## Features
- **User Registration & Login** (email/password, with name and role)
- **Email Verification** (must verify before registering)
- **Role-based Access** (Ops: upload, Client: download/list)
- **File Upload** (Ops only, pptx/docx/xlsx)
- **File Listing** (Client only)
- **Secure Download Links** (encrypted, user-bound)
- **Environment Variables** for all secrets

## Setup

### 1. Clone the Repo
```bash
git clone <repo-url>
cd Ez-task
```

### 2. Create & Activate Virtual Environment
```bash
python3 -m venv ezenv
source ezenv/bin/activate
```

### 3. Install Requirements
```bash
pip install django mysqlclient python-dotenv cryptography
```

### 4. MySQL Setup
- Create a database (e.g. `ez`)
- Update `.env` with your DB credentials

### 5. Configure `.env`
```
SECRET_KEY=your-django-secret
DEBUG=True
DB_NAME=ez
DB_USER=youruser
DB_PASSWORD=yourpass
DB_HOST=localhost
DB_PORT=3306
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=yourgmail@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```
- **EMAIL_HOST_PASSWORD:** Must be a Gmail App Password (not your regular password)

### 6. Migrate
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Run Server
```bash
python manage.py runserver
```

## API Endpoints

### **User APIs**
- `POST /api/verify/` — Request/verify email code
- `POST /api/user_registration/` — Register (after verifying email)
- `POST /api/login_view/` — Login
- `GET /api/logout_view/` — Logout

### **File APIs**
- `POST /api/upload/` — Upload file (Ops only, form-data: file)
- `GET /api/list/` — List files (Client only)
- `GET /api/download-file/<file_id>/` — Get secure download link (Client only)
- `GET /api/secure-download/<token>/` — Download file (Client only)

## Example Requests

### Registration
```json
{
  "email": "user@example.com",
  "password": "Test@1234",
  "role": "Ops",
  "name": "User Name"
}
```

### Email Verification
```json
{
  "email": "user@example.com"
}
{
  "email": "user@example.com",
  "code": "1234"
}
```


## Deployment Notes
- Use Gunicorn + Nginx for production
- Set `DEBUG=False` and configure `ALLOWED_HOSTS`
- Store `.env` securely (never commit to git)
- Use HTTPS

## Testing
- Use Postman or curl for API testing
- Write Django `TestCase` classes for automated tests (recommended)

