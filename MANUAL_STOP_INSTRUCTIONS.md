# Manual Stop Instructions for BankU

Your application won't stop normally because of a lock. Here's how to force-stop it:

## 🚨 QUICK FIX (Choose based on your setup)

### Option 1: Using the Force Stop Script
```bash
python force_stop_app.py
```

---

### Option 2: Manual Commands (Linux/Unix)

#### Step 1: Find Running Processes
```bash
ps aux | grep -E '(app.py|main.py|python)' | grep -v grep
```

#### Step 2: Kill the Processes
```bash
# Replace <PID> with the process ID from step 1
kill -9 <PID>

# Or kill all python processes (CAREFUL - this kills ALL python processes)
pkill -9 python
```

#### Step 3: Remove Lock Files
```bash
# Find lock files
find /tmp -name "*banku*" -o -name "*.lock" 2>/dev/null
find /var/run -name "*banku*" 2>/dev/null

# Remove them
rm -f /tmp/banku*.lock
rm -f /var/run/banku*.lock
```

---

### Option 3: If Using Passenger (Namecheap Shared Hosting)

```bash
# Method 1: Restart Passenger
passenger-config restart-app /

# Method 2: Create restart file
touch tmp/restart.txt

# Method 3: Through cPanel
# Go to cPanel → Application Manager → Restart
```

---

### Option 4: Through Your Hosting Control Panel

**cPanel:**
1. Login to cPanel
2. Go to "Setup Python App" or "Application Manager"
3. Find your BankU application
4. Click "Stop Application"
5. If that fails, click "Restart" (this forces a stop+start)

**Plesk:**
1. Login to Plesk
2. Go to your domain → Python
3. Click "Restart App"

**Direct Admin:**
1. Login to Direct Admin
2. Python Setup → Restart Application

---

## 🔍 Verify It's Stopped

```bash
# Check for running processes
ps aux | grep -E '(app.py|main.py)' | grep -v grep

# If output is EMPTY - app is stopped ✓
# If you see processes - kill them manually
```

---

## 🚀 After Stopping - Start With Fixes

Once stopped, start the application normally through your hosting panel.

The fixes in app.py, advanced_data_collector.py, and health_monitor.py will automatically take effect.

---

## 🆘 If Nothing Works

### Nuclear Option (Linux):
```bash
# Kill ALL Python processes (WARNING: This kills ALL Python programs)
pkill -9 python
pkill -9 python3

# Kill web server processes
pkill -9 gunicorn
pkill -9 uwsgi

# Remove all lock files
find /tmp -name "*.lock" -delete
find /var/run -name "*.lock" -delete

# Clear Passenger temp
rm -rf tmp/pids/*
rm -rf tmp/cache/*
```

### Then restart your server:
```bash
# If you have access
sudo systemctl restart apache2
# OR
sudo systemctl restart nginx
```

---

## 📝 Common Lock File Locations

- `/tmp/banku.lock`
- `/tmp/app.lock`
- `/var/run/banku.pid`
- `tmp/pids/` (in your application directory)
- `.lock` files in application root

---

## ✅ After Successfully Stopping

1. **Start the app again** (through control panel or manually)
2. **Run verification:**
   ```bash
   python quick_timeout_check.py
   ```
3. **Look for:**
   - Pool Usage: Should be 0-20%
   - Sleeping Connections: Should be < 60 seconds (NOT 1212s anymore!)

---

## 🎯 Expected Outcome

After restart with fixes applied:
- ✅ No more sleeping connections for 1200+ seconds
- ✅ Pool usage stays below 50%
- ✅ No more timeouts after 30-60 minutes
- ✅ Application runs indefinitely

The lock issue is just preventing shutdown - once you force-stop and restart, the REAL fixes will prevent the timeout problem!

