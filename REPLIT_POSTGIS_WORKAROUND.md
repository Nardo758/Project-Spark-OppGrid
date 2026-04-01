# 🔧 Replit PostGIS Deployment Blocker - Workarounds

**Issue:** PostGIS schema sync fails on Replit  
**Error:** `ALTER TABLE 'spatial_ref_sys' ADD PRIMARY KEY ('srid')`  
**Status:** Replit engineering aware, no ETA  
**Severity:** 🔴 CRITICAL (blocks deployment)

---

## Problem Statement

When deploying OppGrid to Replit, the PostGIS extension initialization fails during database migration:

```
Error during migration:
  Error in statement: 
    ALTER TABLE spatial_ref_sys ADD PRIMARY KEY (srid)
  
  This table already exists with different schema.
  PostGIS extension may already be partially installed.
```

**Root Cause:** Replit's PostgreSQL has PostGIS pre-installed with schema conflicts. The migration tries to create constraints that already exist.

**Replit Status:** This is a widespread issue. Their engineering team is working on a fix but has no ETA.

---

## ✅ RECOMMENDED SOLUTION: Use External PostgreSQL

**Best for production, scales well**

### Option A: Supabase (Easiest)

**Setup (10 minutes):**
1. Go to https://supabase.com
2. Create free project
3. Copy connection string
4. Add to Replit secrets:

```bash
# In Replit Secrets (.env)
DATABASE_URL=postgresql://[user]:[password]@[host]:[port]/[database]?sslmode=require
```

**Pros:**
- ✅ Free tier generous (500MB database)
- ✅ Automatic backups
- ✅ Full PostGIS support
- ✅ Easy to scale
- ✅ Same region as Replit (low latency)

**Cons:**
- External service dependency
- May have slight latency

**Files to Update:**
```
backend/.env
  → DATABASE_URL=your_supabase_url
```

**Cost:** Free tier covers most use cases

---

### Option B: Railway

**Setup (10 minutes):**
1. Go to https://railway.app
2. Create PostgreSQL database
3. Copy connection string
4. Add to Replit

**Pros:**
- ✅ $5/month free credit
- ✅ Full PostGIS support
- ✅ Easy integrations
- ✅ Good performance

**Cost:** Free tier + $5 credit = enough for testing

---

### Option C: Render

**Setup (10 minutes):**
1. Go to https://render.com
2. Create PostgreSQL database
3. Copy connection string
4. Add to Replit

**Pros:**
- ✅ PostgreSQL with PostGIS included
- ✅ Free tier available
- ✅ Easy Replit integration

**Cost:** Free tier limited, ~$15/month for production

---

## 🔄 TEMPORARY SOLUTION: Use SQLite Locally

**Good for development, not production**

### Setup (15 minutes)

**Step 1: Update database config**

```python
# backend/app/db/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Check if on Replit
ON_REPLIT = os.getenv('REPLIT_DB_URL') is not None

# Use SQLite if on Replit, PostgreSQL otherwise
if ON_REPLIT:
    DATABASE_URL = "sqlite:///./oppgrid.db"
else:
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://...')

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 2: Skip PostGIS models**

```python
# backend/app/models/google_maps_business.py

from geoalchemy2 import Geometry
import os

ON_REPLIT = os.getenv('REPLIT_DB_URL') is not None

if not ON_REPLIT:
    # PostGIS columns (PostgreSQL only)
    location = Column(Geometry('POINT'))
else:
    # SQLite fallback
    location = Column(String)  # Store as WKT string
```

**Step 3: Run migrations**

```bash
# Skip spatial features
alembic upgrade head
```

**Pros:**
- ✅ Works immediately
- ✅ No external service
- ✅ Good for development

**Cons:**
- ❌ No spatial queries
- ❌ No geospatial features
- ❌ SQLite limited to 1 user

---

## 🚀 ADVANCED SOLUTION: Disable PostGIS Schema Sync

**If you want to keep PostgreSQL on Replit without PostGIS**

### Step 1: Skip PostGIS initialization

```python
# backend/alembic/env.py

# Add this function
def skip_postgis(revision, op, context):
    """Skip PostGIS-specific operations on Replit"""
    import os
    if os.getenv('REPLIT_DB_URL'):
        return True
    return False

# In upgrade/downgrade functions
if not skip_postgis(None, None, None):
    # Only run on non-Replit
    pass
