# 🔍 CONSULTANT STUDIO DIAGNOSTIC GUIDE

## Step 1: Verify Environment Variables

```bash
# Check if .env file exists
cd backend
ls -la .env

# Verify keys are set (don't print them, just check)
grep -c "DEEPSEEK_API_KEY=sk_live" .env && echo "✅ DEEPSEEK_API_KEY appears to be set" || echo "❌ DEEPSEEK_API_KEY not set"
grep -c "ANTHROPIC_API_KEY=sk-ant" .env && echo "✅ ANTHROPIC_API_KEY appears to be set" || echo "❌ ANTHROPIC_API_KEY not set"
```

---

## Step 2: Check Current Implementation

### What's the actual flow?

```
Frontend (ConsultantStudio.tsx)
    ↓ (mutates validate-idea)
Backend (consultant.py route)
    ↓ (calls service)
ConsultantStudioService.validate_idea()
    ↓ (calls parallel tasks)
    ├→ _deepseek_pattern_analysis_parallel()
    │   ↓ (calls orchestrator)
    │   ai_orchestrator.process_request(OPPORTUNITY_VALIDATION)
    │       ↓ (calls)
    │       _call_deepseek() OR _call_claude() (fallback)
    │
    ├→ _claude_viability_report_parallel()
    │   ↓ (calls orchestrator)
    │   ai_orchestrator.process_request()
    │
    └→ _find_similar_opportunities()
        ↓ (queries database)
        Returns Opportunity[] from DB
```

### Known Issues:

1. **API Keys Not Loaded**
   - .env file is created but empty (placeholder values)
   - Need: DEEPSEEK_API_KEY, ANTHROPIC_API_KEY
   - Impact: DeepSeek fails → falls back to Claude
   - If Claude also missing → returns empty results

2. **Timeout Issues**
   - Current timeout: 30 seconds for AI calls
   - DeepSeek + Claude can take 20-40 seconds
   - Solution: Increase timeout to 60 seconds

3. **Error Handling**
   - Service catches exceptions
   - Returns empty dict `{}` on failure
   - Frontend doesn't know request failed (silent failure)
   - Shows default 50/50 scores

4. **UI Not Showing Errors**
   - ConsultantStudio.tsx has error states defined
   - But errors aren't being captured properly
   - Missing: Loading state improvements

---

## Step 3: IMMEDIATE FIXES

### Fix 1: Add Real API Keys

```bash
# Edit backend/.env
nano backend/.env

# Find these lines and REPLACE with real keys:
DEEPSEEK_API_KEY=sk_live_YOUR_KEY_HERE
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE

# Save and exit (Ctrl+X, Y, Enter in nano)
```

### Fix 2: Increase Timeouts

**File:** `backend/app/services/ai_orchestrator.py`

```python
# Line 10 - CHANGE THIS:
AI_CALL_TIMEOUT_SECONDS = 30

# TO THIS:
AI_CALL_TIMEOUT_SECONDS = 60  # Increased for long-running AI calls
```

**File:** `backend/app/routers/consultant.py`

```python
# Line ~168 - CHANGE THIS:
timeout=40.0

# TO THIS:
timeout=60.0  # Match AI orchestrator timeout
```

### Fix 3: Improve Error Logging

**File:** `backend/app/services/consultant_studio.py`

Around line 180, ADD logging:

```python
if isinstance(viability_report, Exception):
    logger.warning(f"Claude viability report failed: {viability_report}")
    logger.error(f"Claude error details: {str(viability_report)}")  # ADD THIS
    viability_report = {}

if isinstance(pattern_analysis, Exception):
    logger.warning(f"DeepSeek pattern analysis failed: {pattern_analysis}")
    logger.error(f"DeepSeek error details: {str(pattern_analysis)}")  # ADD THIS
    pattern_analysis = {}
```

### Fix 4: Improve Frontend Error Handling

**File:** `frontend/src/pages/build/ConsultantStudio.tsx`

Around line 180 (validateMutation), ADD error handling:

```typescript
// FIND THIS:
onSuccess: (data) => setValidateResult(data),

// CHANGE TO THIS:
onSuccess: (data) => {
  if (!data.success) {
    setValidateError(data.error || "Analysis failed. Please try again.");
  } else {
    setValidateResult(data);
  }
},
onError: (err: Error) => {
  console.error("Validate mutation error:", err);
  setValidateError(err.message || "Network error. Check browser console.");
}
```

---

## Step 4: Test Each Endpoint

### Test 1: Validate Idea (Simplest)

