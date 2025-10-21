#!/usr/bin/env python3
"""
Force Stop Application
This script forcefully stops all BankU processes when normal shutdown fails
"""

import os
import sys
import subprocess
import time
import signal

def force_stop_app():
    """Force stop the BankU application"""
    
    print("\n" + "="*80)
    print("FORCE STOPPING BANKU APPLICATION")
    print("="*80)
    
    stopped_processes = []
    
    # Method 1: Find Python processes running app.py or main.py
    print("\n[1/4] Finding BankU processes...")
    try:
        # Find processes
        if os.name == 'posix':  # Linux/Unix
            cmd = "ps aux | grep -E '(app.py|main.py|python.*banku)' | grep -v grep"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.stdout:
                print("  Found processes:")
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    print(f"    {line}")
                    # Extract PID (second column in ps aux output)
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        try:
                            print(f"    Killing PID {pid}...")
                            os.kill(int(pid), signal.SIGTERM)
                            stopped_processes.append(pid)
                            time.sleep(1)
                            # Force kill if still running
                            try:
                                os.kill(int(pid), signal.SIGKILL)
                            except ProcessLookupError:
                                print(f"    ✓ Process {pid} stopped")
                        except Exception as e:
                            print(f"    ! Could not kill {pid}: {e}")
            else:
                print("  No Python processes found")
        else:  # Windows
            cmd = 'tasklist | findstr python'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout:
                print("  Found Python processes:")
                print(result.stdout)
                print("\n  Run this command in Command Prompt as Administrator:")
                print("  taskkill /F /IM python.exe")
                
    except Exception as e:
        print(f"  Error finding processes: {e}")
    
    # Method 2: Find and remove lock files
    print("\n[2/4] Removing lock files...")
    lock_patterns = [
        '/tmp/banku*.lock',
        '/var/run/banku*.lock',
        '/tmp/app.lock',
        '.lock',
        '*.lock'
    ]
    
    for pattern in lock_patterns:
        try:
            cmd = f"find . -name '{pattern}' 2>/dev/null"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.stdout:
                lock_files = result.stdout.strip().split('\n')
                for lock_file in lock_files:
                    if lock_file:
                        try:
                            os.remove(lock_file)
                            print(f"  ✓ Removed lock file: {lock_file}")
                        except Exception as e:
                            print(f"  ! Could not remove {lock_file}: {e}")
        except:
            pass
    
    # Method 3: Kill gunicorn/uwsgi if running
    print("\n[3/4] Checking for web server processes...")
    for process_name in ['gunicorn', 'uwsgi', 'flask']:
        try:
            cmd = f"pkill -9 {process_name}"
            subprocess.run(cmd, shell=True)
            print(f"  ✓ Killed {process_name} processes")
        except:
            pass
    
    # Method 4: Check for passenger (Namecheap hosting often uses this)
    print("\n[4/4] Checking for Passenger processes...")
    try:
        # Passenger restart
        cmd = "passenger-config restart-app /"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✓ Passenger restarted")
        else:
            print("  ! Passenger command not available or failed")
    except Exception as e:
        print(f"  ! Passenger not available: {e}")
    
    print("\n" + "="*80)
    print("CLEANUP SUMMARY")
    print("="*80)
    
    if stopped_processes:
        print(f"✓ Stopped {len(stopped_processes)} processes")
    else:
        print("! No processes found to stop")
    
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    print("\nVerifying no BankU processes are running...")
    
    time.sleep(2)
    
    if os.name == 'posix':
        cmd = "ps aux | grep -E '(app.py|main.py)' | grep -v grep"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            print("⚠ WARNING: Some processes may still be running:")
            print(result.stdout)
            print("\nManually kill these with:")
            print("  kill -9 <PID>")
        else:
            print("✓ All processes stopped successfully!")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Application should now be stopped")
    print("2. Start it again with your hosting control panel")
    print("3. OR run: python main.py (or however you normally start it)")
    print("4. Then verify: python quick_timeout_check.py")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        force_stop_app()
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

