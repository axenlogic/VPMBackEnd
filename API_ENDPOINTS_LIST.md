# VPM Backend API - Complete Endpoints List

**Base URL:** `http://localhost:8000` (development)  
**API Version:** 1.0.0  
**Last Updated:** January 2025

---

## 📋 Table of Contents

1. [Public Endpoints](#public-endpoints)
2. [Authentication Endpoints](#authentication-endpoints)
3. [Protected Endpoints](#protected-endpoints)
4. [Intake Form Endpoints](#intake-form-endpoints)
5. [Dashboard Endpoints](#dashboard-endpoints)

---

## 🌐 Public Endpoints

### Health Check
```
GET /
```
**Description:** Root endpoint - API status  
**Authentication:** None  
**Response:**
```json
{
  "message": "API running successfully"
}
```

### Health Check
```
GET /health
```
**Description:** Health check endpoint  
**Authentication:** None  
**Response:**
```json
{
  "status": "ok"
}
```

---

## 🔐 Authentication Endpoints

**Base Path:** `/auth`  
**Authentication:** Varies by endpoint (see below)

### 1. User Signup
```
POST /auth/signup
```
**Description:** Register a new user and send OTP for verification  
**Authentication:** None (Public)  
**Request Body:**
```json
{
  "full_name": "John Doe",
  "email": "user@example.com",
  "password": "SecurePass123"
}
```
**Response:**
```json
{
  "message": "OTP sent to your email for verification",
  "username": "user@example.com",
  "full_name": "John Doe",
  "otp": "123456"  // Only in DEBUG mode
}
```

### 2. Verify OTP
```
POST /auth/verify-otp
```
**Description:** Verify email OTP and activate user account  
**Authentication:** None (Public)  
**Request Body:**
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "username": "user@example.com",
  "full_name": "John Doe"
}
```

### 3. Login
```
POST /auth/login
```
**Description:** Login user and return JWT token  
**Authentication:** None (Public)  
**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "username": "user@example.com",
  "full_name": "John Doe"
}
```

### 4. Resend OTP
```
POST /auth/resend-otp
```
**Description:** Resend OTP to user's email  
**Authentication:** None (Public)  
**Request Body:**
```json
{
  "email": "user@example.com"
}
```
**Response:**
```json
{
  "message": "OTP sent to your email for verification",
  "username": "user@example.com",
  "full_name": "John Doe",
  "otp": "123456"  // Only in DEBUG mode
}
```

### 5. Forgot Password
```
POST /auth/forgot-password
```
**Description:** Send password reset link to user's email  
**Authentication:** None (Public)  
**Request Body:**
```json
{
  "email": "user@example.com"
}
```
**Response:**
```json
{
  "message": "Password reset link sent to your email"
}
```

### 6. Reset Password
```
POST /auth/reset-password
```
**Description:** Reset password using reset token  
**Authentication:** None (Public)  
**Request Body:**
```json
{
  "email": "user@example.com",
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass123"
}
```
**Response:**
```json
{
  "message": "Password reset successfully. Please log in again."
}
```

### 7. Get User Profile
```
GET /auth/user/profile
```
**Description:** Get current user's profile  
**Authentication:** Required (JWT Bearer Token)  
**Headers:**
```
Authorization: Bearer <jwt_token>
```
**Response:**
```json
{
  "id": 1,
  "full_name": "John Doe",
  "email": "user@example.com",
  "is_verified": true,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### 8. Update User Profile
```
PATCH /auth/user/profile
```
**Description:** Update current user's profile  
**Authentication:** Required (JWT Bearer Token)  
**Headers:**
```
Authorization: Bearer <jwt_token>
```
**Request Body:**
```json
{
  "full_name": "John Updated"
}
```
**Response:**
```json
{
  "id": 1,
  "full_name": "John Updated",
  "email": "user@example.com",
  "is_verified": true,
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T11:00:00Z"
}
```

---

## 📝 Intake Form Endpoints

**Base Path:** `/api/v1/intake`  
**Authentication:** None (Public endpoints with security measures)

### 1. Submit Intake Form
```
POST /api/v1/intake/submit
```
**Description:** Submit student intake form (PUBLIC - No authentication required)  
**Authentication:** None (Public)  
**Content-Type:** `multipart/form-data`  
**Security:** Rate limiting, CAPTCHA validation, input validation

**Request Fields:**
- `student_information.first_name` (required)
- `student_information.last_name` (required)
- `student_information.full_name` (required)
- `student_information.grade` (required)
- `student_information.school` (required)
- `student_information.date_of_birth` (required, YYYY-MM-DD)
- `student_information.student_id` (required)
- `parent_guardian_contact.name` (required)
- `parent_guardian_contact.email` (required)
- `parent_guardian_contact.phone` (required)
- `service_request_type` (required: "start_now" | "opt_in_future")
- `insurance_information.has_insurance` (required: "true" | "false")
- `insurance_information.insurance_company` (required if has_insurance=true)
- `insurance_information.policyholder_name` (required if has_insurance=true)
- `insurance_information.member_id` (required if has_insurance=true)
- `insurance_information.insurance_card_front` (optional, File)
- `insurance_information.insurance_card_back` (optional, File)
- `service_needs.service_category[0]` (required, array)
- `service_needs.severity_of_concern` (required: "mild" | "moderate" | "severe")
- `service_needs.type_of_service_needed[0]` (required, array)
- `immediate_safety_concern` (required: "true" | "false")
- `authorization_consent` (required: "true")
- `captcha_token` (optional but recommended)

**Response:**
```json
{
  "student_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Intake form submitted successfully",
  "status": "pending"
}
```

### 2. Check Intake Status
```
GET /api/v1/intake/status/{student_uuid}
```
**Description:** Check intake form status using UUID (PUBLIC - No authentication required)  
**Authentication:** None (Public)  
**Path Parameters:**
- `student_uuid` (UUID format)

**Response:**
```json
{
  "student_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "submitted_date": "2025-01-15T10:30:00Z",
  "processed_date": null
}
```

**Status Values:**
- `"pending"` - Form submitted, awaiting processing
- `"processed"` - Form has been processed
- `"active"` - Student is active in system

---

## 📊 Dashboard Endpoints

**Base Path:** `/api/v1/dashboard`  
**Authentication:** Required (JWT Bearer Token)

### 1. Districts & Schools Overview
```
GET /api/v1/dashboard/districts-schools
```
**Description:** Get hierarchical view of districts, schools, and intake forms  
**Authentication:** Required (JWT Bearer Token)  
**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `page` (integer, default: 1) - Page number
- `limit` (integer, default: 50, max: 100) - Districts per page
- `district_id` (integer, optional) - Filter by district ID
- `school_id` (integer, optional) - Filter by school ID
- `status` (string, optional) - Filter forms: "pending", "processed", "active"
- `date_from` (string, optional) - Filter from date (YYYY-MM-DD)
- `date_to` (string, optional) - Filter to date (YYYY-MM-DD)
- `include_forms` (boolean, default: true) - Include intake forms
- `forms_limit` (integer, default: 50, max: 200) - Forms per school
- `sort_by` (string, default: "name") - Sort: "name", "total_students", "active_students", "total_schools"
- `sort_order` (string, default: "asc") - "asc" or "desc"

**Example Request:**
```
GET /api/v1/dashboard/districts-schools?page=1&limit=10&status=active&include_forms=true
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "districts": [
      {
        "id": "1",
        "name": "Springfield District",
        "total_schools": 12,
        "total_students": 2450,
        "active_students": 890,
        "schools": [
          {
            "id": "1-1",
            "name": "Springfield Elementary",
            "total_students": 450,
            "active_students": 180,
            "forms": [
              {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "student_name": "John Doe",
                "submitted_date": "2025-01-15T10:30:00Z",
                "status": "active",
                "student_uuid": "550e8400-e29b-41d4-a716-446655440000"
              }
            ]
          }
        ]
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 3,
      "total_districts": 25,
      "per_page": 10,
      "has_next": true,
      "has_previous": false
    },
    "summary": {
      "total_districts": 25,
      "total_schools": 180,
      "total_students": 12500,
      "total_active_students": 4500,
      "total_forms": 3200
    }
  }
}
```

---

## 📝 Summary

### Total Endpoints: 12

**Public Endpoints (No Auth):** 4
- `GET /` - Root
- `GET /health` - Health check
- `POST /api/v1/intake/submit` - Submit intake form
- `GET /api/v1/intake/status/{student_uuid}` - Check status

**Authentication Endpoints (Public):** 6
- `POST /auth/signup` - Signup
- `POST /auth/verify-otp` - Verify OTP
- `POST /auth/login` - Login
- `POST /auth/resend-otp` - Resend OTP
- `POST /auth/forgot-password` - Forgot password
- `POST /auth/reset-password` - Reset password

**Protected Endpoints (JWT Required):** 3
- `GET /auth/user/profile` - Get profile
- `PATCH /auth/user/profile` - Update profile
- `GET /api/v1/dashboard/districts-schools` - Districts & schools

---

## 🔗 API Documentation

### Interactive API Docs:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### OpenAPI Schema:
- **JSON Schema:** `http://localhost:8000/openapi.json`

---

## 🔐 Authentication

### JWT Token Usage:
1. **Get Token:** Login or verify OTP to receive `access_token`
2. **Use Token:** Include in request header:
   ```
   Authorization: Bearer <access_token>
   ```
3. **Token Expiry:** 60 minutes (configurable)

### Token Format:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## ⚠️ Important Notes

1. **Intake Form Endpoints are PUBLIC:**
   - No authentication required
   - Protected by rate limiting, CAPTCHA, validation
   - Handle PHI data (encrypted at rest)

2. **Dashboard Endpoints are PROTECTED:**
   - Require JWT authentication
   - Role-based access control (ready for implementation)
   - Returns PHI (student names) - decrypted for authorized users

3. **Rate Limiting:**
   - Intake submission: 5/hour per IP
   - Status check: 10/hour per IP
   - (Requires slowapi package)

4. **Error Responses:**
   - All errors follow consistent format:
   ```json
   {
     "detail": "Error message here"
   }
   ```

---

## 🧪 Testing Endpoints

### Using curl:

```bash
# Health check
curl http://localhost:8000/health

# Signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Test User","email":"test@example.com","password":"Test1234"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234"}'

# Get profile (with token)
curl http://localhost:8000/auth/user/profile \
  -H "Authorization: Bearer <your_token>"

# Submit intake form
curl -X POST http://localhost:8000/api/v1/intake/submit \
  -F "student_information.first_name=John" \
  -F "student_information.last_name=Doe" \
  # ... (all required fields)

# Get districts & schools
curl "http://localhost:8000/api/v1/dashboard/districts-schools?page=1&limit=10" \
  -H "Authorization: Bearer <your_token>"
```

---

**Status:** All endpoints are working and ready for use  
**Last Updated:** January 2025

