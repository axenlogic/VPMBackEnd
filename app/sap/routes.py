"""
SAP Data Dashboard - Intake Form API Routes

PUBLIC ENDPOINTS - No authentication required
Implements security measures: rate limiting, CAPTCHA, input validation
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import UploadFile
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID, uuid4
import json

from app.db.database import get_db
from app.sap.models import (
    District, School, DashboardRecord, IntakeQueue, AuditLog
)
from app.sap.schemas import IntakeFormResponse, IntakeStatusResponse
from app.sap.utils import (
    encrypt_phi, decrypt_phi, calculate_grade_band, 
    calculate_fiscal_period, calculate_expires_at
)
from app.sap.security import validate_captcha, get_client_ip, check_duplicate_submission
from app.sap.file_storage import save_insurance_card
from app.core.config import settings

router = APIRouter()


async def parse_multipart_form(request: Request) -> dict:
    """
    Parse multipart form data with nested field names
    Returns dict with all form fields and files
    """
    form_data = {}
    files = {}
    
    form = await request.form()
    for key, value in form.items():
        if isinstance(value, UploadFile):
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
        
        # File uploads
        insurance_card_front = files.get("insurance_information.insurance_card_front")
        insurance_card_back = files.get("insurance_information.insurance_card_back")
        
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
        has_insurance = has_insurance_str.lower() == "true"
        safety_concern = safety_concern_str.lower() == "true"
        
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
        dashboard_record = DashboardRecord(
            student_uuid=student_uuid,
            district_id=school.district_id,
            school_id=school.id,
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
        
        # 15. Encrypt PHI and create intake queue record
        intake_queue = IntakeQueue(
            dashboard_record_id=dashboard_record.id,
            # Student Information (Encrypted)
            student_first_name_encrypted=encrypt_phi(student_first_name),
            student_last_name_encrypted=encrypt_phi(student_last_name),
            student_full_name_encrypted=encrypt_phi(student_full_name),
            student_id_encrypted=encrypt_phi(student_id) if student_id else None,
            date_of_birth_encrypted=encrypt_phi(student_dob),
            # Parent/Guardian Contact (Encrypted)
            parent_name_encrypted=encrypt_phi(parent_name),
            parent_email_encrypted=encrypt_phi(parent_email),
            parent_phone_encrypted=encrypt_phi(parent_phone),
            # Insurance Information (Encrypted)
            insurance_company_encrypted=encrypt_phi(insurance_company) if insurance_company else None,
            policyholder_name_encrypted=encrypt_phi(policyholder_name) if policyholder_name else None,
            relationship_to_student_encrypted=encrypt_phi(relationship) if relationship else None,
            member_id_encrypted=encrypt_phi(member_id) if member_id else None,
            group_number_encrypted=encrypt_phi(group_number) if group_number else None,
            insurance_card_front_url=front_card_path,
            insurance_card_back_url=back_card_path,
            # Service Needs (Encrypted)
            service_category_encrypted=encrypt_phi(json.dumps(service_category)),
            service_category_other_encrypted=encrypt_phi(service_category_other) if service_category_other else None,
            severity_of_concern_encrypted=encrypt_phi(severity_of_concern),
            type_of_service_needed_encrypted=encrypt_phi(json.dumps(type_of_service_needed)),
            family_resources_encrypted=encrypt_phi(json.dumps(family_resources)) if family_resources else None,
            referral_concern_encrypted=encrypt_phi(json.dumps(referral_concern)) if referral_concern else None,
            # Demographics (Encrypted)
            sex_at_birth_encrypted=encrypt_phi(sex_at_birth) if sex_at_birth else None,
            race_encrypted=encrypt_phi(json.dumps(race)) if race else None,
            race_other_encrypted=encrypt_phi(race_other) if race_other else None,
            ethnicity_encrypted=encrypt_phi(json.dumps(ethnicity)) if ethnicity else None,
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

