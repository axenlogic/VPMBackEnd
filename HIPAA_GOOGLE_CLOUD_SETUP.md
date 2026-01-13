# HIPAA-Compliant Google Cloud Setup Guide

**Version:** 1.0  
**Date:** January 2025  
**Purpose:** Step-by-step guide for deploying VPM Backend on HIPAA-compliant Google Cloud infrastructure

---

## 📋 Overview

This guide covers:
1. Understanding HIPAA compliance requirements
2. Setting up Business Associate Agreement (BAA) with Google
3. Configuring HIPAA-eligible Google Cloud services
4. Security and encryption requirements
5. Deployment steps
6. Ongoing compliance monitoring

---

## 🔐 Step 1: Understand HIPAA Requirements

### What is HIPAA?
- **Health Insurance Portability and Accountability Act**
- Protects Protected Health Information (PHI)
- Requires administrative, physical, and technical safeguards

### Key Requirements:
1. **Business Associate Agreement (BAA)** - Required with Google Cloud
2. **Encryption** - Data at rest and in transit
3. **Access Controls** - Role-based access, audit logs
4. **Data Backup** - Secure backups with retention policies
5. **Incident Response** - Breach notification procedures

---

## 🏢 Step 2: Set Up Google Cloud Account

### 2.1 Create/Upgrade Google Cloud Account

1. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/
   - Sign in with Google account

2. **Create New Project:**
   ```
   Project Name: VPM-Backend-Production
   Project ID: vpm-backend-prod (or your preferred ID)
   Organization: [Your Organization]
   ```

3. **Enable Billing:**
   - Go to: Billing → Link a billing account
   - Add payment method (credit card)
   - **Note:** HIPAA compliance doesn't require special billing, but you need a paid account

### 2.2 Enable Required APIs

Enable these APIs in your project:
```bash
# Cloud SQL API (for PostgreSQL)
# Cloud Run API (for containerized apps)
# Cloud Storage API (for file uploads)
# Secret Manager API (for encryption keys)
# Cloud Logging API
# Cloud Monitoring API
```

**Via Console:**
- Go to: APIs & Services → Enable APIs and Services
- Search and enable each API listed above

**Via gcloud CLI:**
```bash
gcloud services enable sqladmin.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com
```

---

## 📝 Step 3: Sign Business Associate Agreement (BAA) with Google

### 3.1 Request BAA

1. **Contact Google Cloud Sales:**
   - Email: cloud-sales@google.com
   - Phone: 1-844-473-8273 (US)
   - Website: https://cloud.google.com/security/compliance/hipaa

2. **Required Information:**
   - Organization name
   - Google Cloud Project ID
   - Contact information
   - Expected PHI volume
   - Use case description

3. **BAA Process:**
   - Google will review your request
   - They'll send BAA document for signature
   - Sign and return the BAA
   - **Important:** BAA must be signed BEFORE storing any PHI

### 3.2 BAA Requirements

- **Covered Services:** Only HIPAA-eligible services can process PHI
- **Compliance Period:** BAA is valid for the duration of your service
- **Renewal:** Review annually

---

## ☁️ Step 4: Configure HIPAA-Eligible Services

### 4.1 Google Cloud Services Eligible for HIPAA

✅ **HIPAA-Eligible Services:**
- **Cloud SQL** (PostgreSQL) - Database
- **Cloud Run** - Container hosting
- **Cloud Storage** - File storage
- **Secret Manager** - Encryption keys
- **Cloud Logging** - Audit logs
- **Cloud Monitoring** - Monitoring
- **Cloud IAM** - Access control
- **VPC** - Network isolation

❌ **NOT HIPAA-Eligible:**
- Google Analytics
- Some AI/ML services (check current list)
- Public APIs without BAA coverage

**Current List:** https://cloud.google.com/security/compliance/hipaa/hipaa-eligible-services

---

## 🔒 Step 5: Set Up Security & Encryption

### 5.1 Enable Encryption

#### Cloud SQL (PostgreSQL)
```bash
# Create Cloud SQL instance with encryption
gcloud sql instances create vpm-postgres-prod \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --database-flags=max_connections=100 \
  --storage-type=SSD \
  --storage-size=20GB \
  --storage-auto-increase \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=4
```

**Enable Encryption:**
- Cloud SQL automatically encrypts data at rest
- Use SSL/TLS for connections (enabled by default)
- Store connection credentials in Secret Manager

