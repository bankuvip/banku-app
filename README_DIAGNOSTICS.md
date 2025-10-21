# BankU Diagnostic & Fix Tools

## Overview

Complete diagnostic and fix toolkit for resolving the app hanging issue at banku.vip.

## 📁 Files Created

| File | Purpose | When to Use |
|------|---------|-------------|
| `QUICK_FIX.md` | ⚡ Fast 3-step solution | Start here! |
| `DIAGNOSTIC_GUIDE.md` | 📖 Comprehensive guide | Detailed understanding |
| `diagnose_app.py` | 🌐 Remote testing | Test from anywhere |
| `server_diagnostics.py` | 🖥️ Server-side checks | Run on your server |
| `apply_session_fix.py` | 🔧 Automatic fix | Apply the solution |
| `monitor_health.py` | 📊 Health monitoring | Regular checks |
| `diagnose.bat` | 🪟 Windows menu | Easy access (Windows) |

## 🚀 Quick Start (3 Minutes)

### If App is Currently Working

```bash
# 1. Apply the fix
python apply_session_fix.py

# 2. Restart your app
# (Ctrl+C then python app.py, or restart web server)

# 3. Verify
python diagnose_app.py
```

### If App is Currently Hung

```bash
# 1. Kill the app process
taskkill /F /IM python.exe

# 2. Apply the fix
python apply_session_fix.py

# 3. Restart
python app.py

# 4. Verify
python diagnose_app.py
```

## 🔍 Diagnostic Tools

### Remote Diagnostic (Run from Anywhere)

```bash
python diagnose_app.py [optional_url]
```

**Tests:**
- Basic connectivity
- Health endpoint response
- Concurrent request handling
- Database endpoint performance
- Memory leak detection
- Long request timeouts

**Output:** Colored console output + JSON report

### Server Diagnostic (Run on Server)

```bash
python server_diagnostics.py
```

**Tests:**
- CPU, Memory, Disk usage
- **Database connection pool status** ⚠️
- Long-running queries
- Database locks
- Thread/process count
- Application logs

**Output:** Console report + JSON file + Recommended fixes

### Health Monitor (Regular Monitoring)

```bash
# One-time check
python monitor_health.py

# Quiet mode (for cron)
python monitor_health.py --quiet

# Custom URL
python monitor_health.py --url https://yourapp.com
```

**Output:** Console status + health_monitor.log + Alerts

## 🔧 Fix Tool

### Automatic Fix

```bash
python apply_session_fix.py
```

**What it does:**
1. Creates backup of app.py
2. Adds `@app.teardown_appcontext` handler
3. Adds `@app.teardown_request` handler
4. Increases connection pool size (10→20)
5. Increases max overflow (20→40)

**Safe:** Creates backup before modifying

## 🪟 Windows Menu (Easy Mode)

```cmd
diagnose.bat
```

Interactive menu with all tools accessible via number selection.

## 📊 Understanding the Problem

### What Happens

```
Request comes in
    ↓
App gets DB connection from pool (1/10 used)
    ↓
Handles request
    ↓
❌ PROBLEM: Connection NOT returned to pool
    ↓
Eventually: All 10 connections stuck "checked out"
    ↓
New requests wait forever for a connection
    ↓
🔴 APP APPEARS HUNG
```

### The Fix

```python
@app.teardown_request
def teardown_request(exception=None):
    db.session.close()  # ← Returns connection to pool
```

### Why It Works

- After each request, connection is properly closed
- Connection returns to pool
- Pool never gets exhausted
- App continues working

## 🎯 Monitoring

### Set Up Regular Monitoring

**Windows Task Scheduler:**
```cmd
# Create task to run every 15 minutes
schtasks /create /tn "BankU Health Check" /tr "python E:\BankU V0.1\BankU Final Production\monitor_health.py --quiet" /sc minute /mo 15
```

**Linux Cron:**
```bash
# Add to crontab
*/15 * * * * cd /path/to/app && python monitor_health.py --quiet
```

### Health Endpoint

Visit: `https://banku.vip/health/api`

**Good Response:**
```json
{
  "overall_status": "healthy",
  "checks": {
    "database": {
      "status": "healthy",
      "pool_size": 20,
      "checked_out": 2,  ← Good: < 80%
      "overflow": 0,
      "response_time": 0.015
    },
    "system_resources": {
      "cpu_usage": 25.0,
      "memory_usage": 45.0,
      "disk_usage": 50.0
    }
  }
}
```

