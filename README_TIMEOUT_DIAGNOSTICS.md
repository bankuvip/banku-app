# BankU Timeout Diagnostic Tools

These tools will help you identify **exactly** what is causing the timeout issues on banku.vip.

## 🎯 Problem Description

The app works fine after restart, but after some time, users get:
```
Request Timeout
This request takes too long to process, it is timed out by the server.
```

## 🔍 Diagnostic Tools

### 1. Quick Check (Run this FIRST)

```bash
python quick_timeout_check.py
```

**What it does:**
- Instantly checks connection pool status
- Shows active database connections
- Identifies long-running queries
- Takes < 5 seconds

**When to use:** Run this NOW on your live server to see current status

---

### 2. Comprehensive Diagnostics (Run for detailed analysis)

```bash
# Single check
python diagnose_timeout_issue.py --mode single

# Monitor for 10 minutes (recommended)
python diagnose_timeout_issue.py --mode monitor --duration 600 --interval 60

# Monitor for 30 minutes (for slow leaks)
python diagnose_timeout_issue.py --mode monitor --duration 1800 --interval 60
```

**What it does:**
- Monitors connection pool usage over time
- Detects increasing memory usage
- Tracks thread count
- Identifies session leaks
- Saves detailed JSON report

**Output:** Creates `timeout_diagnostics_YYYYMMDD_HHMMSS.json` with full data

**When to use:** 
- After quick check shows issues
- To understand patterns over time
- To prove what's causing the problem

---

### 3. Live Connection Monitor (Real-time watching)

```bash
python monitor_live_connections.py
```

**What it does:**
- Shows connection pool in REAL-TIME
- Updates every 3 seconds
- Shows which queries are running
- Alerts when pool fills up

**When to use:**
- While using the app to see what causes leaks
- To identify which routes leak connections
- To watch the problem happen live

---

## 📊 Understanding the Results

### Healthy System:
```
Pool Usage: 20-40%
Active Connections: 2-5
Long-running Queries: 0
Memory: Stable
```

### Unhealthy System (causing timeouts):
```
Pool Usage: >80% 🔴
Active Connections: >20
Long-running Queries: >5
Memory: Increasing over time
```

---

## 🚨 Common Issues & What They Mean

### Issue 1: Pool Usage >80%
**Problem:** Database sessions are not being closed
**Cause:** Background tasks or routes with unclosed sessions
**Fix Needed:** Add `db.session.remove()` after operations

### Issue 2: Sleeping Connections >50
**Problem:** Old connections not released
**Cause:** Connection pool not recycling properly
**Fix Needed:** Adjust pool settings, add timeout

### Issue 3: Memory Increasing Over Time
**Problem:** Memory leak in background tasks
**Cause:** Objects not being garbage collected
**Fix Needed:** Review background threads, cleanup

### Issue 4: Thread Count Increasing
**Problem:** Threads not stopping properly
**Cause:** Daemon threads or scheduled tasks
**Fix Needed:** Proper thread cleanup on shutdown

---

## 🎬 Recommended Diagnostic Flow

### Step 1: Quick Assessment
```bash
python quick_timeout_check.py
```
→ This tells you if there's a problem NOW

### Step 2: Identify the Pattern
```bash
python diagnose_timeout_issue.py --mode monitor --duration 600 --interval 30
```
→ This runs for 10 minutes to see how problem develops

### Step 3: Watch It Live (Optional)
```bash
python monitor_live_connections.py
```
→ Watch in real-time while you use the app

### Step 4: Analyze Results
- Check the JSON file created by step 2
- Look for increasing trends
- Identify which alerts fired most often

---

## 📝 What to Send Me

After running the diagnostics, send me:

1. **Output from quick check:**
   ```bash
   python quick_timeout_check.py > quick_check_output.txt
   ```

2. **The JSON file from monitoring:**
   ```bash
   python diagnose_timeout_issue.py --mode monitor --duration 300
   # This creates timeout_diagnostics_YYYYMMDD_HHMMSS.json
   ```

3. **Any alerts or warnings you see**

With this data, I can create a **targeted fix** for your exact issue.

---

## 🔧 Expected Findings

Based on your code, I expect to find:

1. **Advanced Data Collector** - Running scheduled tasks without proper session cleanup
2. **Health Monitor** - Background thread may be holding sessions
3. **Route handlers** - Some routes not closing sessions properly
4. **Connection pool** - Pool size too small or timeout too long

The diagnostics will tell us **exactly** which one(s) are the problem.

---

## ⏱️ How Long to Run?

- **Quick check:** 5 seconds
- **If app is currently working well:** Monitor for 30-60 minutes
- **If app is currently slow:** Monitor for 5-10 minutes
- **If app is currently timing out:** Run quick check only

---

## 🎯 Next Steps

1. Run `python quick_timeout_check.py` NOW
2. Based on results, run monitoring for 10-30 minutes
3. Send me the results
4. I'll create the precise fix needed

**No guessing - we'll have data proving what's wrong!**

