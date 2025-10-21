#!/usr/bin/env python3
"""
Server-Side Diagnostic Tool for BankU
Run this ON THE SERVER to diagnose internal issues
"""

import sys
import os

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

import time
from datetime import datetime
import psutil
import json

class ServerDiagnostics:
    def __init__(self):
        self.results = {}
        self.issues = []
        
    def print_header(self, text):
        print("\n" + "="*60)
        print(text.center(60))
        print("="*60 + "\n")
    
    def check_system_resources(self):
        """Check CPU, Memory, Disk usage"""
        self.print_header("System Resources")
        
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"CPU Usage: {cpu_percent}%")
        if cpu_percent > 80:
            self.issues.append(f"HIGH CPU: {cpu_percent}%")
            print(f"⚠ WARNING: High CPU usage!")
        
        # Memory
        memory = psutil.virtual_memory()
        print(f"Memory Usage: {memory.percent}% ({memory.used / (1024**3):.2f}GB / {memory.total / (1024**3):.2f}GB)")
        if memory.percent > 80:
            self.issues.append(f"HIGH MEMORY: {memory.percent}%")
            print(f"⚠ WARNING: High memory usage!")
        
        # Disk
        disk = psutil.disk_usage('/')
        print(f"Disk Usage: {disk.percent}% ({disk.used / (1024**3):.2f}GB / {disk.total / (1024**3):.2f}GB)")
        if disk.percent > 90:
            self.issues.append(f"LOW DISK SPACE: {disk.percent}% used")
            print(f"⚠ WARNING: Low disk space!")
        
        self.results['system'] = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / (1024**3),
            'memory_total_gb': memory.total / (1024**3),
            'disk_percent': disk.percent
        }
    
    def check_database_connections(self):
        """Check database connection pool status"""
        self.print_header("Database Connection Pool")
        
        try:
            from app import app, db
            
            with app.app_context():
                # Get database engine
                engine = db.engine
                pool = engine.pool
                
                print(f"Pool Size: {pool.size()}")
                print(f"Pool Checked Out: {pool.checkedout()}")
                print(f"Pool Overflow: {pool.overflow()}")
                print(f"Pool Checked In: {pool.checkedin()}")
                
                checked_out = pool.checkedout()
                pool_size = pool.size()
                
                # Check if pool is exhausted
                if checked_out >= pool_size:
                    self.issues.append(f"DATABASE POOL EXHAUSTED: {checked_out}/{pool_size} connections in use")
                    print(f"⚠ WARNING: Connection pool is EXHAUSTED!")
                    print(f"  This is likely causing your app to hang!")
                elif checked_out > pool_size * 0.8:
                    self.issues.append(f"DATABASE POOL HIGH: {checked_out}/{pool_size} connections in use")
                    print(f"⚠ WARNING: Connection pool usage is high!")
                
                self.results['database_pool'] = {
                    'size': pool.size(),
                    'checked_out': checked_out,
                    'overflow': pool.overflow(),
                    'checked_in': pool.checkedin()
                }
                
                # Test database connectivity
                print("\nTesting database query...")
                start = time.time()
                result = db.session.execute(db.text("SELECT 1")).fetchone()
                query_time = time.time() - start
                print(f"✓ Database query successful ({query_time:.3f}s)")
                
                if query_time > 1:
                    self.issues.append(f"SLOW DATABASE: Simple query took {query_time:.3f}s")
                    print(f"⚠ WARNING: Database queries are slow!")
                
        except Exception as e:
            print(f"✗ ERROR checking database: {str(e)}")
            self.issues.append(f"DATABASE ERROR: {str(e)}")
            self.results['database_pool'] = {'error': str(e)}
    
    def check_database_locks(self):
        """Check for locked tables or long-running queries"""
        self.print_header("Database Locks & Long Queries")
        
        try:
            from app import app, db
            
            with app.app_context():
                # For MySQL/MariaDB - check processlist
                print("Checking MySQL processlist...")
                result = db.session.execute(db.text("""
                    SELECT 
                        ID,
                        USER,
                        HOST,
                        DB,
                        COMMAND,
                        TIME,
                        STATE,
                        LEFT(INFO, 100) as QUERY_PREVIEW
                    FROM information_schema.PROCESSLIST
                    WHERE COMMAND != 'Sleep'
                    AND TIME > 5
                    ORDER BY TIME DESC
                    LIMIT 10
                """)).fetchall()
                
                if result:
                    print(f"Found {len(result)} queries running > 5 seconds:")
                    for row in result:
                        print(f"  - ID: {row[0]}, Time: {row[5]}s, State: {row[6]}")
                        print(f"    Query: {row[7]}")
                        
                        if row[5] > 30:
                            self.issues.append(f"LONG QUERY: ID {row[0]} running for {row[5]}s")
                else:
                    print("✓ No long-running queries found")
                
                # Check for locked tables
                print("\nChecking for table locks...")
                locks = db.session.execute(db.text("""
                    SELECT 
                        r.trx_id,
                        r.trx_mysql_thread_id,
                        r.trx_query,
                        r.trx_state,
                        TIMESTAMPDIFF(SECOND, r.trx_started, NOW()) as running_seconds
                    FROM information_schema.INNODB_TRX r
                    WHERE TIMESTAMPDIFF(SECOND, r.trx_started, NOW()) > 5
                """)).fetchall()
                
                if locks:
                    print(f"⚠ Found {len(locks)} long-running transactions:")
                    for lock in locks:
                        print(f"  - Transaction ID: {lock[0]}, Running: {lock[4]}s")
                        self.issues.append(f"LONG TRANSACTION: {lock[4]}s")
                else:
                    print("✓ No long-running transactions")
                    
        except Exception as e:
            print(f"✗ ERROR checking locks: {str(e)}")
            # This might fail on some database setups, so don't treat as critical
    
    def check_flask_sessions(self):
        """Check for session leaks"""
        self.print_header("Flask Session Check")
        
        try:
            from app import app, db
            
            with app.app_context():
                # Check if there are uncommitted transactions
                if db.session.is_active:
                    print("⚠ WARNING: Active database session found")
                    if db.session.dirty:
                        print(f"  Dirty objects in session: {len(db.session.dirty)}")
                        self.issues.append(f"UNCOMMITTED CHANGES: {len(db.session.dirty)} objects")
                    if db.session.new:
                        print(f"  New objects in session: {len(db.session.new)}")
                        self.issues.append(f"UNCOMMITTED NEW: {len(db.session.new)} objects")
                else:
                    print("✓ No active session issues")
                    
        except Exception as e:
            print(f"Note: {str(e)}")
    
    def check_process_threads(self):
        """Check number of threads/processes"""
        self.print_header("Process & Thread Count")
        
        try:
            process = psutil.Process()
            num_threads = process.num_threads()
            
            print(f"Current Process Threads: {num_threads}")
            
            if num_threads > 100:
                self.issues.append(f"HIGH THREAD COUNT: {num_threads}")
                print(f"⚠ WARNING: Very high thread count!")
            
            # Get open files
            try:
                open_files = len(process.open_files())
                print(f"Open Files: {open_files}")
                
                if open_files > 100:
                    self.issues.append(f"HIGH FILE DESCRIPTORS: {open_files}")
                    print(f"⚠ WARNING: Many open files!")
            except:
                pass
            
            # Get connections
            connections = len(process.connections())
            print(f"Network Connections: {connections}")
            
            self.results['process'] = {
                'threads': num_threads,
                'connections': connections
            }
            
        except Exception as e:
            print(f"✗ ERROR: {str(e)}")
    
    def check_app_logs(self):
        """Check for recent errors in logs"""
        self.print_header("Recent Application Logs")
        
        print("Checking for common log files...")
        
        log_locations = [
            'app.log',
            'error.log',
            '/var/log/banku/error.log',
            '/var/log/apache2/error.log',
            '/var/log/nginx/error.log',
        ]
        
        for log_path in log_locations:
            if os.path.exists(log_path):
                print(f"\nFound log: {log_path}")
                try:
                    with open(log_path, 'r') as f:
                        lines = f.readlines()
                        recent_lines = lines[-50:]  # Last 50 lines
                        
                        errors = [l for l in recent_lines if 'ERROR' in l.upper() or 'EXCEPTION' in l.upper()]
                        if errors:
                            print(f"  Recent errors found ({len(errors)}):")
                            for error in errors[-5:]:  # Last 5 errors
                                print(f"    {error.strip()[:100]}")
                except:
                    pass
        
        print("\nNote: Check your web server logs for more details")
    
    def test_data_collector_scheduler(self):
        """Check if the data collector scheduler is causing issues"""
        self.print_header("Data Collector Scheduler")
        
        try:
            from utils.advanced_data_collector import advanced_collector
            
            print("Data collector module loaded successfully")
            
            # Check if scheduler is running
            if hasattr(advanced_collector, 'scheduler'):
                print("⚠ Scheduler is active")
                print("  Note: The data collector scheduler may be consuming resources")
                print("  Consider disabling it temporarily to test if it's causing issues")
            else:
                print("✓ Scheduler not found")
                
        except Exception as e:
            print(f"Data collector check: {str(e)}")
    
    def generate_fixes(self):
        """Generate SQL fixes for common issues"""
        self.print_header("Suggested Database Fixes")
        
        print("If database connections are exhausted, run these commands in MySQL:")
        print("\n-- Check current connections:")
        print("SHOW PROCESSLIST;")
        print("\n-- Kill a specific connection (replace ID):")
        print("KILL <process_id>;")
        print("\n-- Kill all sleeping connections:")
        print("""
SELECT CONCAT('KILL ', id, ';') 
FROM information_schema.PROCESSLIST 
WHERE command = 'Sleep' 
AND time > 300;
""")
        
        print("\n-- Check InnoDB status:")
        print("SHOW ENGINE INNODB STATUS;")
        
        print("\n\nPython fixes to add to app.py:")
        print("""
# Add to app.py after request handling:

@app.teardown_appcontext
def shutdown_session(exception=None):
    '''Ensure database sessions are closed after each request'''
    try:
        db.session.remove()
    except Exception as e:
        logger.error(f"Error closing session: {e}")

@app.teardown_request
def teardown_request(exception=None):
    '''Close database connections after each request'''
    if exception:
        db.session.rollback()
    try:
        db.session.close()
    except Exception as e:
        logger.error(f"Error in teardown: {e}")
""")
    
    def generate_report(self):
        """Generate final report"""
        self.print_header("DIAGNOSTIC REPORT")
        
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if not self.issues:
            print("✓ No critical issues detected!")
        else:
            print(f"✗ Found {len(self.issues)} issue(s):\n")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        # Save to file
        report_file = f"server_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'results': self.results,
                'issues': self.issues
            }, f, indent=2)
        
        print(f"\n✓ Report saved to: {report_file}")
        
        # Provide specific recommendations
        if self.issues:
            self.print_header("RECOMMENDED ACTIONS")
            
            issue_text = ' '.join(self.issues).upper()
            
            if 'POOL EXHAUSTED' in issue_text or 'DATABASE POOL' in issue_text:
                print("⚠ DATABASE CONNECTION POOL IS THE PROBLEM!")
                print("\nImmediate fix:")
                print("1. Restart your application")
                print("2. Add session cleanup to app.py (see suggested fixes above)")
                print("3. Increase pool size in app.py:")
                print("   'pool_size': 20,  # Increase from 10")
                print("   'max_overflow': 40,  # Increase from 20")
                
            if 'LONG QUERY' in issue_text or 'LONG TRANSACTION' in issue_text:
                print("⚠ LONG-RUNNING QUERIES/TRANSACTIONS FOUND!")
                print("\nFix:")
                print("1. Check SHOW PROCESSLIST in MySQL")
                print("2. Kill long-running queries")
                print("3. Review code for missing db.session.commit()")
                
            if 'HIGH MEMORY' in issue_text:
                print("⚠ HIGH MEMORY USAGE!")
                print("\nFix:")
                print("1. Restart application")
                print("2. Add proper session cleanup")
                print("3. Consider using a process manager (gunicorn with max_requests)")
                
            if 'HIGH CPU' in issue_text:
                print("⚠ HIGH CPU USAGE!")
                print("\nCheck:")
                print("1. Infinite loops in code")
                print("2. Heavy computations")
                print("3. Data collector scheduler")

def main():
    print("\n" + "="*60)
    print("BankU Server-Side Diagnostic Tool".center(60))
    print("="*60)
    
    diag = ServerDiagnostics()
    
    try:
        diag.check_system_resources()
        diag.check_database_connections()
        diag.check_database_locks()
        diag.check_flask_sessions()
        diag.check_process_threads()
        diag.test_data_collector_scheduler()
        diag.check_app_logs()
        diag.generate_fixes()
        diag.generate_report()
        
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user")
    except Exception as e:
        print(f"\n\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


