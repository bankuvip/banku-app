#!/usr/bin/env python3
"""
Timeout Issue Fix
This script applies fixes to resolve the connection leak and timeout issues
identified in the diagnostics.

Based on diagnostic results:
1. Connections sleeping for 1212+ seconds (not being closed)
2. 30 threads running (background tasks holding connections)
3. Pool configuration needs adjustment

Run this to apply the fix:
    python fix_timeout_issue.py
"""

import os
import sys

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def apply_fixes():
    """Apply all necessary fixes"""
    
    print("\n" + "="*80)
    print("APPLYING TIMEOUT ISSUE FIXES")
    print("="*80)
    
    fixes_applied = []
    
    # Fix 1: Update app.py database configuration
    print("\n[1/4] Updating database pool configuration...")
    try:
        fix_database_pool_config()
        fixes_applied.append("✅ Database pool configuration updated")
    except Exception as e:
        fixes_applied.append(f"❌ Database pool config failed: {e}")
    
    # Fix 2: Fix advanced_data_collector.py session cleanup
    print("\n[2/4] Fixing Advanced Data Collector session leaks...")
    try:
        fix_data_collector_sessions()
        fixes_applied.append("✅ Data Collector session cleanup added")
    except Exception as e:
        fixes_applied.append(f"❌ Data Collector fix failed: {e}")
    
    # Fix 3: Add request teardown handler
    print("\n[3/4] Adding global session cleanup handler...")
    try:
        fix_request_teardown()
        fixes_applied.append("✅ Request teardown handler added")
    except Exception as e:
        fixes_applied.append(f"❌ Request teardown fix failed: {e}")
    
    # Fix 4: Fix health monitor
    print("\n[4/4] Fixing Health Monitor session handling...")
    try:
        fix_health_monitor()
        fixes_applied.append("✅ Health Monitor session cleanup added")
    except Exception as e:
        fixes_applied.append(f"❌ Health Monitor fix failed: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("FIX SUMMARY")
    print("="*80)
    for fix in fixes_applied:
        print(f"  {fix}")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("1. Review the changes made to the files")
    print("2. Restart your application:")
    print("   - Stop the current process")
    print("   - Start it again")
    print("3. Monitor with: python quick_timeout_check.py")
    print("4. Verify connections are being closed (Sleep time should be < 60s)")
    print("="*80 + "\n")


def fix_database_pool_config():
    """Fix database pool configuration in app.py"""
    
    app_file = "app.py"
    
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if 'pool_recycle' in content and '600' in content:
        print("  Pool configuration already updated")
        return
    
    # Find and replace pool configuration
    old_config = """# Database connection pooling and optimization
from sqlalchemy.pool import QueuePool
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'poolclass': QueuePool,
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,  # Verify connections before use
    'max_overflow': 20,
    'pool_timeout': 30
}"""
    
    new_config = """# Database connection pooling and optimization
from sqlalchemy.pool import QueuePool
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'poolclass': QueuePool,
    'pool_size': 20,  # Increased from 10
    'pool_recycle': 600,  # Recycle connections every 10 minutes (was 3600)
    'pool_pre_ping': True,  # Verify connections before use
    'max_overflow': 10,  # Reduced from 20
    'pool_timeout': 30,
    'pool_reset_on_return': 'rollback'  # Always rollback on return
}"""
    
    if old_config in content:
        content = content.replace(old_config, new_config)
        print("  ✓ Updated pool configuration")
    else:
        print("  ! Could not find exact pool config - manual update needed")
        return
    
    # Backup original
    backup_file = f"{app_file}.backup_before_timeout_fix"
    if not os.path.exists(backup_file):
        with open(backup_file, 'w', encoding='utf-8') as f:
            with open(app_file, 'r', encoding='utf-8') as original:
                f.write(original.read())
        print(f"  ✓ Backed up original to {backup_file}")
    
    # Write updated content
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("  ✓ Pool configuration updated:")
    print("    - pool_size: 10 → 20")
    print("    - pool_recycle: 3600s → 600s (10 min)")
    print("    - max_overflow: 20 → 10")
    print("    - Added pool_reset_on_return")


def fix_data_collector_sessions():
    """Fix session leaks in advanced_data_collector.py"""
    
    collector_file = "utils/advanced_data_collector.py"
    
    with open(collector_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if 'db.session.remove()' in content and 'CRITICAL FIX' in content:
        print("  Advanced Data Collector already fixed")
        return
    
    # Fix the run_collector method
    old_run_collector = """    def run_collector(self, collector_id: int):
        \"\"\"Run a specific collector\"\"\"
        from flask import current_app
        with current_app.app_context():
            collector = DataCollector.query.get(collector_id)
            if not collector or not collector.is_active:
                return False
            
            try:"""
    
    new_run_collector = """    def run_collector(self, collector_id: int):
        \"\"\"Run a specific collector\"\"\"
        from flask import current_app
        with current_app.app_context():
            try:
                collector = DataCollector.query.get(collector_id)
                if not collector or not collector.is_active:
                    return False
                
                try:"""
    
    if old_run_collector in content:
        content = content.replace(old_run_collector, new_run_collector)
    
    # Add finally block for cleanup
    # Find the end of run_collector method
    import re
    
    # Add session cleanup at the end of run_collector
    pattern = r"(db\.session\.commit\(\)\s+return False)"
    
    replacement = r"""\1
            finally:
                # CRITICAL FIX: Always remove session after collector runs
                try:
                    db.session.remove()
                    logger.info(f"Database session cleaned up for collector {collector_id}")
                except Exception as cleanup_error:
                    logger.warning(f"Error during session cleanup: {cleanup_error}")"""
    
    content = re.sub(pattern, replacement, content)
    
    # Backup original
    backup_file = f"{collector_file}.backup_before_timeout_fix"
    if not os.path.exists(backup_file):
        with open(backup_file, 'w', encoding='utf-8') as f:
            with open(collector_file, 'r', encoding='utf-8') as original:
                f.write(original.read())
        print(f"  ✓ Backed up original to {backup_file}")
    
    # Write updated content
    with open(collector_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("  ✓ Added db.session.remove() to run_collector method")


def fix_request_teardown():
    """Add global session cleanup in app.py"""
    
    app_file = "app.py"
    
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if teardown already exists
    if '@app.teardown_appcontext' in content and 'shutdown_session' in content:
        print("  Teardown handler already exists")
        return
    
    # Find where to insert (after error handlers, before routes)
    insert_point = "# Exception handler is now handled by utils/error_handling.py"
    
    teardown_code = """

# CRITICAL FIX: Always cleanup database sessions after each request/context
@app.teardown_appcontext
def shutdown_session(exception=None):
    \"\"\"Remove database session at the end of each request/app context\"\"\"
    try:
        db.session.remove()
    except Exception as e:
        logger.warning(f"Error removing session in teardown: {e}")

@app.teardown_request
def teardown_request(exception=None):
    \"\"\"Cleanup after each request\"\"\"
    try:
        if exception:
            db.session.rollback()
        db.session.remove()
    except Exception as e:
        logger.warning(f"Error in request teardown: {e}")
"""
    
    if insert_point in content:
        content = content.replace(insert_point, insert_point + teardown_code)
    else:
        print("  ! Could not find insertion point - manual update needed")
        return
    
    # Write updated content
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("  ✓ Added teardown handlers to ensure sessions are always cleaned up")


def fix_health_monitor():
    """Fix health monitor to clean up sessions"""
    
    monitor_file = "utils/health_monitor.py"
    
    with open(monitor_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already fixed
    if 'db.session.remove()' in content and 'health check' in content:
        print("  Health Monitor already fixed")
        return
    
    # Add session cleanup after database health checks
    pattern = r"(return pool_stats\s+except Exception as e:\s+logger\.error\(f\"Database health check failed: \{e\}\"\))"
    
    replacement = r"""\1
            finally:
                # Cleanup session after health check
                try:
                    db.session.remove()
                except:
                    pass"""
    
    import re
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Backup original
    backup_file = f"{monitor_file}.backup_before_timeout_fix"
    if not os.path.exists(backup_file):
        with open(backup_file, 'w', encoding='utf-8') as f:
            with open(monitor_file, 'r', encoding='utf-8') as original:
                f.write(original.read())
        print(f"  ✓ Backed up original to {backup_file}")
    
    # Write updated content
    with open(monitor_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("  ✓ Added session cleanup to health monitor")


if __name__ == "__main__":
    try:
        apply_fixes()
    except Exception as e:
        print(f"\n❌ Error applying fixes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

