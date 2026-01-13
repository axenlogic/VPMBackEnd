# HIPAA Google Cloud - Quick Start Checklist

## 🚀 Immediate Actions (Do First)

### 1. Contact Google Cloud Sales
- **Email:** cloud-sales@google.com
- **Phone:** 1-844-473-8273 (US)
- **Request:** Business Associate Agreement (BAA) for HIPAA compliance
- **Timeline:** 1-2 weeks for BAA processing
- **Important:** Do NOT store PHI until BAA is signed

### 2. Create Google Cloud Account
1. Go to: https://console.cloud.google.com/
2. Create new project: `VPM-Backend-Production`
3. Enable billing (credit card required)
4. **Cost:** Pay-as-you-go, no upfront fees

### 3. Enable Required APIs
```bash
# Install gcloud CLI first: https://cloud.google.com/sdk/docs/install

gcloud services enable sqladmin.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

---

## 💰 Pricing Overview

### Estimated Monthly Costs (Small-Medium Scale)

| Service | Cost Range |
|---------|-----------|
| Cloud SQL (PostgreSQL) | $7-15/month |
| Cloud Run (App hosting) | $10-30/month |
| Cloud Storage (Files) | $2-5/month |
| Logging & Monitoring | $12-25/month |
| **Total** | **$43-118/month** |

**Note:** Costs scale with usage. Start small and scale as needed.

---

## 📋 Pre-Deployment Checklist

### Before Storing Any PHI:

- [ ] BAA signed with Google Cloud
- [ ] Google Cloud project created
- [ ] Billing enabled
- [ ] Required APIs enabled
- [ ] Service accounts created
- [ ] Secrets configured in Secret Manager
- [ ] Encryption keys generated
- [ ] Database instance created
- [ ] Cloud Storage bucket created
- [ ] IAM roles configured
- [ ] Audit logging enabled

---

## 🔐 Security Requirements

### Must-Have:
1. ✅ **Encryption at Rest** - Automatic with Cloud SQL/Storage
2. ✅ **Encryption in Transit** - TLS 1.3 (automatic)
3. ✅ **Access Control** - IAM roles, service accounts
4. ✅ **Audit Logging** - Cloud Audit Logs enabled
5. ✅ **Backups** - Automated daily backups

### Application-Level:
- Encryption key stored in Secret Manager (not env vars)
- Database password in Secret Manager
- JWT secret in Secret Manager
- All PHI encrypted before storage (your app handles this)

---

## 📞 Support & Resources

### Google Cloud Support:
- **Sales:** cloud-sales@google.com
- **Documentation:** https://cloud.google.com/security/compliance/hipaa
- **Support Portal:** https://cloud.google.com/support

### HIPAA Resources:
- **HHS HIPAA Guide:** https://www.hhs.gov/hipaa/index.html
- **Google Cloud HIPAA:** https://cloud.google.com/security/compliance/hipaa

---

## ⚠️ Critical Notes

1. **BAA is Required** - Cannot store PHI without signed BAA
2. **Only HIPAA-Eligible Services** - Check list before using any service
3. **Encryption Mandatory** - Both at rest and in transit
4. **Access Control** - Principle of least privilege
5. **Audit Logs** - Must be enabled and reviewed regularly

---

## 🎯 Next Steps

1. **Week 1:** Contact Google Cloud Sales, request BAA
2. **Week 1-2:** Set up Google Cloud project, enable APIs
3. **Week 2:** Configure security (IAM, secrets, encryption)
4. **Week 2-3:** Deploy application to Cloud Run
5. **Week 3:** Test thoroughly
6. **Week 4:** Go live (after BAA is signed)

---

**See `HIPAA_GOOGLE_CLOUD_SETUP.md` for detailed instructions.**

