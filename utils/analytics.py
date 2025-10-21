"""
Advanced Analytics and Monitoring Service
Comprehensive tracking, A/B testing, and performance monitoring
"""

import time
import psutil
import uuid
from datetime import datetime, timedelta
from flask import request, current_app, g
from models import db, AnalyticsEvent, ABTest, ABTestAssignment, PerformanceMetric
from functools import wraps
import traceback
import json

class AnalyticsService:
    """Centralized analytics and tracking service"""
    
    @staticmethod
    def track_event(event_type, event_name, properties=None, user_id=None, **kwargs):
        """Track a user event or system event"""
        try:
            event = AnalyticsEvent(
                event_type=event_type,
                event_name=event_name,
                user_id=user_id or (g.user.id if hasattr(g, 'user') and g.user.is_authenticated else None),
                session_id=kwargs.get('session_id'),
                properties=properties or {},
                page_url=kwargs.get('page_url', request.url if request else None),
                referrer=kwargs.get('referrer', request.referrer if request else None),
                user_agent=kwargs.get('user_agent', request.user_agent.string if request else None),
                ip_address=kwargs.get('ip_address', request.remote_addr if request else None),
                button_id=kwargs.get('button_id'),
                item_type_id=kwargs.get('item_type_id'),
                chatbot_id=kwargs.get('chatbot_id')
            )
            
            db.session.add(event)
            db.session.commit()
            return event.id
        except Exception as e:
            current_app.logger.error(f"Failed to track event: {str(e)}")
            return None
    
    @staticmethod
    def track_button_click(button_id, button_name, user_id=None):
        """Track button clicks specifically"""
        return AnalyticsService.track_event(
            event_type='button_click',
            event_name=button_name,
            properties={'button_id': button_id},
            user_id=user_id,
            button_id=button_id
        )
    
    @staticmethod
    def track_page_view(page_name, user_id=None):
        """Track page views"""
        return AnalyticsService.track_event(
            event_type='page_view',
            event_name=page_name,
            user_id=user_id
        )
    
    @staticmethod
    def track_chatbot_start(chatbot_id, chatbot_name, user_id=None):
        """Track chatbot starts"""
        return AnalyticsService.track_event(
            event_type='chatbot_start',
            event_name=chatbot_name,
            user_id=user_id,
            chatbot_id=chatbot_id
        )
    
    @staticmethod
    def track_chatbot_completion(chatbot_id, chatbot_name, user_id=None, completion_data=None):
        """Track chatbot completions"""
        return AnalyticsService.track_event(
            event_type='chatbot_completion',
            event_name=chatbot_name,
            properties={'completion_data': completion_data} if completion_data else {},
            user_id=user_id,
            chatbot_id=chatbot_id
        )

