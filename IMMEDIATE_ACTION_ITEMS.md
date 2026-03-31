# 🚀 OPPGRID - IMMEDIATE ACTION ITEMS

**Start Here →**

---

## ⚡ CRITICAL: DO THESE TODAY (1-2 Hours)

### 1. Set Environment Variables

```bash
# Navigate to backend folder
cd backend

# Copy example file
cp .env.example .env

# Edit .env and add these REQUIRED keys:
DEEPSEEK_API_KEY=YOUR_KEY_HERE
ANTHROPIC_API_KEY=YOUR_KEY_HERE
SERPAPI_KEY=YOUR_KEY_HERE
STRIPE_SECRET_KEY=YOUR_KEY_HERE
STRIPE_PUBLIC_KEY=YOUR_KEY_HERE
DATABASE_URL=postgresql://user:password@localhost/oppgrid

# Verify it worked
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ Keys loaded!' if os.getenv('DEEPSEEK_API_KEY') else '❌ Missing keys')"
```

**Where to Get Keys:**
- **DEEPSEEK_API_KEY:** https://platform.deepseek.com/api_keys
- **ANTHROPIC_API_KEY:** https://console.anthropic.com/ (Claude API)
- **SERPAPI_KEY:** https://serpapi.com/ (Google search API)
- **STRIPE Keys:** https://dashboard.stripe.com/apikeys

---

### 2. Test Consultant Studio Endpoints

```bash
# Start backend server
python backend/main.py

# In another terminal, test the APIs:

# Test 1: Validate Idea
curl -X POST http://localhost:8000/api/v1/consultant/validate-idea \
  -H "Content-Type: application/json" \
  -d '{
    "idea_description": "A subscription service that delivers locally-roasted coffee beans to offices in downtown areas"
  }'

# Test 2: Search Ideas
curl -X POST http://localhost:8000/api/v1/consultant/search-ideas \
  -H "Content-Type: application/json" \
  -d '{"query": "coffee subscription"}'

# Test 3: Identify Location
curl -X POST http://localhost:8000/api/v1/consultant/identify-location \
  -H "Content-Type: application/json" \
  -d '{"city": "Miami, FL", "business_description": "coffee shop"}'

# Test 4: Clone Success
curl -X POST http://localhost:8000/api/v1/consultant/clone-success \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Starbucks",
    "business_address": "123 Main St, New York, NY",
    "target_city": "Miami"
  }'
```

**What Should Happen:**
- ✅ All 4 endpoints return data (not errors)
- ✅ Validate idea returns online_score + physical_score
- ✅ Search ideas returns opportunities array
- ✅ Identify location returns market_report
- ✅ Clone success returns matching_locations

**If you get errors:**
- Check API keys are set correctly
- Check backend is running on port 8000
- Check logs for timeout errors

---

### 3. Check Consultant Studio UI

```bash
# Start frontend
cd frontend
npm run dev

# Open browser to:
http://localhost:5173

# Navigate to: Consultant Studio → Try "Validate Idea" tab
# You should see the UI working properly now (with API keys)
```

---

## 📋 BLOCKING ISSUES CHECKLIST

Before moving to Phase 2, verify:

- [ ] DEEPSEEK_API_KEY is set and valid
- [ ] ANTHROPIC_API_KEY is set and valid
- [ ] All 4 Consultant endpoints return 200 status
- [ ] ConsultantStudio.tsx loads without errors
- [ ] At least one API call works (validate-idea, search-ideas, etc.)

---

## 🎯 IF YOU GET STUCK

### Common Issues & Fixes:

**Issue:** `TypeError: DEEPSEEK_API_KEY is None`
**Fix:** 
```bash
# Check .env file exists
ls -la backend/.env

# Reload environment:
source backend/.env
echo $DEEPSEEK_API_KEY  # Should print your key
```

**Issue:** `Connection refused: localhost:8000`
**Fix:**
```bash
# Make sure backend is running
ps aux | grep python
# Kill any old processes: kill -9 <PID>
# Restart: python backend/main.py
```

**Issue:** `Timeout after 30 seconds`
**Fix:**
```bash
# Check network connection to API
curl https://api.deepseek.com/health
# If fails, check internet connection or firewall

# Increase timeout in code:
# backend/app/services/ai_orchestrator.py
# Change AI_CALL_TIMEOUT_SECONDS = 30 → 60
```

**Issue:** `CORS error in frontend`
**Fix:**
```bash
# Backend should already have CORS enabled
# If not, check backend/app/main.py has:
# CORSMiddleware configuration
```

---

## 📊 QUICK STATUS REFERENCE

| Component | Status | Action |
|-----------|--------|--------|
| **Env Variables** | 🔴 Missing | SET THEM NOW |
| **Consultant Studio** | 🔴 Broken | Test APIs after env setup |
| **Database** | ✅ Ready | No action needed |
| **Auth System** | ✅ Complete | No action needed |
| **Stripe** | ⚠️ Partial | Do Phase 2 |
| **Scrapers** | ⚠️ Stub | Do Phase 3 |

---

## 🗺️ ROADMAP

**Today (1-2 hrs):**
1. Set env variables ✅
2. Test all 4 consultant endpoints ✅
3. Verify Consultant Studio UI works ✅

**This Week (4-6 hrs):**
1. Fix any timeout errors
2. Improve error messages
3. Complete Stripe setup

**Next Week (8-12 hrs):**
1. Activate Google scraper
2. Wire expert marketplace
3. Complete leads marketplace

**Following Week (4-8 hrs):**
1. Production optimization
2. Security audit
3. Deployment preparation

---

## 💡 PRO TIPS

1. **Save API keys in a secure password manager** (1Password, LastPass, etc.)
   - Don't commit to git
   - Don't share in Slack

2. **Use Postman to test APIs**
   - Easier than curl commands
   - Can save requests for future testing
   - Can see response times

3. **Check logs for debugging**
   ```bash
   # Backend logs
   tail -f backend/logs/app.log
   
   # Frontend console
   # Open browser DevTools → Console tab
   ```

4. **Keep OPPGRID_PROJECT_TRACKER.md updated**
   - Check off completed tasks
   - Add notes on blockers
   - Update weekly

---

## 🚀 NEXT MILESTONE

Once you complete these 3 steps (env variables, API tests, UI test), you're ready for:

**Phase 2: Stripe Integration**
- File: `OPPGRID_PROJECT_TRACKER.md` Section "PHASE 2"
- Estimated time: 2-3 days
- Effort: Medium

---

**Questions?** Check the full tracker: `OPPGRID_PROJECT_TRACKER.md`

**Last Updated:** 2026-03-31
**Status:** READY TO START