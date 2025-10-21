#!/usr/bin/env python3
"""
Simple Health Monitoring Script
Run this regularly (cron/task scheduler) to catch issues before app hangs
"""

import sys
import os
import requests
import json
from datetime import datetime
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class HealthMonitor:
    def __init__(self, url="https://banku.vip", alert_threshold=None):
        self.url = url
        self.alert_threshold = alert_threshold or {
            'response_time': 5.0,  # seconds
            'pool_usage': 80,      # percent
            'memory': 80,          # percent
            'cpu': 80              # percent
        }
        self.alerts = []
        
    def check_health(self):
        """Check /health endpoint and analyze results"""
        try:
            import time
            start = time.time()
            
            response = requests.get(
                f"{self.url}/health",
                timeout=10,
                verify=False
            )
            
            response_time = time.time() - start
            
            if response.status_code != 200:
                self.alerts.append(f"CRITICAL: Health endpoint returned {response.status_code}")
                return False
            
            # Check response time
            if response_time > self.alert_threshold['response_time']:
                self.alerts.append(f"WARNING: Slow response time: {response_time:.2f}s")
            
            # Parse health data
            try:
                health_data = response.json()
                
                # Check database pool
                if 'pool_status' in health_data:
                    pool = health_data['pool_status']
                    if 'checked_out' in pool and 'size' in pool:
                        usage = (pool['checked_out'] / pool['size']) * 100 if pool['size'] > 0 else 0
                        if usage > self.alert_threshold['pool_usage']:
                            self.alerts.append(f"CRITICAL: Database pool at {usage:.1f}% ({pool['checked_out']}/{pool['size']})")
                
                # Check memory
                if 'memory_percent' in health_data:
                    mem = health_data['memory_percent']
                    if mem > self.alert_threshold['memory']:
                        self.alerts.append(f"WARNING: High memory usage: {mem}%")
                
                # Check CPU
                if 'cpu_percent' in health_data:
                    cpu = health_data['cpu_percent']
                    if cpu > self.alert_threshold['cpu']:
                        self.alerts.append(f"WARNING: High CPU usage: {cpu}%")
                
                # Check database connectivity
                if 'database' in health_data:
                    if health_data['database'] != 'connected':
                        self.alerts.append(f"CRITICAL: Database not connected: {health_data['database']}")
                
                return True
                
            except json.JSONDecodeError:
                self.alerts.append("ERROR: Health endpoint returned invalid JSON")
                return False
                
        except requests.exceptions.Timeout:
            self.alerts.append("CRITICAL: Health endpoint timeout - app may be hung!")
            return False
            
        except requests.exceptions.ConnectionError:
            self.alerts.append("CRITICAL: Cannot connect to application!")
            return False
            
        except Exception as e:
            self.alerts.append(f"ERROR: {str(e)}")
            return False
    
    def check_homepage(self):
        """Quick check if homepage is responding"""
        try:
            import time
            start = time.time()
            response = requests.get(self.url, timeout=10, verify=False)
            response_time = time.time() - start
            
            if response.status_code != 200:
                self.alerts.append(f"WARNING: Homepage returned {response.status_code}")
                
            if response_time > 3:
                self.alerts.append(f"WARNING: Slow homepage: {response_time:.2f}s")
                
            return True
            
        except Exception as e:
            self.alerts.append(f"ERROR: Homepage check failed: {str(e)}")
            return False
    
    def log_result(self, filename="health_monitor.log"):
        """Log monitoring results"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(filename, 'a') as f:
            f.write(f"\n{timestamp} - Health Check\n")
            
            if not self.alerts:
                f.write("  Status: OK\n")
            else:
                f.write(f"  Status: {len(self.alerts)} alert(s)\n")
                for alert in self.alerts:
                    f.write(f"  - {alert}\n")
    
    def send_notification(self):
        """Send notification if critical issues found"""
        critical_alerts = [a for a in self.alerts if 'CRITICAL' in a]
        
        if critical_alerts:
            # You can implement email, SMS, or webhook notification here
            print("CRITICAL ALERTS DETECTED!")
            for alert in critical_alerts:
                print(f"  - {alert}")
            
            # Example: Write to alert file that can be monitored
            with open('CRITICAL_ALERTS.txt', 'w') as f:
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write("Critical Issues:\n")
                for alert in critical_alerts:
                    f.write(f"  - {alert}\n")
    
    def print_status(self):
        """Print status to console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n{'='*60}")
        print(f"Health Check - {timestamp}")
        print(f"{'='*60}")
        
        if not self.alerts:
            print("✓ Status: OK")
            print("  All systems operational")
        else:
            print(f"⚠ Status: {len(self.alerts)} issue(s) detected")
            print()
            for alert in self.alerts:
                if 'CRITICAL' in alert:
                    print(f"  🔴 {alert}")
                elif 'WARNING' in alert:
                    print(f"  🟡 {alert}")
                else:
                    print(f"  ℹ {alert}")
        
        print(f"{'='*60}\n")
    
    def run(self, verbose=True):
        """Run all health checks"""
        # Check health endpoint
        health_ok = self.check_health()
        
        # Check homepage
        homepage_ok = self.check_homepage()
        
        # Log results
        self.log_result()
        
        # Print if verbose
        if verbose:
            self.print_status()
        
        # Send notifications for critical issues
        self.send_notification()
        
        # Return overall status
        return len([a for a in self.alerts if 'CRITICAL' in a]) == 0

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor BankU application health')
    parser.add_argument('--url', default='https://banku.vip', help='Application URL')
    parser.add_argument('--quiet', action='store_true', help='Quiet mode (no console output)')
    parser.add_argument('--log', default='health_monitor.log', help='Log file path')
    
    args = parser.parse_args()
    
    monitor = HealthMonitor(url=args.url)
    status_ok = monitor.run(verbose=not args.quiet)
    
    # Exit with status code
    sys.exit(0 if status_ok else 1)

if __name__ == "__main__":
    main()