```bash
# Start backend in one terminal:
cd backend
python3 main.py

# In another terminal, wait 10 seconds then run:
sleep 10

# Test the endpoint:
curl -v -X POST http://localhost:8000/api/v1/consultant/validate-idea \
  -H "Content-Type: application/json" \
  -d '{"idea_description": "A coffee subscription service for offices"}'
```

**Expected Response:**
```json
{
  "success": true,
  "idea_description": "A coffee subscription service for offices",
  "recommendation": "online" or "physical" or "hybrid",
  "online_score": 60,
  "physical_score": 40,
  "viability_report": {...},
  "pattern_analysis": {...},
  "processing_time_ms": 2500
}
```

**If you get error, check:**
- [ ] Backend is running (ps aux | grep main.py)
- [ ] API key is set (grep DEEPSEEK_API_KEY backend/.env)
- [ ] Check logs: `tail -f backend/logs/app.log`
- [ ] Check timeout: Did request take >60 seconds?

### Test 2: Search Ideas

```bash
curl -X POST http://localhost:8000/api/v1/consultant/search-ideas \
  -H "Content-Type: application/json" \
  -d '{"query": "coffee business"}'
```

**Expected:** Array of opportunity objects

### Test 3: Identify Location

```bash
curl -X POST http://localhost:8000/api/v1/consultant/identify-location \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Miami, FL",
    "business_description": "coffee shop with drive-thru"
  }'
```

**Expected:** Market analysis for Miami

### Test 4: Clone Success

```bash
curl -X POST http://localhost:8000/api/v1/consultant/clone-success \
  -H "Content-Type: application/json" \
  -d '{
    "business_name": "Starbucks",
    "business_address": "123 Main St, New York, NY",
    "target_city": "Miami, FL"
  }'
```

**Expected:** Similar locations in Miami

---

## Step 5: Frontend Testing

```bash
# Start frontend
cd frontend
npm run dev

# Open http://localhost:5173
# Go to Consultant Studio
# Try "Validate Idea" tab
# Enter: "A coffee subscription service"
# Click "Validate Idea"
# Watch for:
#   ✅ Loading spinner appears
#   ✅ Results appear after 10-30 seconds
#   ✅ Scores are displayed (not 50/50)
#   ❌ Or error message shows
```

---

## Step 6: Debug Checklist

If something is still broken:

- [ ] API keys confirmed in .env file
- [ ] Timeouts increased to 60 seconds
- [ ] Backend restarted after .env changes
- [ ] curl tests all return data (not errors)
- [ ] Browser console shows no CORS errors
- [ ] Network tab shows 200 status (not 500)
- [ ] Response takes 10-30 seconds (not instant 50/50)
- [ ] Logs show which AI service is being called

---

## Step 7: Checking Logs

```bash
# Terminal 1: Start backend with verbose logging
cd backend
PYTHONUNBUFFERED=1 python3 main.py 2>&1 | tee backend.log

# Terminal 2: Trigger request
curl -X POST http://localhost:8000/api/v1/consultant/validate-idea \
  -H "Content-Type: application/json" \
  -d '{"idea_description": "test"}'

# Terminal 1: Look for these log messages:
# ✅ "Processing OPPORTUNITY_VALIDATION request"
# ✅ "DeepSeek call completed successfully" OR "DeepSeek call failed"
# ✅ "Claude call completed successfully" OR "Claude call failed"
# ❌ If you see "API key not found" → KEY IS NOT SET

# Check logs:
tail -100 backend.log | grep -i "deepseek\|claude\|api\|error"
```

---

## Summary: What You Need to Do RIGHT NOW

1. **15 minutes:**
   - [ ] Edit `backend/.env`
   - [ ] Add real API keys for DEEPSEEK and ANTHROPIC
   - [ ] Save file

2. **5 minutes:**
   - [ ] Edit `backend/app/services/ai_orchestrator.py`
   - [ ] Change timeout from 30 to 60 seconds
   - [ ] Save file

3. **5 minutes:**
   - [ ] Edit `backend/app/routers/consultant.py`
   - [ ] Change timeout from 40 to 60 seconds
   - [ ] Save file

4. **20 minutes:**
   - [ ] Start backend: `python3 backend/main.py`
   - [ ] Run curl test
   - [ ] Check if response comes back with real data

5. **10 minutes:**
   - [ ] Test frontend
   - [ ] Try Consultant Studio UI
   - [ ] Verify it works now

**TOTAL TIME: ~55 minutes**

---

**Status:** Ready to implement fixes 🚀