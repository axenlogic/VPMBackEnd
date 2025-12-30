from pydantic import BaseModel, EmailStr, Field, validator

class SignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(None, min_length=8)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if v is not None and 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str  # email address
    full_name: str

class ErrorResponse(BaseModel):
    message: str

class MessageResponse(BaseModel):
    message: str

class SignupResponse(BaseModel):
    message: str
    username: str  # email address
    full_name: str

class UserProfile(BaseModel):
    id: int
    full_name: str
    email: str
    is_verified: bool
    
    class Config:
        from_attributes = True

class UpdateProfileRequest(BaseModel):
    full_name: str = Field(None, min_length=2, max_length=100)