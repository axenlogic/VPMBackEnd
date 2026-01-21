"""
Email notification utilities for SAP intake forms
"""

from app.auth.utils import send_email
from app.core.config import settings
from datetime import datetime
from typing import Optional, List
import json


def format_date(date_str: Optional[str]) -> str:
    """Format date string for display"""
    if not date_str:
        return "Not provided"
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%B %d, %Y")
    except:
        return date_str


def format_datetime(dt_str: Optional[str]) -> str:
    """Format datetime string for display"""
    if not dt_str:
        return "Not provided"
    try:
        dt_obj = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt_obj.strftime("%B %d, %Y at %I:%M %p")
    except:
        return dt_str


def format_array_field(value: Optional[str]) -> str:
    """Format JSON array field for display"""
    if not value:
        return "Not provided"
    try:
        arr = json.loads(value) if isinstance(value, str) else value
        if isinstance(arr, list) and len(arr) > 0:
            return ", ".join(arr)
        return "Not provided"
    except:
        return value if value else "Not provided"


def create_intake_form_email_template(
    student_uuid: str,
    service_request_type: str,
    student_info: dict,
    parent_contact: dict,
    insurance_info: dict,
    service_needs: dict,
    demographics: Optional[dict],
    safety_concern: str,
    authorization_consent: bool,
    submitted_date: str,
    is_update: bool = False
) -> str:
    """Create a beautifully formatted HTML email template for intake form submission"""
    
    # Determine request type label
    request_type_label = "Start Services Now" if service_request_type == "start_now" else "Opt-in for Future Services"
    request_type_badge = "urgent" if service_request_type == "start_now" else "info"
    action_label = "Updated" if is_update else "Submitted"
    
    # Build insurance section
    insurance_section = ""
    has_insurance_value = insurance_info.get("has_insurance", "").lower()
    
    if has_insurance_value == "yes":
        insurance_section = f"""
        <tr>
            <td colspan="2" style="padding: 20px; background-color: #f8f9fa; border-left: 4px solid #28a745;">
                <h3 style="margin-top: 0; color: #28a745;">✓ Insurance Information</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600; width: 40%;">Insurance Company:</td>
                        <td style="padding: 8px 0;">{insurance_info.get('insurance_company', 'Not provided')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600;">Policyholder Name:</td>
                        <td style="padding: 8px 0;">{insurance_info.get('policyholder_name', 'Not provided')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600;">Relationship to Student:</td>
                        <td style="padding: 8px 0;">{insurance_info.get('relationship_to_student', 'Not provided')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600;">Member ID:</td>
                        <td style="padding: 8px 0;">{insurance_info.get('member_id', 'Not provided')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600;">Group Number:</td>
                        <td style="padding: 8px 0;">{insurance_info.get('group_number', 'Not provided')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600;">Insurance Cards:</td>
                        <td style="padding: 8px 0;">
                            {'Front: Uploaded ✓' if insurance_info.get('insurance_card_front_url') else 'Front: Not uploaded'}
                            {' | Back: Uploaded ✓' if insurance_info.get('insurance_card_back_url') else ' | Back: Not uploaded'}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """
    elif has_insurance_value == "no":
        insurance_section = """
        <tr>
            <td colspan="2" style="padding: 20px; background-color: #fff3cd; border-left: 4px solid #ffc107;">
                <h3 style="margin-top: 0; color: #856404;">⚠ No Insurance Information</h3>
                <p style="margin: 0;">Parent/Guardian indicated they do not have insurance.</p>
            </td>
        </tr>
        """
    else:
        # For opt_in_future, insurance might not be provided at all
        insurance_section = """
        <tr>
            <td colspan="2" style="padding: 20px; background-color: #e7f3ff; border-left: 4px solid #17a2b8;">
                <h3 style="margin-top: 0; color: #17a2b8;">ℹ️ Insurance Information</h3>
                <p style="margin: 0;">Insurance information was not provided in this submission. This is optional for opt-in forms.</p>
            </td>
        </tr>
        """
    
    # Build demographics section
    demographics_section = ""
    if demographics:
        demographics_section = f"""
        <tr>
            <td colspan="2" style="padding: 20px; background-color: #f8f9fa;">
                <h3 style="margin-top: 0; color: #495057;">Demographics</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600; width: 40%;">Sex at Birth:</td>
                        <td style="padding: 8px 0;">{demographics.get('sex_at_birth', 'Not provided')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600;">Race:</td>
                        <td style="padding: 8px 0;">{format_array_field(demographics.get('race'))}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600;">Race (Other):</td>
                        <td style="padding: 8px 0;">{demographics.get('race_other', 'Not provided')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-weight: 600;">Ethnicity:</td>
                        <td style="padding: 8px 0;">{format_array_field(demographics.get('ethnicity'))}</td>
                    </tr>
                </table>
            </td>
        </tr>
        """
    
    # Safety concern badge
    safety_badge_color = "#dc3545" if safety_concern == "yes" else "#28a745"
    safety_badge_text = "⚠️ IMMEDIATE SAFETY CONCERN" if safety_concern == "yes" else "✓ No Immediate Safety Concern"
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>New Intake Form {action_label}</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f4f4f4;">
        <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f4f4f4; padding: 20px;">
            <tr>
                <td align="center">
                    <table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background-color: #bae1d3; padding: 30px 20px; text-align: center;">
                                <h1 style="margin: 0; color: #000000; font-size: 24px; font-weight: 600;">
                                    New Intake Form {action_label}
                                </h1>
                                <p style="margin: 10px 0 0 0; color: #000000; font-size: 14px; opacity: 0.9;">
                                    Student Assistance Program (SAP)
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Alert Banner -->
                        <tr>
                            <td style="padding: 20px; background-color: {safety_badge_color}; text-align: center;">
                                <p style="margin: 0; color: #ffffff; font-weight: 600; font-size: 16px;">
                                    {safety_badge_text}
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Request Type Badge -->
                        <tr>
                            <td style="padding: 20px 20px 10px 20px;">
                                <span style="display: inline-block; padding: 8px 16px; background-color: {'#dc3545' if request_type_badge == 'urgent' else '#17a2b8'}; color: #ffffff; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase;">
                                    {request_type_label}
                                </span>
                            </td>
                        </tr>
                        
                        <!-- Student UUID -->
                        <tr>
                            <td style="padding: 0 20px 20px 20px;">
                                <p style="margin: 0; color: #6c757d; font-size: 12px; font-family: monospace;">
                                    <strong>Student UUID:</strong> {student_uuid}
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Main Content -->
                        <tr>
                            <td style="padding: 0 20px;">
                                <table role="presentation" style="width: 100%; border-collapse: collapse;">
                                    <!-- Student Information -->
                                    <tr>
                                        <td colspan="2" style="padding: 20px; background-color: #f8f9fa; border-left: 4px solid #667eea;">
                                            <h3 style="margin-top: 0; color: #667eea;">👤 Student Information</h3>
                                            <table style="width: 100%; border-collapse: collapse;">
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600; width: 40%;">Full Name:</td>
                                                    <td style="padding: 8px 0;">{student_info.get('full_name', 'Not provided')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">First Name:</td>
                                                    <td style="padding: 8px 0;">{student_info.get('first_name', 'Not provided')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Last Name:</td>
                                                    <td style="padding: 8px 0;">{student_info.get('last_name', 'Not provided')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Student ID:</td>
                                                    <td style="padding: 8px 0;">{student_info.get('student_id', 'Not provided')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Grade:</td>
                                                    <td style="padding: 8px 0;">{student_info.get('grade', 'Not provided')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">School:</td>
                                                    <td style="padding: 8px 0;">{student_info.get('school', 'Not provided')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Date of Birth:</td>
                                                    <td style="padding: 8px 0;">{format_date(student_info.get('date_of_birth'))}</td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    
                                    <!-- Parent/Guardian Contact -->
                                    <tr>
                                        <td colspan="2" style="padding: 20px; background-color: #ffffff; border-left: 4px solid #28a745;">
                                            <h3 style="margin-top: 0; color: #28a745;">📞 Parent/Guardian Contact</h3>
                                            <table style="width: 100%; border-collapse: collapse;">
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600; width: 40%;">Name:</td>
                                                    <td style="padding: 8px 0;">{parent_contact.get('name', 'Not provided')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Email:</td>
                                                    <td style="padding: 8px 0;">
                                                        <a href="mailto:{parent_contact.get('email', '')}" style="color: #667eea; text-decoration: none;">
                                                            {parent_contact.get('email', 'Not provided')}
                                                        </a>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Phone:</td>
                                                    <td style="padding: 8px 0;">
                                                        <a href="tel:{parent_contact.get('phone', '')}" style="color: #667eea; text-decoration: none;">
                                                            {parent_contact.get('phone', 'Not provided')}
                                                        </a>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                    
                                    {insurance_section}
                                    
                                    <!-- Service Needs -->
                                    <tr>
                                        <td colspan="2" style="padding: 20px; background-color: #f8f9fa; border-left: 4px solid #17a2b8;">
                                            <h3 style="margin-top: 0; color: #17a2b8;">🩺 Service Needs</h3>
                                            <table style="width: 100%; border-collapse: collapse;">
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600; width: 40%;">Service Category:</td>
                                                    <td style="padding: 8px 0;">{format_array_field(service_needs.get('service_category'))}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Service Category (Other):</td>
                                                    <td style="padding: 8px 0;">{service_needs.get('service_category_other', 'Not provided')}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Severity of Concern:</td>
                                                    <td style="padding: 8px 0;">
                                                        <span style="padding: 4px 12px; background-color: {'#dc3545' if service_needs.get('severity_of_concern') == 'severe' else '#ffc107' if service_needs.get('severity_of_concern') == 'moderate' else '#28a745' if service_needs.get('severity_of_concern') else '#6c757d'}; color: #ffffff; border-radius: 12px; font-size: 12px; font-weight: 600; text-transform: capitalize;">
                                                            {service_needs.get('severity_of_concern', 'Not provided')}
                                                        </span>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Type of Service Needed:</td>
                                                    <td style="padding: 8px 0;">{format_array_field(service_needs.get('type_of_service_needed'))}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Family Resources:</td>
                                                    <td style="padding: 8px 0;">{format_array_field(service_needs.get('family_resources'))}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Referral Concern:</td>
                                                    <td style="padding: 8px 0;">{format_array_field(service_needs.get('referral_concern'))}</td>
                                                </tr>
                                            </table>
                                            {'<p style="margin: 15px 0 0 0; padding: 10px; background-color: #e7f3ff; border-radius: 4px; color: #0066cc; font-size: 13px;"><strong>Note:</strong> This is an opt-in form. Service needs details may be minimal or not provided. VPM will contact the parent/guardian to complete the student file when services are needed.</p>' if service_request_type == 'opt_in_future' and not service_needs.get('service_category') and not service_needs.get('type_of_service_needed') else ''}
                                        </td>
                                    </tr>
                                    
                                    {demographics_section}
                                    
                                    <!-- Authorization -->
                                    <tr>
                                        <td colspan="2" style="padding: 20px; background-color: {'#d4edda' if authorization_consent else '#f8d7da'}; border-left: 4px solid {'#28a745' if authorization_consent else '#dc3545'};">
                                            <h3 style="margin-top: 0; color: {'#155724' if authorization_consent else '#721c24'};">
                                                {'✓' if authorization_consent else '✗'} Authorization & Consent
                                            </h3>
                                            <p style="margin: 0; color: {'#155724' if authorization_consent else '#721c24'};">
                                                {'Parent/Guardian has provided authorization consent.' if authorization_consent else '⚠️ Authorization consent was NOT provided.'}
                                            </p>
                                        </td>
                                    </tr>
                                    
                                    <!-- Submission Info -->
                                    <tr>
                                        <td colspan="2" style="padding: 20px; background-color: #e7f3ff; border-left: 4px solid #0066cc;">
                                            <h3 style="margin-top: 0; color: #0066cc;">📋 Submission Details</h3>
                                            <table style="width: 100%; border-collapse: collapse;">
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600; width: 40%;">Submitted Date:</td>
                                                    <td style="padding: 8px 0;">{format_datetime(submitted_date)}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Form Type:</td>
                                                    <td style="padding: 8px 0;">{request_type_label}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 8px 0; font-weight: 600;">Action:</td>
                                                    <td style="padding: 8px 0;">{action_label}</td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 20px; background-color: #f8f9fa; text-align: center; border-top: 1px solid #dee2e6;">
                                <p style="margin: 0; color: #6c757d; font-size: 12px;">
                                    This is an automated notification from the VPM Student Assistance Program (SAP) system.
                                </p>
                                <p style="margin: 10px 0 0 0; color: #6c757d; font-size: 12px;">
                                    Please review this intake form in the admin dashboard.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    return html_template


def send_intake_form_notification(
    student_uuid: str,
    service_request_type: str,
    student_info: dict,
    parent_contact: dict,
    insurance_info: dict,
    service_needs: dict,
    demographics: Optional[dict],
    safety_concern: str,
    authorization_consent: bool,
    submitted_date: str,
    is_update: bool = False
):
    """Send email notification to VPM admin when intake form is submitted"""
    
    admin_email = "dev-support@vpmforschools.org"
    
    # Determine subject
    action_label = "Updated" if is_update else "Submitted"
    request_type_label = "Start Services Now" if service_request_type == "start_now" else "Opt-in for Future Services"
    subject = f"New Intake Form {action_label} - {request_type_label} - {student_info.get('full_name', 'Unknown')}"
    
    # Create email body
    email_body = create_intake_form_email_template(
        student_uuid=student_uuid,
        service_request_type=service_request_type,
        student_info=student_info,
        parent_contact=parent_contact,
        insurance_info=insurance_info,
        service_needs=service_needs,
        demographics=demographics,
        safety_concern=safety_concern,
        authorization_consent=authorization_consent,
        submitted_date=submitted_date,
        is_update=is_update
    )
    
    # Send email (gracefully handle failures)
    try:
        send_email(admin_email, subject, email_body)
        print(f"✓ Intake form notification email sent to {admin_email}")
    except Exception as e:
        # Log the error but don't fail the request
        print(f"⚠ Failed to send intake form notification email: {e}")
        # In production, you might want to log this to a monitoring system

