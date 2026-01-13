# Google Cloud Setup Requirements - Client Action Items

**Version:** 1.0  
**Date:** January 2025  
**For:** Upwork Client - VPM Backend Project  
**Purpose:** Client-side setup requirements for HIPAA-compliant Google Cloud deployment

---

## 📋 Overview

This document outlines the **required actions** that the client must complete before the developer can proceed with deployment. The client is responsible for:

1. Setting up Google Cloud account
2. Signing Business Associate Agreement (BAA) with Google
3. Granting developer access as Technical Admin
4. Providing necessary project information

---

## ✅ Step 1: Create Google Cloud Account

### Action Required:
1. **Visit:** https://console.cloud.google.com/
2. **Sign in** with your Google account (or create one)
3. **Create New Project:**
   - Project Name: `VPM-Backend-Production` (or your preferred name)
   - Project ID: `vpm-backend-prod` (or auto-generated)
   - Organization: [Your Organization Name]

### Billing Setup:
1. **Go to:** Billing → Link a billing account
2. **Add payment method** (credit card)
3. **Note:** No upfront fees - pay-as-you-go pricing
4. **Estimated cost:** $43-118/month (scales with usage)

### Deliverable:
- [ ] Google Cloud Project created
- [ ] Billing account linked
- [ ] Project ID: `_________________` (fill in and share with developer)

---

## 📝 Step 2: Sign Business Associate Agreement (BAA) with Google

### Action Required:
**This is CRITICAL - Must be completed before storing any PHI**

1. **Contact Google Cloud Sales:**
   - **Email:** cloud-sales@google.com
   - **Phone:** 1-844-473-8273 (US)
   - **Subject:** "Request for HIPAA BAA - VPM Backend Project"

2. **Provide Information:**
   - Organization name
   - Google Cloud Project ID (from Step 1)
   - Contact information
   - Brief description: "HIPAA-compliant backend for student assistance program intake forms"

3. **BAA Process:**
   - Google will review your request (1-2 weeks)
   - They will send BAA document for signature
   - Sign and return the BAA
   - **Important:** Do NOT store PHI until BAA is signed

### Deliverable:
- [ ] BAA request submitted to Google
- [ ] BAA signed and returned to Google
- [ ] BAA confirmation received
- [ ] Date BAA signed: `_________________` (share with developer)

---

## 👤 Step 3: Add Developer as Technical Admin

### Action Required:
**Grant the developer access to manage the Google Cloud project**

1. **Go to:** IAM & Admin → IAM (in Google Cloud Console)

2. **Click:** "Grant Access" or "Add"

3. **Add Developer Email:**
   - **Email:** `[Developer's Google Account Email]` (to be provided by developer)
   - **Role:** Select one of the following:

   **Option A - Full Admin (Recommended for Setup):**
   - Role: `Owner` or `Editor`
   - **Note:** Can be downgraded to more restricted role after setup

   **Option B - Restricted Admin (More Secure):**
   - Roles:
     - `Cloud Run Admin` - Deploy and manage applications
     - `Cloud SQL Admin` - Manage database
     - `Storage Admin` - Manage file storage
     - `Secret Manager Admin` - Manage encryption keys
     - `Service Account User` - Use service accounts
     - `Cloud Build Editor` - Build container images

4. **Click:** "Save"

### Alternative: Invite via Email
1. **Go to:** IAM & Admin → IAM
2. **Click:** "Grant Access"
3. **Enter:** Developer's email address
4. **Select Role:** `Owner` or `Editor` (for initial setup)
5. **Click:** "Send Invitation"
6. Developer will receive email invitation to accept

### Deliverable:
- [ ] Developer email added to IAM
- [ ] Appropriate role assigned
- [ ] Developer has accepted invitation (if sent)
- [ ] Developer email: `_________________` (confirm with developer)

---

## 🔑 Step 4: Enable Required APIs

### Action Required:
**Enable APIs that the developer will need for deployment**

**Option A - Developer Can Enable (If Given Access):**
- Developer can enable APIs themselves if granted appropriate permissions

**Option B - Client Enables (If Restricted Access):**
1. **Go to:** APIs & Services → Enable APIs and Services
2. **Enable the following APIs:**
   - ✅ Cloud SQL Admin API
   - ✅ Cloud Run Admin API
   - ✅ Cloud Storage API
   - ✅ Secret Manager API
   - ✅ Cloud Build API
   - ✅ Cloud Logging API
   - ✅ Cloud Monitoring API
   - ✅ Cloud Resource Manager API

### Deliverable:
- [ ] All required APIs enabled
- [ ] OR developer has permission to enable APIs

---

## 📧 Step 5: Share Project Information

