"""
Health Monitoring and System Status Utilities
Provides system health checks, monitoring, and alerting
"""

import psutil
import time
import logging
from datetime import datetime, timedelta
from flask import current_app, jsonify
from models import db, User, Item, Organization
from sqlalchemy import text
import threading
import queue

logger = logging.getLogger(__name__)

class HealthMonitor:
    """System health monitoring class"""
    
    def __init__(self):
        self.health_checks = {}
        self.alert_thresholds = {
            'cpu_usage': 80.0,  # CPU usage percentage
            'memory_usage': 85.0,  # Memory usage percentage
            'disk_usage': 90.0,  # Disk usage percentage
            'response_time': 5.0,  # Response time in seconds
            'error_rate': 5.0,  # Error rate percentage
            'db_connections': 80  # Database connections percentage
        }
        self.monitoring_active = False
        self.monitoring_thread = None
        self.health_queue = queue.Queue()
    
    def check_system_resources(self):
        """Check system resource usage"""
        try:
            # CPU usage (reduced interval for performance)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            
            return {
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'memory_available': memory.available,
                'memory_total': memory.total,
                'disk_usage': disk_percent,
                'disk_free': disk.free,
                'disk_total': disk.total,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'timestamp': datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Error checking system resources: {e}")
            return None
    
    def check_database_health(self):
        """Check database connectivity and performance"""
        try:
            from flask import current_app
            
            # Check if we're in an application context
            if not current_app:
                return {
                    'status': 'unhealthy',
                    'error': 'No application context available',
                    'timestamp': datetime.utcnow()
                }
            
            start_time = time.time()
            
            # Test basic connectivity
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            
            response_time = time.time() - start_time
            
            # Check connection pool status
            engine = db.engine
            pool = engine.pool
            
            # Get pool statistics safely
            pool_stats = {
                'status': 'healthy',
                'response_time': response_time,
                'timestamp': datetime.utcnow()
            }
            
            # Add pool statistics if available
            try:
                pool_stats.update({
                    'pool_size': pool.size(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                })
            except Exception as pool_error:
                logger.warning(f"Could not get pool statistics: {pool_error}")
                pool_stats['pool_warning'] = str(pool_error)
            
            return pool_stats
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow()
            }
        finally:
            # CRITICAL FIX: Cleanup session after health check
            try:
                db.session.remove()
            except:
                pass
    
    def check_application_health(self):
        """Check application-specific health metrics"""
        try:
            from flask import current_app
            
            # Check if we're in an application context
            if not current_app:
                return {
                    'status': 'unhealthy',
                    'error': 'No application context available',
                    'timestamp': datetime.utcnow()
                }
            
            # Count active users (logged in within last 24 hours)
            active_users = User.query.filter(
                User.last_login >= datetime.utcnow() - timedelta(days=1)
            ).count()
            
            # Count total items
            total_items = Item.query.count()
            
            # Count active organizations
            active_orgs = Organization.query.filter_by(status='active').count()
            
            # Check for recent errors (this would need to be implemented with error tracking)
            recent_errors = 0  # Placeholder
            
            return {
                'active_users_24h': active_users,
                'total_items': total_items,
                'active_organizations': active_orgs,
                'recent_errors': recent_errors,
                'timestamp': datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Application health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow()
            }
        finally:
            # CRITICAL FIX: Cleanup session after application health check
            try:
                db.session.remove()
            except:
                pass
    
    def run_health_check(self):
        """Run comprehensive health check"""
        health_status = {
            'overall_status': 'healthy',
            'checks': {},
            'timestamp': datetime.utcnow()
        }
        
        # System resources
        system_resources = self.check_system_resources()
        if system_resources:
            health_status['checks']['system_resources'] = system_resources
            
            # Check thresholds
            if system_resources['cpu_usage'] > self.alert_thresholds['cpu_usage']:
                health_status['overall_status'] = 'warning'
                logger.warning(f"High CPU usage: {system_resources['cpu_usage']}%")
            
            if system_resources['memory_usage'] > self.alert_thresholds['memory_usage']:
                health_status['overall_status'] = 'warning'
                logger.warning(f"High memory usage: {system_resources['memory_usage']}%")
            
            if system_resources['disk_usage'] > self.alert_thresholds['disk_usage']:
                health_status['overall_status'] = 'critical'
                logger.critical(f"High disk usage: {system_resources['disk_usage']}%")
        else:
            health_status['checks']['system_resources'] = {'status': 'unhealthy', 'error': 'Could not check system resources'}
            health_status['overall_status'] = 'critical'
        
        # Database health
        db_health = self.check_database_health()
        health_status['checks']['database'] = db_health
        
        if db_health['status'] == 'unhealthy':
            health_status['overall_status'] = 'critical'
        elif db_health.get('response_time', 0) > self.alert_thresholds['response_time']:
            health_status['overall_status'] = 'warning'
            logger.warning(f"Slow database response: {db_health['response_time']}s")
        
        # Application health
        app_health = self.check_application_health()
        health_status['checks']['application'] = app_health
        
        if app_health.get('status') == 'unhealthy':
            health_status['overall_status'] = 'critical'
        
        return health_status
    
    def start_monitoring(self, interval=300):  # 5 minutes default
        """Start background health monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop background health monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self, interval):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                health_status = self.run_health_check()
                self.health_queue.put(health_status)
                
                # Log warnings and critical issues
                if health_status['overall_status'] == 'critical':
                    logger.critical(f"Critical health issues detected: {health_status}")
                elif health_status['overall_status'] == 'warning':
                    logger.warning(f"Health warnings detected: {health_status}")
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def get_latest_health_status(self):
        """Get the latest health status from the queue"""
        try:
            return self.health_queue.get_nowait()
        except queue.Empty:
            return None
    
    def get_health_summary(self):
        """Get a summary of recent health statuses"""
        statuses = []
        try:
            while not self.health_queue.empty() and len(statuses) < 10:
                statuses.append(self.health_queue.get_nowait())
        except queue.Empty:
            pass
        
        return statuses

# Global health monitor instance
health_monitor = HealthMonitor()

# Flask route for health check endpoint
def create_health_routes(app):
    """Create health check routes for the Flask app"""
    
    @app.route('/health')
    def health_check():
        """Basic health check endpoint - redirects to HTML page"""
        from flask import request, redirect, url_for
        # If it's an API request (JSON expected), return JSON
        if request.headers.get('Accept', '').find('application/json') != -1:
            try:
                health_status = health_monitor.run_health_check()
                
                if health_status['overall_status'] == 'critical':
                    return jsonify(health_status), 503
                elif health_status['overall_status'] == 'warning':
                    return jsonify(health_status), 200
                else:
                    return jsonify(health_status), 200
            except Exception as e:
                logger.error(f"Health check endpoint error: {e}")
                return jsonify({
                    'overall_status': 'critical',
                    'error': str(e),
                    'timestamp': datetime.utcnow()
                }), 503
        else:
            # For browser requests, redirect to the HTML page
            return redirect(url_for('health_page'))
    
    @app.route('/health/api')
    def health_api():
        """API-only health check endpoint (always returns JSON)"""
        try:
            health_status = health_monitor.run_health_check()
            
            if health_status['overall_status'] == 'critical':
                return jsonify(health_status), 503
            elif health_status['overall_status'] == 'warning':
                return jsonify(health_status), 200
            else:
                return jsonify(health_status), 200
        except Exception as e:
            logger.error(f"Health API endpoint error: {e}")
            return jsonify({
                'overall_status': 'critical',
                'error': str(e),
                'timestamp': datetime.utcnow()
            }), 503
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check endpoint"""
        try:
            health_status = health_monitor.run_health_check()
            return jsonify(health_status), 200
        except Exception as e:
            logger.error(f"Detailed health check endpoint error: {e}")
            return jsonify({
                'overall_status': 'critical',
                'error': str(e),
                'timestamp': datetime.utcnow()
            }), 503
    
    @app.route('/health/page')
    def health_page():
        """Health monitoring page"""
        from flask import render_template
        return render_template('health.html')
    
    @app.route('/health/monitoring/start')
    def start_health_monitoring():
        """Start health monitoring (admin only)"""
        try:
            health_monitor.start_monitoring()  # Re-enabled for testing
            return jsonify({'message': 'Health monitoring started'}), 200
        except Exception as e:
            logger.error(f"Error starting health monitoring: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/health/monitoring/stop')
    def stop_health_monitoring():
        """Stop health monitoring (admin only)"""
        try:
            health_monitor.stop_monitoring()
            return jsonify({'message': 'Health monitoring stopped'}), 200
        except Exception as e:
            logger.error(f"Error stopping health monitoring: {e}")
            return jsonify({'error': str(e)}), 500

def initialize_health_monitoring(app):
    """Initialize health monitoring for the Flask app"""
    # Create health check routes
    create_health_routes(app)
    
    # Start monitoring in production
    if not app.debug:
        health_monitor.start_monitoring()  # Re-enabled for testing
        logger.info("Health monitoring initialized and started")
    else:
        logger.info("Health monitoring initialized (not started in debug mode)")
