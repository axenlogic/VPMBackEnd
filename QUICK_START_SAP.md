# SAP Data Dashboard - Quick Start Guide

**For Developers** - Quick reference to get started

---

## 📁 Project Structure

```
VPMBackEnd/
├── app/
│   ├── sap/                    # NEW: SAP Dashboard module
│   │   ├── __init__.py
│   │   ├── models.py          # Database models
│   │   ├── schemas.py         # API schemas
│   │   ├── utils.py           # Encryption, utilities
│   │   └── routes.py          # TODO: API endpoints
│   ├── auth/                  # Existing auth system
│   ├── db/                    # Database config
│   └── main.py                # FastAPI app
├── SAP_DASHBOARD_ARCHITECTURE.md  # Full architecture
├── FRONTEND_REQUIREMENTS.md       # Frontend specs
└── IMPLEMENTATION_SUMMARY.md      # Implementation plan
```

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# New dependency: cryptography (for PHI encryption)
```

### 2. Set Environment Variables
Add to `.env`:
```env
# Encryption key for PHI (generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your-encryption-key-here

# Retention period for intake queue (days)
INTAKE_RETENTION_DAYS=45
```

### 3. Database Migration
```bash
# Create migration (using Alembic - to be set up)
alembic revision --autogenerate -m "Initial SAP schema"
alembic upgrade head
```

### 4. Seed Initial Data
```python
# Create districts and schools
# Chesapeake and Norfolk districts
# Schools for each district
```

---

## 🔑 Key Concepts

### Dual-Record System
1. **Dashboard Record** (non-PHI, permanent)
   - Anonymous student UUID
   - District/school identifiers
   - Service status, session counts
   - Used for reporting

2. **Intake Queue Record** (PHI, temporary)
   - Encrypted student/parent information
   - Insurance details (encrypted)
   - Auto-deleted after 30-60 days
   - Only accessible to VPM admins

### User Roles
- **vpm_admin**: Full access, can view PHI
- **district_admin**: Read-only, district-scoped, no PHI
- **district_viewer**: Read-only, district-scoped, no PHI

---

## 📡 API Endpoints (To Implement)

### Public
- `POST /api/v1/intake/submit` - Submit intake form
- `GET /api/v1/intake/status/{uuid}` - Check status

### Admin (VPM Admin only)
- `GET /api/v1/admin/intake-queue` - List pending intakes
- `GET /api/v1/admin/intake-queue/{id}` - View PHI
- `POST /api/v1/admin/intake-queue/{id}/process` - Mark processed
- `POST /api/v1/admin/sessions` - Add session
- `POST /api/v1/admin/outcomes` - Add outcome

### Dashboard (Authenticated)
- `GET /api/v1/dashboard/summary` - Summary stats
- `GET /api/v1/dashboard/records` - List records
- `GET /api/v1/reports/district/{id}` - District report

---

## 🔒 Security Notes

1. **PHI Encryption**: All PHI fields encrypted using Fernet (AES-256)
2. **Access Control**: Role-based, district-scoped
3. **Audit Logging**: All PHI access logged
4. **Auto-Purge**: Background job deletes processed intakes after retention period

---

## 📝 Next Steps

1. **Create API routes** (`app/sap/routes.py`)
2. **Set up database migration** (Alembic)
3. **Implement encryption utilities** (enhance `app/sap/utils.py`)
4. **Create admin email notifications**
5. **Set up background purge job**

---

## 📚 Documentation

- **Full Architecture**: `SAP_DASHBOARD_ARCHITECTURE.md`
- **Frontend Specs**: `FRONTEND_REQUIREMENTS.md`
- **Implementation Plan**: `IMPLEMENTATION_SUMMARY.md`

---

## ⚠️ Critical Deadline

**January 5, 2025** - Intake form must be live before school districts return.

---

**Status**: Architecture Complete ✅  
**Ready for**: Implementation Phase 1