#### Cloud Storage (File Uploads)
```bash
# Create bucket with encryption
gsutil mb -p vpm-backend-prod -c STANDARD -l us-central1 gs://vpm-uploads-prod
gsutil versioning set on gs://vpm-uploads-prod
gsutil encryption set gs://vpm-uploads-prod
```

### 5.2 Set Up Secret Manager

```bash
# Create secrets for sensitive data
gcloud secrets create encryption-key \
  --data-file=encryption-key.txt \
  --replication-policy="automatic"

gcloud secrets create db-password \
  --data-file=db-password.txt \
  --replication-policy="automatic"

gcloud secrets create jwt-secret \
  --data-file=jwt-secret.txt \
  --replication-policy="automatic"
```

### 5.3 Configure IAM & Access Control

```bash
# Create service account for Cloud Run
gcloud iam service-accounts create vpm-backend-sa \
  --display-name="VPM Backend Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding vpm-backend-prod \
  --member="serviceAccount:vpm-backend-sa@vpm-backend-prod.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding vpm-backend-prod \
  --member="serviceAccount:vpm-backend-sa@vpm-backend-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding vpm-backend-prod \
  --member="serviceAccount:vpm-backend-sa@vpm-backend-prod.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

## 🚀 Step 6: Deploy Application

### 6.1 Update Dockerfile for Production

Ensure your `Dockerfile` is production-ready:
- Use specific Python version
- Multi-stage build (optional)
- Non-root user
- Health checks

### 6.2 Build and Push Container

```bash
# Set project
gcloud config set project vpm-backend-prod

# Build container
gcloud builds submit --tag gcr.io/vpm-backend-prod/vpm-backend:latest

# Or use Docker directly
docker build -t gcr.io/vpm-backend-prod/vpm-backend:latest .
docker push gcr.io/vpm-backend-prod/vpm-backend:latest
```

### 6.3 Deploy to Cloud Run

```bash
gcloud run deploy vpm-backend \
  --image gcr.io/vpm-backend-prod/vpm-backend:latest \
  --platform managed \
  --region us-central1 \
  --service-account vpm-backend-sa@vpm-backend-prod.iam.gserviceaccount.com \
  --add-cloudsql-instances vpm-backend-prod:us-central1:vpm-postgres-prod \
  --set-env-vars ENVIRONMENT=cloud_run \
  --set-env-vars INSTANCE_CONN_NAME=vpm-backend-prod:us-central1:vpm-postgres-prod \
  --set-env-vars DB_NAME=app_db \
  --set-env-vars DB_USER=app_admin \
  --set-secrets DB_PASS=db-password:latest \
  --set-secrets ENCRYPTION_KEY=encryption-key:latest \
  --set-secrets JWT_SECRET_KEY=jwt-secret:latest \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 1 \
  --max-instances 10 \
  --timeout 300 \
  --no-allow-unauthenticated
```

**Important Settings:**
- `--no-allow-unauthenticated` - Requires authentication
- `--min-instances 1` - Keeps instance warm (reduces cold starts)
- Service account with minimal permissions
- Secrets from Secret Manager (not environment variables)

---

## 🔐 Step 7: Configure Network Security

### 7.1 VPC & Firewall Rules

```bash
# Create VPC network
gcloud compute networks create vpm-vpc \
  --subnet-mode=auto

# Create firewall rule for Cloud SQL
gcloud compute firewall-rules create allow-cloud-sql \
  --network vpm-vpc \
  --allow tcp:5432 \
  --source-ranges 0.0.0.0/0 \
  --target-tags cloud-sql
```

### 7.2 Private IP for Cloud SQL (Recommended)

```bash
# Configure Cloud SQL with private IP
gcloud sql instances patch vpm-postgres-prod \
  --network=vpm-vpc \
  --no-assign-ip
```

---

## 📊 Step 8: Set Up Monitoring & Logging

### 8.1 Enable Audit Logging

```bash
# Enable Cloud Audit Logs
gcloud logging sinks create hipaa-audit-sink \
  bigquery.googleapis.com/projects/vpm-backend-prod/datasets/audit_logs \
  --log-filter='protoPayload.serviceName="cloudsql.googleapis.com" OR protoPayload.serviceName="run.googleapis.com"'
