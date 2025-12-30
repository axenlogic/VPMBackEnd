# Chat History Summary - MedicalCare Backend

This document summarizes key conversations, decisions, fixes, and configurations from the development of the MedicalCare Backend API.

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture Decisions](#architecture-decisions)
3. [Database Configuration](#database-configuration)
4. [Authentication System](#authentication-system)
5. [Deployment Setup](#deployment-setup)
6. [Local Development Fixes](#local-development-fixes)
7. [API Endpoints](#api-endpoints)
8. [Troubleshooting Guide](#troubleshooting-guide)

---

## 🏗️ Project Overview

**Tech Stack:**
- FastAPI 0.109.0 (Python 3.11)
- PostgreSQL with SQLAlchemy ORM 2.0.25
- JWT Authentication (python-jose)
- Bcrypt password hashing
- SMTP email sending

**Purpose:** Production-ready authentication backend for MedicalCare application with signup, OTP verification, login, and password reset functionality.

---

## 🎯 Architecture Decisions

### 1. **Multi-Environment Database Support**
**Decision:** Support three deployment environments with dynamic database connection configuration.

**Implementation:**
- `local`: Standard PostgreSQL connection (for development)
- `cloud_run`: Cloud SQL via Unix socket (for Google Cloud Run)
- `proxy`: Cloud SQL via TCP proxy (for VPS with Cloud SQL Proxy)

**Location:** `app/db/database.py`

**Key Code:**
```python
ENV = os.getenv("ENVIRONMENT", "local")  # local, cloud_run, or proxy

if ENV == "cloud_run":
    # Unix socket connection
    DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{encoded_password}@/{DB_NAME}?host={DB_SOCKET_DIR}/{INSTANCE_CONN_NAME}"
elif ENV == "proxy":
    # TCP connection via Cloud SQL Proxy
    DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{encoded_password}@localhost:5432/{DB_NAME}"
else:
    # Local development
    DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
```

### 2. **Password URL Encoding**
**Decision:** URL-encode database passwords to handle special characters (e.g., `@`, `#`, `$`).

**Reason:** Special characters in passwords can break database connection strings.

**Implementation:**
```python
from urllib.parse import quote_plus
encoded_password = quote_plus(DB_PASS) if DB_PASS else ""
```

### 3. **Error Response Format**
**Decision:** Most authentication endpoints return `200 OK` with error messages in response body, not HTTP error codes.

**Reason:** Consistent response format for frontend handling. Protected routes still use proper HTTP status codes (401, 404).

**Example:**
```python
# Login endpoint returns 200 OK even for invalid credentials
if not user:
    return {"message": "Invalid credentials"}  # 200 OK, not 401
```

### 4. **Graceful Database Startup**
**Decision:** Don't crash service if database is unavailable during startup.

**Implementation:** Wrapped table creation in try-except block in `app/main.py`:
```python
@app.on_event("startup")
def on_startup() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"Startup DB init skipped: {exc}")
```

### 5. **CORS Configuration**
**Decision:** Support multiple frontend URLs via environment variables.

**Implementation:**
- `FRONTEND_URL`: Primary frontend URL
- `FRONTEND_URL_8081`: Secondary frontend URL
- Defaults to `localhost:8080` and `localhost:8000` for development

---

## 🗄️ Database Configuration

### Local Development Setup

**Issue:** Initial setup failed because:
1. Database user `app_user` didn't exist
2. Database `app_db` didn't exist
3. Tables weren't created

**Solution:**
1. **Default User:** Changed to use current system user for local development (macOS Homebrew PostgreSQL standard)
   ```python
   if ENV == "local":
       import getpass
       DB_USER = os.getenv("DB_USER", getpass.getuser())  # Uses 'qatesting' on macOS
   ```

2. **Database Creation:**
   ```bash
   createdb app_db
   # or
   psql -d postgres -c "CREATE DATABASE app_db;"
   ```

3. **Table Creation:**
   ```python
   from app.db.database import Base, engine
   Base.metadata.create_all(bind=engine)
   ```

### Environment Variables

**Required for Local:**
```env
ENVIRONMENT=local
DB_NAME=app_db
DB_USER=qatesting  # or your system username
DB_PASS=           # empty if no password
DB_HOST=localhost
DB_PORT=5432
```

**Required for Cloud Run:**
```env
ENVIRONMENT=cloud_run
INSTANCE_CONN_NAME=project:region:instance
DB_NAME=app_db
DB_USER=app_admin
DB_PASS=Dzjone05@  # URL-encoded automatically
```

**Required for VPS Proxy:**
```env
ENVIRONMENT=proxy
DB_NAME=app_db
DB_USER=app_admin
DB_PASS=Dzjone05@
```

### Connection Pooling
```python
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,    # Verify connections before use
    pool_size=5,           # Base connection pool size
    max_overflow=2,        # Additional connections allowed
)
```

---

## 🔐 Authentication System

### User Flow

1. **Signup** (`POST /auth/signup`)
   - Validates email format and password strength (min 8 chars, 1 uppercase, 1 digit)
   - Creates user with `is_verified=False`
   - Generates 6-digit OTP
   - Sends OTP email
   - Returns OTP in response if `DEBUG=True` (development only)

2. **Verify OTP** (`POST /auth/verify-otp`)
   - Validates OTP and expiry (10 minutes)
   - Sets `user.is_verified = True`
   - Deletes OTP record
   - Returns JWT token

3. **Login** (`POST /auth/login`)
   - Validates credentials
   - Checks if user is verified
   - Returns JWT token on success
   - Returns `{"message": "Invalid credentials"}` on failure (200 OK)

4. **Password Reset** (`POST /auth/forgot-password` → `POST /auth/reset-password`)
   - Generates UUID reset token
   - Sends email with reset link
   - Validates token and expiry (15 minutes)
   - Updates password and marks token as used

### JWT Configuration

**Settings:** `app/core/config.py`
```python
JWT_SECRET_KEY: str  # From environment
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRATION_MINUTES: int = 60
```

**Token Payload:**
```python
{
    "user_id": int,
    "email": str,
    "exp": datetime  # Expiration timestamp
}
```

### Password Security

- **Hashing:** Bcrypt with automatic salt generation
- **Limitation Handling:** Truncates passwords to 72 bytes (bcrypt limit)
- **Validation:** Minimum 8 characters, 1 uppercase letter, 1 digit

### Protected Routes

**Helper Function:** `get_user_from_token()` in `app/auth/routes.py`
- Extracts JWT from `Authorization: Bearer <token>` header
- Validates token and expiry
- Returns user or raises `HTTPException` (401/404)

**Protected Endpoints:**
- `GET /auth/user/profile` - Get user profile
- `PATCH /auth/user/profile` - Update user profile

---

## 🚀 Deployment Setup

### Google Cloud Run

**Dockerfile:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app /app/app
EXPOSE 8080
ENV PORT=8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

**Key Fix:** Use shell form for CMD to expand `$PORT` environment variable:
```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```

**Deployment Command:**
```bash
gcloud run deploy medicalcare-api \
  --source . \
  --region us-central1 \
  --service-account=medicalcare-api-sa@project.iam.gserviceaccount.com \
  --add-cloudsql-instances=project:region:instance \
  --set-env-vars=ENVIRONMENT=cloud_run \
  --set-env-vars=INSTANCE_CONN_NAME=project:region:instance \
  --set-env-vars=DB_NAME=app_db \
  --set-env-vars=DB_USER=app_admin \
  --set-env-vars=DB_PASS='Dzjone05@' \
  --set-env-vars=FRONTEND_URL=https://dashboard.vpmforschools.org \
  --no-allow-unauthenticated
```

**Service Account Permissions:**
- `roles/cloudsql.client`
- `roles/cloudsql.instanceUser`

### VPS Proxy Setup

**Environment:** `ENVIRONMENT=proxy`
- Application runs on VPS
- Cloud SQL Proxy runs as sidecar on `localhost:5432`
- Nginx proxies frontend requests to application

---

## 🛠️ Local Development Fixes

### Issue 1: 500 Internal Server Error on Login

**Problem:** Login endpoint returned 500 error due to:
1. Database user didn't exist
2. Database didn't exist
3. Tables weren't created

**Solution:**
1. Updated `app/db/database.py` to use system user for local:
   ```python
   if ENV == "local":
       import getpass
       DB_USER = os.getenv("DB_USER", getpass.getuser())
   ```

2. Created database:
   ```bash
   createdb app_db
   ```

3. Created tables:
   ```python
   from app.db.database import Base, engine
   Base.metadata.create_all(bind=engine)
   ```

4. Added error handling to login endpoint:
   ```python
   try:
       # ... login logic ...
   except Exception as e:
       if settings.DEBUG:
           return {"message": f"Internal server error: {str(e)}"}
       return {"message": "Internal server error. Please try again later."}
   ```

### Issue 2: Pydantic Validation Error

**Problem:** `ValidationError: Extra inputs are not permitted` for environment variables.

**Solution:** Added `extra = "ignore"` to Pydantic Settings config:
```python
class Config:
    env_file = ".env"
    case_sensitive = True
    extra = "ignore"  # Ignore extra environment variables
```

### Issue 3: Module Not Found

**Problem:** `ModuleNotFoundError: No module named 'psycopg'`

**Solution:** Reinstalled dependencies:
```bash
pip install psycopg[binary]
```

---

## 📡 API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint |
| GET | `/health` | Health check |
| POST | `/auth/signup` | Register new user |
| POST | `/auth/verify-otp` | Verify email OTP |
| POST | `/auth/login` | Login user |
| POST | `/auth/forgot-password` | Request password reset |
| POST | `/auth/reset-password` | Reset password with token |

### Protected Endpoints (JWT Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/user/profile` | Get user profile |
| PATCH | `/auth/user/profile` | Update user profile |

### Response Format

**Success:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "username": "user@example.com",
  "full_name": "John Doe"
}
```

**Error (200 OK with message):**
```json
{
  "message": "Invalid credentials"
}
```

**Protected Route Error (HTTP Status):**
- `401 Unauthorized` - Invalid or missing token
- `404 Not Found` - User not found

---

## 🔧 Troubleshooting Guide

### Database Connection Issues

**Error:** `role "app_user" does not exist`
- **Solution:** For local development, use system username or set `DB_USER` in `.env`

**Error:** `database "app_db" does not exist`
- **Solution:** Create database: `createdb app_db`

**Error:** `relation "users" does not exist`
- **Solution:** Create tables:
  ```python
  from app.db.database import Base, engine
  Base.metadata.create_all(bind=engine)
  ```

**Error:** `password authentication failed`
- **Solution:** Check `DB_PASS` in environment variables. Password is automatically URL-encoded.

### Cloud Run Deployment Issues

**Error:** `Invalid value for '--port': '$PORT' is not a valid integer`
- **Solution:** Use shell form in Dockerfile CMD:
  ```dockerfile
  CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
  ```

**Error:** `connection to server on socket "/cloudsql/..." failed: Connection refused`
- **Solution:** 
  1. Grant service account `roles/cloudsql.client` and `roles/cloudsql.instanceUser`
  2. Ensure `--add-cloudsql-instances` flag is set correctly

**Error:** `404 Not Found` for `/healthz`
- **Solution:** Changed endpoint to `/health` (Cloud Run may reserve `/healthz`)

### Local Development Issues

**Error:** `500 Internal Server Error` on all endpoints
- **Solution:** 
  1. Check PostgreSQL is running: `brew services list | grep postgresql`
  2. Verify database exists and tables are created
  3. Check environment variables in `.env` file

**Error:** `ModuleNotFoundError`
- **Solution:** Activate virtual environment and install dependencies:
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

### Email Sending Issues

**Error:** `Failed to send email`
- **Solution:**
  1. Check SMTP credentials in `.env`
  2. For Gmail, use App Password (not regular password)
  3. Email failures are logged but don't fail the request (graceful handling)

---

## 📝 Key Code Changes

### 1. Database Configuration (`app/db/database.py`)
- Added multi-environment support
- URL-encoding for passwords
- System user default for local development

### 2. Login Endpoint (`app/auth/routes.py`)
- Added try-except error handling
- Returns 200 OK with error messages
- Debug mode shows detailed errors

### 3. Configuration (`app/core/config.py`)
- Pydantic BaseSettings with `extra = "ignore"`
- Environment variable loading from `.env`

### 4. Main Application (`app/main.py`)
- Graceful database startup (doesn't crash if DB unavailable)
- CORS with multiple frontend URL support
- Health check endpoint

---

## 🎯 Best Practices Implemented

1. **Error Handling:** Graceful failures, informative error messages
2. **Security:** Password hashing, JWT tokens, email verification
3. **Environment Separation:** Clear separation between local, cloud, and proxy environments
4. **Database Resilience:** Connection pooling, pre-ping, graceful startup
5. **Development Experience:** Debug mode, OTP in responses for testing
6. **Production Ready:** Proper error handling, environment-based configuration

---

## 📚 Additional Notes

- **Password Requirements:** Minimum 8 characters, 1 uppercase, 1 digit
- **OTP Expiry:** 10 minutes
- **Reset Token Expiry:** 15 minutes
- **JWT Expiry:** 60 minutes (configurable)
- **Email Verification:** Required before login
- **CORS:** Configured for production frontend URL

---

## 🚦 Next Steps / Future Improvements

1. **Rate Limiting:** Add rate limiting to prevent brute force attacks
2. **Refresh Tokens:** Implement refresh token mechanism
3. **Logging:** Replace `print()` with proper logging module
4. **Database Migrations:** Use Alembic for migration management
5. **Testing:** Add unit tests and integration tests
6. **Monitoring:** Add health check dependencies (database connectivity)
7. **Secrets Management:** Use Google Secret Manager for production secrets

---

**Last Updated:** December 29, 2025
**Project:** MedicalCare Backend API
**Version:** 1.0.0

