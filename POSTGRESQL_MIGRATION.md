# PostgreSQL Migration Guide

## 🏥 MedicalCare Backend - Database Migration

### Overview

This guide will help you migrate from SQLite to PostgreSQL for the MedicalCare authentication backend.

## 🚀 Quick Migration Steps

### 1. Install PostgreSQL

```bash
# macOS (using Homebrew)
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### 2. Create Database

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE medicalcare_db;

-- Create user (optional)
CREATE USER medicalcare_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE medicalcare_db TO medicalcare_user;

-- Exit
\q
```

### 3. Install Python Dependencies

```bash
# Install PostgreSQL adapter
pip install psycopg2-binary

# Or install all requirements
pip install -r requirements.txt
```

### 4. Update Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your PostgreSQL credentials
DATABASE_URL=postgresql://username:password@localhost:5432/medicalcare_db
```

### 5. Run Migration

```bash
# The application will automatically create tables on first run
cd /Users/qatesting/Documents/medicalCareBackend
source venv/bin/activate
uvicorn app.main:app --reload
```

## 🔧 Configuration Details

### Database URL Format

```
postgresql://username:password@host:port/database_name
```

### Example Configurations

#### Local Development

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/medicalcare_db
```

#### Production (with SSL)

```env
DATABASE_URL=postgresql://user:pass@host:5432/medicalcare_db?sslmode=require
```

#### Docker PostgreSQL

```env
DATABASE_URL=postgresql://postgres:password@db:5432/medicalcare_db
```

## 📊 Data Migration (if you have existing SQLite data)

### Option 1: Fresh Start (Recommended for Development)

- Just run the application - tables will be created automatically
- No data migration needed

### Option 2: Migrate Existing Data

```bash
# Install sqlite3-to-postgresql
pip install sqlite3-to-postgresql

# Export from SQLite
sqlite3 app.db .dump > data.sql

# Import to PostgreSQL (manual process)
# You'll need to modify the SQL file for PostgreSQL compatibility
```

## 🐳 Docker Setup (Optional)

### docker-compose.yml

```yaml
version: "3.8"
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: medicalcare_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:password@db:5432/medicalcare_db
    depends_on:
      - db

volumes:
  postgres_data:
```

## 🔍 Verification

### Test Database Connection

```python
# Test script
from app.db.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print("PostgreSQL version:", result.fetchone()[0])
        print("✅ Database connection successful!")
except Exception as e:
    print("❌ Database connection failed:", e)
```

### Check Tables

```sql
-- Connect to database
psql -U postgres -d medicalcare_db

-- List tables
\dt

-- Check users table
SELECT * FROM users LIMIT 5;
```

## 🚨 Troubleshooting

### Common Issues

1. **Connection Refused**

   - Check if PostgreSQL is running: `brew services list | grep postgresql`
   - Verify port 5432 is not blocked

2. **Authentication Failed**

   - Check username/password in DATABASE_URL
   - Verify user has database permissions

3. **Database Does Not Exist**

   - Create database: `CREATE DATABASE medicalcare_db;`

4. **Permission Denied**
   - Grant permissions: `GRANT ALL PRIVILEGES ON DATABASE medicalcare_db TO your_user;`

## 📈 Performance Benefits

### PostgreSQL vs SQLite

- **Concurrent Users**: PostgreSQL handles multiple users better
- **Data Integrity**: ACID compliance
- **Scalability**: Can handle larger datasets
- **Advanced Features**: JSON support, full-text search, etc.
- **Production Ready**: Enterprise-grade database

## 🔒 Security Considerations

### Production Setup

1. Use strong passwords
2. Enable SSL connections
3. Restrict database access by IP
4. Regular backups
5. Monitor connection logs

### Environment Variables

```env
# Production example
DATABASE_URL=postgresql://prod_user:strong_password@prod_host:5432/medicalcare_db?sslmode=require
```

## 📝 Next Steps

1. ✅ Install PostgreSQL
2. ✅ Update requirements.txt
3. ✅ Configure DATABASE_URL
4. ✅ Test connection
5. ✅ Deploy application
6. ✅ Monitor performance

## 🆘 Support

If you encounter issues:

1. Check PostgreSQL logs
2. Verify connection string format
3. Test with psql command line
4. Check firewall settings
5. Review application logs

---

**Migration Complete!** 🎉
Your MedicalCare backend is now running on PostgreSQL!