class ABTestingService:
    """A/B Testing framework service"""
    
    @staticmethod
    def create_test(name, description, test_type, variants, traffic_split, target_metric, created_by):
        """Create a new A/B test"""
        try:
            test = ABTest(
                name=name,
                description=description,
                test_type=test_type,
                variants=variants,
                traffic_split=traffic_split,
                target_metric=target_metric,
                created_by=created_by,
                status='draft'
            )
            
            db.session.add(test)
            db.session.commit()
            return test
        except Exception as e:
            current_app.logger.error(f"Failed to create A/B test: {str(e)}")
            return None
    
    @staticmethod
    def assign_user_to_test(test_id, user_id):
        """Assign a user to a test variant"""
        try:
            # Check if user is already assigned
            existing = ABTestAssignment.query.filter_by(test_id=test_id, user_id=user_id).first()
            if existing:
                return existing.variant
            
            # Get test configuration
            test = ABTest.query.get(test_id)
            if not test or test.status != 'active':
                return None
            
            # Determine variant based on traffic split
            variant = ABTestingService._determine_variant(test.traffic_split)
            
            # Create assignment
            assignment = ABTestAssignment(
                test_id=test_id,
                user_id=user_id,
                variant=variant
            )
            
            db.session.add(assignment)
            db.session.commit()
            return variant
        except Exception as e:
            current_app.logger.error(f"Failed to assign user to test: {str(e)}")
            return None
    
    @staticmethod
    def _determine_variant(traffic_split):
        """Determine which variant to assign based on traffic split"""
        import random
        rand = random.randint(1, 100)
        cumulative = 0
        
        for variant, percentage in traffic_split.items():
            cumulative += percentage
            if rand <= cumulative:
                return variant
        
        return list(traffic_split.keys())[0]  # Fallback to first variant
    
    @staticmethod
    def get_user_variant(test_id, user_id):
        """Get the variant assigned to a user for a specific test"""
        assignment = ABTestAssignment.query.filter_by(test_id=test_id, user_id=user_id).first()
        return assignment.variant if assignment else None
    
    @staticmethod
    def calculate_test_results(test_id):
        """Calculate A/B test results"""
        try:
            test = ABTest.query.get(test_id)
            if not test:
                return None
            
            # Get all assignments for this test
            assignments = ABTestAssignment.query.filter_by(test_id=test_id).all()
            
            # Calculate metrics for each variant
            results = {}
            for variant in test.traffic_split.keys():
                variant_assignments = [a for a in assignments if a.variant == variant]
                variant_users = [a.user_id for a in variant_assignments]
                
                # Calculate conversion rate based on target metric
                if test.target_metric == 'conversion_rate':
                    # This would need to be customized based on what conversion means
                    conversions = AnalyticsEvent.query.filter(
                        AnalyticsEvent.user_id.in_(variant_users),
                        AnalyticsEvent.event_type == 'conversion'
                    ).count()
                    
                    conversion_rate = (conversions / len(variant_users)) * 100 if variant_users else 0
                    
                    results[variant] = {
                        'users': len(variant_users),
                        'conversions': conversions,
                        'conversion_rate': conversion_rate
                    }
            
            # Update test results
            test.results = results
            db.session.commit()
            
            return results
        except Exception as e:
            current_app.logger.error(f"Failed to calculate test results: {str(e)}")
            return None

