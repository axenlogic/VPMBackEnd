# Docker Setup Guide

## Why Docker is Required

### ✅ Production Deployment
- **Google Cloud Run requires Docker** - Your architecture specifies Cloud Run deployment
- Containerized deployment is standard for cloud platforms
- Ensures consistent environment across dev/staging/production

### ✅ Local Development Benefits
- **Easy PostgreSQL setup** - No need to install PostgreSQL locally
- **Consistent environment** - Same setup for all developers
- **One-command startup** - `docker compose up` runs everything
- **Isolated environment** - Doesn't pollute your local system

### ✅ Team Collaboration
- Everyone runs the same environment
- No "works on my machine" issues
- Easy onboarding for new developers

---

## Quick Start

### 1. Prerequisites
- Docker Desktop installed (Mac/Windows) or Docker Engine (Linux)
- Docker Compose v2 (included with Docker Desktop)

### 2. Create `.env` file (if not exists)
```bash
cp env.example .env
# Edit .env with your settings
```

### 3. Start Services
```bash
# Build and start all services
docker compose up --build

# Or run in background
docker compose up -d --build
```

### 4. Verify
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

### 5. Stop Services
```bash
docker compose down

# Remove volumes (deletes database data)
docker compose down -v
```

---

## Services

### PostgreSQL
- **Port**: 5432
- **Database**: `app_db` (or from `.env`)
- **User**: `postgres` (or from `.env`)
- **Password**: `postgres` (or from `.env`)
- **Data Persistence**: Named volume `postgres_data`

### Backend (FastAPI)
- **Port**: 8000
- **Auto-reload**: Enabled (for development)
- **Dependencies**: Waits for PostgreSQL to be healthy

---

## Environment Variables

Create `.env` file with:

```env
# Database
DB_NAME=app_db
DB_USER=postgres
DB_PASS=postgres

# JWT
JWT_SECRET_KEY=your-secret-key-here

# SMTP
SMTP_EMAIL=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Encryption (generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-encryption-key-here

# Debug
DEBUG=True
```

---

## Development Workflow

### With Docker Compose (Recommended)
```bash
# Start services
docker compose up

# View logs
docker compose logs -f backend
docker compose logs -f postgres

# Execute commands in container
docker compose exec backend python -m alembic upgrade head
docker compose exec backend python -c "from app.sap.models import *; print('Models loaded')"

# Access PostgreSQL
docker compose exec postgres psql -U postgres -d app_db
```

### Without Docker (Alternative)
If you prefer local development without Docker:
```bash
# Install PostgreSQL locally
brew install postgresql  # Mac
# or
sudo apt install postgresql  # Linux

# Start PostgreSQL
brew services start postgresql

# Create database
createdb app_db

# Run backend locally
source venv/bin/activate
uvicorn app.main:app --reload
```

---

## Production Deployment

### Google Cloud Run
```bash
# Build image
docker build -t gcr.io/PROJECT_ID/vpm-backend .

# Push to Google Container Registry
docker push gcr.io/PROJECT_ID/vpm-backend

# Deploy to Cloud Run
gcloud run deploy vpm-backend \
  --image gcr.io/PROJECT_ID/vpm-backend \
  --platform managed \
  --region us-central1 \
  --add-cloudsql-instances=PROJECT:REGION:INSTANCE \
  --set-env-vars ENVIRONMENT=cloud_run
```

---

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 5432 or 8000
lsof -i :5432
lsof -i :8000

# Stop conflicting services or change ports in docker-compose.yml
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker compose ps

# Check logs
docker compose logs postgres

# Test connection
docker compose exec postgres pg_isready -U postgres
```

### Rebuild Everything
```bash
# Stop and remove everything
docker compose down -v

# Rebuild from scratch
docker compose up --build
```

---

## File Structure

```
VPMBackEnd/
├── Dockerfile              # Backend container definition
├── docker-compose.yml      # Multi-container orchestration
├── .dockerignore          # Files to exclude from build
└── .env                   # Environment variables (not in git)
```

---

## Benefits Summary

✅ **Required for Cloud Run deployment**  
✅ **Simplifies local PostgreSQL setup**  
✅ **Consistent development environment**  
✅ **Easy team collaboration**  
✅ **One-command startup**  
✅ **Data persistence with volumes**  

---

**Recommendation**: Use Docker Compose for local development. It's the standard approach and required for production deployment anyway.