```

### Step 2: Remove PostGIS from models

```python
# Remove all Geometry columns from models
# Or make them optional/conditional
```

### Step 3: Update migrations

```bash
# Create new migration that skips PostGIS
alembic revision --autogenerate -m "skip postgis on replit"
```

**Pros:**
- ✅ Keep Replit PostgreSQL
- ✅ No external service

**Cons:**
- ❌ No PostGIS features
- ❌ Complex conditional logic

---

## 📋 IMPLEMENTATION PLAN

### Phase 1: Immediate (Use SQLite)
**Timeline:** Now  
**Effort:** 1-2 hours

1. Update database config to detect Replit
2. Switch to SQLite on Replit
3. Remove PostGIS imports from models
4. Test locally and on Replit
5. Deploy to Replit (should work)

**Result:** OppGrid runs on Replit, no spatial features

### Phase 2: Production Ready (Add Supabase)
**Timeline:** After Phase 1  
**Effort:** 30 minutes

1. Create Supabase project
2. Add DATABASE_URL to Replit secrets
3. Update code to use external DB
4. Run migrations against Supabase
5. Deploy to Replit with full PostGIS support

**Result:** OppGrid fully functional on Replit + external DB

### Phase 3: Monitor Replit Fix
**Timeline:** Ongoing  
**Action:** Check Replit status page monthly

If Replit fixes PostGIS, switch back to Replit PostgreSQL.

---

## 🎯 RECOMMENDED PATH (Leon's choice)

**I recommend: Phase 1 (SQLite) immediately, then Phase 2 (Supabase)**

**Why:**
1. **SQLite** gets you deploying NOW
2. **Supabase** gives you production-ready setup
3. **GIS features** can be added later if needed
4. **Cost:** Free tier covers your needs
5. **No blocker:** You can keep building

**Timeline:**
- SQLite setup: 1-2 hours (today)
- Deploy to Replit: ✅ Works
- Supabase setup: 30 mins (later this week)
- Switch to external DB: ✅ Full features

---

## 🔍 DETAILED IMPLEMENTATION (SQLite Path)

### File 1: Update Database Config

**File:** `backend/app/db/database.py`

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Detect if running on Replit
IS_REPLIT = 'REPLIT_DB_URL' in os.environ

# Use SQLite on Replit, PostgreSQL elsewhere
if IS_REPLIT:
    DATABASE_URL = "sqlite:///./oppgrid.db"
    # SQLite needs special config
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://user:password@localhost/oppgrid'
    )
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### File 2: Skip PostGIS Models

**File:** `backend/app/models/google_maps_business.py`

```python
import os
from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.orm import declarative_base

IS_REPLIT = 'REPLIT_DB_URL' in os.environ

Base = declarative_base()

class GoogleMapsBusiness(Base):
    __tablename__ = "google_maps_businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    address = Column(String)
    city = Column(String, index=True)
    state = Column(String)
    
    # Store location as string on Replit (no PostGIS)
    if not IS_REPLIT:
        # PostgreSQL with PostGIS
        try:
            from geoalchemy2 import Geometry
            location = Column(Geometry('POINT', srid=4326))
        except:
            latitude = Column(Float)
            longitude = Column(Float)
    else:
        # SQLite fallback
        latitude = Column(Float)
        longitude = Column(Float)
    
    # Rest of fields...
```

### File 3: Update Requirements

**File:** `backend/requirements.txt`

```
# Make PostGIS optional
geoalchemy2>=0.14.0; python_version>='3.8'  # Optional for geo features
```

### File 4: Environment Config

**File:** `backend/.env`

```bash
# Auto-detected on Replit (SQLite)
# Override if needed:
DATABASE_URL=sqlite:///./oppgrid.db

# For production with Supabase:
# DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres
```

---

## ✅ TESTING CHECKLIST

### Local Testing
- [ ] `python -c "from app.db.database import engine; print(engine.url)"`
  - Should show `sqlite:///./oppgrid.db`
- [ ] `alembic upgrade head` succeeds
- [ ] Create test user: `python scripts/create_user.py test@test.com`
- [ ] Test API: `curl http://localhost:8000/api/v1/users/me`

### Replit Testing
- [ ] Push code to GitHub
- [ ] Replit pulls and redeploys
- [ ] Check Replit console for errors
- [ ] Test API endpoint in Replit shell
- [ ] Database file created: `ls -la oppgrid.db`

### Supabase Testing (Later)
- [ ] Update DATABASE_URL in Replit secrets
- [ ] Run migrations: `alembic upgrade head`
- [ ] Create test data
- [ ] Query from Replit works

---

## 📞 NEXT STEPS

1. **Choose path:** SQLite now, or Supabase now?
2. **Update files:** Copy code snippets above
3. **Test locally:** Verify SQLite works
4. **Deploy to Replit:** Should succeed
5. **Monitor:** Check Replit status for PostGIS fix

---

## 📚 REFERENCES

- Replit Support: PostGIS schema sync issue (widespread, no ETA)
- Supabase Docs: https://supabase.com/docs/guides/database
- SQLAlchemy SQLite: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
- OppGrid Database Config: `backend/app/db/database.py`

---

**Status:** 🔴 BLOCKER identified, ✅ Workarounds documented, ready for implementation

**Recommendation:** Implement Phase 1 (SQLite) today, Phase 2 (Supabase) later this week.
