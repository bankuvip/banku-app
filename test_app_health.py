#!/usr/bin/env python3
"""
Simple Non-Interactive App Health Test
Run this on the server to quickly check if the app is responding
"""

import sys
import os
import time

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

def test_local_health():
    """Test the app health by importing it directly (no HTTP required)"""
    print("="*60)
    print("BankU Health Test (Server-Side)".center(60))
    print("="*60)
    print()
    
    try:
        print("1. Testing app import...")
        from app import app, db
        print("   ✓ App imported successfully")
        
        print("\n2. Testing database connection...")
        with app.app_context():
            try:
                result = db.session.execute(db.text("SELECT 1")).fetchone()
                print("   ✓ Database connected")
                
                # Check connection pool
                print("\n3. Checking database connection pool...")
                engine = db.engine
                pool = engine.pool
                
                pool_size = pool.size()
                checked_out = pool.checkedout()
                overflow = pool.overflow()
                checked_in = pool.checkedin()
                
                print(f"   Pool Size: {pool_size}")
                print(f"   Checked Out: {checked_out}")
                print(f"   Overflow: {overflow}")
                print(f"   Checked In: {checked_in}")
                
                # Calculate usage percentage
                if pool_size > 0:
                    usage = (checked_out / pool_size) * 100
                    print(f"\n   Pool Usage: {usage:.1f}%")
                    
                    if usage > 80:
                        print("   ⚠ WARNING: Pool usage is HIGH!")
                        print("   This may cause the app to hang soon!")
                        print("\n   RECOMMENDED ACTION:")
                        print("   - Run: python apply_session_fix.py")
                        print("   - Restart the application")
                    elif usage > 50:
                        print("   ⚠ Pool usage is moderate - monitor closely")
                    else:
                        print("   ✓ Pool usage is healthy")
                else:
                    print("   Note: Could not determine pool size")
                
            except Exception as e:
                print(f"   ✗ Database error: {str(e)}")
                return False
        
        print("\n4. Testing system resources...")
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            
            print(f"   CPU Usage: {cpu}%")
            print(f"   Memory Usage: {memory.percent}%")
            
            if memory.percent > 80:
                print("   ⚠ WARNING: High memory usage!")
            if cpu > 80:
                print("   ⚠ WARNING: High CPU usage!")
                
        except ImportError:
            print("   Note: psutil not available, skipping resource check")
        
        print("\n5. Testing for long-running queries...")
        with app.app_context():
            try:
                # Check for long queries
                long_queries = db.session.execute(db.text("""
                    SELECT 
                        ID,
                        USER,
                        TIME,
                        STATE,
                        LEFT(INFO, 50) as QUERY_PREVIEW
                    FROM information_schema.PROCESSLIST
                    WHERE COMMAND != 'Sleep'
                    AND TIME > 5
                    LIMIT 5
                """)).fetchall()
                
                if long_queries:
                    print(f"   ⚠ Found {len(long_queries)} long-running queries:")
                    for q in long_queries:
                        print(f"     - Query running for {q[2]}s")
                else:
                    print("   ✓ No long-running queries")
                    
            except Exception as e:
                print(f"   Note: Could not check queries: {str(e)}")
        
        print("\n" + "="*60)
        print("SUMMARY".center(60))
        print("="*60)
        print("\n✓ App is operational")
        print("\nTo fix the hanging issue permanently:")
        print("  1. Run: python apply_session_fix.py")
        print("  2. Restart your application")
        print("\nTo monitor remotely:")
        print("  Visit: https://banku.vip/health/api")
        print("\n" + "="*60)
        
        return True
        
    except ImportError as e:
        print(f"✗ Error importing app: {str(e)}")
        print("\nMake sure you're running this from the app directory")
        return False
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_local_health()
    sys.exit(0 if success else 1)


