#!/usr/bin/env python3
"""
Quick Fix Script - Adds proper database session cleanup to app.py
This fixes the most common cause of app hanging (database connection pool exhaustion)
"""

import os
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create a backup of the file"""
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"✓ Backup created: {backup_path}")
    return backup_path

def apply_session_cleanup_fix(app_file='app.py'):
    """Add session cleanup handlers to app.py"""
    
    if not os.path.exists(app_file):
        print(f"✗ Error: {app_file} not found!")
        return False
    
    # Backup first
    print(f"\nBacking up {app_file}...")
    backup_file(app_file)
    
    # Read current content
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if fix is already applied
    if 'teardown_appcontext' in content and 'shutdown_session' in content:
        print("✓ Session cleanup handlers already exist!")
        return True
    
    # Find where to insert the cleanup code (after error handlers, before routes)
    session_cleanup_code = '''
# Database session cleanup (CRITICAL FIX FOR APP HANGING)
@app.teardown_appcontext
def shutdown_session(exception=None):
    """
    Ensure database sessions are properly closed after each request.
    This prevents connection pool exhaustion which causes app hanging.
    """
    try:
        db.session.remove()
    except Exception as e:
        logger.error(f"Error removing session in teardown_appcontext: {e}")

@app.teardown_request
def teardown_request(exception=None):
    """
    Close database connections and rollback on errors.
    This ensures no connections are left open.
    """
    if exception:
        try:
            db.session.rollback()
            logger.warning(f"Session rolled back due to exception: {exception}")
        except Exception as e:
            logger.error(f"Error rolling back session: {e}")
    
    try:
        db.session.close()
    except Exception as e:
        logger.error(f"Error closing session in teardown_request: {e}")

'''
    
    # Find a good insertion point - after error handlers, before routes
    # Look for the @app.route('/') line
    lines = content.split('\n')
    insertion_index = None
    
    for i, line in enumerate(lines):
        # Insert before the first @app.route or @app.before_request
        if "@app.route('/')" in line or "def index():" in line:
            insertion_index = i
            break
    
    if insertion_index is None:
        # Fallback: insert after load_user
        for i, line in enumerate(lines):
            if "def load_user" in line:
                # Find end of this function
                for j in range(i+1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                        insertion_index = j
                        break
                break
    
    if insertion_index is None:
        print("✗ Could not find appropriate insertion point!")
        print("  Please manually add the session cleanup code to app.py")
        print("\nCode to add:")
        print(session_cleanup_code)
        return False
    
    # Insert the cleanup code
    lines.insert(insertion_index, session_cleanup_code)
    new_content = '\n'.join(lines)
    
    # Write back
    with open(app_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✓ Session cleanup handlers added to {app_file}!")
    print("\nAdded functions:")
    print("  - shutdown_session() - removes sessions after each request")
    print("  - teardown_request() - closes connections and rolls back on errors")
    
    return True

def increase_connection_pool(app_file='app.py'):
    """Increase database connection pool settings"""
    
    print("\nUpdating connection pool settings...")
    
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update pool settings
    replacements = [
        ("'pool_size': 10,", "'pool_size': 20,  # Increased for better concurrency"),
        ("'max_overflow': 20,", "'max_overflow': 40,  # Increased to handle spikes"),
        ("'pool_timeout': 30", "'pool_timeout': 30,  # Timeout for getting connection from pool")
    ]
    
    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
            print(f"  ✓ Updated: {old} -> {new}")
    
    if modified:
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ Connection pool settings updated!")
    else:
        print("  Note: Pool settings not found or already updated")
    
    return modified

def add_connection_monitoring(app_file='app.py'):
    """Add connection pool monitoring to health endpoint"""
    
    print("\nNote: Connection pool monitoring is handled by health_monitor.py")
    print("  Make sure /health endpoint is accessible to monitor pool status")

def main():
    print("="*60)
    print("BankU Session Cleanup Fix".center(60))
    print("="*60)
    print("\nThis script will:")
    print("  1. Backup your current app.py")
    print("  2. Add proper database session cleanup handlers")
    print("  3. Increase connection pool size")
    print("\nThis should fix the app hanging issue!")
    print("="*60)
    
    try:
        response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        # Non-interactive mode - proceed automatically
        response = 'yes'
        print("\nNon-interactive mode detected - proceeding automatically...")
    
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    print("\nApplying fixes...\n")
    
    success = apply_session_cleanup_fix()
    
    if success:
        increase_connection_pool()
        add_connection_monitoring()
        
        print("\n" + "="*60)
        print("FIXES APPLIED SUCCESSFULLY!".center(60))
        print("="*60)
        print("\nNext steps:")
        print("  1. Review the changes in app.py")
        print("  2. Restart your application:")
        print("     - Stop the current app")
        print("     - Start it again (python app.py or restart web server)")
        print("  3. Monitor with: python server_diagnostics.py")
        print("  4. Test from remote: python diagnose_app.py")
        print("\nThe app should no longer hang!")
        print("\nIf issues persist:")
        print("  - Run server_diagnostics.py to check for other issues")
        print("  - Check database logs")
        print("  - Review recent code changes")
    else:
        print("\n✗ Fix could not be applied automatically")
        print("  Please manually add the session cleanup code")

if __name__ == "__main__":
    main()

