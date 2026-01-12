"""
SAP Data Dashboard - Pydantic Schemas
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID


# Intake Form Schemas
class IntakeFormRequest(BaseModel):
    """Intake form submission from district website"""
    # District/School identifiers
    district_code: str = Field(..., min_length=1, max_length=50)
    school_code: str = Field(..., min_length=1, max_length=50)
    grade_level: str = Field(..., description="Grade level: K, 1, 2, ..., 12")
    referral_source: str = Field(..., description="parent, teacher, counselor, etc.")
    opt_in_type: str = Field(..., description="immediate_service or future_eligibility")
    
    # PHI - Student Information
    student_full_name: str = Field(..., min_length=1, max_length=255)
    student_id: Optional[str] = Field(None, max_length=100)
    date_of_birth: date
    
    # PHI - Parent/Guardian Contact
    parent_name: str = Field(..., min_length=1, max_length=255)
    parent_email: EmailStr
    parent_phone: str = Field(..., min_length=10, max_length=20)
    
    # Insurance Information
    has_insurance: bool
    insurance_company: Optional[str] = Field(None, max_length=255)
    policyholder_name: Optional[str] = Field(None, max_length=255)
    relationship_to_student: Optional[str] = Field(None, max_length=100)
    member_id: Optional[str] = Field(None, max_length=100)
    group_number: Optional[str] = Field(None, max_length=100)
    insurance_card_front: Optional[str] = Field(None, description="Base64 encoded image or URL")
    insurance_card_back: Optional[str] = Field(None, description="Base64 encoded image or URL")
    
    @validator('opt_in_type')
    def validate_opt_in_type(cls, v):
        if v not in ['immediate_service', 'future_eligibility']:
            raise ValueError('opt_in_type must be "immediate_service" or "future_eligibility"')
        return v


class IntakeFormResponse(BaseModel):
    """Response after intake form submission"""
    student_uuid: UUID
    message: str
    status: str


class IntakeStatusResponse(BaseModel):
    """Intake processing status (non-PHI)"""
    student_uuid: UUID
    status: str
    submitted_date: Optional[str]  # ISO 8601 datetime
    processed_date: Optional[str]  # ISO 8601 datetime


# Dashboard Schemas
class DashboardSummaryResponse(BaseModel):
    """Dashboard summary statistics"""
    total_opt_ins: int
    total_referrals: int
    active_students: int
    pending_intakes: int
    completed_sessions: int
    by_district: List[dict]
    by_school: List[dict]


class DashboardRecordResponse(BaseModel):
    """Dashboard record (non-PHI)"""
    student_uuid: UUID
    district_name: str
    school_name: str
    grade_band: Optional[str]
    referral_source: Optional[str]
    opt_in_type: str
    referral_date: date
    fiscal_period: Optional[str]
    insurance_present: bool
    service_status: str
    session_count: int
    outcome_collected: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DashboardRecordsListResponse(BaseModel):
    """Paginated list of dashboard records"""
    records: List[DashboardRecordResponse]
    pagination: dict


# Admin Schemas
class IntakeQueueListItem(BaseModel):
    """Intake queue list item (no PHI)"""
    id: int
    student_uuid: UUID
    district_name: str
    school_name: str
    created_at: datetime
    processed: bool
    has_insurance: bool
    
    class Config:
        from_attributes = True


class IntakeQueueDetailResponse(BaseModel):
    """Full intake queue record with decrypted PHI (VPM admin only)"""
    id: int
    student_uuid: UUID
    # Decrypted PHI
    student_full_name: str
    student_id: Optional[str]
    date_of_birth: date
    parent_name: str
    parent_email: str
    parent_phone: str
    insurance_company: Optional[str]
    policyholder_name: Optional[str]
    relationship_to_student: Optional[str]
    member_id: Optional[str]
    group_number: Optional[str]
    insurance_card_front_url: Optional[str]
    insurance_card_back_url: Optional[str]
    processed: bool
    simplepractice_record_id: Optional[str]
    created_at: datetime


class ProcessIntakeRequest(BaseModel):
    """Mark intake as processed"""
    simplepractice_record_id: str = Field(..., min_length=1, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)


class CreateSessionRequest(BaseModel):
    """Create session record"""
    student_uuid: UUID
    session_date: date
    session_type: str = Field(..., description="individual, group, or family")
    
    @validator('session_type')
    def validate_session_type(cls, v):
        if v not in ['individual', 'group', 'family']:
            raise ValueError('session_type must be "individual", "group", or "family"')
        return v


class CreateOutcomeRequest(BaseModel):
    """Create outcome record (aggregate only)"""
    student_uuid: UUID
    outcome_type: str = Field(..., max_length=100)
    outcome_value: str = Field(..., description="Aggregate data only, no PHI")
    measured_date: date