**Bad Response (Issue Detected):**
```json
{
  "overall_status": "warning",
  "checks": {
    "database": {
      "pool_size": 20,
      "checked_out": 18,  ← Bad: 90% used!
      "response_time": 2.5  ← Slow!
    }
  }
}
```

## 🚨 Troubleshooting

### Issue: Fix script fails

**Solution:** Apply manual fix from QUICK_FIX.md

### Issue: Still hanging after fix

**Debug steps:**
```bash
# 1. Check if fix was applied
grep "teardown_request" app.py

# 2. Verify app restarted
tasklist | findstr python

# 3. Check database pool
python server_diagnostics.py

# 4. Check database locks
mysql -u root -p -e "SHOW PROCESSLIST;"
```

### Issue: High memory usage

**Check:**
- Are sessions being created repeatedly?
- Is cache growing unbounded?
- Memory leak in custom code?

**Fix:**
- Ensure `db.session.remove()` is called
- Clear caches periodically
- Add max_requests to gunicorn config

### Issue: Slow queries

**Check:**
```sql
-- Find slow queries
SELECT * FROM information_schema.PROCESSLIST 
WHERE TIME > 5 AND COMMAND != 'Sleep';
```

**Fix:**
- Add database indexes
- Optimize queries
- Use query caching

## 📈 Performance Tuning

### Increase Pool Size (if needed)

In `app.py`:
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 30,        # Increase if you have many concurrent users
    'max_overflow': 60,     # Increase to handle traffic spikes
    'pool_recycle': 1800,   # Recycle connections every 30 min
    'pool_pre_ping': True,  # Verify connections before use
}
```

### Use Gunicorn (Production)

```bash
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 60 --max-requests 1000 app:app
```

**Benefits:**
- Multiple worker processes
- Automatic worker restart (max-requests)
- Better concurrency

### Database Optimization

```sql
-- Add indexes to frequently queried columns
CREATE INDEX idx_user_email ON user(email);
CREATE INDEX idx_item_created ON item(created_at);

-- Optimize tables
OPTIMIZE TABLE user, item, deal;
```

## 📝 Logs

### Application Logs

Monitor these files:
- `health_monitor.log` - Health check results
- `diagnostic_report_*.json` - Diagnostic results
- `server_diagnostic_*.json` - Server diagnostics

### Web Server Logs

Check for errors:
- Apache: `/var/log/apache2/error.log`
- Nginx: `/var/log/nginx/error.log`

### Database Logs

Enable slow query log in MySQL:
```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';
```

## 🎓 Learning Resources

### Database Connection Pooling
- [SQLAlchemy Pooling](https://docs.sqlalchemy.org/en/14/core/pooling.html)
- [Flask-SQLAlchemy Config](https://flask-sqlalchemy.palletsprojects.com/en/2.x/config/)

### Flask Best Practices
- [Flask Production Deployment](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Flask Error Handling](https://flask.palletsprojects.com/en/2.3.x/errorhandling/)

## 🆘 Support Checklist

If you need help, gather this information:

```bash
# 1. Run diagnostics
python diagnose_app.py > remote_diagnostic.txt
python server_diagnostics.py > server_diagnostic.txt

# 2. Check health
curl https://banku.vip/health/api > health.json

# 3. Database status
mysql -u root -p -e "SHOW PROCESSLIST;" > processlist.txt
mysql -u root -p -e "SHOW ENGINE INNODB STATUS;" > innodb.txt

# 4. System info
python -c "import platform; print(platform.platform())" > system.txt
python --version >> system.txt
pip list > packages.txt
```

Share these files when asking for help.

## 📌 Summary

| Tool | Purpose | Use Case |
|------|---------|----------|
| `QUICK_FIX.md` | Quick solution | I need to fix it NOW |
| `diagnose_app.py` | Remote test | Is the app working? |
| `server_diagnostics.py` | Internal check | What's wrong internally? |
| `apply_session_fix.py` | Fix the problem | Apply the solution |
| `monitor_health.py` | Regular monitoring | Prevent future issues |

**Most Common Path:**
1. Read `QUICK_FIX.md`
2. Run `apply_session_fix.py`
3. Restart app
4. Verify with `diagnose_app.py`
5. Set up `monitor_health.py` for ongoing monitoring

## ✅ Success Indicators

After applying the fix, you should see:

- ✅ App responds quickly (< 2s)
- ✅ No timeouts on requests
- ✅ Database pool has available connections
- ✅ No need to restart app
- ✅ Stable memory usage
- ✅ Health endpoint shows "healthy"

**You're done! Your app is fixed! 🎉**


