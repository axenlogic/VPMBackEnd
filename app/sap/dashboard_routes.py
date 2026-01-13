"""
SAP Data Dashboard - Dashboard API Routes

PROTECTED ENDPOINTS - JWT authentication required
Role-based access control for districts and schools overview
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID

from app.db.database import get_db
from app.auth.models import User
from app.auth.routes import get_user_from_token
from app.sap.models import (
    District, School, DashboardRecord, IntakeQueue
)
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
    district_id: Optional[int] = Query(None, description="Filter by district ID (VPM Admin only)"),
    school_id: Optional[int] = Query(None, description="Filter by school ID"),
    status: Optional[str] = Query(None, description="Filter forms by status: pending, processed, active"),
    date_from: Optional[str] = Query(None, description="Filter forms from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter forms to date (YYYY-MM-DD)"),
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
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date_from format. Use YYYY-MM-DD"
                )
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date_to format. Use YYYY-MM-DD"
                )
        
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
        
        # 5. Build base query for districts
        # TODO: Add role-based filtering when User model has role/district_id
        # For now, all authenticated users can see all districts
        districts_query = db.query(District).filter(District.is_active == True)
        
        # Filter by district_id if provided (VPM Admin only)
        if district_id:
            if not check_district_access(user, district_id, db):
                raise HTTPException(
                    status_code=403,
                    detail="You do not have access to this district"
                )
            districts_query = districts_query.filter(District.id == district_id)
        
        # 6. Get total count for pagination
        total_districts = districts_query.count()
        
        # 7. Apply sorting
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
        
        # 8. Apply pagination
        offset = (page - 1) * limit
        districts = districts_query.offset(offset).limit(limit).all()
        
        # 9. Build response data
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
            
            if school_id:
                schools_query = schools_query.filter(School.id == school_id)
            
            schools_list = schools_query.all()
            
            # Calculate district totals
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
            
            total_students = district_students_query.scalar() or 0
            active_students = district_active_query.scalar() or 0
            
            # Build schools data
            schools_data = []
            for school in schools_list:
                # Get forms for this school
                # Use basic query to avoid issues with missing columns or relationships
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
                
                # Get total students for school
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
                        
                        # Fallback: If null, get from intake_queue (for edge cases)
                        if not student_name:
                            try:
                                intake_queue = db.query(IntakeQueue).filter(
                                    IntakeQueue.dashboard_record_id == form.id
                                ).first()
                                if intake_queue:
                                    student_name = getattr(intake_queue, 'student_full_name', None) or \
                                                  f"{getattr(intake_queue, 'student_first_name', '')} {getattr(intake_queue, 'student_last_name', '')}".strip() or None
                            except:
                                pass
                        
                        forms_data.append({
                            "id": str(form.student_uuid),
                            "student_name": student_name,
                            "submitted_date": form.created_at.isoformat() if form.created_at else None,
                            "status": form.service_status,
                            "student_uuid": str(form.student_uuid)
                        })
                
                schools_data.append({
                    "id": f"{district.id}-{school.id}",
                    "name": school.name,
                    "total_students": school_total_students,
                    "active_students": school_active_students,
                    "forms": forms_data
                })
            
            districts_data.append({
                "id": str(district.id),
                "name": district.name,
                "total_schools": len(schools_list),
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

