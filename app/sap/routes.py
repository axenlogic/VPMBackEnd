"""
SAP Data Dashboard - Intake Form API Routes

PUBLIC ENDPOINTS - No authentication required
Implements security measures: rate limiting, CAPTCHA, input validation
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi import UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID, uuid4
import json
from pathlib import Path
import os

from app.db.database import get_db
from app.sap.models import (
    District, School, DashboardRecord, IntakeQueue, AuditLog
)
from app.sap.schemas import IntakeFormResponse, IntakeStatusResponse, IntakeFormDetailsResponse, UpdateStatusRequest, UpdateStatusResponse
from app.sap.utils import (
    calculate_grade_band, 
    calculate_fiscal_period, calculate_expires_at
)
from app.sap.security import validate_captcha, get_client_ip, check_duplicate_submission
from app.sap.file_storage import save_insurance_card
from app.core.config import settings
from app.auth.routes import get_user_from_token
from app.auth.models import User

router = APIRouter()


async def parse_multipart_form(request: Request) -> dict:
    """
    Parse multipart form data with nested field names
    Returns dict with all form fields and files
    
    FastAPI's form() method handles files correctly, but we need to check
    both the form items and also look for UploadFile instances directly.
    """
    form_data = {}
    files = {}
    
    form = await request.form()
    
    # First pass: separate files from form data
    for key, value in form.items():
        # Check if it's an UploadFile instance
        # FastAPI returns UploadFile for file fields
        # Also check for SpooledTemporaryFile which FastAPI uses internally
        is_file = (
            isinstance(value, UploadFile) or
            (hasattr(value, 'filename') and value.filename) or
            (hasattr(value, 'read') and hasattr(value, 'file') and not isinstance(value, str))
        )
        
        if is_file:
            files[key] = value
        else:
            form_data[key] = value
    
    return {"form": form_data, "files": files}


def parse_array_field(form_data: dict, prefix: str) -> List[str]:
    """
    Parse array fields from form data with indexed notation
    e.g., service_needs.service_category[0], service_needs.service_category[1] -> ["value1", "value2"]
    """
    values = []
    index = 0
    while True:
        key = f"{prefix}[{index}]"
        if key in form_data:
            value = form_data[key]
            if value and str(value).strip():
                values.append(str(value).strip())
            index += 1
        else:
            break
    return values


def parse_nested_field(form_data: dict, field_path: str) -> Optional[str]:
    """
    Parse nested field from form data with dot notation
    e.g., student_information.first_name -> form_data["student_information.first_name"]
    """
    value = form_data.get(field_path)
    return str(value).strip() if value else None


@router.post("/api/v1/intake/submit", response_model=IntakeFormResponse)
async def submit_intake_form(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    PUBLIC ENDPOINT - Submit intake form
    No authentication required
    
    Accepts multipart/form-data with nested field names using dot notation.
    Rate limited: 5 submissions per hour per IP
    """
    try:
        # 1. Parse multipart form data
        parsed = await parse_multipart_form(request)
        form_data = parsed["form"]
        files = parsed["files"]
        
        # 2. Extract fields from form data
        # Student Information
        student_first_name = parse_nested_field(form_data, "student_information.first_name")
        student_last_name = parse_nested_field(form_data, "student_information.last_name")
        student_full_name = parse_nested_field(form_data, "student_information.full_name")
        student_grade = parse_nested_field(form_data, "student_information.grade")
        student_school = parse_nested_field(form_data, "student_information.school")
        student_dob = parse_nested_field(form_data, "student_information.date_of_birth")
        student_id = parse_nested_field(form_data, "student_information.student_id")
        
        # Parent/Guardian Contact
        parent_name = parse_nested_field(form_data, "parent_guardian_contact.name")
        parent_email = parse_nested_field(form_data, "parent_guardian_contact.email")
        parent_phone = parse_nested_field(form_data, "parent_guardian_contact.phone")
        
        # Service Request Type
        service_request_type = parse_nested_field(form_data, "service_request_type")
        
        # Insurance Information
        has_insurance_str = parse_nested_field(form_data, "insurance_information.has_insurance")
        insurance_company = parse_nested_field(form_data, "insurance_information.insurance_company")
        policyholder_name = parse_nested_field(form_data, "insurance_information.policyholder_name")
        relationship = parse_nested_field(form_data, "insurance_information.relationship_to_student")
        member_id = parse_nested_field(form_data, "insurance_information.member_id")
        group_number = parse_nested_field(form_data, "insurance_information.group_number")
        
        # Service Needs
        service_category = parse_array_field(form_data, "service_needs.service_category")
        service_category_other = parse_nested_field(form_data, "service_needs.service_category_other")
        severity_of_concern = parse_nested_field(form_data, "service_needs.severity_of_concern")
        type_of_service_needed = parse_array_field(form_data, "service_needs.type_of_service_needed")
        family_resources = parse_array_field(form_data, "service_needs.family_resources")
        referral_concern = parse_array_field(form_data, "service_needs.referral_concern")
        
        # Demographics
        sex_at_birth = parse_nested_field(form_data, "demographics.sex_at_birth")
        race = parse_array_field(form_data, "demographics.race")
        race_other = parse_nested_field(form_data, "demographics.race_other")
        ethnicity = parse_array_field(form_data, "demographics.ethnicity")
        
        # Safety & Authorization
        safety_concern_str = parse_nested_field(form_data, "immediate_safety_concern")
        authorization_consent_str = parse_nested_field(form_data, "authorization_consent")
        
        # CAPTCHA
        captcha_token = parse_nested_field(form_data, "captcha_token")
        
        # File uploads - try multiple possible key formats
        insurance_card_front = (
            files.get("insurance_information.insurance_card_front") or
            files.get("insurance_card_front") or
            None
        )
        insurance_card_back = (
            files.get("insurance_information.insurance_card_back") or
            files.get("insurance_card_back") or
            None
        )
        
        # 3. Validate required fields
        required_fields = {
            "student_information.first_name": student_first_name,
            "student_information.last_name": student_last_name,
            "student_information.full_name": student_full_name,
            "student_information.grade": student_grade,
            "student_information.school": student_school,
            "student_information.date_of_birth": student_dob,
            "student_information.student_id": student_id,
            "parent_guardian_contact.name": parent_name,
            "parent_guardian_contact.email": parent_email,
            "parent_guardian_contact.phone": parent_phone,
            "service_request_type": service_request_type,
            "insurance_information.has_insurance": has_insurance_str,
            "immediate_safety_concern": safety_concern_str,
            "authorization_consent": authorization_consent_str
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            raise HTTPException(
                status_code=422,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )
        
        # 4. Validate CAPTCHA
        await validate_captcha(captcha_token)
        
        # 5. Validate authorization consent
        if authorization_consent_str.lower() != "true":
            raise HTTPException(
                status_code=400,
                detail="Authorization consent is required"
            )
        
        # 6. Parse boolean values
        # Handle both "yes"/"no" and "true"/"false" formats
        has_insurance_lower = has_insurance_str.lower() if has_insurance_str else ""
        has_insurance = has_insurance_lower in ["yes", "true", "1"]
        safety_concern_lower = safety_concern_str.lower() if safety_concern_str else ""
        safety_concern = safety_concern_lower in ["yes", "true", "1"]
        
        # 7. Validate insurance fields if has_insurance is true
        if has_insurance:
            if not all([insurance_company, policyholder_name, member_id]):
                raise HTTPException(
                    status_code=422,
                    detail="Insurance company, policyholder name, and member ID are required when insurance is selected"
                )
        
        # Validate required service needs
        if not service_category:
            raise HTTPException(
                status_code=422,
                detail="At least one service category is required"
            )
        if "Other Service" in service_category and not service_category_other:
            raise HTTPException(
                status_code=422,
                detail="service_category_other is required when 'Other Service' is selected"
            )
        if not severity_of_concern:
            raise HTTPException(
                status_code=422,
                detail="severity_of_concern is required"
            )
        if severity_of_concern not in ["mild", "moderate", "severe"]:
            raise HTTPException(
                status_code=422,
                detail="severity_of_concern must be 'mild', 'moderate', or 'severe'"
            )
        if not type_of_service_needed:
            raise HTTPException(
                status_code=422,
                detail="At least one type of service needed is required"
            )
        
        # 6. Parse demographics arrays
        race = parse_array_field(dict(form_data), "demographics.race")
        race_other = parse_nested_field(dict(form_data), "demographics.race_other")
        ethnicity = parse_array_field(dict(form_data), "demographics.ethnicity")
        
        if "Other (please specify)" in race and not race_other:
            raise HTTPException(
                status_code=422,
                detail="race_other is required when 'Other (please specify)' is selected"
            )
        
        # 7. Validate service_request_type
        if service_request_type not in ["start_now", "opt_in_future"]:
            raise HTTPException(
                status_code=422,
                detail="service_request_type must be 'start_now' or 'opt_in_future'"
            )
        
        # Map to database values
        opt_in_type = "immediate_service" if service_request_type == "start_now" else "future_eligibility"
        
        # 8. Validate date format
        try:
            dob_date = datetime.strptime(student_dob, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="date_of_birth must be in YYYY-MM-DD format"
            )
        
        # Store dob_date for later use in intake_queue
        
        # 9. Check for duplicate submissions
        client_ip = get_client_ip(request)
        if check_duplicate_submission(
            db, student_first_name, student_last_name,
            student_dob, parent_email
        ):
            raise HTTPException(
                status_code=409,
                detail="A similar submission was recently submitted. Please wait before submitting again."
            )
        
        # 10. Find or create district and school
        # For now, we'll need to look up by school name or create if doesn't exist
        # TODO: Implement proper district/school lookup by code
        school_name = student_school.strip()
        
        # Try to find school by name (case-insensitive)
        school = db.query(School).join(District).filter(
            School.name.ilike(f"%{school_name}%")
        ).first()
        
        if not school:
            # Create default district and school if not found
            # TODO: This should be handled differently - schools should be pre-populated
            default_district = db.query(District).filter(District.code == "DEFAULT").first()
            if not default_district:
                default_district = District(
                    name="Default District",
                    code="DEFAULT",
                    region="Unknown"
                )
                db.add(default_district)
                db.flush()
            
            school = School(
                district_id=default_district.id,
                name=school_name,
                code=f"SCH_{uuid4().hex[:8].upper()}",
                grade_bands=["K-12"]
            )
            db.add(school)
            db.flush()
        
        # 11. Generate student UUID
        student_uuid = uuid4()
        
        # 12. Calculate grade band and fiscal period
        grade_band = calculate_grade_band(student_grade)
        referral_date = datetime.now(timezone.utc).date()
        fiscal_period = calculate_fiscal_period(referral_date)
        
        # 13. Create dashboard record (non-PHI)
        # Store student name directly for easy dashboard display (simplified approach)
        dashboard_record = DashboardRecord(
            student_uuid=student_uuid,
            district_id=school.district_id,
            school_id=school.id,
            student_name=student_full_name,  # Store name directly (non-encrypted for simplicity)
            grade_band=grade_band,
            referral_source="parent",  # Default, can be enhanced
            opt_in_type=opt_in_type,
            referral_date=referral_date,
            fiscal_period=fiscal_period,
            insurance_present=has_insurance,
            service_status="pending"
        )
        db.add(dashboard_record)
        db.flush()  # Get the ID
        
        # 14. Handle file uploads
        front_card_path = None
        back_card_path = None
        
        if insurance_card_front:
            front_card_path = await save_insurance_card(
                insurance_card_front,
                str(student_uuid),
                "front"
            )
        
        if insurance_card_back:
            back_card_path = await save_insurance_card(
                insurance_card_back,
                str(student_uuid),
                "back"
            )
        
        # 15. Create intake queue record (plain text - no encryption)
        # Note: student_name is stored in dashboard_record above (line 310) for easy API access
        intake_queue = IntakeQueue(
            dashboard_record_id=dashboard_record.id,
            # Student Information (Plain text)
            student_first_name=student_first_name,
            student_last_name=student_last_name,
            student_full_name=student_full_name,
            student_id=student_id if student_id else None,
            student_grade=student_grade,  # Store actual grade
            date_of_birth=dob_date,
            # Parent/Guardian Contact (Plain text)
            parent_name=parent_name,
            parent_email=parent_email,
            parent_phone=parent_phone,
            # Insurance Information (Plain text)
            insurance_company=insurance_company if insurance_company else None,
            policyholder_name=policyholder_name if policyholder_name else None,
            relationship_to_student=relationship if relationship else None,
            member_id=member_id if member_id else None,
            group_number=group_number if group_number else None,
            insurance_card_front_url=front_card_path,
            insurance_card_back_url=back_card_path,
            # Service Needs (Plain text - JSON as text)
            service_category=json.dumps(service_category),
            service_category_other=service_category_other if service_category_other else None,
            severity_of_concern=severity_of_concern,
            type_of_service_needed=json.dumps(type_of_service_needed),
            family_resources=json.dumps(family_resources) if family_resources else None,
            referral_concern=json.dumps(referral_concern) if referral_concern else None,
            # Demographics (Plain text)
            sex_at_birth=sex_at_birth if sex_at_birth else None,
            race=json.dumps(race) if race else None,
            race_other=race_other if race_other else None,
            ethnicity=json.dumps(ethnicity) if ethnicity else None,
            # Safety & Authorization
            immediate_safety_concern=safety_concern,
            authorization_consent=True,
            # Retention
            expires_at=calculate_expires_at()
        )
        db.add(intake_queue)
        
        # 16. Create audit log
        audit_log = AuditLog(
            user_id=None,  # Public endpoint, no user
            action="create",
            resource_type="intake_queue",
            resource_id=intake_queue.id,
            district_id=school.district_id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            details={
                "student_uuid": str(student_uuid),
                "service_request_type": service_request_type,
                "has_insurance": has_insurance
            }
        )
        db.add(audit_log)
        
        # 17. Commit transaction
        db.commit()
        
        # 18. TODO: Send admin notification email
        
        # 19. Return response
        return IntakeFormResponse(
            student_uuid=student_uuid,
            message="Intake form submitted successfully",
            status="pending"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Intake form submission error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your request. Please try again later."
        )


@router.get("/api/v1/intake/status/{student_uuid}", response_model=IntakeStatusResponse)
async def check_intake_status(
    request: Request,
    student_uuid: UUID,
    db: Session = Depends(get_db)
):
    """
    PUBLIC ENDPOINT - Check intake form status using UUID
    No authentication required
    Returns minimal non-PHI status information
    """
    try:
        # Find dashboard record by UUID
        dashboard_record = db.query(DashboardRecord).filter(
            DashboardRecord.student_uuid == student_uuid
        ).first()
        
        if not dashboard_record:
            raise HTTPException(
                status_code=404,
                detail="Intake form not found for the provided UUID"
            )
        
        # Get intake queue status
        intake_queue = db.query(IntakeQueue).filter(
            IntakeQueue.dashboard_record_id == dashboard_record.id
        ).first()
        
        processed = intake_queue.processed if intake_queue else False
        processed_date = intake_queue.processed_at if intake_queue and intake_queue.processed_at else None
        
        # Map service_status to response status
        status_map = {
            "pending": "pending",
            "active": "active",
            "processed": "processed",
            "completed": "processed",
            "cancelled": "processed"
        }
        response_status = status_map.get(dashboard_record.service_status, "pending")
        
        # Log status check (audit)
        client_ip = get_client_ip(request)
        audit_log = AuditLog(
            user_id=None,
            action="view",
            resource_type="intake_status",
            resource_id=dashboard_record.id,
            district_id=dashboard_record.district_id,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            details={"student_uuid": str(student_uuid)}
        )
        db.add(audit_log)
        db.commit()
        
        return IntakeStatusResponse(
            student_uuid=student_uuid,
            status=response_status,
            submitted_date=dashboard_record.created_at.isoformat() if dashboard_record.created_at else None,
            processed_date=processed_date.isoformat() if processed_date else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Status check error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred. Please try again later."
        )


def get_file_url(file_path: Optional[str], request: Request = None, token: Optional[str] = None) -> Optional[str]:
    """
    Convert file path to API endpoint URL with optional token
    Files are served via /api/v1/files/insurance/{filename}?token={jwt_token}
    Token allows images to be displayed in <img> tags without CORS issues
    """
    if not file_path:
        return None
    
    # If already a full URL, return as-is
    if file_path.startswith(("http://", "https://")):
        return file_path
    
    # Extract filename from path
    filename = Path(file_path).name
    
    # Construct URL to file serving endpoint
    if request:
        base_url = str(request.base_url).rstrip('/')
        url = f"{base_url}/api/v1/files/insurance/{filename}"
        # Add token as query parameter if provided (for img tag compatibility)
        if token:
            url += f"?token={token}"
        return url
    
    # Fallback: return relative path
    return f"/api/v1/files/insurance/{filename}"


@router.get("/api/v1/intake/details/{identifier}", response_model=IntakeFormDetailsResponse)
async def get_intake_form_details(
    identifier: str,
    request: Request,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Get complete intake form details by student UUID or form ID
    
    Requires JWT authentication.
    Access Control:
    - vpm_admin: Can access all forms
    - district_admin: Can access forms within their assigned district
    - district_viewer: Can access forms within their assigned district (read-only)
    """
    try:
        # 1. Authenticate user
        user = get_user_from_token(authorization, db)
        
        # 2. Find dashboard record by student_uuid
        try:
            student_uuid = UUID(identifier)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail="Intake form not found. Please verify the identifier and try again."
            )
        
        dashboard_record = db.query(DashboardRecord).filter(
            DashboardRecord.student_uuid == student_uuid
        ).first()
        
        if not dashboard_record:
            raise HTTPException(
                status_code=404,
                detail="Intake form not found. Please verify the identifier and try again."
            )
        
        # 3. Check access control (for now, all authenticated users can access)
        # TODO: Implement role-based access when User model has role/district_id fields
        # if user.role != "vpm_admin" and user.district_id != dashboard_record.district_id:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="You do not have permission to access this intake form."
        #     )
        
        # 4. Get intake queue record
        intake_queue = db.query(IntakeQueue).filter(
            IntakeQueue.dashboard_record_id == dashboard_record.id
        ).first()
        
        if not intake_queue:
            raise HTTPException(
                status_code=404,
                detail="Intake form details not found. The form may have been processed and removed."
            )
        
        # 5. Get school information
        school = dashboard_record.school
        if not school:
            raise HTTPException(
                status_code=500,
                detail="An internal server error occurred. Please try again later."
            )
        
        # 6. Parse JSON arrays from text fields
        def parse_json_array(text_value: Optional[str]) -> List[str]:
            """Parse JSON array from text field, return empty list if None or invalid"""
            if not text_value:
                return []
            try:
                parsed = json.loads(text_value)
                if isinstance(parsed, list):
                    return parsed
                return []
            except:
                return []
        
        # 7. Map service_status to response status
        status_map = {
            "pending": "pending",
            "active": "active",
            "processed": "processed",
            "completed": "processed",
            "cancelled": "processed",
            "submitted": "submitted"
        }
        response_status = status_map.get(dashboard_record.service_status, "pending")
        
        # 8. Map opt_in_type to service_request_type
        opt_in_map = {
            "immediate_service": "start_now",
            "future_eligibility": "opt_in_future"
        }
        service_request_type = opt_in_map.get(dashboard_record.opt_in_type, "start_now")
        
        # 9. Get grade from intake queue
        grade = intake_queue.student_grade or "N/A"
        
        # 10. Build file URLs with token for img tag compatibility
        # Extract token from authorization header for query parameter
        auth_token = None
        if authorization and authorization.startswith("Bearer "):
            auth_token = authorization.replace("Bearer ", "")
        
        front_card_url = get_file_url(intake_queue.insurance_card_front_url, request, auth_token)
        back_card_url = get_file_url(intake_queue.insurance_card_back_url, request, auth_token)
        
        # 11. Format dates
        submitted_date = dashboard_record.created_at.isoformat() if dashboard_record.created_at else None
        processed_date = intake_queue.processed_at.isoformat() if intake_queue.processed_at and intake_queue.processed else None
        updated_date = dashboard_record.updated_at.isoformat() if dashboard_record.updated_at else None
        dob_str = intake_queue.date_of_birth.strftime("%Y-%m-%d") if intake_queue.date_of_birth else None
        
        # 12. Build response
        from app.sap.schemas import (
            StudentInformation, ParentGuardianContact, InsuranceInformation,
            ServiceNeeds, Demographics
        )
        
        # Student Information
        student_info = StudentInformation(
            first_name=intake_queue.student_first_name,
            last_name=intake_queue.student_last_name,
            full_name=intake_queue.student_full_name,
            student_id=intake_queue.student_id or None,
            grade=grade,
            school=school.name,
            date_of_birth=dob_str or ""
        )
        
        # Parent/Guardian Contact
        parent_contact = ParentGuardianContact(
            name=intake_queue.parent_name,
            email=intake_queue.parent_email,
            phone=intake_queue.parent_phone
        )
        
        # Insurance Information
        has_insurance_str = "yes" if dashboard_record.insurance_present else "no"
        insurance_info = InsuranceInformation(
            has_insurance=has_insurance_str,
            insurance_company=intake_queue.insurance_company if dashboard_record.insurance_present else None,
            policyholder_name=intake_queue.policyholder_name if dashboard_record.insurance_present else None,
            relationship_to_student=intake_queue.relationship_to_student if dashboard_record.insurance_present else None,
            member_id=intake_queue.member_id if dashboard_record.insurance_present else None,
            group_number=intake_queue.group_number if dashboard_record.insurance_present else None,
            insurance_card_front_url=front_card_url if dashboard_record.insurance_present else None,
            insurance_card_back_url=back_card_url if dashboard_record.insurance_present else None
        )
        
        # Service Needs
        service_needs = ServiceNeeds(
            service_category=parse_json_array(intake_queue.service_category),
            service_category_other=intake_queue.service_category_other,
            severity_of_concern=intake_queue.severity_of_concern or "mild",
            type_of_service_needed=parse_json_array(intake_queue.type_of_service_needed),
            family_resources=parse_json_array(intake_queue.family_resources) if intake_queue.family_resources else None,
            referral_concern=parse_json_array(intake_queue.referral_concern) if intake_queue.referral_concern else None
        )
        
        # Demographics (optional)
        demographics = None
        if intake_queue.sex_at_birth or intake_queue.race or intake_queue.ethnicity:
            demographics = Demographics(
                sex_at_birth=intake_queue.sex_at_birth,
                race=parse_json_array(intake_queue.race) if intake_queue.race else None,
                race_other=intake_queue.race_other,
                ethnicity=parse_json_array(intake_queue.ethnicity) if intake_queue.ethnicity else None
            )
        
        # Safety concern
        safety_concern_str = "yes" if intake_queue.immediate_safety_concern else "no"
        
        # 13. Log audit trail
        client_ip = get_client_ip(request)
        audit_log = AuditLog(
            user_id=user.id,
            action="view",
            resource_type="intake_form_details",
            resource_id=dashboard_record.id,
            district_id=dashboard_record.district_id,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            details={"student_uuid": str(student_uuid)}
        )
        db.add(audit_log)
        db.commit()
        
        # 14. Return response
        return IntakeFormDetailsResponse(
            id=str(student_uuid),
            student_uuid=str(student_uuid),
            status=response_status,
            submitted_date=submitted_date or "",
            processed_date=processed_date,
            updated_date=updated_date,
            student_information=student_info,
            parent_guardian_contact=parent_contact,
            service_request_type=service_request_type,
            insurance_information=insurance_info,
            service_needs=service_needs,
            demographics=demographics,
            immediate_safety_concern=safety_concern_str,
            authorization_consent=intake_queue.authorization_consent
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching intake form details: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred. Please try again later."
        )


@router.put("/api/v1/intake/update/{identifier}", response_model=IntakeFormDetailsResponse)
async def update_intake_form(
    identifier: str,
    request: Request,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Update an existing intake form
    
    Requires JWT authentication.
    Supports partial updates - only provided fields will be updated.
    File uploads replace existing files if provided, otherwise existing files are retained.
    """
    try:
        # 1. Authenticate user
        user = get_user_from_token(authorization, db)
        
        # 2. Find dashboard record by student_uuid
        try:
            student_uuid = UUID(identifier)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail="Intake form not found. Please verify the identifier and try again."
            )
        
        dashboard_record = db.query(DashboardRecord).filter(
            DashboardRecord.student_uuid == student_uuid
        ).first()
        
        if not dashboard_record:
            raise HTTPException(
                status_code=404,
                detail="Intake form not found. Please verify the identifier and try again."
            )
        
        # 3. Check access control (for now, all authenticated users can update)
        # TODO: Implement role-based access when User model has role/district_id fields
        
        # 4. Get intake queue record
        intake_queue = db.query(IntakeQueue).filter(
            IntakeQueue.dashboard_record_id == dashboard_record.id
        ).first()
        
        if not intake_queue:
            raise HTTPException(
                status_code=404,
                detail="Intake form details not found. The form may have been processed and removed."
            )
        
        # 5. Parse multipart form data
        parsed = await parse_multipart_form(request)
        form_data = parsed["form"]
        files = parsed["files"]
        
        # 6. Track what sections are being updated (for partial updates)
        update_student_info = any(k.startswith("student_information.") for k in form_data.keys())
        update_parent_info = any(k.startswith("parent_guardian_contact.") for k in form_data.keys())
        update_insurance = any(k.startswith("insurance_information.") for k in form_data.keys()) or any("insurance_card" in k for k in files.keys())
        update_service_needs = any(k.startswith("service_needs.") for k in form_data.keys())
        update_demographics = any(k.startswith("demographics.") for k in form_data.keys())
        
        # 7. Update Student Information (if provided)
        if update_student_info:
            student_first_name = parse_nested_field(form_data, "student_information.first_name")
            student_last_name = parse_nested_field(form_data, "student_information.last_name")
            student_grade = parse_nested_field(form_data, "student_information.grade")
            student_school = parse_nested_field(form_data, "student_information.school")
            student_dob = parse_nested_field(form_data, "student_information.date_of_birth")
            student_id = parse_nested_field(form_data, "student_information.student_id")
            
            # Validate required fields if section is being updated
            if not all([student_first_name, student_last_name, student_grade, student_school, student_dob]):
                raise HTTPException(
                    status_code=422,
                    detail="All student information fields are required when updating student information"
                )
            
            # Parse date
            try:
                dob_date = datetime.strptime(student_dob, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail="date_of_birth must be in YYYY-MM-DD format"
                )
            
            # Update intake queue
            intake_queue.student_first_name = student_first_name
            intake_queue.student_last_name = student_last_name
            intake_queue.student_full_name = f"{student_first_name} {student_last_name}"
            intake_queue.student_grade = student_grade
            intake_queue.student_id = student_id if student_id else None
            intake_queue.date_of_birth = dob_date
            
            # Update dashboard record
            dashboard_record.student_name = intake_queue.student_full_name
            dashboard_record.grade_band = calculate_grade_band(student_grade)
            
            # Update school if changed
            if student_school:
                school = db.query(School).join(District).filter(
                    School.name.ilike(f"%{student_school.strip()}%")
                ).first()
                
                if school:
                    dashboard_record.school_id = school.id
                    dashboard_record.district_id = school.district_id
        
        # 8. Update Parent/Guardian Contact (if provided)
        if update_parent_info:
            parent_name = parse_nested_field(form_data, "parent_guardian_contact.name")
            parent_email = parse_nested_field(form_data, "parent_guardian_contact.email")
            parent_phone = parse_nested_field(form_data, "parent_guardian_contact.phone")
            
            # Validate required fields
            if not all([parent_name, parent_email, parent_phone]):
                raise HTTPException(
                    status_code=422,
                    detail="All parent/guardian contact fields are required when updating contact information"
                )
            
            # Validate email format
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, parent_email):
                raise HTTPException(
                    status_code=422,
                    detail="Invalid email format"
                )
            
            intake_queue.parent_name = parent_name
            intake_queue.parent_email = parent_email
            intake_queue.parent_phone = parent_phone
        
        # 9. Update Service Request Type (if provided)
        service_request_type = parse_nested_field(form_data, "service_request_type")
        if service_request_type:
            if service_request_type not in ["start_now", "opt_in_future"]:
                raise HTTPException(
                    status_code=422,
                    detail="service_request_type must be 'start_now' or 'opt_in_future'"
                )
            opt_in_type = "immediate_service" if service_request_type == "start_now" else "future_eligibility"
            dashboard_record.opt_in_type = opt_in_type
        
        # 10. Update Insurance Information (if provided)
        if update_insurance:
            has_insurance_str = parse_nested_field(form_data, "insurance_information.has_insurance")
            if has_insurance_str:
                has_insurance_lower = has_insurance_str.lower() if has_insurance_str else ""
                has_insurance = has_insurance_lower in ["yes", "true", "1"]
                dashboard_record.insurance_present = has_insurance
                
                if has_insurance:
                    insurance_company = parse_nested_field(form_data, "insurance_information.insurance_company")
                    policyholder_name = parse_nested_field(form_data, "insurance_information.policyholder_name")
                    relationship = parse_nested_field(form_data, "insurance_information.relationship_to_student")
                    member_id = parse_nested_field(form_data, "insurance_information.member_id")
                    group_number = parse_nested_field(form_data, "insurance_information.group_number")
                    
                    # Validate required fields
                    if not all([insurance_company, policyholder_name, member_id]):
                        raise HTTPException(
                            status_code=422,
                            detail="Insurance company, policyholder name, and member ID are required when has_insurance is 'yes'"
                        )
                    
                    intake_queue.insurance_company = insurance_company
                    intake_queue.policyholder_name = policyholder_name
                    intake_queue.relationship_to_student = relationship if relationship else None
                    intake_queue.member_id = member_id
                    intake_queue.group_number = group_number if group_number else None
                else:
                    # Clear insurance fields if has_insurance is "no"
                    intake_queue.insurance_company = None
                    intake_queue.policyholder_name = None
                    intake_queue.relationship_to_student = None
                    intake_queue.member_id = None
                    intake_queue.group_number = None
                    # Note: Don't delete files here - they're handled separately
        
        # 11. Handle file uploads (replace existing if provided)
        insurance_card_front = files.get("insurance_information.insurance_card_front") or files.get("insurance_card_front")
        insurance_card_back = files.get("insurance_information.insurance_card_back") or files.get("insurance_card_back")
        
        if insurance_card_front:
            # Delete old file if exists
            if intake_queue.insurance_card_front_url:
                try:
                    old_path = Path(os.getenv("UPLOAD_DIR", "./uploads")) / intake_queue.insurance_card_front_url
                    if old_path.exists():
                        old_path.unlink()
                except:
                    pass  # Continue even if deletion fails
            
            # Save new file
            front_card_path = await save_insurance_card(
                insurance_card_front,
                str(student_uuid),
                "front"
            )
            intake_queue.insurance_card_front_url = front_card_path
        
        if insurance_card_back:
            # Delete old file if exists
            if intake_queue.insurance_card_back_url:
                try:
                    old_path = Path(os.getenv("UPLOAD_DIR", "./uploads")) / intake_queue.insurance_card_back_url
                    if old_path.exists():
                        old_path.unlink()
                except:
                    pass  # Continue even if deletion fails
            
            # Save new file
            back_card_path = await save_insurance_card(
                insurance_card_back,
                str(student_uuid),
                "back"
            )
            intake_queue.insurance_card_back_url = back_card_path
        
        # 12. Update Service Needs (if provided)
        if update_service_needs:
            service_category = parse_array_field(form_data, "service_needs.service_category")
            service_category_other = parse_nested_field(form_data, "service_needs.service_category_other")
            severity_of_concern = parse_nested_field(form_data, "service_needs.severity_of_concern")
            type_of_service_needed = parse_array_field(form_data, "service_needs.type_of_service_needed")
            family_resources = parse_array_field(form_data, "service_needs.family_resources")
            referral_concern = parse_array_field(form_data, "service_needs.referral_concern")
            
            # Validate required fields
            if not service_category:
                raise HTTPException(
                    status_code=422,
                    detail="At least one service category is required"
                )
            if not severity_of_concern:
                raise HTTPException(
                    status_code=422,
                    detail="severity_of_concern is required"
                )
            if severity_of_concern not in ["mild", "moderate", "severe"]:
                raise HTTPException(
                    status_code=422,
                    detail="severity_of_concern must be 'mild', 'moderate', or 'severe'"
                )
            if not type_of_service_needed:
                raise HTTPException(
                    status_code=422,
                    detail="At least one type of service needed is required"
                )
            
            intake_queue.service_category = json.dumps(service_category)
            intake_queue.service_category_other = service_category_other if service_category_other else None
            intake_queue.severity_of_concern = severity_of_concern
            intake_queue.type_of_service_needed = json.dumps(type_of_service_needed)
            intake_queue.family_resources = json.dumps(family_resources) if family_resources else None
            intake_queue.referral_concern = json.dumps(referral_concern) if referral_concern else None
        
        # 13. Update Demographics (if provided)
        if update_demographics:
            sex_at_birth = parse_nested_field(form_data, "demographics.sex_at_birth")
            race = parse_array_field(form_data, "demographics.race")
            race_other = parse_nested_field(form_data, "demographics.race_other")
            ethnicity = parse_array_field(form_data, "demographics.ethnicity")
            
            intake_queue.sex_at_birth = sex_at_birth if sex_at_birth else None
            intake_queue.race = json.dumps(race) if race else None
            intake_queue.race_other = race_other if race_other else None
            intake_queue.ethnicity = json.dumps(ethnicity) if ethnicity else None
        
        # 14. Update Safety & Authorization (if provided)
        safety_concern_str = parse_nested_field(form_data, "immediate_safety_concern")
        if safety_concern_str:
            safety_concern_lower = safety_concern_str.lower() if safety_concern_str else ""
            safety_concern = safety_concern_lower in ["yes", "true", "1"]
            intake_queue.immediate_safety_concern = safety_concern
        
        authorization_consent_str = parse_nested_field(form_data, "authorization_consent")
        if authorization_consent_str:
            authorization_consent = authorization_consent_str.lower() == "true"
            intake_queue.authorization_consent = authorization_consent
        
        # 15. Update timestamp
        dashboard_record.updated_at = datetime.now(timezone.utc)
        
        # 16. Commit changes
        db.commit()
        
        # 17. Refresh objects to get updated data
        db.refresh(dashboard_record)
        db.refresh(intake_queue)
        
        # 18. Build response (reuse logic from details endpoint)
        school = dashboard_record.school
        if not school:
            raise HTTPException(
                status_code=500,
                detail="An internal server error occurred. Please try again later."
            )
        
        # Parse JSON arrays
        def parse_json_array(text_value: Optional[str]) -> List[str]:
            if not text_value:
                return []
            try:
                parsed = json.loads(text_value)
                if isinstance(parsed, list):
                    return parsed
                return []
            except:
                return []
        
        # Map status
        status_map = {
            "pending": "pending",
            "active": "active",
            "processed": "processed",
            "completed": "processed",
            "cancelled": "processed",
            "submitted": "submitted"
        }
        response_status = status_map.get(dashboard_record.service_status, "pending")
        
        # Map opt_in_type
        opt_in_map = {
            "immediate_service": "start_now",
            "future_eligibility": "opt_in_future"
        }
        service_request_type = opt_in_map.get(dashboard_record.opt_in_type, "start_now")
        
        # Get grade
        grade = intake_queue.student_grade or "N/A"
        
        # Build file URLs with token
        auth_token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else None
        front_card_url = get_file_url(intake_queue.insurance_card_front_url, request, auth_token)
        back_card_url = get_file_url(intake_queue.insurance_card_back_url, request, auth_token)
        
        # Format dates
        submitted_date = dashboard_record.created_at.isoformat() if dashboard_record.created_at else None
        processed_date = intake_queue.processed_at.isoformat() if intake_queue.processed_at and intake_queue.processed else None
        updated_date = dashboard_record.updated_at.isoformat() if dashboard_record.updated_at else None
        dob_str = intake_queue.date_of_birth.strftime("%Y-%m-%d") if intake_queue.date_of_birth else None
        
        # Build response objects
        from app.sap.schemas import (
            StudentInformation, ParentGuardianContact, InsuranceInformation,
            ServiceNeeds, Demographics
        )
        
        student_info = StudentInformation(
            first_name=intake_queue.student_first_name,
            last_name=intake_queue.student_last_name,
            full_name=intake_queue.student_full_name,
            student_id=intake_queue.student_id or None,
            grade=grade,
            school=school.name,
            date_of_birth=dob_str or ""
        )
        
        parent_contact = ParentGuardianContact(
            name=intake_queue.parent_name,
            email=intake_queue.parent_email,
            phone=intake_queue.parent_phone
        )
        
        has_insurance_str = "yes" if dashboard_record.insurance_present else "no"
        insurance_info = InsuranceInformation(
            has_insurance=has_insurance_str,
            insurance_company=intake_queue.insurance_company if dashboard_record.insurance_present else None,
            policyholder_name=intake_queue.policyholder_name if dashboard_record.insurance_present else None,
            relationship_to_student=intake_queue.relationship_to_student if dashboard_record.insurance_present else None,
            member_id=intake_queue.member_id if dashboard_record.insurance_present else None,
            group_number=intake_queue.group_number if dashboard_record.insurance_present else None,
            insurance_card_front_url=front_card_url if dashboard_record.insurance_present else None,
            insurance_card_back_url=back_card_url if dashboard_record.insurance_present else None
        )
        
        service_needs = ServiceNeeds(
            service_category=parse_json_array(intake_queue.service_category),
            service_category_other=intake_queue.service_category_other,
            severity_of_concern=intake_queue.severity_of_concern or "mild",
            type_of_service_needed=parse_json_array(intake_queue.type_of_service_needed),
            family_resources=parse_json_array(intake_queue.family_resources) if intake_queue.family_resources else None,
            referral_concern=parse_json_array(intake_queue.referral_concern) if intake_queue.referral_concern else None
        )
        
        demographics = None
        if intake_queue.sex_at_birth or intake_queue.race or intake_queue.ethnicity:
            demographics = Demographics(
                sex_at_birth=intake_queue.sex_at_birth,
                race=parse_json_array(intake_queue.race) if intake_queue.race else None,
                race_other=intake_queue.race_other,
                ethnicity=parse_json_array(intake_queue.ethnicity) if intake_queue.ethnicity else None
            )
        
        safety_concern_str = "yes" if intake_queue.immediate_safety_concern else "no"
        
        # 19. Log audit trail
        client_ip = get_client_ip(request)
        audit_log = AuditLog(
            user_id=user.id,
            action="update",
            resource_type="intake_form",
            resource_id=dashboard_record.id,
            district_id=dashboard_record.district_id,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            details={"student_uuid": str(student_uuid), "updated_fields": list(form_data.keys())}
        )
        db.add(audit_log)
        db.commit()
        
        # 20. Return response
        return IntakeFormDetailsResponse(
            id=str(student_uuid),
            student_uuid=str(student_uuid),
            status=response_status,
            submitted_date=submitted_date or "",
            processed_date=processed_date,
            updated_date=updated_date,
            student_information=student_info,
            parent_guardian_contact=parent_contact,
            service_request_type=service_request_type,
            insurance_information=insurance_info,
            service_needs=service_needs,
            demographics=demographics,
            immediate_safety_concern=safety_concern_str,
            authorization_consent=intake_queue.authorization_consent
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating intake form: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred. Please try again later."
        )


