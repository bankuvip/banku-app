#!/usr/bin/env python3
"""
BankU Application Diagnostic Tool
Tests for common issues that cause app hanging/freezing
"""

import requests
import time
import sys
import json
from datetime import datetime
import threading
from collections import defaultdict

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")

class AppDiagnostics:
    def __init__(self, base_url="https://banku.vip"):
        self.base_url = base_url
        self.results = {}
        self.issues_found = []
        
    def test_basic_connectivity(self):
        """Test if the app responds at all"""
        print_header("Test 1: Basic Connectivity")
        
        try:
            print_info(f"Testing connection to {self.base_url}...")
            start_time = time.time()
            response = requests.get(self.base_url, timeout=10, verify=False)
            response_time = time.time() - start_time
            
            print_success(f"Server responded in {response_time:.2f} seconds")
            print_success(f"Status Code: {response.status_code}")
            
            self.results['connectivity'] = {
                'status': 'OK',
                'response_time': response_time,
                'status_code': response.status_code
            }
            
            if response_time > 5:
                self.issues_found.append(f"SLOW RESPONSE: Homepage took {response_time:.2f}s (should be < 2s)")
                print_warning(f"Response time is high! This suggests performance issues.")
                
        except requests.exceptions.Timeout:
            print_error("TIMEOUT: Server did not respond within 10 seconds")
            self.issues_found.append("CRITICAL: Server timeout - app may be hung")
            self.results['connectivity'] = {'status': 'TIMEOUT'}
            
        except requests.exceptions.ConnectionError as e:
            print_error(f"CONNECTION ERROR: {str(e)}")
            self.issues_found.append("CRITICAL: Cannot connect to server")
            self.results['connectivity'] = {'status': 'CONNECTION_ERROR'}
            
        except Exception as e:
            print_error(f"ERROR: {str(e)}")
            self.results['connectivity'] = {'status': 'ERROR', 'message': str(e)}
    
    def test_health_endpoint(self):
        """Test the health monitoring endpoint"""
        print_header("Test 2: Health Endpoint Check")
        
        try:
            print_info("Checking /health endpoint...")
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=10, verify=False)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                print_success(f"Health endpoint responded in {response_time:.2f}s")
                try:
                    health_data = response.json()
                    print_success(f"Status: {health_data.get('status', 'unknown')}")
                    
                    # Check database connection
                    if 'database' in health_data:
                        db_status = health_data['database']
                        print_info(f"Database: {db_status}")
                        if db_status != 'connected':
                            self.issues_found.append(f"DATABASE ISSUE: {db_status}")
                            
                    # Check memory usage
                    if 'memory_percent' in health_data:
                        mem = health_data['memory_percent']
                        print_info(f"Memory Usage: {mem}%")
                        if mem > 80:
                            self.issues_found.append(f"HIGH MEMORY: {mem}% (threshold: 80%)")
                            print_warning(f"Memory usage is high!")
                            
                    # Check CPU
                    if 'cpu_percent' in health_data:
                        cpu = health_data['cpu_percent']
                        print_info(f"CPU Usage: {cpu}%")
                        if cpu > 80:
                            self.issues_found.append(f"HIGH CPU: {cpu}%")
                            
                    self.results['health'] = health_data
                    
                except json.JSONDecodeError:
                    print_warning("Health endpoint returned non-JSON response")
                    
            else:
                print_error(f"Health endpoint returned status {response.status_code}")
                
        except requests.exceptions.Timeout:
            print_error("Health endpoint timeout")
            self.issues_found.append("Health endpoint hanging - possible app freeze")
            
        except Exception as e:
            print_error(f"Health check failed: {str(e)}")
    
    def test_concurrent_requests(self):
        """Test how app handles multiple concurrent requests"""
        print_header("Test 3: Concurrent Request Handling")
        
        num_requests = 10
        results = defaultdict(list)
        
        def make_request(i):
            try:
                start = time.time()
                r = requests.get(self.base_url, timeout=30, verify=False)
                duration = time.time() - start
                results['times'].append(duration)
                results['statuses'].append(r.status_code)
                results['success'].append(True)
                print_info(f"Request {i+1}: {r.status_code} in {duration:.2f}s")
            except Exception as e:
                results['success'].append(False)
                results['errors'].append(str(e))
                print_error(f"Request {i+1} failed: {str(e)}")
        
        print_info(f"Sending {num_requests} concurrent requests...")
        threads = []
        start_time = time.time()
        
        for i in range(num_requests):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join(timeout=35)
        
        total_time = time.time() - start_time
        
        successes = sum(results['success'])
        failures = len(results['success']) - successes
        
        print_success(f"Completed: {successes}/{num_requests} successful")
        
        if failures > 0:
            print_error(f"Failures: {failures}")
            self.issues_found.append(f"CONCURRENT REQUEST FAILURES: {failures}/{num_requests} failed")
        
        if results['times']:
            avg_time = sum(results['times']) / len(results['times'])
            max_time = max(results['times'])
            print_info(f"Average response time: {avg_time:.2f}s")
            print_info(f"Max response time: {max_time:.2f}s")
            
            if avg_time > 5:
                self.issues_found.append(f"SLOW CONCURRENT RESPONSES: avg {avg_time:.2f}s")
                
        self.results['concurrent'] = {
            'total_requests': num_requests,
            'successful': successes,
            'failed': failures,
            'total_time': total_time,
            'avg_time': avg_time if results['times'] else 0,
            'max_time': max_time if results['times'] else 0
        }
    
    def test_database_endpoints(self):
        """Test endpoints that interact with database"""
        print_header("Test 4: Database-Heavy Endpoints")
        
        endpoints = [
            '/auth/login',
            '/banks',
            '/deals',
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                print_info(f"Testing {endpoint}...")
                start = time.time()
                response = requests.get(url, timeout=10, verify=False, allow_redirects=False)
                duration = time.time() - start
                
                print_success(f"{endpoint}: {response.status_code} in {duration:.2f}s")
                
                if duration > 3:
                    print_warning(f"{endpoint} is slow ({duration:.2f}s)")
                    self.issues_found.append(f"SLOW ENDPOINT: {endpoint} took {duration:.2f}s")
                    
            except requests.exceptions.Timeout:
                print_error(f"{endpoint}: TIMEOUT")
                self.issues_found.append(f"TIMEOUT: {endpoint} not responding")
                
            except Exception as e:
                print_error(f"{endpoint}: {str(e)}")
    
    def test_repeated_requests(self):
        """Test for memory leaks by making repeated requests"""
        print_header("Test 5: Memory Leak Detection (Repeated Requests)")
        
        num_iterations = 20
        print_info(f"Making {num_iterations} sequential requests to detect memory leaks...")
        
        times = []
        for i in range(num_iterations):
            try:
                start = time.time()
                requests.get(self.base_url, timeout=10, verify=False)
                duration = time.time() - start
                times.append(duration)
                
                if (i + 1) % 5 == 0:
                    print_info(f"Completed {i+1}/{num_iterations} requests")
                    
            except Exception as e:
                print_error(f"Request {i+1} failed: {str(e)}")
        
        if times:
            # Check if response times are increasing (sign of memory leak)
            first_half_avg = sum(times[:len(times)//2]) / (len(times)//2)
            second_half_avg = sum(times[len(times)//2:]) / (len(times) - len(times)//2)
            
            print_info(f"First half avg: {first_half_avg:.2f}s")
            print_info(f"Second half avg: {second_half_avg:.2f}s")
            
            if second_half_avg > first_half_avg * 1.5:
                print_warning("Response times increasing - possible memory leak!")
                self.issues_found.append("MEMORY LEAK SUSPECTED: Response times degrading over time")
            else:
                print_success("No memory leak detected in this test")
                
            self.results['memory_leak_test'] = {
                'first_half_avg': first_half_avg,
                'second_half_avg': second_half_avg,
                'degradation': (second_half_avg / first_half_avg - 1) * 100
            }
    
    def test_long_request(self):
        """Test with a very long timeout to see if app eventually responds"""
        print_header("Test 6: Long Request Test (60s timeout)")
        
        print_info("Testing with 60 second timeout to check if app is just slow or completely hung...")
        
        try:
            start = time.time()
            response = requests.get(self.base_url, timeout=60, verify=False)
            duration = time.time() - start
            
            print_success(f"Response received after {duration:.2f} seconds")
            print_success(f"Status: {response.status_code}")
            
            if duration > 30:
                print_warning("CRITICAL: App is extremely slow (>30s)")
                self.issues_found.append(f"EXTREME SLOWNESS: {duration:.2f}s response time")
            elif duration > 10:
                print_warning("App is very slow (>10s)")
                self.issues_found.append(f"VERY SLOW: {duration:.2f}s response time")
                
        except requests.exceptions.Timeout:
            print_error("TIMEOUT even after 60 seconds - app is completely hung")
            self.issues_found.append("CRITICAL: App completely unresponsive (60s+ timeout)")
            
        except Exception as e:
            print_error(f"Error: {str(e)}")
    
    def generate_report(self):
        """Generate diagnostic report"""
        print_header("DIAGNOSTIC REPORT")
        
        print(f"{Colors.BOLD}Timestamp:{Colors.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Colors.BOLD}Target:{Colors.ENDC} {self.base_url}")
        print()
        
        if not self.issues_found:
            print_success("No critical issues detected!")
            print_info("Your app appears to be functioning normally.")
        else:
            print_error(f"Found {len(self.issues_found)} issue(s):")
            print()
            for i, issue in enumerate(self.issues_found, 1):
                print(f"  {i}. {issue}")
            
            print()
            print_header("RECOMMENDED ACTIONS")
            
            # Analyze issues and provide recommendations
            issue_text = ' '.join(self.issues_found).upper()
            
            if 'TIMEOUT' in issue_text or 'HUNG' in issue_text:
                print_warning("⚠ APP HANGING DETECTED")
                print("  Possible causes:")
                print("  • Database connection pool exhausted")
                print("  • Deadlocked database queries")
                print("  • Infinite loops in code")
                print("  • Worker/thread exhaustion")
                print()
                print("  Recommended fixes:")
                print("  1. Check database connection pool settings")
                print("  2. Look for uncommitted database transactions")
                print("  3. Review recent code changes for loops/blocking calls")
                print("  4. Increase worker processes/threads")
                print("  5. Check server logs for errors")
                
            if 'MEMORY' in issue_text or 'LEAK' in issue_text:
                print_warning("⚠ MEMORY ISSUES DETECTED")
                print("  Possible causes:")
                print("  • Database sessions not being closed")
                print("  • Large objects accumulating in memory")
                print("  • Cache not being cleared")
                print()
                print("  Recommended fixes:")
                print("  1. Ensure db.session.close() is called after requests")
                print("  2. Add db.session.remove() in teardown")
                print("  3. Review caching strategy")
                print("  4. Monitor memory usage over time")
                
            if 'SLOW' in issue_text:
                print_warning("⚠ PERFORMANCE ISSUES DETECTED")
                print("  Possible causes:")
                print("  • Inefficient database queries")
                print("  • Missing database indexes")
                print("  • Too many database connections")
                print("  • External API calls blocking requests")
                print()
                print("  Recommended fixes:")
                print("  1. Add database query logging")
                print("  2. Review and optimize slow queries")
                print("  3. Add database indexes")
                print("  4. Use async for external API calls")
                
            if 'DATABASE' in issue_text:
                print_warning("⚠ DATABASE ISSUES DETECTED")
                print("  Recommended fixes:")
                print("  1. Check database server status")
                print("  2. Verify connection string is correct")
                print("  3. Check for locked tables: SHOW FULL PROCESSLIST;")
                print("  4. Review connection pool configuration")
        
        # Save report to file
        report_file = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'target': self.base_url,
                'results': self.results,
                'issues': self.issues_found
            }, f, indent=2)
        
        print()
        print_success(f"Detailed report saved to: {report_file}")

def main():
    print(f"{Colors.BOLD}{Colors.OKCYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         BankU Application Diagnostic Tool                  ║")
    print("║         Detecting app hanging & performance issues         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    # Check if custom URL provided
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        # Try to get input, but use default if not in interactive mode
        try:
            base_url = input(f"\nEnter your app URL [{Colors.OKGREEN}https://banku.vip{Colors.ENDC}]: ").strip()
            if not base_url:
                base_url = "https://banku.vip"
        except (EOFError, KeyboardInterrupt):
            # Non-interactive mode - use default
            base_url = "https://banku.vip"
            print(f"\nUsing default URL: {base_url}")
    
    # Disable SSL warnings for self-signed certificates
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    diag = AppDiagnostics(base_url)
    
    try:
        diag.test_basic_connectivity()
        diag.test_health_endpoint()
        diag.test_concurrent_requests()
        diag.test_database_endpoints()
        diag.test_repeated_requests()
        diag.test_long_request()
        
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Diagnostic interrupted by user{Colors.ENDC}")
    
    finally:
        diag.generate_report()

if __name__ == "__main__":
    main()
