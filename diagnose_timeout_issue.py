#!/usr/bin/env python3
"""
Comprehensive Timeout Issue Diagnostic Tool
This script monitors the BankU application to identify the root cause of timeouts
that occur after the app has been running for some time.

Run this on your server while the app is running:
    python diagnose_timeout_issue.py

It will monitor and log:
1. Database connection pool status
2. Active database sessions
3. Memory usage trends
4. Thread count and status
5. Long-running queries
6. Session leaks
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta
from collections import defaultdict
import threading

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

class TimeoutDiagnostics:
    """Comprehensive diagnostics for timeout issues"""
    
    def __init__(self):
        self.metrics_history = []
        self.alerts = []
        self.start_time = datetime.now()
        self.monitoring = False
        
    def check_database_connections(self):
        """Check database connection pool status"""
        from app import app, db
        
        with app.app_context():
            try:
                engine = db.engine
                pool = engine.pool
                
                # Get pool statistics
                pool_size = pool.size()
                checked_out = pool.checkedout()
                overflow = pool.overflow()
                checked_in = pool.checkedin()
                
                # Calculate usage
                total_available = pool_size + overflow
                usage_percentage = (checked_out / total_available * 100) if total_available > 0 else 0
                
                # Check for active connections in database
                try:
                    active_connections = db.session.execute(db.text("""
                        SELECT COUNT(*) as count
                        FROM information_schema.PROCESSLIST
                        WHERE COMMAND != 'Sleep'
                    """)).scalar()
                except:
                    active_connections = None
                
                # Check for sleeping connections
                try:
                    sleeping_connections = db.session.execute(db.text("""
                        SELECT COUNT(*) as count
                        FROM information_schema.PROCESSLIST
                        WHERE COMMAND = 'Sleep'
                    """)).scalar()
                except:
                    sleeping_connections = None
                
                result = {
                    'timestamp': datetime.now().isoformat(),
                    'pool_size': pool_size,
                    'checked_out': checked_out,
                    'overflow': overflow,
                    'checked_in': checked_in,
                    'usage_percentage': round(usage_percentage, 2),
                    'active_connections': active_connections,
                    'sleeping_connections': sleeping_connections,
                    'status': 'healthy' if usage_percentage < 80 else 'warning' if usage_percentage < 95 else 'critical'
                }
                
                # Alert if usage is high
                if usage_percentage > 80:
                    self.alerts.append({
                        'timestamp': datetime.now().isoformat(),
                        'severity': 'warning' if usage_percentage < 95 else 'critical',
                        'message': f'High connection pool usage: {usage_percentage:.1f}%',
                        'details': result
                    })
                
                return result
                
            except Exception as e:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e),
                    'status': 'error'
                }
    
    def check_long_running_queries(self):
        """Check for long-running database queries"""
        from app import app, db
        
        with app.app_context():
            try:
                long_queries = db.session.execute(db.text("""
                    SELECT 
                        ID,
                        USER,
                        DB,
                        TIME,
                        STATE,
                        LEFT(INFO, 100) as QUERY_PREVIEW
                    FROM information_schema.PROCESSLIST
                    WHERE COMMAND != 'Sleep'
                    AND TIME > 3
                    ORDER BY TIME DESC
                    LIMIT 10
                """)).fetchall()
                
                queries = []
                for q in long_queries:
                    query_info = {
                        'id': q[0],
                        'user': q[1],
                        'database': q[2],
                        'time_seconds': q[3],
                        'state': q[4],
                        'query_preview': q[5]
                    }
                    queries.append(query_info)
                    
                    # Alert on very long queries
                    if q[3] > 10:
                        self.alerts.append({
                            'timestamp': datetime.now().isoformat(),
                            'severity': 'warning' if q[3] < 30 else 'critical',
                            'message': f'Long-running query detected: {q[3]} seconds',
                            'details': query_info
                        })
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'count': len(queries),
                    'queries': queries
                }
                
            except Exception as e:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e)
                }
    
    def check_system_resources(self):
        """Check system resource usage"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_count = psutil.cpu_count()
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Process-specific info
            process = psutil.Process()
            process_memory = process.memory_info()
            process_threads = process.num_threads()
            process_connections = len(process.connections())
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / 1024 / 1024,
                'memory_total_mb': memory.total / 1024 / 1024,
                'process_memory_mb': process_memory.rss / 1024 / 1024,
                'process_threads': process_threads,
                'process_connections': process_connections,
                'status': 'healthy' if memory.percent < 80 and cpu_percent < 80 else 'warning'
            }
            
            # Alert on high resource usage
            if memory.percent > 85:
                self.alerts.append({
                    'timestamp': datetime.now().isoformat(),
                    'severity': 'critical',
                    'message': f'High memory usage: {memory.percent:.1f}%',
                    'details': result
                })
            
            if cpu_percent > 85:
                self.alerts.append({
                    'timestamp': datetime.now().isoformat(),
                    'severity': 'warning',
                    'message': f'High CPU usage: {cpu_percent:.1f}%',
                    'details': result
                })
            
            return result
            
        except ImportError:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': 'psutil not installed'
            }
        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def check_background_threads(self):
        """Check for background threads"""
        import threading
        
        active_threads = threading.enumerate()
        thread_info = []
        
        for thread in active_threads:
            thread_info.append({
                'name': thread.name,
                'daemon': thread.daemon,
                'alive': thread.is_alive(),
                'ident': thread.ident
            })
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'total_threads': len(active_threads),
            'threads': thread_info
        }
        
        # Alert if thread count is unusually high
        if len(active_threads) > 20:
            self.alerts.append({
                'timestamp': datetime.now().isoformat(),
                'severity': 'warning',
                'message': f'High thread count: {len(active_threads)}',
                'details': result
            })
        
        return result
    
    def check_session_leaks(self):
        """Check for database session leaks"""
        from app import app, db
        
        with app.app_context():
            try:
                # Check SQLAlchemy session registry
                from sqlalchemy.orm import scoped_session
                
                # Get session info
                session_info = {
                    'timestamp': datetime.now().isoformat(),
                    'session_class': str(type(db.session)),
                    'is_scoped': isinstance(db.session, scoped_session)
                }
                
                # Try to get session registry info
                try:
                    if hasattr(db.session, 'registry'):
                        registry = db.session.registry
                        session_info['has_registry'] = True
                        session_info['registry_has_value'] = registry.has()
                    else:
                        session_info['has_registry'] = False
                except:
                    session_info['registry_check_failed'] = True
                
                return session_info
                
            except Exception as e:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e)
                }
    
    def run_comprehensive_check(self):
        """Run all diagnostic checks"""
        print("\n" + "="*80)
        print(f"Diagnostic Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # 1. Database connections
        print("\n[1/6] Checking database connection pool...")
        db_connections = self.check_database_connections()
        print(f"  Pool Usage: {db_connections.get('usage_percentage', 'N/A')}%")
        print(f"  Checked Out: {db_connections.get('checked_out', 'N/A')}/{db_connections.get('pool_size', 'N/A')}")
        print(f"  Active Connections: {db_connections.get('active_connections', 'N/A')}")
        print(f"  Sleeping Connections: {db_connections.get('sleeping_connections', 'N/A')}")
        print(f"  Status: {db_connections.get('status', 'unknown').upper()}")
        
        # 2. Long-running queries
        print("\n[2/6] Checking for long-running queries...")
        long_queries = self.check_long_running_queries()
        print(f"  Found: {long_queries.get('count', 0)} long-running queries")
        if long_queries.get('count', 0) > 0:
            for q in long_queries['queries'][:3]:
                print(f"    - Query running for {q['time_seconds']}s: {q['query_preview'][:60]}...")
        
        # 3. System resources
        print("\n[3/6] Checking system resources...")
        resources = self.check_system_resources()
        print(f"  CPU: {resources.get('cpu_percent', 'N/A')}%")
        print(f"  Memory: {resources.get('memory_percent', 'N/A')}%")
        print(f"  Process Memory: {resources.get('process_memory_mb', 'N/A'):.1f} MB")
        print(f"  Threads: {resources.get('process_threads', 'N/A')}")
        print(f"  Connections: {resources.get('process_connections', 'N/A')}")
        
        # 4. Background threads
        print("\n[4/6] Checking background threads...")
        threads = self.check_background_threads()
        print(f"  Total Threads: {threads.get('total_threads', 'N/A')}")
        print(f"  Daemon Threads: {sum(1 for t in threads.get('threads', []) if t['daemon'])}")
        
        # 5. Session leaks
        print("\n[5/6] Checking for session leaks...")
        sessions = self.check_session_leaks()
        print(f"  Session Type: {sessions.get('session_class', 'N/A')}")
        print(f"  Is Scoped: {sessions.get('is_scoped', 'N/A')}")
        
        # 6. Recent alerts
        print("\n[6/6] Checking recent alerts...")
        recent_alerts = [a for a in self.alerts if a['timestamp'] > (datetime.now() - timedelta(minutes=5)).isoformat()]
        print(f"  Alerts (last 5 min): {len(recent_alerts)}")
        for alert in recent_alerts[-5:]:
            print(f"    [{alert['severity'].upper()}] {alert['message']}")
        
        # Store metrics
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'database': db_connections,
            'queries': long_queries,
            'resources': resources,
            'threads': threads,
            'sessions': sessions
        }
        self.metrics_history.append(metrics)
        
        return metrics
    
    def monitor_continuously(self, interval=60, duration=3600):
        """Monitor continuously and save results"""
        print("\n" + "="*80)
        print("CONTINUOUS MONITORING STARTED")
        print("="*80)
        print(f"Interval: {interval} seconds")
        print(f"Duration: {duration} seconds ({duration//60} minutes)")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nPress Ctrl+C to stop early and save results...")
        print("="*80)
        
        self.monitoring = True
        start_time = time.time()
        check_count = 0
        
        try:
            while self.monitoring and (time.time() - start_time) < duration:
                check_count += 1
                print(f"\n--- Check #{check_count} ---")
                self.run_comprehensive_check()
                
                # Show trend analysis every 5 checks
                if check_count % 5 == 0:
                    self.show_trend_analysis()
                
                # Wait for next interval
                if (time.time() - start_time) < duration:
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
        
        finally:
            self.monitoring = False
            self.save_results()
    
    def show_trend_analysis(self):
        """Show trend analysis of metrics"""
        if len(self.metrics_history) < 2:
            return
        
        print("\n" + "-"*80)
        print("TREND ANALYSIS")
        print("-"*80)
        
        # Analyze connection pool usage trend
        pool_usage = [m['database'].get('usage_percentage', 0) for m in self.metrics_history]
        if pool_usage:
            print(f"Connection Pool Usage Trend:")
            print(f"  Min: {min(pool_usage):.1f}%")
            print(f"  Max: {max(pool_usage):.1f}%")
            print(f"  Avg: {sum(pool_usage)/len(pool_usage):.1f}%")
            print(f"  Latest: {pool_usage[-1]:.1f}%")
            
            # Check if increasing
            if len(pool_usage) >= 5:
                recent_avg = sum(pool_usage[-5:]) / 5
                earlier_avg = sum(pool_usage[-10:-5]) / 5 if len(pool_usage) >= 10 else sum(pool_usage[:-5]) / len(pool_usage[:-5])
                if recent_avg > earlier_avg + 10:
                    print(f"  ⚠ WARNING: Pool usage is INCREASING (from {earlier_avg:.1f}% to {recent_avg:.1f}%)")
        
        # Analyze memory usage trend
        memory_usage = [m['resources'].get('memory_percent', 0) for m in self.metrics_history if 'resources' in m]
        if memory_usage:
            print(f"\nMemory Usage Trend:")
            print(f"  Min: {min(memory_usage):.1f}%")
            print(f"  Max: {max(memory_usage):.1f}%")
            print(f"  Avg: {sum(memory_usage)/len(memory_usage):.1f}%")
            print(f"  Latest: {memory_usage[-1]:.1f}%")
        
        # Analyze thread count trend
        thread_counts = [m['threads'].get('total_threads', 0) for m in self.metrics_history if 'threads' in m]
        if thread_counts:
            print(f"\nThread Count Trend:")
            print(f"  Min: {min(thread_counts)}")
            print(f"  Max: {max(thread_counts)}")
            print(f"  Latest: {thread_counts[-1]}")
            
            if thread_counts[-1] > thread_counts[0] + 5:
                print(f"  ⚠ WARNING: Thread count is INCREASING (from {thread_counts[0]} to {thread_counts[-1]})")
        
        print("-"*80)
    
    def save_results(self):
        """Save diagnostic results to file"""
        filename = f"timeout_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'total_checks': len(self.metrics_history),
            'total_alerts': len(self.alerts),
            'metrics_history': self.metrics_history,
            'alerts': self.alerts
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'='*80}")
        print(f"Results saved to: {filename}")
        print(f"Total checks: {len(self.metrics_history)}")
        print(f"Total alerts: {len(self.alerts)}")
        print(f"{'='*80}")
        
        # Show summary
        self.show_summary()
    
    def show_summary(self):
        """Show diagnostic summary"""
        print("\n" + "="*80)
        print("DIAGNOSTIC SUMMARY")
        print("="*80)
        
        if not self.metrics_history:
            print("No data collected")
            return
        
        # Connection pool analysis
        pool_usage = [m['database'].get('usage_percentage', 0) for m in self.metrics_history]
        max_pool_usage = max(pool_usage) if pool_usage else 0
        avg_pool_usage = sum(pool_usage) / len(pool_usage) if pool_usage else 0
        
        print(f"\n📊 Connection Pool:")
        print(f"  Average Usage: {avg_pool_usage:.1f}%")
        print(f"  Peak Usage: {max_pool_usage:.1f}%")
        
        if max_pool_usage > 90:
            print(f"  🔴 CRITICAL: Pool usage exceeded 90%")
            print(f"     This is likely causing the timeout issues!")
        elif max_pool_usage > 75:
            print(f"  🟡 WARNING: Pool usage exceeded 75%")
            print(f"     Monitor closely - may cause issues soon")
        else:
            print(f"  🟢 OK: Pool usage is healthy")
        
        # Alert summary
        critical_alerts = [a for a in self.alerts if a['severity'] == 'critical']
        warning_alerts = [a for a in self.alerts if a['severity'] == 'warning']
        
        print(f"\n⚠️  Alerts:")
        print(f"  Critical: {len(critical_alerts)}")
        print(f"  Warnings: {len(warning_alerts)}")
        
        if critical_alerts:
            print(f"\n  Recent Critical Issues:")
            for alert in critical_alerts[-5:]:
                print(f"    - {alert['message']}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if max_pool_usage > 90:
            print("  1. DATABASE CONNECTION LEAK DETECTED")
            print("     → Sessions are not being closed properly")
            print("     → Check background tasks and scheduled jobs")
            print("     → Add db.session.remove() after operations")
        
        if len(critical_alerts) > 10:
            print("  2. MULTIPLE CRITICAL ISSUES DETECTED")
            print("     → Review the detailed logs above")
            print("     → Consider restarting the application")
        
        # Show most common issues
        issue_types = defaultdict(int)
        for alert in self.alerts:
            issue_types[alert['message'].split(':')[0]] += 1
        
        if issue_types:
            print(f"\n  Most Common Issues:")
            for issue, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"    - {issue}: {count} times")
        
        print("\n" + "="*80)

def main():
    """Main diagnostic function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Diagnose BankU timeout issues')
    parser.add_argument('--mode', choices=['single', 'monitor'], default='single',
                      help='Run mode: single check or continuous monitoring')
    parser.add_argument('--interval', type=int, default=60,
                      help='Monitoring interval in seconds (default: 60)')
    parser.add_argument('--duration', type=int, default=1800,
                      help='Monitoring duration in seconds (default: 1800 = 30 min)')
    
    args = parser.parse_args()
    
    diagnostics = TimeoutDiagnostics()
    
    if args.mode == 'single':
        print("\nRunning single diagnostic check...")
        diagnostics.run_comprehensive_check()
        diagnostics.save_results()
    else:
        print(f"\nStarting continuous monitoring...")
        print(f"This will run for {args.duration} seconds ({args.duration//60} minutes)")
        print(f"Checking every {args.interval} seconds")
        diagnostics.monitor_continuously(interval=args.interval, duration=args.duration)

if __name__ == "__main__":
    main()

