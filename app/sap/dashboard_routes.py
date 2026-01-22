"""
SAP Data Dashboard - Dashboard API Routes

PROTECTED ENDPOINTS - JWT authentication required
Role-based access control for districts and schools overview
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date, timedelta
from uuid import UUID

from app.db.database import get_db
from app.auth.models import User
from app.auth.routes import get_user_from_token
from app.sap.models import (
    District, School, DashboardRecord, IntakeQueue, Session as SessionModel
)
from app.core.config import settings
# decrypt_phi no longer needed - student_name stored directly in dashboard_record
# Schemas not used in this endpoint, but available if needed
# from app.sap.schemas import DashboardSummaryResponse, DashboardRecordResponse

router = APIRouter()


def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    return get_user_from_token(authorization, db)


def get_admin_emails() -> List[str]:
    raw = settings.VPM_ADMIN_EMAILS or ""
    return [email.strip().lower() for email in raw.split(",") if email.strip()]


def is_vpm_admin(user: User) -> bool:
    return user.email.lower() in get_admin_emails()


def parse_date_param(value: Optional[str], name: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {name} format. Use YYYY-MM-DD"
        )


def subtract_months(base_date: date, months: int) -> date:
    year = base_date.year
    month = base_date.month - months
    while month <= 0:
        month += 12
        year -= 1
    day = min(base_date.day, 28)
    return date(year, month, day)


def get_date_range(start_date: Optional[date], end_date: Optional[date]) -> Tuple[date, date]:
    today = datetime.now().date()
    if not start_date and not end_date:
        end_date = today
        start_date = subtract_months(today, 6)
    elif start_date and not end_date:
        end_date = today
    elif end_date and not start_date:
        start_date = subtract_months(end_date, 6)
    return start_date, end_date


def normalize_period_start(value: date, period: str) -> date:
    if period == "week":
        period = "weekly"
    if period == "quarter":
        period = "quarterly"
    if period == "month":
        period = "monthly"
    if period == "year":
        period = "yearly"
    if period == "weekly":
        return value - timedelta(days=value.weekday())
    if period == "monthly":
        return value.replace(day=1)
    if period == "quarterly":
        quarter = (value.month - 1) // 3
        month = quarter * 3 + 1
        return date(value.year, month, 1)
    if period == "yearly":
        return date(value.year, 1, 1)
    return value


def next_period(value: date, period: str) -> date:
    if period == "week":
        period = "weekly"
    if period == "quarter":
        period = "quarterly"
    if period == "month":
        period = "monthly"
    if period == "year":
        period = "yearly"
    if period == "weekly":
        return value + timedelta(days=7)
    if period == "monthly":
        year = value.year + (1 if value.month == 12 else 0)
        month = 1 if value.month == 12 else value.month + 1
        return date(year, month, 1)
    if period == "quarterly":
        month = value.month + 3
        year = value.year
        if month > 12:
            month -= 12
            year += 1
        return date(year, month, 1)
    if period == "yearly":
        return date(value.year + 1, 1, 1)
    return value


def build_period_labels(start: date, end: date, period: str) -> Tuple[List[str], List[date]]:
    if period == "week":
        period = "weekly"
    if period == "quarter":
        period = "quarterly"
    if period == "month":
        period = "monthly"
    if period == "year":
        period = "yearly"
    labels = []
    buckets = []
    current = normalize_period_start(start, period)
    end_norm = normalize_period_start(end, period)
    while current <= end_norm:
        if period == "weekly":
            labels.append(current.strftime("%Y-%m-%d"))
        elif period == "monthly":
            labels.append(current.strftime("%b"))
        elif period == "quarterly":
            quarter = (current.month - 1) // 3 + 1
            labels.append(f"Q{quarter} {current.year}")
        elif period == "yearly":
            labels.append(str(current.year))
        else:
            labels.append(current.strftime("%Y-%m-%d"))
        buckets.append(current)
        current = next_period(current, period)
    return labels, buckets


def apply_scope_filters(query, user: User, district_id: Optional[int], school_id: Optional[int]) -> Tuple:
    admin = is_vpm_admin(user)
    user_district_id = getattr(user, "district_id", None)
    if not admin:
        if district_id and user_district_id and district_id != user_district_id:
            raise HTTPException(status_code=403, detail="You do not have access to this district")
        if not user_district_id:
            raise HTTPException(status_code=403, detail="District access not configured for this user")
        query = query.filter(DashboardRecord.district_id == user_district_id)
    else:
        if district_id:
            query = query.filter(DashboardRecord.district_id == district_id)
    if school_id:
        query = query.filter(DashboardRecord.school_id == school_id)
    return query, admin, user_district_id


def check_district_access(user: User, district_id: int, db: Session) -> bool:
    """
    Check if user has access to a district
    VPM Admin: has access to all districts
    District Admin/Viewer: only their assigned district
    """
    # TODO: Add role and district_id fields to User model
    # For now, assume all users are VPM Admin (can access all)
    # When roles are implemented:
    # if user.role == "vpm_admin":
    #     return True
    # return user.district_id == district_id
    return True


@router.get("/api/v1/dashboard/districts-schools")
async def get_districts_schools(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Number of districts per page"),
    district_id: Optional[str] = Query(None, description="Filter by district ID (VPM Admin only)"),
    school_id: Optional[str] = Query(None, description="Filter by school ID"),
    status: Optional[str] = Query(None, description="Filter forms by status: pending, processed, active"),
    date_from: Optional[str] = Query(None, description="Filter forms from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter forms to date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search by student name or student ID"),
    include_forms: bool = Query(True, description="Include intake forms in response"),
    forms_limit: int = Query(50, ge=1, le=200, description="Maximum forms per school"),
    sort_by: str = Query("name", description="Sort by: name, total_students, active_students, total_schools"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Get districts and schools overview with intake forms
    
    Requires JWT authentication.
    Role-based access: VPM Admin sees all, District Admin/Viewer see only their district.
    """
    try:
        # 1. Authenticate user
        user = get_current_user(authorization, db)
        
        # 2. Parse date filters
        date_from_obj = None
        date_to_obj = None
        if date_from:
            date_from_obj = parse_date_param(date_from, "date_from")
        if date_to:
            date_to_obj = parse_date_param(date_to, "date_to")
        
        # 3. Validate status filter
        if status and status not in ["pending", "processed", "active"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid status. Must be: pending, processed, or active"
            )
        
        # 4. Validate sort parameters
        if sort_by not in ["name", "total_students", "active_students", "total_schools"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid sort_by. Must be: name, total_students, active_students, or total_schools"
            )
        if sort_order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid sort_order. Must be: asc or desc"
            )
        
        # Normalize IDs (accepts plain IDs or "district-school" format)
        def parse_int_id(value: Optional[str], label: str) -> Optional[int]:
            if not value:
                return None
            raw = value.strip()
            if "-" in raw:
                raw = raw.split("-")[-1]
            if not raw.isdigit():
                raise HTTPException(status_code=400, detail=f"Invalid {label} format")
            return int(raw)
        
        district_id_int = parse_int_id(district_id, "district_id")
        school_id_int = parse_int_id(school_id, "school_id")
        
        # 5. Build base query for districts
        districts_query = db.query(District).filter(District.is_active == True)
        
        # Filter by district_id if provided (VPM Admin only)
        if district_id_int and not is_vpm_admin(user):
            raise HTTPException(status_code=403, detail="You do not have access to this district")
        if not is_vpm_admin(user):
            user_district_id = getattr(user, "district_id", None)
            if not user_district_id:
                raise HTTPException(status_code=403, detail="District access not configured for this user")
            districts_query = districts_query.filter(District.id == user_district_id)
        elif district_id_int:
            districts_query = districts_query.filter(District.id == district_id_int)
        
        # 6. Validate district/school existence when filters provided
        if district_id_int:
            district_exists = db.query(District.id).filter(District.id == district_id_int).first()
            if not district_exists:
                raise HTTPException(status_code=404, detail="District not found")
        if school_id_int:
            school_exists = db.query(School.id).filter(School.id == school_id_int).first()
            if not school_exists:
                raise HTTPException(status_code=404, detail="School not found")

        # 7. Get total count for pagination
        total_districts = districts_query.count()
        
        # 8. Apply sorting
        if sort_by == "name":
            order_by = District.name.asc() if sort_order == "asc" else District.name.desc()
        elif sort_by == "total_students":
            # Subquery for total students per district
            students_subq = db.query(
                DashboardRecord.district_id,
                func.count(func.distinct(DashboardRecord.student_uuid)).label('total')
            ).group_by(DashboardRecord.district_id).subquery()
            # This is complex - for now, sort by name
            order_by = District.name.asc() if sort_order == "asc" else District.name.desc()
        else:
            order_by = District.name.asc() if sort_order == "asc" else District.name.desc()
        
        districts_query = districts_query.order_by(order_by)
        
        # 9. Apply pagination
        offset = (page - 1) * limit
        districts = districts_query.offset(offset).limit(limit).all()
        
        # 10. Build response data
        districts_data = []
        total_students_all = 0
        total_active_students_all = 0
        total_schools_all = 0
        total_forms_all = 0
        
        for district in districts:
            # Get schools for this district
            schools_query = db.query(School).filter(
                School.district_id == district.id,
                School.is_active == True
            )
            
            if school_id_int:
                schools_query = schools_query.filter(School.id == school_id_int)
            
            schools_list = schools_query.all()
            
            # Calculate district totals (respect filters when search is used)
            district_students_query = db.query(
                func.count(func.distinct(DashboardRecord.student_uuid))
            ).filter(DashboardRecord.district_id == district.id)
            
            district_active_query = db.query(
                func.count(func.distinct(DashboardRecord.student_uuid))
            ).filter(
                DashboardRecord.district_id == district.id,
                DashboardRecord.service_status == "active"
            )
            
            # Apply date filters if provided
            if date_from_obj:
                district_students_query = district_students_query.filter(
                    DashboardRecord.referral_date >= date_from_obj
                )
                district_active_query = district_active_query.filter(
                    DashboardRecord.referral_date >= date_from_obj
                )
            if date_to_obj:
                district_students_query = district_students_query.filter(
                    DashboardRecord.referral_date <= date_to_obj
                )
                district_active_query = district_active_query.filter(
                    DashboardRecord.referral_date <= date_to_obj
                )
            if status:
                district_students_query = district_students_query.filter(
                    DashboardRecord.service_status == status
                )
                district_active_query = district_active_query.filter(
                    DashboardRecord.service_status == status
                )
            if search:
                search_value = f"%{search.strip().lower()}%"
                district_students_query = district_students_query.outerjoin(
                    IntakeQueue, IntakeQueue.dashboard_record_id == DashboardRecord.id
                ).filter(
                    or_(
                        func.lower(DashboardRecord.student_name).like(search_value),
                        func.lower(IntakeQueue.student_id).like(search_value)
                    )
                )
                district_active_query = district_active_query.outerjoin(
                    IntakeQueue, IntakeQueue.dashboard_record_id == DashboardRecord.id
                ).filter(
                    or_(
                        func.lower(DashboardRecord.student_name).like(search_value),
                        func.lower(IntakeQueue.student_id).like(search_value)
                    )
                )
            
            total_students = district_students_query.scalar() or 0
            active_students = district_active_query.scalar() or 0
            
            # Build schools data
            schools_data = []
            for school in schools_list:
                # Get forms for this school
                forms_query = db.query(DashboardRecord).filter(
                    DashboardRecord.school_id == school.id
                )
                
                # Apply status filter
                if status:
                    forms_query = forms_query.filter(DashboardRecord.service_status == status)
                
                # Apply date filters
                if date_from_obj:
                    forms_query = forms_query.filter(DashboardRecord.referral_date >= date_from_obj)
                if date_to_obj:
                    forms_query = forms_query.filter(DashboardRecord.referral_date <= date_to_obj)

                # Apply search filter (student_name or student_id)
                if search:
                    search_value = f"%{search.strip().lower()}%"
                    forms_query = forms_query.outerjoin(
                        IntakeQueue, IntakeQueue.dashboard_record_id == DashboardRecord.id
                    ).filter(
                        or_(
                            func.lower(DashboardRecord.student_name).like(search_value),
                            func.lower(IntakeQueue.student_id).like(search_value)
                        )
                    )
                
                # Get total students for school (respect filters when search is used)
                school_students_query = db.query(
                    func.count(func.distinct(DashboardRecord.student_uuid))
                ).filter(DashboardRecord.school_id == school.id)
                
                school_active_query = db.query(
                    func.count(func.distinct(DashboardRecord.student_uuid))
                ).filter(
                    DashboardRecord.school_id == school.id,
                    DashboardRecord.service_status == "active"
                )
                
                if date_from_obj:
                    school_students_query = school_students_query.filter(
                        DashboardRecord.referral_date >= date_from_obj
                    )
                    school_active_query = school_active_query.filter(
                        DashboardRecord.referral_date >= date_from_obj
                    )
                if date_to_obj:
                    school_students_query = school_students_query.filter(
                        DashboardRecord.referral_date <= date_to_obj
                    )
                    school_active_query = school_active_query.filter(
                        DashboardRecord.referral_date <= date_to_obj
                    )
                if status:
                    school_students_query = school_students_query.filter(
                        DashboardRecord.service_status == status
                    )
                    school_active_query = school_active_query.filter(
                        DashboardRecord.service_status == status
                    )
                if search:
                    search_value = f"%{search.strip().lower()}%"
                    school_students_query = school_students_query.outerjoin(
                        IntakeQueue, IntakeQueue.dashboard_record_id == DashboardRecord.id
                    ).filter(
                        or_(
                            func.lower(DashboardRecord.student_name).like(search_value),
                            func.lower(IntakeQueue.student_id).like(search_value)
                        )
                    )
                    school_active_query = school_active_query.outerjoin(
                        IntakeQueue, IntakeQueue.dashboard_record_id == DashboardRecord.id
                    ).filter(
                        or_(
                            func.lower(DashboardRecord.student_name).like(search_value),
                            func.lower(IntakeQueue.student_id).like(search_value)
                        )
                    )
                
                school_total_students = school_students_query.scalar() or 0
                school_active_students = school_active_query.scalar() or 0
                
                # Get forms if requested
                forms_data = []
                if include_forms:
                    forms = forms_query.order_by(
                        DashboardRecord.created_at.desc()
                    ).limit(forms_limit).all()
                    
                    for form in forms:
                        # Get student name from dashboard_record (always stored there)
                        student_name = getattr(form, 'student_name', None)
                        student_id = None
                        
                        # Fallback: If null, get from intake_queue (for edge cases)
                        if not student_name:
                            try:
                                intake_queue = db.query(IntakeQueue).filter(
                                    IntakeQueue.dashboard_record_id == form.id
                                ).first()
                                if intake_queue:
                                    student_name = getattr(intake_queue, 'student_full_name', None) or \
                                                  f"{getattr(intake_queue, 'student_first_name', '')} {getattr(intake_queue, 'student_last_name', '')}".strip() or None
                                    student_id = getattr(intake_queue, 'student_id', None)
                            except:
                                pass
                        else:
                            # Get student_id for search response
                            try:
                                intake_queue = db.query(IntakeQueue).filter(
                                    IntakeQueue.dashboard_record_id == form.id
                                ).first()
                                if intake_queue:
                                    student_id = getattr(intake_queue, 'student_id', None)
                            except:
                                pass
                        
                        forms_data.append({
                            "id": str(form.student_uuid),
                            "student_name": student_name,
                            "student_id": student_id,
                            "submitted_date": form.created_at.isoformat() if form.created_at else None,
                            "status": form.service_status,
                            "student_uuid": str(form.student_uuid)
                        })
                
                # When searching, only include schools that have matching forms or matching totals
                if search and not forms_data and school_total_students == 0 and school_active_students == 0:
                    continue
                
                schools_data.append({
                    "id": f"{district.id}-{school.id}",
                    "name": school.name,
                    "total_students": school_total_students,
                    "active_students": school_active_students,
                    "forms": forms_data
                })
            
            # When searching, only include districts that have matching schools
            if search and not schools_data:
                continue
            
            districts_data.append({
                "id": str(district.id),
                "name": district.name,
                "total_schools": len(schools_data) if search else len(schools_list),
                "total_students": total_students,
                "active_students": active_students,
                "schools": schools_data
            })
            
            # Accumulate totals
            total_students_all += total_students
            total_active_students_all += active_students
            total_schools_all += len(schools_list)
            total_forms_all += sum(len(school["forms"]) for school in schools_data)
        
        # 10. Calculate pagination
        total_pages = (total_districts + limit - 1) // limit
        
        # 11. Build response
        return {
            "success": True,
            "data": {
                "districts": districts_data,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_districts": total_districts,
                    "per_page": limit,
                    "has_next": page < total_pages,
                    "has_previous": page > 1
                },
                "summary": {
                    "total_districts": total_districts,
                    "total_schools": total_schools_all,
                    "total_students": total_students_all,
                    "total_active_students": total_active_students_all,
                    "total_forms": total_forms_all
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Districts schools error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching districts and schools data: {str(e)}"
        )


@router.get("/api/v1/dashboard/summary")
async def get_dashboard_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    period: str = Query("monthly", description="weekly, monthly, quarterly, yearly"),
    district_id: Optional[int] = Query(None, description="Filter by district ID (admin only)"),
    school_id: Optional[int] = Query(None, description="Filter by school ID (admin only)"),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(authorization, db)
    if period in ["week", "month", "quarter", "year"]:
        period = "weekly" if period == "week" else "monthly" if period == "month" else "quarterly" if period == "quarter" else "yearly"
    if period not in ["weekly", "monthly", "quarterly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid period. Must be weekly, monthly, quarterly, or yearly")
    start = parse_date_param(start_date, "start_date")
    end = parse_date_param(end_date, "end_date")
    start, end = get_date_range(start, end)

    base_query = db.query(DashboardRecord)
    base_query, admin, user_district_id = apply_scope_filters(base_query, user, district_id, school_id)
    base_query = base_query.filter(DashboardRecord.referral_date.between(start, end))

    total_opt_ins = base_query.filter(DashboardRecord.opt_in_type == "future_eligibility").count()
    total_referrals = base_query.filter(DashboardRecord.opt_in_type == "immediate_service").count()
    active_students_served = base_query.filter(DashboardRecord.service_status == "active").count()

    # Session Counts Analytics = total referrals + active students
    session_counts = total_referrals + active_students_served

    districts_query = db.query(func.count(District.id)).filter(District.is_active == True)
    schools_query = db.query(func.count(School.id)).filter(School.is_active == True)
    if not admin:
        if not user_district_id:
            raise HTTPException(status_code=403, detail="District access not configured for this user")
        districts_query = districts_query.filter(District.id == user_district_id)
        schools_query = schools_query.filter(School.district_id == user_district_id)
    elif district_id:
        districts_query = districts_query.filter(District.id == district_id)
        schools_query = schools_query.filter(School.district_id == district_id)
    if school_id:
        schools_query = schools_query.filter(School.id == school_id)

    return {
        "total_opt_ins": total_opt_ins,
        "total_referrals": total_referrals,
        "active_students_served": active_students_served,
        "session_counts": session_counts,
        "districts_count": districts_query.scalar() or 0,
        "schools_count": schools_query.scalar() or 0
    }


@router.get("/api/v1/dashboard/trends")
async def get_dashboard_trends(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    period: str = Query("monthly", description="weekly, monthly, quarterly, yearly"),
    district_id: Optional[int] = Query(None, description="Filter by district ID (admin only)"),
    school_id: Optional[int] = Query(None, description="Filter by school ID (admin only)"),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(authorization, db)
    if period in ["week", "month", "quarter", "year"]:
        period = "weekly" if period == "week" else "monthly" if period == "month" else "quarterly" if period == "quarter" else "yearly"
    if period not in ["weekly", "monthly", "quarterly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid period. Must be weekly, monthly, quarterly, or yearly")
    start = parse_date_param(start_date, "start_date")
    end = parse_date_param(end_date, "end_date")
    start, end = get_date_range(start, end)

    labels, buckets = build_period_labels(start, end, period)

    base_query = db.query(DashboardRecord)
    base_query, _, _ = apply_scope_filters(base_query, user, district_id, school_id)
    base_query = base_query.filter(DashboardRecord.referral_date.between(start, end))

    def bucket_counts(dates: List[date]) -> Dict[date, int]:
        counts = {bucket: 0 for bucket in buckets}
        for value in dates:
            if not value:
                continue
            bucket = normalize_period_start(value, period)
            if bucket in counts:
                counts[bucket] += 1
        return counts

    opt_in_dates = [
        row[0] for row in base_query.filter(
            DashboardRecord.opt_in_type == "future_eligibility"
        ).with_entities(DashboardRecord.referral_date).all()
    ]
    referral_dates = [
        row[0] for row in base_query.filter(
            DashboardRecord.opt_in_type == "immediate_service"
        ).with_entities(DashboardRecord.referral_date).all()
    ]
    active_dates = [
        row[0] for row in base_query.filter(
            DashboardRecord.service_status == "active"
        ).with_entities(DashboardRecord.referral_date).all()
    ]

    opt_ins_map = bucket_counts(opt_in_dates)
    referrals_map = bucket_counts(referral_dates)
    active_map = bucket_counts(active_dates)
    # Session Counts Analytics = referrals + active students per bucket
    sessions_map = {bucket: referrals_map.get(bucket, 0) + active_map.get(bucket, 0) for bucket in buckets}

    def build_series(mapping):
        return [mapping.get(bucket, 0) for bucket in buckets]

    return {
        "period": period,
        "labels": labels,
        "series": {
            "opt_ins": build_series(opt_ins_map),
            "referrals": build_series(referrals_map),
            "active_students": build_series(active_map),
            "sessions": build_series(sessions_map)
        }
    }


@router.get("/api/v1/dashboard/district-breakdown")
async def get_district_breakdown(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    period: str = Query("monthly", description="weekly, monthly, quarterly, yearly"),
    district_id: Optional[int] = Query(None, description="Filter by district ID (admin only)"),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(authorization, db)
    if not is_vpm_admin(user):
        raise HTTPException(status_code=403, detail="You do not have access to district breakdown")
    if period in ["week", "month", "quarter", "year"]:
        period = "weekly" if period == "week" else "monthly" if period == "month" else "quarterly" if period == "quarter" else "yearly"
    if period not in ["weekly", "monthly", "quarterly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid period. Must be weekly, monthly, quarterly, or yearly")
    start = parse_date_param(start_date, "start_date")
    end = parse_date_param(end_date, "end_date")
    start, end = get_date_range(start, end)

    districts_query = db.query(District).filter(District.is_active == True)
    if district_id:
        districts_query = districts_query.filter(District.id == district_id)
    districts = districts_query.all()

    result = []
    for district in districts:
        records = db.query(DashboardRecord).filter(
            DashboardRecord.district_id == district.id,
            DashboardRecord.referral_date.between(start, end)
        )
        total_opt_ins = records.filter(DashboardRecord.opt_in_type == "future_eligibility").count()
        total_referrals = records.filter(DashboardRecord.opt_in_type == "immediate_service").count()
        active_students = records.filter(DashboardRecord.service_status == "active").count()
        # Session Counts Analytics = total referrals + active students
        session_counts = total_referrals + active_students
        schools_count = db.query(School).filter(
            School.district_id == district.id,
            School.is_active == True
        ).count()

        result.append({
            "district_id": str(district.id),
            "district_name": district.name,
            "total_opt_ins": total_opt_ins,
            "total_referrals": total_referrals,
            "active_students": active_students,
            "session_counts": session_counts,
            "schools_count": schools_count
        })

    return {"districts": result}


@router.get("/api/v1/dashboard/school-breakdown")
async def get_school_breakdown(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    period: str = Query("monthly", description="weekly, monthly, quarterly, yearly"),
    district_id: Optional[int] = Query(None, description="Filter by district ID (admin only)"),
    school_id: Optional[int] = Query(None, description="Filter by school ID"),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(authorization, db)
    if period in ["week", "month", "quarter", "year"]:
        period = "weekly" if period == "week" else "monthly" if period == "month" else "quarterly" if period == "quarter" else "yearly"
    if period not in ["weekly", "monthly", "quarterly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid period. Must be weekly, monthly, quarterly, or yearly")
    start = parse_date_param(start_date, "start_date")
    end = parse_date_param(end_date, "end_date")
    start, end = get_date_range(start, end)

    admin = is_vpm_admin(user)
    user_district_id = getattr(user, "district_id", None)
    if not admin:
        if district_id and user_district_id and district_id != user_district_id:
            raise HTTPException(status_code=403, detail="You do not have access to this district")
        if not user_district_id:
            raise HTTPException(status_code=403, detail="District access not configured for this user")
        district_id = user_district_id

    schools_query = db.query(School).filter(School.is_active == True)
    if district_id:
        schools_query = schools_query.filter(School.district_id == district_id)
    if school_id:
        schools_query = schools_query.filter(School.id == school_id)
    schools = schools_query.all()

    result = []
    for school in schools:
        records = db.query(DashboardRecord).filter(
            DashboardRecord.school_id == school.id,
            DashboardRecord.referral_date.between(start, end)
        )
        total_opt_ins = records.filter(DashboardRecord.opt_in_type == "future_eligibility").count()
        total_referrals = records.filter(DashboardRecord.opt_in_type == "immediate_service").count()
        active_students = records.filter(DashboardRecord.service_status == "active").count()
        # Session Counts Analytics = total referrals + active students
        session_counts = total_referrals + active_students

        result.append({
            "school_id": str(school.id),
            "school_name": school.name,
            "district_id": str(school.district_id),
            "district_name": school.district.name if school.district else "",
            "total_opt_ins": total_opt_ins,
            "total_referrals": total_referrals,
            "active_students": active_students,
            "session_counts": session_counts
        })

    return {"schools": result}

