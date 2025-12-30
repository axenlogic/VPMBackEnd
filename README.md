MedicalCare Backend - Authentication API
A complete, production-ready authentication backend built with FastAPI, PostgreSQL, JWT, and email verification (OTP) for the MedicalCare application.

Features
✅ User Signup with Email OTP Verification
✅ Login with JWT Authentication
✅ Forgot Password Flow with Email Reset Link
✅ Password Reset with Token Validation
✅ Protected Routes (JWT Required)
✅ CORS Enabled for Frontend Integration
✅ PostgreSQL Database with SQLAlchemy ORM (local, Cloud SQL, or proxy)
✅ Bcrypt Password Hashing
✅ Input Validation with Pydantic
✅ Multi-Environment Support (Local, Cloud Run, VPS Proxy)

Deployment Options
🚀 Local Development - Run with local PostgreSQL
☁️ Cloud Run - Fully managed on Google Cloud
🖥️ VPS Proxy - Deploy on your VPS with Cloud SQL

Quick Start
See `QUICK_START.md` for quick deployment commands.

Full Documentation
See `DEPLOYMENT_GUIDE.md` for complete setup instructions for all environments.

Project Structure
medicalCareBackend/
├── app/
│ ├── **init**.py
│ ├── main.py # FastAPI application entry point
│ ├── core/
│ │ └── config.py # Configuration and environment variables
│ ├── db/
│ │ └── database.py # Database setup with multi-env support
│ └── auth/
│ ├── models.py # SQLAlchemy database models
│ ├── schemas.py # Pydantic request/response schemas
│ ├── routes.py # Authentication endpoints
│ └── utils.py # Helper functions (JWT, email, hashing)
├── requirements.txt # Python dependencies
├── .env # Environment variables (create from .env.example)
├── Dockerfile # Container configuration for Cloud Run
├── QUICK_START.md # Quick reference for deployment
├── DEPLOYMENT_GUIDE.md # Complete deployment documentation
└── README.md # This file
Installation

1. Clone Repository and Setup Structure
   bash

# Clone the repository

git clone <your-repo-url> medicalCareBackend
cd medicalCareBackend

# Create the project structure

mkdir -p app/core app/db app/auth 2. Install Dependencies
bash
pip install -r requirements.txt 3. Configure Environment Variables
Copy .env.example to .env and update the values:

bash
cp .env.example .env
Important: Update these values in your .env file:

JWT_SECRET_KEY: Generate a secure random key
SMTP_EMAIL: Your email address
SMTP_PASSWORD: Your email app password (for Gmail, use App Password)
FRONTEND_URL: Your React app URL 4. Run the Application
bash

# From the medicalCareBackend directory

cd app
uvicorn main:app --reload
The API will be available at http://localhost:8000

API documentation at http://localhost:8000/docs

API Endpoints
Authentication Endpoints
Endpoint Method Description
/auth/signup POST Register user and send OTP
/auth/verify-otp POST Verify email OTP
/auth/login POST Login user
/auth/forgot-password POST Send password reset email
/auth/reset-password POST Reset password with token
/user/profile GET Get user profile (JWT required)
Example Requests

1. Signup
   bash
   POST /auth/signup
   Content-Type: application/json

{
"full_name": "John Doe",
"email": "john@example.com",
"password": "StrongPass123"
}
Response:

json
{
"message": "OTP sent to your email for verification"
} 2. Verify OTP
bash
POST /auth/verify-otp
Content-Type: application/json

{
"email": "john@example.com",
"otp": "123456"
}
Response:

json
{
"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
"token_type": "bearer"
} 3. Login
bash
POST /auth/login
Content-Type: application/json

{
"email": "john@example.com",
"password": "StrongPass123"
}
Response:

json
{
"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
"token_type": "bearer"
} 4. Forgot Password
bash
POST /auth/forgot-password
Content-Type: application/json

{
"email": "john@example.com"
}
Response:

json
{
"message": "Password reset link sent to your email"
} 5. Reset Password
bash
POST /auth/reset-password
Content-Type: application/json

{
"token": "550e8400-e29b-41d4-a716-446655440000",
"new_password": "NewStrongPass123",
"confirm_password": "NewStrongPass123"
}
Response:

json
{
"message": "Password reset successfully. Please log in again."
} 6. Get User Profile (Protected Route)
bash
GET /user/profile
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Response:

json
{
"id": 1,
"full_name": "John Doe",
"email": "john@example.com",
"is_verified": true
}
SMTP Configuration
Gmail Setup
Enable 2-Factor Authentication on your Google account
Generate an App Password:
Go to Google Account → Security → App Passwords
Select "Mail" and generate password
Use the generated password in .env as SMTP_PASSWORD
Other Email Providers
Update SMTP_SERVER and SMTP_PORT in .env:

Outlook: smtp.office365.com:587
Yahoo: smtp.mail.yahoo.com:587
Custom SMTP: Use your provider's settings
Security Features
✅ Bcrypt password hashing
✅ JWT with expiration (1 hour default)
✅ OTP expiry (10 minutes)
✅ Password reset token expiry (15 minutes)
✅ Email verification required before login
✅ Password strength validation
✅ CORS protection
Frontend Integration
Using Fetch API
javascript
// Signup
const response = await fetch('http://localhost:8000/auth/signup', {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({
full_name: 'John Doe',
email: 'john@example.com',
password: 'StrongPass123'
})
});

// Login
const loginResponse = await fetch('http://localhost:8000/auth/login', {
method: 'POST',
headers: { 'Content-Type': 'application/json' },
body: JSON.stringify({
email: 'john@example.com',
password: 'StrongPass123'
})
});

const { access_token } = await loginResponse.json();

// Get Profile (with JWT)
const profileResponse = await fetch('http://localhost:8000/user/profile', {
headers: { 'Authorization': `Bearer ${access_token}` }
});
Using Axios
javascript
import axios from 'axios';

const api = axios.create({
baseURL: 'http://localhost:8000'
});

// Set token after login
api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

// Make authenticate