class PerformanceMonitoringService:
    """Performance monitoring and metrics collection"""
    
    @staticmethod
    def track_performance(metric_name, metric_value, metric_unit=None, endpoint=None, method=None, user_id=None):
        """Track a performance metric"""
        try:
            metric = PerformanceMetric(
                metric_name=metric_name,
                metric_value=metric_value,
                metric_unit=metric_unit,
                endpoint=endpoint,
                method=method,
                user_id=user_id
            )
            
            db.session.add(metric)
            db.session.commit()
            return metric.id
        except Exception as e:
            current_app.logger.error(f"Failed to track performance metric: {str(e)}")
            return None
    
    @staticmethod
    def get_system_metrics():
        """Get current system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            return {
                'cpu_usage': cpu_percent,
                'memory_usage': memory_percent,
                'memory_used_mb': memory_used_mb,
                'disk_usage': disk_percent,
                'timestamp': datetime.utcnow()
            }
        except Exception as e:
            current_app.logger.error(f"Failed to get system metrics: {str(e)}")
            return None
    
    @staticmethod
    def record_system_health():
        """Record overall system health"""
        try:
            metrics = PerformanceMonitoringService.get_system_metrics()
            if not metrics:
                return None
            
            # Calculate health score (0-100)
            health_score = 100
            
            # Deduct points for high usage
            if metrics['cpu_usage'] > 80:
                health_score -= 20
            elif metrics['cpu_usage'] > 60:
                health_score -= 10
            
            if metrics['memory_usage'] > 90:
                health_score -= 25
            elif metrics['memory_usage'] > 75:
                health_score -= 15
            
            if metrics['disk_usage'] > 90:
                health_score -= 20
            elif metrics['disk_usage'] > 80:
                health_score -= 10
            
            # Determine health status
            if health_score >= 80:
                status = 'healthy'
            elif health_score >= 60:
                status = 'warning'
            else:
                status = 'critical'
            
            # Record health
            # Convert datetime to string for JSON serialization
            metrics_serializable = metrics.copy()
            if 'timestamp' in metrics_serializable:
                metrics_serializable['timestamp'] = metrics_serializable['timestamp'].isoformat()
            
            health = SystemHealth(
                health_status=status,
                overall_score=health_score,
                response_time_avg=PerformanceMonitoringService._get_avg_response_time(),
                error_rate=PerformanceMonitoringService._get_error_rate(),
                memory_usage=metrics['memory_usage'],
                cpu_usage=metrics['cpu_usage'],
                active_users=PerformanceMonitoringService._get_active_users(),
                details=metrics_serializable
            )
            
            db.session.add(health)
            db.session.commit()
            
            return health
        except Exception as e:
            current_app.logger.error(f"Failed to record system health: {str(e)}")
            return None
    
    @staticmethod
    def _get_avg_response_time():
        """Get average response time from recent metrics"""
        try:
            recent_metrics = PerformanceMetric.query.filter(
                PerformanceMetric.metric_name == 'response_time',
                PerformanceMetric.recorded_at >= datetime.utcnow() - timedelta(minutes=5)
            ).all()
            
            if not recent_metrics:
                return 0
            
            return sum(m.metric_value for m in recent_metrics) / len(recent_metrics)
        except:
            return 0
    
    @staticmethod
    def _get_error_rate():
        """Get error rate from recent logs"""
        try:
            recent_errors = ErrorLog.query.filter(
                ErrorLog.occurred_at >= datetime.utcnow() - timedelta(minutes=5)
            ).count()
            
            recent_events = AnalyticsEvent.query.filter(
                AnalyticsEvent.created_at >= datetime.utcnow() - timedelta(minutes=5)
            ).count()
            
            if recent_events == 0:
                return 0
            
            return (recent_errors / recent_events) * 100
        except:
            return 0
    
    @staticmethod
    def _get_active_users():
        """Get count of active users in last 5 minutes"""
        try:
            return AnalyticsEvent.query.filter(
                AnalyticsEvent.created_at >= datetime.utcnow() - timedelta(minutes=5)
            ).with_entities(AnalyticsEvent.user_id).distinct().count()
        except:
            return 0

class ErrorTrackingService:
    """Error tracking and logging service"""
    
    @staticmethod
    def log_error(error_type, error_message, stack_trace=None, user_id=None, **kwargs):
        """Log an error"""
        try:
            error = ErrorLog(
                error_type=error_type,
                error_message=error_message,
                stack_trace=stack_trace,
                user_id=user_id,
                endpoint=kwargs.get('endpoint'),
                method=kwargs.get('method'),
                session_id=kwargs.get('session_id'),
                ip_address=kwargs.get('ip_address', request.remote_addr if request else None),
                user_agent=kwargs.get('user_agent', request.user_agent.string if request else None)
            )
            
            db.session.add(error)
            db.session.commit()
            return error.id
        except Exception as e:
            current_app.logger.error(f"Failed to log error: {str(e)}")
            return None

# Decorators for automatic tracking

def track_performance(metric_name, metric_unit=None):
    """Decorator to automatically track function performance"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                PerformanceMonitoringService.track_performance(
                    metric_name=metric_name,
                    metric_value=response_time,
                    metric_unit=metric_unit or 'ms',
                    endpoint=request.endpoint if request else None,
                    method=request.method if request else None,
                    user_id=g.user.id if hasattr(g, 'user') and g.user.is_authenticated else None
                )
        return decorated_function
    return decorator

def track_errors(f):
    """Decorator to automatically track errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            ErrorTrackingService.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                user_id=g.user.id if hasattr(g, 'user') and g.user.is_authenticated else None,
                endpoint=request.endpoint if request else None,
                method=request.method if request else None
            )
            raise
    return decorated_function
