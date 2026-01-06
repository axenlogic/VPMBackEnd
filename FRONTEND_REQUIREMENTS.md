# SAP Data Dashboard - Frontend Requirements

**Version:** 1.0  
**Date:** December 2025  
**Tech Stack:** React (with Cursor AI)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [User Roles & Access](#user-roles--access)
3. [Pages & Components](#pages--components)
4. [API Integration](#api-integration)
5. [State Management](#state-management)
6. [UI/UX Requirements](#uiux-requirements)
7. [Implementation Priority](#implementation-priority)

---

## 🎯 Overview

The SAP Data Dashboard frontend is a React-based application that provides:
- **Public Intake Form** - Embedded on district websites
- **Admin Portal** - For VPM administrators to process intakes
- **Dashboard Views** - For district users to view aggregated data

### Key Principles

1. **No PHI in Dashboard Views** - Only aggregated, non-identifiable data
2. **Role-Based UI** - Different views based on user role
3. **District Scoping** - Automatic filtering for district users
4. **Responsive Design** - Works on desktop, tablet, mobile
5. **Accessibility** - WCAG 2.1 AA compliance

---

## 👥 User Roles & Access

### 1. Public User (No Login Required)
- **Access**: Intake form only
- **Features**: Submit intake form, check status

### 2. VPM Admin (Full Access)
- **Access**: All districts, PHI access
- **Features**:
  - View all intake queue records
  - Decrypt and view PHI
  - Process intakes
  - Add session counts
  - Add outcome data
  - View all dashboard data
  - Export reports

### 3. District Admin (Read-Only, District-Scoped)
- **Access**: Assigned district only, no PHI
- **Features**:
  - View dashboard summary for their district
  - View aggregated data by school
  - View trends and reports
  - Export district reports (no PHI)

### 4. District Viewer (Read-Only, District-Scoped)
- **Access**: Same as District Admin
- **Features**: Same as District Admin (may have fewer export permissions)

---

## 📄 Pages & Components

### Public Pages

#### 1. Intake Form Page (`/intake`)
**Purpose**: Embedded on district websites for parent submissions

**Components**:
- `IntakeForm` - Main form component
- `FormSection` - Reusable section wrapper
- `FileUpload` - Insurance card upload (mobile-friendly)
- `StatusCheck` - Check intake status by student UUID

**Form Sections**:
1. **Student Information** (PHI)
   - Full Name (required)
   - Student ID (optional)
   - Date of Birth (required)
   - Grade Level (required)

2. **Parent/Guardian Contact** (PHI)
   - Name (required)
   - Email (required, validated)
   - Phone (required, validated)

3. **Service Request Type** (required)
   - Radio buttons:
     - "My child needs to start services now"
     - "I am opting in for future services if needed"

4. **Insurance Information** (required)
   - Has insurance? (Yes/No)
   - If Yes:
     - Insurance Company
     - Policyholder Name
     - Relationship to Student
     - Member ID
     - Group Number
     - Upload insurance card (front & back) - mobile camera support

5. **Demographics** (optional)
   - Age at birth
   - Gender
   - Race/Ethnicity
   - Other optional fields

**Validation**:
- Real-time field validation
- Email format validation
- Phone number format validation
- Required field indicators
- Error messages below fields

**Submission**:
- Show loading state
- Disable form during submission
- Success message with student UUID
- Error handling with retry option

**Status Check**:
- Input field for student UUID
- Display current status (pending, processed, active)
- Non-PHI status only

---

### Admin Portal Pages

#### 2. Admin Dashboard (`/admin/dashboard`)
**Access**: VPM Admin only

**Components**:
- `AdminSummaryCards` - Key metrics cards
- `PendingIntakesList` - List of pending intakes
- `RecentActivity` - Recent processing activity

**Metrics Cards**:
- Total Pending Intakes
- Processed Today
- Active Students
- Total Sessions This Month

**Pending Intakes List**:
- Table with columns:
  - Student UUID
  - District
  - School
  - Submitted Date
  - Has Insurance (Yes/No)
  - Actions (View Details button)
- Pagination
- Filter by district
- Sort by date

---

#### 3. Intake Processing Page (`/admin/intake/{id}`)
**Access**: VPM Admin only

**Components**:
- `IntakeDetails` - Full PHI display (decrypted)
- `ProcessIntakeForm` - Mark as processed
- `InsuranceCardViewer` - Display uploaded insurance cards

**PHI Display**:
- Student Information section
- Parent/Guardian Contact section
- Insurance Information section
- Insurance card images (if uploaded)

**Actions**:
- "Mark as Processed" button
  - Opens modal with:
    - SimplePractice Record ID input
    - Notes textarea
    - Confirm button
- "Download PDF" - Generate intake PDF
- "Back to List" button

**Security**:
- Show warning banner: "PHI Data - Restricted Access"
- Log all PHI views in audit trail
- Auto-logout after 15 minutes of inactivity

---

#### 4. Session Management (`/admin/sessions`)
**Access**: VPM Admin only

**Components**:
- `AddSessionForm` - Add session count
- `SessionsList` - List of sessions by student

**Add Session Form**:
- Search by Student UUID
- Session Date (date picker)
- Session Type (dropdown: individual, group, family)
- Submit button

**Sessions List**:
- Filter by date range
- Group by student UUID
- Show total sessions per student
- Export to CSV

---

#### 5. Outcome Management (`/admin/outcomes`)
**Access**: VPM Admin only

**Components**:
- `AddOutcomeForm` - Add outcome data
- `OutcomesList` - List of outcomes

**Add Outcome Form**:
- Search by Student UUID
- Outcome Type (dropdown)
- Outcome Value (textarea - aggregate data only)
- Measured Date
- Submit button

---

### Dashboard Pages

#### 6. District Dashboard (`/dashboard`)
**Access**: All authenticated users (district-scoped for district users)

**Components**:
- `DashboardSummary` - Summary cards
- `DistrictBreakdown` - Data by district
- `SchoolBreakdown` - Data by school
- `TrendsChart` - Time series charts
- `FiltersPanel` - Date range, district, school filters

**Summary Cards**:
- Total Opt-Ins
- Total Referrals
- Active Students
- Pending Intakes
- Completed Sessions

**Charts**:
- Opt-ins over time (line chart)
- Referrals by source (pie chart)
- Service status distribution (bar chart)
- Sessions by month (bar chart)

**Filters**:
- Date Range (start date, end date)
- District (dropdown - disabled for district users)
- School (dropdown)
- Service Status (multi-select)
- Fiscal Period (dropdown)

**Export**:
- "Export to CSV" button
- "Export to PDF" button
- No PHI in exports

---

#### 7. Reports Page (`/reports`)
**Access**: All authenticated users

**Components**:
- `ReportGenerator` - Generate custom reports
- `SavedReports` - List of saved reports
- `ReportPreview` - Preview before export

**Report Types**:
- District Summary Report
- School Comparison Report
- Trend Analysis Report
- Fiscal Period Report

**Export Formats**:
- CSV
- PDF
- Excel (future)

---

### Shared Components

#### Authentication
- `LoginForm` - Email/password login
- `ProtectedRoute` - Route wrapper for auth
- `RoleGuard` - Component wrapper for role-based access

#### Navigation
- `Sidebar` - Main navigation (role-based menu items)
- `TopBar` - User info, logout, notifications
- `Breadcrumbs` - Navigation breadcrumbs

#### Common
- `DataTable` - Reusable table with sorting, filtering, pagination
- `Chart` - Reusable chart component (using Chart.js or Recharts)
- `Modal` - Reusable modal component
- `LoadingSpinner` - Loading indicator
- `ErrorMessage` - Error display component
- `SuccessMessage` - Success notification
- `Pagination` - Pagination controls

---

## 🔌 API Integration

### API Base URL
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';
```

### Authentication
```javascript
// Store JWT token in localStorage or httpOnly cookie
// Include in all requests:
headers: {
  'Authorization': `Bearer ${token}`,
  'Content-Type': 'application/json'
}
```

### API Service Layer
Create service files for each module:

```javascript
// services/intakeService.js
export const submitIntakeForm = async (formData) => {
  const response = await fetch(`${API_BASE_URL}/intake/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  });
  return response.json();
};

export const checkIntakeStatus = async (studentUuid) => {
  const response = await fetch(`${API_BASE_URL}/intake/status/${studentUuid}`);
  return response.json();
};

// services/dashboardService.js
export const getDashboardSummary = async (filters) => {
  const token = localStorage.getItem('token');
  const queryParams = new URLSearchParams(filters);
  const response = await fetch(`${API_BASE_URL}/dashboard/summary?${queryParams}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

// services/adminService.js
export const getIntakeQueue = async () => {
  const token = localStorage.getItem('token');
  const response = await fetch(`${API_BASE_URL}/admin/intake-queue`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

export const getIntakeDetails = async (id) => {
  const token = localStorage.getItem('token');
  const response = await fetch(`${API_BASE_URL}/admin/intake-queue/${id}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

export const processIntake = async (id, data) => {
  const token = localStorage.getItem('token');
  const response = await fetch(`${API_BASE_URL}/admin/intake-queue/${id}/process`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
  return response.json();
};
```

### Error Handling
```javascript
// utils/apiErrorHandler.js
export const handleApiError = (error) => {
  if (error.response?.status === 401) {
    // Unauthorized - redirect to login
    localStorage.removeItem('token');
    window.location.href = '/login';
  } else if (error.response?.status === 403) {
    // Forbidden - show access denied message
    return 'You do not have permission to access this resource';
  } else {
    return error.response?.data?.message || 'An error occurred';
  }
};
```

---

## 🗂️ State Management

### Recommended: React Context + useReducer or Zustand

#### Auth Context
```javascript
// contexts/AuthContext.js
- user: { id, email, role, district_id }
- token: string
- login: (email, password) => Promise
- logout: () => void
- isAuthenticated: boolean
```

#### Dashboard Context
```javascript
// contexts/DashboardContext.js
- summary: DashboardSummary
- filters: { district_id, school_id, date_range, ... }
- loading: boolean
- error: string
- fetchSummary: (filters) => Promise
- updateFilters: (filters) => void
```

---

## 🎨 UI/UX Requirements

### Design System

**Color Palette**:
- Primary: Blue (#2563EB) - Trust, professionalism
- Secondary: Green (#10B981) - Success, positive metrics
- Warning: Yellow (#F59E0B) - Pending, attention needed
- Error: Red (#EF4444) - Errors, critical
- Neutral: Gray scale for text and backgrounds

**Typography**:
- Headings: Inter or Roboto (sans-serif)
- Body: System font stack
- Sizes: 12px, 14px, 16px, 18px, 24px, 32px

**Spacing**:
- Use 4px or 8px grid system
- Consistent padding/margins

**Components Style**:
- Modern, clean design
- Subtle shadows and borders
- Smooth transitions
- Hover states on interactive elements

### Responsive Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

### Accessibility
- ARIA labels on all interactive elements
- Keyboard navigation support
- Focus indicators
- Screen reader friendly
- Color contrast ratios (WCAG AA)

### Loading States
- Skeleton loaders for data tables
- Spinner for forms
- Progress indicators for long operations

### Error States
- Inline error messages
- Toast notifications for API errors
- Retry buttons where appropriate

---

## 📱 Mobile Considerations

### Intake Form (Mobile-First)
- Large touch targets (min 44x44px)
- Camera integration for insurance card upload
- Auto-format phone numbers
- Date picker optimized for mobile
- Sticky submit button
- Progress indicator for multi-step forms

### Admin Portal (Responsive)
- Collapsible sidebar on mobile
- Touch-friendly tables (swipe to scroll)
- Bottom sheet modals on mobile
- Simplified filters on small screens

---

## 🚀 Implementation Priority

### Phase 1: MVP (Before Jan 5, 2025) - CRITICAL

1. **Intake Form** (3 days)
   - Basic form structure
   - Field validation
   - File upload (insurance cards)
   - API integration
   - Status check

2. **Admin Intake Queue** (2 days)
   - List pending intakes
   - View intake details (PHI)
   - Process intake form
   - Basic styling

3. **Basic Dashboard** (2 days)
   - Summary cards
   - District/school breakdown
   - Basic filters
   - API integration

4. **Authentication** (1 day)
   - Login form
   - Protected routes
   - Role-based access
   - Token management

**Total: 8 days**

### Phase 2: Enhanced Features (Weeks 2-4)

1. Session management UI
2. Outcome management UI
3. Advanced filtering
4. Charts and visualizations
5. Export functionality
6. Reports page

### Phase 3: Polish & Optimization (Month 2+)

1. Performance optimization
2. Advanced analytics
3. Mobile app (if needed)
4. Advanced reporting
5. User preferences

---

## 📝 Technical Requirements

### Dependencies (Suggested)
```json
{
  "react": "^18.2.0",
  "react-router-dom": "^6.8.0",
  "axios": "^1.3.0",
  "zustand": "^4.3.0",  // or React Context
  "react-hook-form": "^7.43.0",
  "zod": "^3.21.0",  // Form validation
  "recharts": "^2.5.0",  // Charts
  "date-fns": "^2.29.0",  // Date utilities
  "react-query": "^3.39.0",  // Data fetching (optional)
  "tailwindcss": "^3.2.0"  // or styled-components
}
```

### Project Structure
```
src/
├── components/
│   ├── common/
│   ├── forms/
│   ├── charts/
│   └── layout/
├── pages/
│   ├── public/
│   ├── admin/
│   └── dashboard/
├── services/
│   ├── api/
│   └── auth/
├── contexts/
├── hooks/
├── utils/
└── styles/
```

---

## ✅ Testing Requirements

1. **Unit Tests**: Form validation, utility functions
2. **Integration Tests**: API calls, authentication flow
3. **E2E Tests**: Critical user flows (intake submission, admin processing)
4. **Accessibility Tests**: Screen reader, keyboard navigation

---

## 📋 Deliverables Checklist

### Phase 1 MVP
- [ ] Intake form with all required fields
- [ ] Form validation and error handling
- [ ] Insurance card upload (mobile camera)
- [ ] Status check functionality
- [ ] Admin login
- [ ] Intake queue list
- [ ] Intake detail view (PHI)
- [ ] Process intake functionality
- [ ] Basic dashboard with summary
- [ ] District/school filtering
- [ ] Responsive design (mobile-friendly)

---

**Document Status**: Ready for Frontend Development  
**Next Steps**: Begin Phase 1 implementation with intake form

