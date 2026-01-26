# External Student Verification API
Version: 1.0  
Date: Jan 2026  
Audience: External Integration Team  

This document describes how an external platform (e.g., `portal-district.com`)
can securely verify student data against VPM systems.

---

## 1) High-Level Flow (2 calls)
1. **Get an access token** (client credentials)  
2. **Call the verification API** with that token

This flow avoids sharing end-user passwords and supports short-lived tokens.

---

## 2) Authentication

### 2.1 Token Endpoint
**POST** `/api/v1/integration/token`

**Headers**
- `Content-Type: application/json`

**Request Body**
```json
{
  "client_id": "portal-district",
  "client_secret": "********"
}
```

**Success Response (200)**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Error Responses**
- `401 Unauthorized` → invalid client credentials  
- `429 Too Many Requests` → rate limit exceeded  

**Notes**
- Token expiry is 1 hour (configurable).
- Tokens must be sent in the `Authorization` header for all protected APIs.

---

## 3) Student Verification API

### 3.1 Endpoint
**POST** `/api/v1/integration/verify-student`

**Headers**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### 3.2 Request Body (camelCase)
```json
{
  "student": {
    "firstName": "John",
    "lastName": "Doe",
    "grade": "5",
    "school": "Butts Road Intermediate",
    "dateOfBirth": "2010-05-15",
    "studentId": "STU-12345"
  },
  "parent": {
    "fatherName": "Mark Doe",
    "emailAddress": "parent@example.com",
    "phone": "555-123-4567"
  },
  "school": {
    "schoolName": "Butts Road Intermediate",
    "districtName": "Chesapeake",
    "schoolId": "11",
    "districtId": "4"
  }
}
```

### 3.3 Success Response (200)
```json
{
  "verified": true,
  "matchLevel": "exact",
  "student": {
    "firstName": "John",
    "lastName": "Doe",
    "grade": "5",
    "school": "Butts Road Intermediate",
    "dateOfBirth": "2010-05-15",
    "studentId": "STU-12345"
  },
  "parent": {
    "fatherName": "Mark Doe",
    "emailAddress": "parent@example.com",
    "phone": "555-123-4567"
  },
  "school": {
    "schoolName": "Butts Road Intermediate",
    "districtName": "Chesapeake",
    "schoolId": "11",
    "districtId": "4"
  }
}
```

### 3.4 No-Match Response (200)
```json
{
  "verified": false,
  "matchLevel": "none",
  "reason": "No record found"
}
```

---

## 4) Matching Rules

The system attempts to match a student using:
- `firstName`, `lastName`
- `dateOfBirth`
- `studentId`
- `schoolId` OR `schoolName`
- `districtId` OR `districtName`

**Match Levels**
- `exact`: all keys match  
- `partial`: name + DOB match, but studentId or school mismatch  
- `none`: no match

---

## 5) Required Fields

**Student**
- `firstName` (required)
- `lastName` (required)
- `dateOfBirth` (required, `YYYY-MM-DD`)
- `studentId` (required)

**School**
- `districtId` OR `districtName` (required)
- `schoolId` OR `schoolName` (required)

**Parent**
- `emailAddress` (required)
- `phone` (required)

---

## 6) Validation Rules
- All dates must be `YYYY-MM-DD`
- All requests must be JSON (`Content-Type: application/json`)
- Missing required fields → `422 Unprocessable Entity`

---

## 7) Error Responses

**401 Unauthorized**
```json
{ "detail": "Invalid or expired token" }
```

**403 Forbidden**
```json
{ "detail": "Client does not have access to this district or school" }
```

**422 Validation Error**
```json
{ "detail": "Missing or invalid fields" }
```

**500 Internal Server Error**
```json
{ "detail": "Server error. Try again later." }
```

---

## 8) HIPAA / BAA Compliance Notes
- External access is allowed under Google Cloud with a signed BAA.
- All traffic must be HTTPS (TLS 1.2+).
- Tokens are short-lived and required for every request.
- API access is audited and rate-limited.
- Optional: IP allowlisting for additional security.

---

## 9) Example cURL

**Token**
```bash
curl -X POST https://api.example.com/api/v1/integration/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"portal-district","client_secret":"*****"}'
```

**Verify**
```bash
curl -X POST https://api.example.com/api/v1/integration/verify-student \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{ "student": { "firstName": "John", "lastName": "Doe", "grade": "5", "school": "Butts Road Intermediate", "dateOfBirth": "2010-05-15", "studentId": "STU-12345" }, "parent": { "fatherName": "Mark Doe", "emailAddress": "parent@example.com", "phone": "555-123-4567" }, "school": { "schoolName": "Butts Road Intermediate", "districtName": "Chesapeake", "schoolId": "11", "districtId": "4" } }'
```

---

## 10) Contact
For onboarding, credentials, or whitelisting, contact the VPM technical admin.

