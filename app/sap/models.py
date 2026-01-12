"""
SAP Data Dashboard - Database Models

Dual-record system:
1. Dashboard Records (non-PHI, permanent)
2. Intake Queue Records (PHI, temporary, encrypted)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID, BYTEA, INET
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
    """PHI intake queue records (temporary, encrypted)"""
    __tablename__ = "intake_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    dashboard_record_id = Column(Integer, ForeignKey("dashboard_records.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Encrypted PHI Fields (BYTEA = binary data)
    student_first_name_encrypted = Column(BYTEA, nullable=False)
    student_last_name_encrypted = Column(BYTEA, nullable=False)
    student_full_name_encrypted = Column(BYTEA, nullable=False)
    student_id_encrypted = Column(BYTEA)
    date_of_birth_encrypted = Column(BYTEA)
    
    # Parent/Guardian Contact (Encrypted)
    parent_name_encrypted = Column(BYTEA, nullable=False)
    parent_email_encrypted = Column(BYTEA, nullable=False)
    parent_phone_encrypted = Column(BYTEA, nullable=False)
    
    # Insurance Information (Encrypted)
    insurance_company_encrypted = Column(BYTEA)
    policyholder_name_encrypted = Column(BYTEA)
    relationship_to_student_encrypted = Column(BYTEA)
    member_id_encrypted = Column(BYTEA)
    group_number_encrypted = Column(BYTEA)
    insurance_card_front_url = Column(Text)  # Encrypted storage path
    insurance_card_back_url = Column(Text)    # Encrypted storage path
    
    # Service Needs (Encrypted - contains PHI context)
    service_category_encrypted = Column(BYTEA)  # JSON array encrypted
    service_category_other_encrypted = Column(BYTEA)
    severity_of_concern_encrypted = Column(BYTEA)
    type_of_service_needed_encrypted = Column(BYTEA)  # JSON array encrypted
    family_resources_encrypted = Column(BYTEA)  # JSON array encrypted, nullable
    referral_concern_encrypted = Column(BYTEA)  # JSON array encrypted, nullable
    
    # Demographics (Encrypted - PHI)
    sex_at_birth_encrypted = Column(BYTEA)
    race_encrypted = Column(BYTEA)  # JSON array encrypted
    race_other_encrypted = Column(BYTEA)
    ethnicity_encrypted = Column(BYTEA)  # JSON array encrypted
    
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

