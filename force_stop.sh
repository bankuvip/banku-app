#!/bin/bash
# Force Stop BankU Application - Shell Script
# This bypasses Python and directly kills processes

echo "======================================================================"
echo "FORCE STOPPING BANKU APPLICATION"
echo "======================================================================"

# Step 1: Kill all Python processes related to BankU
echo ""
echo "[1/5] Finding and killing BankU Python processes..."

# Find PIDs
PIDS=$(ps aux | grep -E '(app\.py|main\.py)' | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "  No BankU processes found"
else
    echo "  Found processes: $PIDS"
    for PID in $PIDS; do
        echo "  Killing PID $PID..."
        kill -9 $PID 2>/dev/null
        sleep 0.5
    done
    echo "  ✓ Processes killed"
fi

# Step 2: Kill any remaining Python processes
echo ""
echo "[2/5] Checking for any hanging Python processes..."
pkill -9 -f "python.*banku" 2>/dev/null
echo "  ✓ Cleanup complete"

# Step 3: Remove lock files
echo ""
echo "[3/5] Removing lock files..."

# Common lock file locations
rm -f /tmp/banku*.lock 2>/dev/null
rm -f /var/run/banku*.lock 2>/dev/null
rm -f *.lock 2>/dev/null
rm -f tmp/pids/* 2>/dev/null

# Find and remove any .lock files in current directory
find . -name "*.lock" -type f -delete 2>/dev/null

echo "  ✓ Lock files removed"

# Step 4: Trigger Passenger restart (for Namecheap/cPanel hosting)
echo ""
echo "[4/5] Triggering Passenger restart..."

# Create tmp directory if it doesn't exist
mkdir -p tmp 2>/dev/null

# Create restart.txt (Passenger restart trigger)
touch tmp/restart.txt
echo "  ✓ Created restart trigger: tmp/restart.txt"

# Also try passenger-config if available
if command -v passenger-config &> /dev/null; then
    passenger-config restart-app / 2>/dev/null
    echo "  ✓ Passenger restart command executed"
else
    echo "  ! Passenger command not available (this is normal)"
fi

# Step 5: Verify
echo ""
echo "[5/5] Verifying processes are stopped..."
sleep 2

REMAINING=$(ps aux | grep -E '(app\.py|main\.py)' | grep -v grep)

if [ -z "$REMAINING" ]; then
    echo "  ✓ All processes stopped successfully!"
else
    echo "  ⚠ Some processes may still be running:"
    echo "$REMAINING"
    echo ""
    echo "  If you see processes above, run:"
    echo "  kill -9 <PID>"
fi

echo ""
echo "======================================================================"
echo "NEXT STEPS"
echo "======================================================================"
echo "1. Wait 10 seconds for hosting to recognize the stop"
echo "2. Start app through your hosting control panel"
echo "3. OR manually run: python main.py"
echo "4. Verify with: python quick_timeout_check.py"
echo "======================================================================"

