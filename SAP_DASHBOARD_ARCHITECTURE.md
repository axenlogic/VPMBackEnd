# SAP Data Dashboard - Technical Architecture & Implementation Plan

**Version:** 1.0  
**Date:** December 2025  
**Status:** Design Phase

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Database Architecture](#database-architecture)
3. [API Design](#api-design)
4. [Security & Compliance](#security--compliance)
5. [Data Flow](#data-flow)
6. [Implementation Phases](#implementation-phases)
7. [Frontend Requirements](#frontend-requirements)

---

## 🏗️ System Overview

### Architecture Principles

1. **Dual-Record System**: Strict separation between non-PHI dashboard data and temporary PHI intake queue
2. **HIPAA Compliance**: Encrypted storage, role-based access, audit logging
3. **Scalability**: Designed for 15 districts, 20-30 schools each, 18K+ active clients
4. **Zero PHI Exposure**: Dashboard never exposes protected health information

### Technology Stack

- **Backend**: FastAPI (Python 3.13)
- **Database**: PostgreSQL (Google Cloud SQL)
- **Authentication**: JWT with role-based access control
- **Encryption**: AES-256 for PHI at rest, TLS 1.3 in transit
- **Hosting**: Google Cloud Run (HIPAA-aligned)
- **Frontend**: React (separate repo)

---

## 🗄️ Database Architecture

### Schema Design

#### 1. Core Tables (Non-PHI Dashboard)

```sql
-- Districts
CREATE TABLE districts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50) UNIQUE,  -- District identifier code
    region VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Schools
CREATE TABLE schools (
    id SERIAL PRIMARY KEY,
    district_id INTEGER REFERENCES districts(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50),  -- School identifier code
    grade_bands TEXT[],  -- Array of grade bands: ['K-5', '6-8', '9-12']
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(district_id, code)
);

-- Dashboard Records (Non-PHI, Permanent)
CREATE TABLE dashboard_records (
    id SERIAL PRIMARY KEY,
    student_uuid UUID NOT NULL UNIQUE,  -- Anonymous identifier
    district_id INTEGER REFERENCES districts(id),
    school_id INTEGER REFERENCES schools(id),
    grade_band VARCHAR(20),  -- 'K-5', '6-8', '9-12', etc.
    referral_source VARCHAR(100),  -- 'parent', 'teacher', 'counselor', etc.
    opt_in_type VARCHAR(50) NOT NULL,  -- 'immediate_service', 'future_eligibility'
    referral_date DATE NOT NULL,
    fiscal_period VARCHAR(20),  -- 'FY2025-Q1', etc.
    insurance_present BOOLEAN DEFAULT FALSE,  -- Yes/No only, no details
    service_status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'active', 'completed', 'cancelled'
    session_count INTEGER DEFAULT 0,
    outcome_collected BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    INDEX idx_district_school (district_id, school_id),
    INDEX idx_referral_date (referral_date),
    INDEX idx_service_status (service_status)
);

-- Sessions (Manual entry by VPM admin)
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    dashboard_record_id INTEGER REFERENCES dashboard_records(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    session_type VARCHAR(50),  -- 'individual', 'group', 'family'
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_dashboard_record (dashboard_record_id),
    INDEX idx_session_date (session_date)
);

-- Outcomes (Aggregate only)
CREATE TABLE outcomes (
    id SERIAL PRIMARY KEY,
    dashboard_record_id INTEGER REFERENCES dashboard_records(id) ON DELETE CASCADE,
    outcome_type VARCHAR(100),  -- 'attendance_improvement', 'behavioral_improvement', etc.
    outcome_value TEXT,  -- Aggregate data only, no individual details
    measured_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_dashboard_record (dashboard_record_id)
);

-- Audit Log
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,  -- 'create', 'update', 'delete', 'view', 'export'
    resource_type VARCHAR(50),  -- 'dashboard_record', 'intake_queue', 'session'
    resource_id INTEGER,
    district_id INTEGER REFERENCES districts(id),
    ip_address INET,
    user_agent TEXT,
    details JSONB,  -- Additional context
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    INDEX idx_user_action (user_id, action),
    INDEX idx_created_at (created_at),
    INDEX idx_resource (resource_type, resource_id)
);
```

#### 2. PHI Tables (Temporary Intake Queue)

```sql
-- Intake Queue Records (PHI, Temporary - 30-60 day retention)
CREATE TABLE intake_queue (
    id SERIAL PRIMARY KEY,
    dashboard_record_id INTEGER REFERENCES dashboard_records(id) ON DELETE CASCADE,
    
    -- PHI Fields (Encrypted)
    student_full_name_encrypted BYTEA NOT NULL,
    student_id_encrypted BYTEA,
    date_of_birth_encrypted BYTEA,
    
    -- Parent/Guardian Contact (Encrypted)
    parent_name_encrypted BYTEA NOT NULL,
    parent_email_encrypted BYTEA NOT NULL,
    parent_phone_encrypted BYTEA NOT NULL,
    
    -- Insurance Information (Encrypted)
    insurance_company_encrypted BYTEA,
    policyholder_name_encrypted BYTEA,
    relationship_to_student_encrypted BYTEA,
    member_id_encrypted BYTEA,
    group_number_encrypted BYTEA,
    insurance_card_front_url TEXT,  -- Encrypted storage path
    insurance_card_back_url TEXT,    -- Encrypted storage path
    
    -- Processing Status
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    processed_by INTEGER REFERENCES users(id),
    simplepractice_record_id VARCHAR(100),  -- Reference to EHR
    
    -- Retention Management
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,  -- Auto-calculated: created_at + retention_days
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    INDEX idx_dashboard_record (dashboard_record_id),
    INDEX idx_processed (processed),
    INDEX idx_expires_at (expires_at),
    INDEX idx_created_at (created_at)
);

-- Encryption Keys Management (separate secure storage recommended)
-- Note: Use Google Cloud KMS or AWS KMS in production
```

#### 3. User & Access Control

```sql
-- Extend existing users table
ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'vpm_admin';
ALTER TABLE users ADD COLUMN district_id INTEGER REFERENCES districts(id);
ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;

-- User Roles:
-- 'vpm_admin' - Full access to all districts and PHI
-- 'district_admin' - Read-only access to assigned district (no PHI)
-- 'district_viewer' - Read-only access to assigned district (no PHI)

-- Permissions Matrix
CREATE TABLE user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    resource_type VARCHAR(50),  -- 'dashboard', 'intake_queue', 'reports'
    permission_type VARCHAR(50),  -- 'read', 'write', 'delete', 'export'
    district_id INTEGER REFERENCES districts(id),  -- NULL = all districts
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, resource_type, permission_type, district_id)
);
```

---

## 🔌 API Design

### Endpoint Structure

```
/api/v1/
├── /auth/              # Authentication (existing)
├── /intake/            # Intake form submission
├── /dashboard/         # Dashboard data retrieval
├── /admin/             # Admin operations
└── /reports/           # Reporting endpoints
```

### 1. Intake Form Endpoints

#### `POST /api/v1/intake/submit`
**Public endpoint** - Accepts intake form data from district websites

**Request:**
```json
{
  "district_code": "CHESAPEAKE",
  "school_code": "CHES_001",
  "grade_level": "9",
  "referral_source": "parent",
  "opt_in_type": "immediate_service",  // or "future_eligibility"
  
  // PHI (will be encrypted)
  "student_full_name": "John Doe",
  "student_id": "12345",
  "date_of_birth": "2010-05-15",
  
  "parent_name": "Jane Doe",
  "parent_email": "jane@example.com",
  "parent_phone": "+1234567890",
  
  "has_insurance": true,
  "insurance_company": "Blue Cross",
  "policyholder_name": "Jane Doe",
  "relationship_to_student": "mother",
  "member_id": "BC123456",
  "group_number": "GRP789",
  "insurance_card_front": "base64_encoded_image_or_url",
  "insurance_card_back": "base64_encoded_image_or_url"
}
```

**Response:**
```json
{
  "success": true,
  "student_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Intake form submitted successfully",
  "intake_id": 12345
}
```

**Process:**
1. Validate district/school codes
2. Generate anonymous student UUID
3. Create dashboard record (non-PHI)
4. Encrypt PHI fields
5. Create intake queue record (PHI)
6. Send admin notification email
7. Return success with student UUID

#### `GET /api/v1/intake/status/{student_uuid}`
**Public endpoint** - Check intake processing status (non-PHI only)

**Response:**
```json
{
  "student_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "service_status": "pending",
  "processed": false,
  "message": "Your intake form is being processed"
}
```

### 2. Dashboard Endpoints

#### `GET /api/v1/dashboard/summary`
**Protected** - District-scoped or all districts (based on role)

**Query Parameters:**
- `district_id` (optional, required for district users)
- `school_id` (optional)
- `fiscal_period` (optional)
- `start_date`, `end_date` (optional)

**Response:**
```json
{
  "total_opt_ins": 1250,
  "total_referrals": 890,
  "active_students": 450,
  "pending_intakes": 120,
  "completed_sessions": 2340,
  "by_district": [
    {
      "district_id": 1,
      "district_name": "Chesapeake",
      "opt_ins": 650,
      "referrals": 445,
      "active_students": 225
    }
  ],
  "by_school": [
    {
      "school_id": 1,
      "school_name": "Chesapeake High School",
      "opt_ins": 120,
      "referrals": 85,
      "active_students": 45
    }
  ]
}
```

#### `GET /api/v1/dashboard/records`
**Protected** - List dashboard records with filtering

**Query Parameters:**
- `district_id`, `school_id`
- `service_status`
- `referral_date_from`, `referral_date_to`
- `page`, `limit`

**Response:**
```json
{
  "records": [
    {
      "student_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "district_name": "Chesapeake",
      "school_name": "Chesapeake High School",
      "grade_band": "9-12",
      "referral_source": "parent",
      "opt_in_type": "immediate_service",
      "referral_date": "2025-01-15",
      "insurance_present": true,
      "service_status": "active",
      "session_count": 12,
      "outcome_collected": false
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1250,
    "pages": 25
  }
}
```

### 3. Admin Endpoints

#### `GET /api/v1/admin/intake-queue`
**Protected** - VPM Admin only, list pending intake queue records

**Response:**
```json
{
  "pending_intakes": [
    {
      "id": 12345,
      "student_uuid": "550e8400-e29b-41d4-a716-446655440000",
      "district_name": "Chesapeake",
      "school_name": "Chesapeake High School",
      "created_at": "2025-01-15T10:30:00Z",
      "processed": false,
      "has_insurance": true
      // No PHI exposed in list view
    }
  ]
}
```

#### `GET /api/v1/admin/intake-queue/{id}`
**Protected** - VPM Admin only, get full PHI for processing

**Response:**
```json
{
  "id": 12345,
  "student_uuid": "550e8400-e29b-41d4-a716-446655440000",
  // Decrypted PHI (only for VPM admins)
  "student_full_name": "John Doe",
  "student_id": "12345",
  "date_of_birth": "2010-05-15",
  "parent_name": "Jane Doe",
  "parent_email": "jane@example.com",
  "parent_phone": "+1234567890",
  "insurance_company": "Blue Cross",
  // ... all PHI fields decrypted
}
```

#### `POST /api/v1/admin/intake-queue/{id}/process`
**Protected** - VPM Admin only, mark intake as processed

**Request:**
```json
{
  "simplepractice_record_id": "SP-12345",
  "notes": "Entered into EHR on 2025-01-15"
}
```

#### `POST /api/v1/admin/sessions`
**Protected** - VPM Admin only, add session count

**Request:**
```json
{
  "student_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "session_date": "2025-01-15",
  "session_type": "individual"
}
```

#### `POST /api/v1/admin/outcomes`
**Protected** - VPM Admin only, add outcome data (aggregate only)

**Request:**
```json
{
  "student_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "outcome_type": "attendance_improvement",
  "outcome_value": "Improved attendance by 15%",
  "measured_date": "2025-01-15"
}
```

### 4. Reports Endpoints

#### `GET /api/v1/reports/district/{district_id}`
**Protected** - District-level aggregated reports

#### `GET /api/v1/reports/trends`
**Protected** - Monthly/quarterly trend analysis

#### `GET /api/v1/reports/export`
**Protected** - Export dashboard data (CSV/JSON, no PHI)

---

## 🔒 Security & Compliance

### Encryption Strategy

1. **PHI Encryption at Rest**
   - Use AES-256-GCM encryption
   - Store encryption keys in Google Cloud KMS
   - Encrypt each PHI field separately

2. **Encryption in Transit**
   - TLS 1.3 for all API communications
   - HTTPS only (no HTTP endpoints)

3. **Key Management**
   - Rotate encryption keys quarterly
   - Use separate keys per district (optional enhancement)

### Access Control

1. **Role-Based Access Control (RBAC)**
   ```python
   Roles:
   - vpm_admin: Full access, can view PHI
   - district_admin: Read-only, district-scoped, no PHI
   - district_viewer: Read-only, district-scoped, no PHI
   ```

2. **API Authorization**
   - JWT tokens with role claims
   - District-scoped queries for district users
   - PHI endpoints restricted to VPM admins only

3. **Data Filtering**
   - Automatic district filtering for district users
   - No PHI in dashboard endpoints
   - PHI only in admin/intake-queue endpoints

### Audit Logging

- Log all PHI access (who, when, what)
- Log all data modifications
- Log all exports
- Retain audit logs for 7 years (HIPAA requirement)

### Automated Purge

- Background job runs daily
- Deletes intake_queue records where:
  - `processed = true` AND `processed_at < NOW() - retention_days`
  - OR `expires_at < NOW()`
- Retention window: 30-60 days (configurable)

---

## 🔄 Data Flow

### Intake Form Submission Flow

```
1. Parent submits form on district website
   ↓
2. Form POSTs to /api/v1/intake/submit
   ↓
3. Backend validates district/school codes
   ↓
4. Generate anonymous student UUID
   ↓
5. Create dashboard_record (non-PHI)
   ↓
6. Encrypt all PHI fields
   ↓
7. Create intake_queue record (PHI, encrypted)
   ↓
8. Send email notification to VPM admin
   ↓
9. Return success with student_uuid
```

### Admin Processing Flow

```
1. VPM admin logs in
   ↓
2. Views /api/v1/admin/intake-queue (list, no PHI)
   ↓
3. Clicks on intake → GET /api/v1/admin/intake-queue/{id} (decrypted PHI)
   ↓
4. Enters data into SimplePractice EHR
   ↓
5. Marks as processed → POST /api/v1/admin/intake-queue/{id}/process
   ↓
6. System updates dashboard_record.service_status
   ↓
7. Intake queue record scheduled for deletion (30-60 days)
```

### Dashboard Query Flow

```
1. District user logs in
   ↓
2. Queries /api/v1/dashboard/summary?district_id=X
   ↓
3. Backend filters by district_id (automatic)
   ↓
4. Returns aggregated non-PHI data only
   ↓
5. Audit log records the query
```

---

## 📅 Implementation Phases

### Phase 1: MVP (Before Jan 5, 2025) - CRITICAL

**Priority: HIGHEST**

1. **Database Schema** (2 days)
   - Create all tables
   - Set up indexes
   - Migration scripts

2. **Intake Form API** (3 days)
   - POST /api/v1/intake/submit
   - Encryption utilities
   - Dual-record creation
   - Email notifications

3. **Admin Intake Queue** (2 days)
   - List pending intakes
   - View PHI (decrypted)
   - Mark as processed

4. **Basic Dashboard** (2 days)
   - Summary endpoint
   - District/school aggregation
   - Manual session entry

5. **Testing & Deployment** (1 day)
   - Integration testing
   - Security audit
   - Deploy to staging

**Total: 10 days**

### Phase 2: Enhanced Reporting (Weeks 2-4)

1. Advanced filtering and search
2. Trend analysis endpoints
3. Export functionality
4. Outcome tracking
5. Attendance correlation (aggregate)

### Phase 3: Advanced Features (Month 2+)

1. Automated session sync (if EHR API available)
2. Longitudinal comparisons
3. Behavioral trend indicators
4. Advanced analytics dashboard
5. Performance optimizations

---

## 🎨 Frontend Requirements

See `FRONTEND_REQUIREMENTS.md` for detailed frontend specifications.

---

## 📊 Performance Considerations

### Database Optimization

- Indexes on all foreign keys
- Composite indexes for common queries
- Partitioning dashboard_records by fiscal_period (future)
- Connection pooling (already configured)

### Caching Strategy

- Redis for frequently accessed dashboard summaries
- Cache TTL: 5 minutes for summaries
- Invalidate on data updates

### Scalability

- Designed for 15 districts × 30 schools = 450 schools
- 18,000 active clients
- Horizontal scaling via Cloud Run
- Database read replicas for reporting (future)

---

## 🧪 Testing Strategy

1. **Unit Tests**: All encryption/decryption functions
2. **Integration Tests**: API endpoints with test data
3. **Security Tests**: PHI access restrictions
4. **Performance Tests**: Load testing for 10K+ records
5. **Compliance Tests**: Audit log verification

---

## 📝 Next Steps

1. Review and approve architecture
2. Set up development environment
3. Create database migration scripts
4. Begin Phase 1 implementation
5. Daily standups for Jan 5 deadline

---

**Document Status**: Ready for Review  
**Next Review Date**: December 29, 2025 (Technical Architecture Meeting)

