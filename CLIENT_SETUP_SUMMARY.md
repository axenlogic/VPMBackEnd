# Google Cloud Setup - Client Action Items (Summary)

**For:** Upwork Client  
**Purpose:** Quick reference for required client actions

---

## 🎯 What You Need to Do (4 Simple Steps)

### Step 1: Create Google Cloud Account ⏱️ 30 min
1. Go to: https://console.cloud.google.com/
2. Create project: `VPM-Backend-Production`
3. Enable billing (credit card required)
4. **Cost:** ~$43-118/month (pay-as-you-go)

### Step 2: Sign BAA with Google ⏱️ 1-2 weeks
1. Email: cloud-sales@google.com
2. Request: HIPAA Business Associate Agreement
3. **Important:** Must be signed before storing PHI
4. **Timeline:** 1-2 weeks for processing

### Step 3: Add Developer Access ⏱️ 15 min
1. Go to: IAM & Admin → IAM
2. Click: "Grant Access"
3. Add developer email: `[DEVELOPER_EMAIL]`
4. Role: `Owner` or `Editor`
5. Click: "Save"

### Step 4: Enable APIs ⏱️ 15 min
1. Go to: APIs & Services → Enable APIs
2. Enable:
   - Cloud SQL Admin API
   - Cloud Run Admin API
   - Cloud Storage API
   - Secret Manager API
   - Cloud Build API

---

## ✅ Checklist

Before developer can deploy:

- [ ] Google Cloud project created
- [ ] Billing enabled
- [ ] BAA request submitted to Google
- [ ] BAA signed (wait 1-2 weeks)
- [ ] Developer added to IAM
- [ ] APIs enabled
- [ ] Project ID shared with developer

---

## 📧 Information to Share

Once complete, share with developer:

```
Project ID: _________________
Region: us-central1
BAA Signed: Yes / Pending
Developer Access: Granted
```

---

## 💰 Cost Estimate

**Monthly:** $43-118/month (scales with usage)  
**No upfront fees** - Pay only for what you use

---

## 📞 Need Help?

- **Google Cloud Sales:** cloud-sales@google.com
- **Developer:** [Your Contact Info]

---

**See `CLIENT_REQUIREMENTS_GOOGLE_CLOUD.md` for detailed instructions.**

