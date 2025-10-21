# BankU App Hanging - Diagnostic & Fix Guide

## Problem Description

Your app at **banku.vip** is loading but not opening, and you need to restart the server to make it work again. This is a classic symptom of **database connection pool exhaustion**.

## What's Happening

When your Flask app runs, it creates a pool of database connections (currently 10 connections). Every time a request comes in, it uses one connection. The problem is:

1. **Connections not being released** - After handling a request, the connection isn't properly returned to the pool
2. **Pool gets exhausted** - Eventually all 10 connections are "checked out" but not returned
3. **New requests hang** - New requests wait forever for a free connection that never comes
4. **App appears frozen** - The app is technically running, but can't process any requests

## Root Cause (Most Likely)

Your `app.py` is **missing critical session cleanup code**. Looking at your code:

```python
# You have error handlers and routes, but NO teardown handlers
# This means database sessions are never properly closed!
```

## Diagnostic Tools Provided

### 1. **diagnose_app.py** - Remote Diagnostic (Run from anywhere)

Tests your app from the outside to identify issues.

**Usage:**
```bash
python diagnose_app.py
# Or specify URL:
python diagnose_app.py https://banku.vip
```

**What it tests:**
- ✓ Basic connectivity
- ✓ Health endpoint
- ✓ Concurrent request handling
- ✓ Database endpoint performance
- ✓ Memory leak detection
- ✓ Long request timeout

**When to use:** Run this when the app is hanging to see what's wrong

### 2. **server_diagnostics.py** - Server-Side Diagnostic (Run on server)

Checks internal server state, database connections, and resources.

**Usage (on server):**
```bash
python server_diagnostics.py
```

**What it checks:**
- ✓ CPU, Memory, Disk usage
- ✓ **Database connection pool status** ⚠️ MOST IMPORTANT
- ✓ Long-running queries
- ✓ Database locks
- ✓ Thread count
- ✓ Open file descriptors

**When to use:** Run this when app is hanging to see internal state

### 3. **apply_session_fix.py** - Automatic Fix (Run once)

Automatically adds the missing session cleanup code to your `app.py`.

**Usage:**
```bash
python apply_session_fix.py
```

**What it does:**
- Creates backup of `app.py`
- Adds `@app.teardown_appcontext` handler
- Adds `@app.teardown_request` handler
- Increases connection pool size
- These ensure database sessions are properly closed

**When to use:** Run this ONCE to fix the problem

## Quick Fix Instructions

### Option 1: Automatic Fix (Recommended)

```bash
# 1. Run the fix script
python apply_session_fix.py

# 2. Restart your app
# Stop current process, then:
python app.py
# Or restart your web server (Apache/Nginx)

# 3. Monitor
python server_diagnostics.py
```

### Option 2: Manual Fix

Add this code to your `app.py` (after error handlers, before routes):

```python
# Database session cleanup (CRITICAL FIX FOR APP HANGING)
@app.teardown_appcontext
def shutdown_session(exception=None):
    """
    Ensure database sessions are properly closed after each request.
    This prevents connection pool exhaustion which causes app hanging.
    """
    try:
        db.session.remove()
    except Exception as e:
        logger.error(f"Error removing session in teardown_appcontext: {e}")

@app.teardown_request
def teardown_request(exception=None):
    """
    Close database connections and rollback on errors.
    This ensures no connections are left open.
    """
    if exception:
        try:
            db.session.rollback()
            logger.warning(f"Session rolled back due to exception: {exception}")
        except Exception as e:
            logger.error(f"Error rolling back session: {e}")
    
    try:
        db.session.close()
    except Exception as e:
        logger.error(f"Error closing session in teardown_request: {e}")
```

Also increase pool size in `app.py`:

```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'poolclass': QueuePool,
    'pool_size': 20,        # Increased from 10
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 40,     # Increased from 20
    'pool_timeout': 30
}
```

