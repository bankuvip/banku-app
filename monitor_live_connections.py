#!/usr/bin/env python3
"""
Live Connection Monitor - Watch connections in real-time
This helps identify which routes/operations are leaking sessions

Usage: python monitor_live_connections.py
"""

import sys
import os
import time
from datetime import datetime

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def monitor_connections():
    """Monitor database connections in real-time"""
    from app import app, db
    
    print("\n" + "="*100)
    print("LIVE CONNECTION MONITOR - Press Ctrl+C to stop")
    print("="*100)
    print("\nThis will show you real-time connection activity to help identify leaks\n")
    
    previous_count = 0
    
    try:
        with app.app_context():
            while True:
                # Clear screen (optional)
                # os.system('clear' if os.name == 'posix' else 'cls')
                
                print(f"\n{'='*100}")
                print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*100}")
                
                # Get pool status
                try:
                    engine = db.engine
                    pool = engine.pool
                    
                    pool_size = pool.size()
                    checked_out = pool.checkedout()
                    overflow = pool.overflow()
                    checked_in = pool.checkedin()
                    
                    total = pool_size + overflow
                    usage_pct = (checked_out / total * 100) if total > 0 else 0
                    
                    print(f"\n📊 Connection Pool Status:")
                    print(f"  Pool Size: {pool_size} | Overflow: {overflow} | Total Capacity: {total}")
                    print(f"  Checked Out: {checked_out} | Checked In: {checked_in}")
                    print(f"  Usage: {usage_pct:.1f}% {'🔴 CRITICAL!' if usage_pct > 90 else '🟡 HIGH!' if usage_pct > 75 else '🟢 OK'}")
                    
                    # Alert on changes
                    if checked_out != previous_count:
                        change = checked_out - previous_count
                        symbol = "📈" if change > 0 else "📉"
                        print(f"  {symbol} Change: {'+' if change > 0 else ''}{change} connections")
                    
                    previous_count = checked_out
                    
                except Exception as e:
                    print(f"❌ Pool Error: {e}")
                
                # Get detailed connection info
                try:
                    connections = db.session.execute(db.text("""
                        SELECT 
                            ID,
                            USER,
                            HOST,
                            DB,
                            COMMAND,
                            TIME,
                            STATE,
                            LEFT(INFO, 50) as INFO
                        FROM information_schema.PROCESSLIST
                        ORDER BY TIME DESC
                        LIMIT 15
                    """)).fetchall()
                    
                    active = sum(1 for c in connections if c[4] != 'Sleep')
                    sleeping = sum(1 for c in connections if c[4] == 'Sleep')
                    
                    print(f"\n🔌 Database Connections: {len(connections)} total ({active} active, {sleeping} sleeping)")
                    print(f"\n{'ID':<8} {'USER':<15} {'COMMAND':<10} {'TIME':<6} {'STATE':<20} {'QUERY':<40}")
                    print("-"*100)
                    
                    for conn in connections:
                        status_icon = "🟢" if conn[4] == "Sleep" else "🟡" if conn[5] < 10 else "🔴"
                        print(f"{status_icon} {conn[0]:<6} {conn[1]:<15} {conn[4]:<10} {conn[5]:<6} {str(conn[6] or ''):<20} {str(conn[7] or 'None'):<40}")
                    
                    # Check for stuck queries
                    stuck_queries = [c for c in connections if c[4] != 'Sleep' and c[5] > 30]
                    if stuck_queries:
                        print(f"\n🔴 WARNING: {len(stuck_queries)} queries running over 30 seconds!")
                        for q in stuck_queries:
                            print(f"   Query #{q[0]} running for {q[5]} seconds")
                    
                except Exception as e:
                    print(f"❌ Connection Query Error: {e}")
                
                # Check for connection leaks pattern
                try:
                    if checked_out > pool_size * 0.8:
                        print(f"\n⚠️  LEAK ALERT: Pool is {usage_pct:.1f}% full!")
                        print(f"   This indicates sessions are not being closed properly")
                        print(f"   Look for:")
                        print(f"   - Background tasks not calling db.session.remove()")
                        print(f"   - Routes with database queries but no proper cleanup")
                        print(f"   - Scheduled jobs that don't close sessions")
                except:
                    pass
                
                print(f"\n{'='*100}")
                time.sleep(3)  # Update every 3 seconds
                
    except KeyboardInterrupt:
        print("\n\n✋ Monitoring stopped by user")
        print(f"Final pool usage: {usage_pct:.1f}%")
        print("="*100 + "\n")

if __name__ == "__main__":
    monitor_connections()