### Information to Share with Developer:

Once Steps 1-4 are complete, share the following with the developer:

```
Google Cloud Project ID: _________________
Region: us-central1 (or your preferred region)
Organization Name: _________________
BAA Status: [ ] Signed [ ] Pending
Developer Email Added: [ ] Yes [ ] No
```

### Deliverable:
- [ ] Project information shared with developer
- [ ] Developer has confirmed access

---

## ⏱️ Timeline

### Expected Timeline:

| Step | Task | Estimated Time |
|------|------|----------------|
| 1 | Create Google Cloud Account | 30 minutes |
| 2 | Request & Sign BAA | 1-2 weeks |
| 3 | Add Developer Access | 15 minutes |
| 4 | Enable APIs | 15 minutes |
| 5 | Share Information | 5 minutes |

**Total Client Time:** ~1 hour (plus BAA wait time)

---

## 💰 Cost Information

### Monthly Cost Estimate:

| Service | Estimated Cost |
|---------|----------------|
| Cloud SQL (Database) | $7-15/month |
| Cloud Run (Application) | $10-30/month |
| Cloud Storage (Files) | $2-5/month |
| Logging & Monitoring | $12-25/month |
| **Total Estimated** | **$43-118/month** |

**Note:**
- Pay-as-you-go pricing (no upfront fees)
- Costs scale with usage
- Can start with smaller instances and scale up
- Free tier available for some services (limited)

---

## 🔐 Security Notes

### Important Security Information:

1. **BAA is Required:**
   - Cannot store PHI without signed BAA
   - Developer will NOT deploy until BAA is confirmed

2. **Access Control:**
   - Developer access can be restricted after initial setup
   - Recommend starting with broader access, then restricting
   - All actions are logged in Cloud Audit Logs

3. **Encryption:**
   - All data encrypted at rest (automatic)
   - All data encrypted in transit (TLS 1.3)
   - Application-level encryption (handled by developer)

---

## 📞 Support Contacts

### Google Cloud Support:
- **Sales:** cloud-sales@google.com
- **Phone:** 1-844-473-8273 (US)
- **Support Portal:** https://cloud.google.com/support

### Developer Contact:
- **Email:** [Developer's Email]
- **Upwork Profile:** [Upwork Profile Link]

---

## ✅ Final Checklist

Before developer can proceed with deployment:

- [ ] Google Cloud project created
- [ ] Billing account linked and active
- [ ] BAA request submitted to Google
- [ ] BAA signed and confirmed
- [ ] Developer added as IAM user with appropriate role
- [ ] Required APIs enabled (or developer has permission)
- [ ] Project information shared with developer
- [ ] Developer has confirmed access and can see project

---

## 🚀 After Setup Complete

Once all items above are complete:

1. **Developer will:**
   - Configure Cloud SQL database instance
   - Set up Cloud Storage for file uploads
   - Configure Secret Manager for encryption keys
   - Deploy application to Cloud Run
   - Set up monitoring and logging
   - Test deployment thoroughly

2. **Client will:**
   - Review deployment
   - Test application functionality
   - Approve go-live

---

## 📋 Quick Reference

### Google Cloud Console:
- **URL:** https://console.cloud.google.com/
- **Project Selector:** Top of page (select your project)

### Key Sections:
- **IAM & Admin → IAM** - Manage user access
- **APIs & Services** - Enable APIs
- **Billing** - Manage billing account
- **Cloud SQL** - Database instances
- **Cloud Run** - Application hosting
- **Storage** - File storage

---

## ⚠️ Important Notes

1. **BAA Must Be Signed First**
   - Developer cannot deploy PHI-handling code until BAA is signed
   - This is a legal requirement, not optional

2. **Developer Access**
   - Developer needs sufficient permissions to deploy
   - Can be restricted after deployment is complete
   - All actions are logged and auditable

3. **Costs**
   - No upfront fees
   - Pay only for what you use
   - Can set budget alerts in Google Cloud Console

4. **Timeline**
   - BAA process takes 1-2 weeks
   - Deployment can begin immediately after BAA is signed
   - Developer can prepare code while waiting for BAA

---

## 📧 Template Email to Developer

Once setup is complete, send this information:

```
Subject: Google Cloud Setup Complete - Ready for Deployment

Hi [Developer Name],

Google Cloud setup is complete. Here are the details:

Project ID: [Your Project ID]
Region: us-central1
BAA Status: Signed on [Date]
Your Email: [Developer Email] - Added with [Role] role

Please confirm you can access the project and proceed with deployment.

Thanks,
[Client Name]
```

---

**Status:** Ready for Client Action  
**Next:** Client completes Steps 1-4, then developer proceeds with deployment

