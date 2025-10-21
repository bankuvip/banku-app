#!/usr/bin/env python3
"""
Quick Timeout Check - Run this for immediate diagnosis
Usage: python quick_timeout_check.py
"""

import sys
import os

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def quick_check():
    """Quick check for the most common timeout causes"""
    from app import app, db
    from datetime import datetime
    
    print("\n" + "="*80)
    print("QUICK TIMEOUT DIAGNOSIS")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    with app.app_context():
        # Check 1: Connection Pool
        print("📊 Checking Connection Pool...")
        try:
            engine = db.engine
            pool = engine.pool
            
            pool_size = pool.size()
            checked_out = pool.checkedout()
            overflow = pool.overflow()
            
            total_capacity = pool_size + overflow
            usage_pct = (checked_out / total_capacity * 100) if total_capacity > 0 else 0
            
            print(f"  Pool Size: {pool_size}")
            print(f"  Max Overflow: {overflow}")
            print(f"  Currently Checked Out: {checked_out}")
            print(f"  Usage: {usage_pct:.1f}%")
            
            if usage_pct > 90:
                print("  🔴 CRITICAL: Pool is almost full! This WILL cause timeouts!")
                print("  👉 Problem: Database sessions are not being released")
            elif usage_pct > 75:
                print("  🟡 WARNING: Pool usage is high - approaching timeout risk")
            else:
                print("  🟢 OK: Pool usage is healthy")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Check 2: Active Connections
        print("\n🔌 Checking Active Database Connections...")
        try:
            result = db.session.execute(db.text("""
                SELECT 
                    COMMAND,
                    COUNT(*) as count,
                    AVG(TIME) as avg_time,
                    MAX(TIME) as max_time
                FROM information_schema.PROCESSLIST
                GROUP BY COMMAND
                ORDER BY count DESC
            """)).fetchall()
            
            for row in result:
                status = "🟢" if row[0] == "Sleep" else "🟡" if row[3] < 10 else "🔴"
                print(f"  {status} {row[0]}: {row[1]} connections (avg: {row[2]:.1f}s, max: {row[3]}s)")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Check 3: Long Running Queries
        print("\n⏱️  Checking Long-Running Queries...")
        try:
            long_queries = db.session.execute(db.text("""
                SELECT COUNT(*) as count
                FROM information_schema.PROCESSLIST
                WHERE COMMAND != 'Sleep' AND TIME > 5
            """)).scalar()
            
            if long_queries > 0:
                print(f"  🔴 Found {long_queries} queries running over 5 seconds")
                
                details = db.session.execute(db.text("""
                    SELECT TIME, STATE, LEFT(INFO, 60) as QUERY
                    FROM information_schema.PROCESSLIST
                    WHERE COMMAND != 'Sleep' AND TIME > 5
                    ORDER BY TIME DESC
                    LIMIT 3
                """)).fetchall()
                
                for q in details:
                    print(f"    - {q[0]}s: {q[2]}")
            else:
                print(f"  🟢 No long-running queries detected")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # Check 4: Memory and Resources
        print("\n💾 Checking System Resources...")
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.5)
            
            print(f"  Memory: {memory.percent:.1f}% used")
            print(f"  CPU: {cpu:.1f}%")
            
            process = psutil.Process()
            print(f"  App Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB")
            print(f"  App Threads: {process.num_threads()}")
            
            if memory.percent > 85:
                print("  🔴 WARNING: High memory usage")
            if cpu > 80:
                print("  🔴 WARNING: High CPU usage")
                
        except ImportError:
            print("  ℹ️  psutil not installed - skipping system resource check")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "="*80)
    print("DIAGNOSIS COMPLETE")
    print("="*80)
    print("\n💡 Next Steps:")
    print("  1. If pool usage is >75%, you have a SESSION LEAK problem")
    print("  2. Run: python diagnose_timeout_issue.py --mode monitor --duration 600")
    print("     (This will monitor for 10 minutes and identify the pattern)")
    print("  3. The detailed diagnostic will pinpoint the exact cause")
    print("="*80 + "\n")

if __name__ == "__main__":
    quick_check()