```

### 8.2 Set Up Alerts

Create alerts for:
- Failed authentication attempts
- Unusual database access patterns
- High error rates
- Storage quota warnings

---

## 💰 Step 9: Cost Estimation

### Monthly Cost Estimate (Small-Medium Scale)

| Service | Configuration | Estimated Cost |
|---------|--------------|----------------|
| **Cloud SQL** | db-f1-micro (1 vCPU, 0.6GB RAM) | $7-15/month |
| **Cloud Run** | 1 instance, 512MB RAM | $10-30/month |
| **Cloud Storage** | 100GB storage | $2-5/month |
| **Secret Manager** | 10 secrets | $0.06/month |
| **Cloud Logging** | 50GB logs | $12-25/month |
| **Network Egress** | 100GB | $12-23/month |
| **Total** | | **$43-118/month** |

### Cost Optimization Tips:
1. Use committed use discounts (1-3 year commitments)
2. Right-size instances (start small, scale as needed)
3. Use Cloud SQL scheduled backups (not continuous)
4. Archive old logs to Cloud Storage (cheaper)
5. Monitor and optimize query performance

---

## ✅ Step 10: Compliance Checklist

### Pre-Deployment Checklist

- [ ] BAA signed with Google Cloud
- [ ] All PHI encrypted at rest (Cloud SQL, Cloud Storage)
- [ ] All PHI encrypted in transit (TLS 1.3)
- [ ] Access controls configured (IAM, service accounts)
- [ ] Audit logging enabled
- [ ] Backup strategy implemented
- [ ] Incident response plan documented
- [ ] Security policies documented
- [ ] Staff training completed
- [ ] Penetration testing completed (optional but recommended)

### Ongoing Compliance

- [ ] Monthly security reviews
- [ ] Quarterly access audits
- [ ] Annual BAA review
- [ ] Regular security updates
- [ ] Monitor for security alerts
- [ ] Review audit logs weekly

---

## 📚 Step 11: Additional Resources

### Google Cloud Documentation
- **HIPAA Compliance:** https://cloud.google.com/security/compliance/hipaa
- **BAA Information:** https://cloud.google.com/security/compliance/hipaa/hipaa-eligible-services
- **Cloud SQL Security:** https://cloud.google.com/sql/docs/postgres/security
- **Cloud Run Security:** https://cloud.google.com/run/docs/securing

### Support Contacts
- **Google Cloud Support:** https://cloud.google.com/support
- **Sales Team:** cloud-sales@google.com
- **Security Team:** security@google.com

### Compliance Resources
- **HIPAA Guide:** https://www.hhs.gov/hipaa/index.html
- **Google Cloud Compliance:** https://cloud.google.com/security/compliance

---

## 🚨 Important Notes

### Critical Requirements:

1. **BAA Must Be Signed First**
   - Do NOT store PHI until BAA is signed
   - BAA typically takes 1-2 weeks to process

2. **Only Use HIPAA-Eligible Services**
   - Check current list before using any service
   - Some services may require additional configuration

3. **Encryption is Mandatory**
   - Data at rest: Automatic with Cloud SQL/Storage
   - Data in transit: TLS 1.3 required
   - Application-level: Use your encryption key from Secret Manager

4. **Access Control**
   - Use IAM roles (principle of least privilege)
   - Enable MFA for all admin accounts
   - Regular access reviews

5. **Audit Logging**
   - Enable Cloud Audit Logs
   - Store logs for minimum 6 years (HIPAA requirement)
   - Review logs regularly

---

## 📞 Next Steps

1. **Contact Google Cloud Sales** to initiate BAA process
2. **Set up Google Cloud Project** and enable billing
3. **Enable required APIs** for your services
4. **Configure security** (encryption, IAM, VPC)
5. **Deploy application** to Cloud Run
6. **Test thoroughly** before going live
7. **Monitor and maintain** compliance

---

## 🔄 Deployment Script

Create a deployment script to automate the process:

```bash
#!/bin/bash
# deploy-hipaa.sh

PROJECT_ID="vpm-backend-prod"
REGION="us-central1"
SERVICE_NAME="vpm-backend"

# Set project
gcloud config set project $PROJECT_ID

# Build and push
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

# Deploy
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --platform managed \
  --region $REGION \
  --service-account $SERVICE_NAME-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --add-cloudsql-instances $PROJECT_ID:$REGION:vpm-postgres-prod \
  --set-env-vars ENVIRONMENT=cloud_run \
  --set-secrets DB_PASS=db-password:latest,ENCRYPTION_KEY=encryption-key:latest \
  --no-allow-unauthenticated
```

---

**Status:** Ready for HIPAA-compliant deployment  
**Last Updated:** January 2025