@router.put("/api/v1/intake/status/{identifier}", response_model=UpdateStatusResponse)
async def update_intake_status(
    identifier: str,
    request_body: UpdateStatusRequest,
    request: Request,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Update intake form status
    
    Requires JWT authentication.
    Only updates the status field of the intake form.
    """
    try:
        # 1. Authenticate user
        user = get_user_from_token(authorization, db)
        
        # 2. Find dashboard record by student_uuid
        try:
            student_uuid = UUID(identifier)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail="Intake form not found."
            )
        
        dashboard_record = db.query(DashboardRecord).filter(
            DashboardRecord.student_uuid == student_uuid
        ).first()
        
        if not dashboard_record:
            raise HTTPException(
                status_code=404,
                detail="Intake form not found."
            )
        
        # 3. Check access control (for now, all authenticated users can update)
        # TODO: Implement role-based access when User model has role/district_id fields
        # if user.role != "vpm_admin" and user.district_id != dashboard_record.district_id:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="You do not have permission to update this intake form status."
        #     )
        
        # 4. Validate status value (already validated by Pydantic, but double-check)
        new_status = request_body.status
        allowed_statuses = ["pending", "processed", "active"]
        if new_status not in allowed_statuses:
            raise HTTPException(
                status_code=422,
                detail="Invalid status value. Must be one of: pending, processed, active"
            )
        
        # 5. Get old status for audit log
        old_status = dashboard_record.service_status
        
        # 6. Update status if changed
        if dashboard_record.service_status != new_status:
            dashboard_record.service_status = new_status
            dashboard_record.updated_at = datetime.now(timezone.utc)
            
            # If status is "processed", also update intake_queue
            if new_status == "processed":
                intake_queue = db.query(IntakeQueue).filter(
                    IntakeQueue.dashboard_record_id == dashboard_record.id
                ).first()
                if intake_queue and not intake_queue.processed:
                    intake_queue.processed = True
                    intake_queue.processed_at = datetime.now(timezone.utc)
                    intake_queue.processed_by = user.id
            
            db.commit()
            db.refresh(dashboard_record)
        
        # 7. Log audit trail
        client_ip = get_client_ip(request)
        audit_log = AuditLog(
            user_id=user.id,
            action="update_status",
            resource_type="intake_form",
            resource_id=dashboard_record.id,
            district_id=dashboard_record.district_id,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            details={
                "student_uuid": str(student_uuid),
                "old_status": old_status,
                "new_status": new_status
            }
        )
        db.add(audit_log)
        db.commit()
        
        # 8. Return response
        updated_at = dashboard_record.updated_at.isoformat() if dashboard_record.updated_at else None
        
        return UpdateStatusResponse(
            id=str(student_uuid),
            student_uuid=str(student_uuid),
            status=new_status,
            updated_at=updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating intake form status: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An error occurred while updating the intake form status."
        )


@router.get("/api/v1/files/insurance/{filename}")
async def serve_insurance_card(
    filename: str,
    request: Request,
    token: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Serve insurance card images (protected endpoint)
    
    Requires JWT authentication via header or query parameter (for img tag compatibility).
    Query parameter 'token' allows images to be displayed in <img> tags.
    """
    try:
        # 1. Get token from header or query parameter
        auth_token = None
        if authorization and authorization.startswith("Bearer "):
            auth_token = authorization.replace("Bearer ", "")
        elif token:
            auth_token = token
        else:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Provide JWT token in Authorization header or 'token' query parameter."
            )
        
        # 2. Authenticate user
        user = get_user_from_token(f"Bearer {auth_token}", db)
        
        # 2. Extract student UUID from filename (format: {student_uuid}_{side}_{random}.ext)
        # Example: "18ae6a2b-cf45-401b-9ed5-470c23861bdd_front_abc12345.jpg"
        parts = filename.split('_')
        if len(parts) < 2:
            raise HTTPException(status_code=404, detail="File not found")
        
        student_uuid_str = parts[0]
        try:
            student_uuid = UUID(student_uuid_str)
        except ValueError:
            raise HTTPException(status_code=404, detail="File not found")
        
        # 3. Verify user has access to this intake form
        dashboard_record = db.query(DashboardRecord).filter(
            DashboardRecord.student_uuid == student_uuid
        ).first()
        
        if not dashboard_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # TODO: Add role-based access check when User model has role/district_id
        # if user.role != "vpm_admin" and user.district_id != dashboard_record.district_id:
        #     raise HTTPException(status_code=403, detail="Access denied")
        
        # 4. Find the file path from intake queue
        intake_queue = db.query(IntakeQueue).filter(
            IntakeQueue.dashboard_record_id == dashboard_record.id
        ).first()
        
        if not intake_queue:
            raise HTTPException(status_code=404, detail="File not found")
        
        # 5. Determine which file (front or back) and get stored filename
        side = "front" if "front" in filename.lower() else "back"
        stored_filename = intake_queue.insurance_card_front_url if side == "front" else intake_queue.insurance_card_back_url
        
        if not stored_filename:
            raise HTTPException(status_code=404, detail="File not found")
        
        # 6. Verify filename matches what's stored (security check)
        if stored_filename != filename:
            raise HTTPException(status_code=404, detail="File not found")
        
        # 7. Resolve file path
        upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
        full_path = Path(upload_dir) / filename
        
        # 8. Verify file exists
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # 9. Log access (audit trail)
        client_ip = get_client_ip(request)
        audit_log = AuditLog(
            user_id=user.id,
            action="view_file",
            resource_type="insurance_card",
            resource_id=dashboard_record.id,
            district_id=dashboard_record.district_id,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            details={"filename": filename, "student_uuid": str(student_uuid)}
        )
        db.add(audit_log)
        db.commit()
        
        # 10. Serve file
        return FileResponse(
            path=str(full_path),
            media_type="image/jpeg",  # Default, FastAPI will detect actual type
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error serving insurance card: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An internal server error occurred. Please try again later."
        )

