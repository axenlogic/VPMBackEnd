"""
SAP Data Dashboard - Utility Functions
"""


def calculate_grade_band(grade_level: str) -> str:
    """Calculate grade band from grade level
    
    Handles formats like:
    - "10th", "11th", "12th" (ordinal)
    - "10", "11", "12" (numeric)
    - "K", "PK", "Pre-K" (kindergarten)
    """
    grade_str = str(grade_level).strip().upper()
    
    # Handle ordinal formats: "10th", "11th", "12th", "1st", "2nd", "3rd", etc.
    if grade_str.endswith('TH') or grade_str.endswith('ST') or grade_str.endswith('ND') or grade_str.endswith('RD'):
        try:
            grade_num = int(grade_str[:-2])
        except ValueError:
            grade_num = None
    else:
        # Try to parse as integer
        try:
            grade_num = int(grade_str)
        except ValueError:
            grade_num = None
    
    # Handle numeric grades
    if grade_num is not None:
        if grade_num <= 5:
            return "K-5"
        elif grade_num <= 8:
            return "6-8"
        else:
            return "9-12"
    
    # Handle non-numeric grades
    if grade_str in ['K', 'PK', 'PRE-K', 'PREK', 'KINDERGARTEN']:
        return "K-5"
    
    # Default to K-5 for unknown formats
    return "K-5"


def calculate_fiscal_period(referral_date) -> str:
    """Calculate fiscal period from date (FY starts July 1)"""
    from datetime import date
    if isinstance(referral_date, str):
        from datetime import datetime
        referral_date = datetime.strptime(referral_date, "%Y-%m-%d").date()
    
    year = referral_date.year
    month = referral_date.month
    
    # Fiscal year starts July 1
    if month >= 7:
        fiscal_year = year + 1
        quarter = ((month - 7) // 3) + 1
    else:
        fiscal_year = year
        quarter = ((month + 5) // 3) + 1
    
    return f"FY{fiscal_year}-Q{quarter}"


def calculate_expires_at(retention_days: int = 45):
    """Calculate expiration date for intake queue records"""
    from datetime import datetime, timedelta, timezone
    import os
    # Get retention days from environment or use default
    retention = int(os.getenv("INTAKE_RETENTION_DAYS", retention_days))
    return datetime.now(timezone.utc) + timedelta(days=retention)