Then restart your app.

## Verification

After applying the fix, verify it's working:

```bash
# 1. Check from remote
python diagnose_app.py

# 2. Check on server
python server_diagnostics.py

# 3. Monitor connection pool
# Visit: https://banku.vip/health
# Look for database pool status
```

## Emergency Recovery (If App is Currently Hung)

### Step 1: Kill Hung MySQL Connections

```bash
# Connect to MySQL
mysql -u root -p

# Check for hung connections
SHOW PROCESSLIST;

# Kill sleeping connections over 5 minutes old
SELECT CONCAT('KILL ', id, ';') 
FROM information_schema.PROCESSLIST 
WHERE command = 'Sleep' 
AND time > 300;

# Copy the KILL commands and run them
```

### Step 2: Restart Application

```bash
# Find the process
ps aux | grep python

# Kill it
kill -9 <process_id>

# Restart
python app.py
# Or restart web server
```

### Step 3: Apply Fix

```bash
python apply_session_fix.py
```

## Monitoring Going Forward

### Monitor Connection Pool Health

Add this to your monitoring (cron job or systemd timer):

```bash
# Every 5 minutes, check health
*/5 * * * * curl https://banku.vip/health | grep -i pool

# Or run diagnostic
*/15 * * * * cd /path/to/app && python server_diagnostics.py
```

### Watch for Warning Signs

1. **Slow response times** - First sign of pool pressure
2. **Increasing memory usage** - Session leak
3. **High connection count** - Pool getting full

## Common Issues & Solutions

### Issue: Still Hanging After Fix

**Possible causes:**
1. Didn't restart app properly
2. Other code keeping connections open
3. Long-running background tasks

**Solution:**
```bash
# Run full diagnostic
python server_diagnostics.py

# Check for:
# - Are teardown handlers actually running?
# - Any long queries in SHOW PROCESSLIST?
# - Memory increasing over time?
```

### Issue: High Memory Usage

**Cause:** Sessions accumulating in memory

**Solution:**
```python
# Add to app configuration
app.config['SQLALCHEMY_ENGINE_OPTIONS']['pool_pre_ping'] = True
app.config['SQLALCHEMY_ENGINE_OPTIONS']['pool_recycle'] = 1800  # Recycle every 30 min
```

### Issue: Slow Queries

**Cause:** Database queries not optimized

**Solution:**
```bash
# Enable query logging in app.py
app.config['SQLALCHEMY_ECHO'] = True  # Shows all queries

# Find slow queries
# Add indexes where needed
```

## Advanced Diagnostics

### Enable Detailed Logging

Add to `app.py`:

```python
# Detailed database logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
```

### Monitor Pool in Real-Time

```python
# Add to /health endpoint or create new endpoint
@app.route('/pool-status')
def pool_status():
    pool = db.engine.pool
    return jsonify({
        'size': pool.size(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'checked_in': pool.checkedin()
    })
```

## Files Created

1. **diagnose_app.py** - Remote diagnostic tool
2. **server_diagnostics.py** - Server-side diagnostic tool
3. **apply_session_fix.py** - Automatic fix script
4. **DIAGNOSTIC_GUIDE.md** - This guide

## Support

If issues persist after applying fixes:

1. Run both diagnostic tools
2. Check the generated JSON reports
3. Review database logs
4. Check web server logs (Apache/Nginx)
5. Review recent code changes

## Summary

**The Problem:** Database connections not being released → Pool exhausted → App hangs

**The Solution:** Add proper session cleanup handlers → Connections released → No more hanging

**Quick Fix:** Run `python apply_session_fix.py`, restart app, problem solved!

---

**Next Steps:**
1. ✓ Run `python apply_session_fix.py`
2. ✓ Restart your application
3. ✓ Test with `python diagnose_app.py`
4. ✓ Monitor with `python server_diagnostics.py`
5. ✓ Enjoy your stable app! 🎉


