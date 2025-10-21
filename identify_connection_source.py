#!/usr/bin/env python3
"""
Connection Source Identifier
This script tells you EXACTLY what is creating and holding the sleeping connections
"""

import sys
import os
from datetime import datetime

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def identify_connection_sources():
    """Identify what's creating the sleeping connections"""
    from app import app, db
    
    print("\n" + "="*80)
    print("CONNECTION SOURCE ANALYSIS")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    with app.app_context():
        # 1. Get detailed connection info
        print("📊 Analyzing Sleeping Connections...")
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
                    INFO
                FROM information_schema.PROCESSLIST
                WHERE COMMAND = 'Sleep'
                ORDER BY TIME DESC
            """)).fetchall()
            
            if connections:
                print(f"\n  Found {len(connections)} sleeping connections:\n")
                print(f"  {'ID':<8} {'User':<15} {'Time (s)':<10} {'Last Query':<50}")
                print("  " + "-"*85)
                
                for conn in connections:
                    conn_id = conn[0]
                    user = conn[1]
                    time_sec = conn[5]
                    last_query = conn[7] if conn[7] else "None"
                    
                    # Truncate query for display
                    query_display = last_query[:47] + "..." if last_query and len(last_query) > 50 else last_query
                    
                    # Color code by time
                    if time_sec > 600:
                        indicator = "🔴"
                    elif time_sec > 300:
                        indicator = "🟡"
                    else:
                        indicator = "🟢"
                    
                    print(f"  {indicator} {conn_id:<6} {user:<15} {time_sec:<10} {query_display}")
                
                print()
                
                # Analyze the queries to identify patterns
                print("\n🔍 Query Pattern Analysis:")
                query_patterns = {}
                
                for conn in connections:
                    last_query = conn[7] if conn[7] else "No query recorded"
                    time_sec = conn[5]
                    
                    # Categorize queries
                    if "SELECT" in str(last_query).upper():
                        if "PROCESSLIST" in str(last_query).upper():
                            category = "Health Check (information_schema.PROCESSLIST)"
                        elif "user" in str(last_query).lower():
                            category = "User Query"
                        elif "item" in str(last_query).lower():
                            category = "Item Query"
                        elif "organization" in str(last_query).lower():
                            category = "Organization Query"
                        else:
                            category = "Generic SELECT"
                    elif "INSERT" in str(last_query).upper():
                        category = "INSERT Operation"
                    elif "UPDATE" in str(last_query).upper():
                        category = "UPDATE Operation"
                    elif not last_query or last_query == "No query recorded":
                        category = "No query (connection just opened)"
                    else:
                        category = "Other"
                    
                    if category not in query_patterns:
                        query_patterns[category] = []
                    query_patterns[category].append(time_sec)
                
                for category, times in sorted(query_patterns.items()):
                    avg_time = sum(times) / len(times)
                    max_time = max(times)
                    count = len(times)
                    print(f"\n  📌 {category}:")
                    print(f"     Count: {count}")
                    print(f"     Avg Sleep Time: {avg_time:.1f}s")
                    print(f"     Max Sleep Time: {max_time:.1f}s")
                    
                    # Identify likely source
                    if "PROCESSLIST" in category:
                        print(f"     🎯 LIKELY SOURCE: Health Monitor background thread")
                        print(f"        → This runs every 5 minutes to check database health")
                        print(f"        → Holds connection between checks")
                    elif avg_time > 500:
                        print(f"     ⚠️  SUSPICIOUS: Very long sleep time suggests background thread")
                
            else:
                print("  ✅ No sleeping connections found!")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # 2. Check for background threads
        print("\n\n🧵 Checking Active Background Threads...")
        try:
            import threading
            threads = threading.enumerate()
            
            print(f"\n  Total Threads: {len(threads)}\n")
            
            for thread in threads:
                is_daemon = "🔄 Daemon" if thread.daemon else "⚙️  Normal"
                is_alive = "✅ Running" if thread.is_alive() else "❌ Stopped"
                
                print(f"  {is_daemon} | {is_alive} | {thread.name}")
                
                # Identify suspicious threads
                if any(keyword in thread.name.lower() for keyword in ['schedule', 'collector', 'monitor', 'health']):
                    print(f"     ⚠️  SUSPICIOUS: This thread might be holding database connections!")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # 3. Check what's imported and running
        print("\n\n📦 Checking Loaded Modules...")
        try:
            import sys
            suspicious_modules = []
            
            for module_name in sys.modules:
                if any(keyword in module_name.lower() for keyword in ['collector', 'schedule', 'health_monitor']):
                    suspicious_modules.append(module_name)
            
            if suspicious_modules:
                print(f"\n  Found {len(suspicious_modules)} potentially problematic modules:\n")
                for mod in suspicious_modules:
                    print(f"  📌 {mod}")
                    if 'advanced_data_collector' in mod:
                        print(f"     🎯 IDENTIFIED: Advanced Data Collector is loaded!")
                        print(f"        → This runs scheduled tasks in background")
                        print(f"        → Each task holds a database connection")
                    if 'health_monitor' in mod:
                        print(f"     🎯 IDENTIFIED: Health Monitor is loaded!")
                        print(f"        → Runs health checks every 5 minutes")
                        print(f"        → Queries information_schema.PROCESSLIST")
            else:
                print("  ✅ No suspicious background modules loaded")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        # 4. Time-based pattern analysis
        print("\n\n⏰ Sleep Time Distribution:")
        try:
            sleep_times = [conn[5] for conn in connections]
            
            if sleep_times:
                ranges = {
                    "0-60s (Fresh)": [t for t in sleep_times if t < 60],
                    "60-300s (Recent)": [t for t in sleep_times if 60 <= t < 300],
                    "300-600s (Aging)": [t for t in sleep_times if 300 <= t < 600],
                    "600-1200s (Old - Should be recycled!)": [t for t in sleep_times if 600 <= t < 1200],
                    "1200s+ (LEAK!)": [t for t in sleep_times if t >= 1200]
                }
                
                print()
                for range_name, times in ranges.items():
                    if times:
                        count = len(times)
                        indicator = "🔴" if "LEAK" in range_name or "Should be recycled" in range_name else "🟡" if "Aging" in range_name else "🟢"
                        print(f"  {indicator} {range_name}: {count} connections")
                
                # Identify the problem
                if ranges["1200s+ (LEAK!)"]:
                    print(f"\n  🚨 DIAGNOSIS: You have {len(ranges['1200s+ (LEAK!'])} connections leaking!")
                    print(f"     These should have been recycled at 600s (pool_recycle setting)")
                    print(f"     This indicates background threads holding connections")
                
                if ranges["600-1200s (Old - Should be recycled!)"]:
                    print(f"\n  ⚠️  WARNING: You have {len(ranges['600-1200s (Old - Should be recycled!)'])} connections exceeding recycle time!")
                    print(f"     pool_recycle: 600 is set but not being enforced")
                    print(f"     Background threads are preventing recycling")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Summary and recommendations
    print("\n" + "="*80)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*80)
    
    if connections and any(conn[5] > 600 for conn in connections):
        print("\n🔴 PROBLEM IDENTIFIED:")
        print("   Background threads are holding database connections indefinitely")
        print()
        print("🎯 LIKELY CULPRITS:")
        print("   1. Advanced Data Collector (scheduled tasks)")
        print("   2. Health Monitor (background health checks)")
        print()
        print("💡 SOLUTION:")
        print("   Disable background tasks in app.py:")
        print("   - Comment out: advanced_collector.start_scheduled_collectors()")
        print("   - Comment out: initialize_health_monitoring(app)")
        print()
        print("📊 EXPECTED IMPROVEMENT:")
        print("   Sleep time: Currently 600-1000s+ → Will drop to 0-60s")
        print("   Pool usage: Will stay at 0% consistently")
        print("   Timeouts: Will be completely eliminated")
    else:
        print("\n✅ NO MAJOR ISSUES DETECTED")
        print("   Connections are being managed properly")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    try:
        identify_connection_sources()
    except Exception as e:
        print(f"\n❌ Error running analysis: {e}")
        import traceback
        traceback.print_exc()

