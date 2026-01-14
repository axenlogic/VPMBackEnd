"""
SAP Data Dashboard - Database Models

Dual-record system:
1. Dashboard Records (non-PHI, permanent)
2. Intake Queue Records (PHI, temporary, plain text)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class District(Base):
    """School districts"""
    __tablename__ = "districts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), unique=True, index=True)  # District identifier code
    region = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    schools = relationship("School", back_populates="district", cascade="all, delete-orphan")
    dashboard_records = relationship("DashboardRecord", back_populates="district")


class School(Base):
    """Schools within districts"""
    __tablename__ = "schools"
    
    id = Column(Integer, primary_key=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), index=True)  # School identifier code
    grade_bands = Column(ARRAY(String))  # ['K-5', '6-8', '9-12']
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    district = relationship("District", back_populates="schools")
    dashboard_records = relationship("DashboardRecord", back_populates="school")


class DashboardRecord(Base):
    """Non-PHI dashboard records (permanent)"""
    __tablename__ = "dashboard_records"
    
    id = Column(Integer, primary_key=True, index=True)
    student_uuid = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4, index=True)
    
    # District/School identifiers
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False, index=True)
    
    # Non-PHI data
    student_name = Column(String(200), nullable=True)  # Student name (stored for dashboard display) - nullable for backward compatibility
    grade_band = Column(String(20))  # 'K-5', '6-8', '9-12'
    referral_source = Column(String(100))  # 'parent', 'teacher', 'counselor'
    opt_in_type = Column(String(50), nullable=False)  # 'immediate_service', 'future_eligibility'
    referral_date = Column(Date, nullable=False, index=True)
    fiscal_period = Column(String(20))  # 'FY2025-Q1'
    
    # Service tracking
    insurance_present = Column(Boolean, default=False)  # Yes/No only
    service_status = Column(String(50), default='pending', index=True)  # 'pending', 'active', 'completed', 'cancelled'
    session_count = Column(Integer, default=0)
    outcome_collected = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    district = relationship("District", back_populates="dashboard_records")
    school = relationship("School", back_populates="dashboard_records")
    intake_queue = relationship("IntakeQueue", back_populates="dashboard_record", uselist=False)
    sessions = relationship("Session", back_populates="dashboard_record", cascade="all, delete-orphan")
    outcomes = relationship("Outcome", back_populates="dashboard_record", cascade="all, delete-orphan")


class IntakeQueue(Base):
    """Intake queue records (temporary, plain text - no encryption)"""
    __tablename__ = "intake_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    dashboard_record_id = Column(Integer, ForeignKey("dashboard_records.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Student Information (Plain text - no encryption)
    student_first_name = Column(String(100), nullable=False)
    student_last_name = Column(String(100), nullable=False)
    student_full_name = Column(String(200), nullable=False)
    student_id = Column(String(50))
    student_grade = Column(String(20))  # Store actual grade (e.g., "5", "K", "12")
    date_of_birth = Column(Date)
    
    # Parent/Guardian Contact (Plain text)
    parent_name = Column(String(200), nullable=False)
    parent_email = Column(String(200), nullable=False)
    parent_phone = Column(String(50), nullable=False)
    
    # Insurance Information (Plain text)
    insurance_company = Column(String(200))
    policyholder_name = Column(String(200))
    relationship_to_student = Column(String(100))
    member_id = Column(String(100))
    group_number = Column(String(100))
    insurance_card_front_url = Column(Text)
    insurance_card_back_url = Column(Text)
    
    # Service Needs (Plain text - JSON stored as text)
    service_category = Column(Text)  # JSON array as text
    service_category_other = Column(Text)
    severity_of_concern = Column(String(50))
    type_of_service_needed = Column(Text)  # JSON array as text
    family_resources = Column(Text)  # JSON array as text, nullable
    referral_concern = Column(Text)  # JSON array as text, nullable
    
    # Demographics (Plain text)
    sex_at_birth = Column(String(50))
    race = Column(Text)  # JSON array as text
    race_other = Column(String(200))
    ethnicity = Column(Text)  # JSON array as text
    
    # Safety & Authorization
    immediate_safety_concern = Column(Boolean, nullable=False)  # Non-PHI, can be stored unencrypted
    authorization_consent = Column(Boolean, nullable=False)  # Non-PHI
    
    # Processing Status
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime(timezone=True))
    processed_by = Column(Integer, ForeignKey("users.id"))
    simplepractice_record_id = Column(String(100))  # Reference to EHR
    
    # Retention Management
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), index=True)  # Auto-calculated
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    dashboard_record = relationship("DashboardRecord", back_populates="intake_queue")


class Session(Base):
    """Session tracking (manual entry by VPM admin)"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    dashboard_record_id = Column(Integer, ForeignKey("dashboard_records.id", ondelete="CASCADE"), nullable=False, index=True)
    session_date = Column(Date, nullable=False, index=True)
    session_type = Column(String(50))  # 'individual', 'group', 'family'
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    dashboard_record = relationship("DashboardRecord", back_populates="sessions")


class Outcome(Base):
    """Outcome tracking (aggregate only, no PHI)"""
    __tablename__ = "outcomes"
    
    id = Column(Integer, primary_key=True, index=True)
    dashboard_record_id = Column(Integer, ForeignKey("dashboard_records.id", ondelete="CASCADE"), nullable=False, index=True)
    outcome_type = Column(String(100))  # 'attendance_improvement', 'behavioral_improvement'
    outcome_value = Column(Text)  # Aggregate data only
    measured_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    dashboard_record = relationship("DashboardRecord", back_populates="outcomes")


class AuditLog(Base):
    """Audit logging for compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    action = Column(String(100), nullable=False, index=True)  # 'create', 'update', 'delete', 'view', 'export'
    resource_type = Column(String(50), index=True)  # 'dashboard_record', 'intake_queue', 'session'
    resource_id = Column(Integer, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"), index=True)
    ip_address = Column(INET)
    user_agent = Column(Text)
    details = Column(JSON)  # Additional context as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

