from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.integration.auth import create_intake_token, verify_intake_token
from app.integration.schemas import (
    IntegrationTokenRequest,
    IntegrationTokenResponse,
    VerifyStudentRequest,
    VerifyStudentResponse,
)
from app.sap.models import District, School, DashboardRecord, IntakeQueue


router = APIRouter()


@router.post("/api/v1/integration/token", response_model=IntegrationTokenResponse)
def integration_token(request: IntegrationTokenRequest):
    if (
        request.client_id != settings.INTEGRATION_CLIENT_ID
        or request.client_secret != settings.INTEGRATION_CLIENT_SECRET
    ):
        raise HTTPException(status_code=401, detail="Invalid client credentials")

    token = create_intake_token(request.client_id)
    return IntegrationTokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.INTEGRATION_TOKEN_EXPIRY_MINUTES * 60,
    )


@router.post("/api/v1/integration/verify-student", response_model=VerifyStudentResponse)
def verify_student(
    payload: VerifyStudentRequest,
    authorization: str = Header(...),
    db: Session = Depends(get_db),
):
    verify_intake_token(authorization)

    district = None
    school = None

    if payload.school.district_id:
        district = db.query(District).filter(District.id == int(payload.school.district_id)).first()
    elif payload.school.district_name:
        district = db.query(District).filter(District.name.ilike(payload.school.district_name)).first()

    if payload.school.school_id:
        school = db.query(School).filter(School.id == int(payload.school.school_id)).first()
    elif payload.school.school_name and district:
        school = (
            db.query(School)
            .filter(School.district_id == district.id, School.name.ilike(payload.school.school_name))
            .first()
        )

    if not district or not school:
        return VerifyStudentResponse(
            verified=False,
            match_level="none",
            reason="No record found",
        )

    # Match using student_id + name + dob in the same school
    student_id = payload.student.student_id.strip()
    first_name = payload.student.first_name.strip().lower()
    last_name = payload.student.last_name.strip().lower()
    dob = payload.student.date_of_birth.strip()

    matches = (
        db.query(DashboardRecord, IntakeQueue)
        .join(IntakeQueue, IntakeQueue.dashboard_record_id == DashboardRecord.id)
        .filter(DashboardRecord.school_id == school.id)
        .filter(IntakeQueue.student_id.ilike(student_id))
        .all()
    )

    match_level = "none"
    if matches:
        for _, intake in matches:
            name_match = (
                intake.student_first_name.lower() == first_name
                and intake.student_last_name.lower() == last_name
            )
            dob_match = intake.date_of_birth and intake.date_of_birth.isoformat() == dob
            if name_match and dob_match:
                match_level = "exact"
                break
            if name_match:
                match_level = "partial"

    if match_level == "none":
        return VerifyStudentResponse(
            verified=False,
            match_level="none",
            reason="No record found",
        )

    return VerifyStudentResponse(
        verified=True,
        match_level=match_level,
        student=payload.student,
        parent=payload.parent,
        school=payload.school,
    )

