import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import schedule
import threading
from models import DataCollector, Bank, Item, Organization, User, Need, db
from flask import current_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedDataCollector:
    """Advanced data collector with web scraping and chatbot integration"""
    
    def __init__(self):
        self.drivers = {}  # Store webdriver instances
        self.running_collectors = {}  # Track running collectors
        self.rate_limits = {}  # Track rate limits per domain
        self.max_requests_per_minute = 30  # Default rate limit
        self._scheduler_running = False  # Track scheduler state
        self._scheduler_thread = None  # Store scheduler thread reference
        self._cleanup_registered = False  # Track if cleanup is registered
        
    def create_webdriver(self, headless=True):
        """Create a new webdriver instance"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            print(f"Error creating webdriver: {e}")
            return None
    
    def scrape_website(self, url: str, selectors: Dict[str, str], use_selenium: bool = False) -> List[Dict[str, Any]]:
        """Scrape data from any website using CSS selectors or XPath"""
        try:
            logger.info(f"Starting scrape of {url} with {len(selectors)} selectors")
            
            if use_selenium:
                result = self._scrape_with_selenium(url, selectors)
            else:
                result = self._scrape_with_requests(url, selectors)
            
            logger.info(f"Successfully scraped {len(result)} items from {url}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error scraping {url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            return []
    
    def _scrape_with_requests(self, url: str, selectors: Dict[str, str]) -> List[Dict[str, Any]]:
        """Scrape using requests and BeautifulSoup"""
        from urllib.parse import urlparse
        
        # Extract domain for rate limiting
        domain = urlparse(url).netloc
        
        # Check rate limit
        if not self._check_rate_limit(domain):
            self._wait_for_rate_limit(domain)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        # Extract data using selectors
        for key, selector in selectors.items():
            elements = soup.select(selector)
            for i, element in enumerate(elements):
                if i >= len(results):
                    results.append({})
                results[i][key] = element.get_text(strip=True)
        
        return results
    
    def _scrape_with_selenium(self, url: str, selectors: Dict[str, str]) -> List[Dict[str, Any]]:
        """Scrape using Selenium for JavaScript-heavy sites"""
        driver = self.create_webdriver()
        if not driver:
            return []
        
        try:
            driver.get(url)
            time.sleep(3)  # Wait for page to load
            
            results = []
            
            # Extract data using selectors
            for key, selector in selectors.items():
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for i, element in enumerate(elements):
                        if i >= len(results):
                            results.append({})
                        results[i][key] = element.text.strip()
                except Exception as e:
                    print(f"Error extracting {key}: {e}")
            
            return results
            
        finally:
            driver.quit()
    
    def scrape_google_maps(self, query: str, location: str = "") -> List[Dict[str, Any]]:
        """Scrape Google Maps for business information"""
        search_query = f"{query} {location}".strip()
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        selectors = {
            'name': '[data-value="Directions"]',
            'phone': '[data-value="Phone"]',
            'address': '[data-value="Address"]',
            'rating': '[data-value="Rating"]',
            'website': '[data-value="Website"]'
        }
        
        return self.scrape_website(url, selectors, use_selenium=True)
    
    def scrape_wikipedia(self, search_term: str) -> List[Dict[str, Any]]:
        """Scrape Wikipedia for information"""
        url = f"https://en.wikipedia.org/wiki/{search_term.replace(' ', '_')}"
        
        selectors = {
            'title': 'h1.firstHeading',
            'description': '.mw-parser-output > p:first-of-type',
            'infobox': '.infobox tr',
            'categories': '.catlinks a'
        }
        
        return self.scrape_website(url, selectors)
    
    def map_data_to_chatbot_fields(self, scraped_data: List[Dict], field_mapping: Dict[str, str]) -> List[Dict]:
        """Map scraped data to chatbot form fields"""
        mapped_data = []
        
        for item in scraped_data:
            mapped_item = {}
            for chatbot_field, scraped_field in field_mapping.items():
                if scraped_field in item:
                    mapped_item[chatbot_field] = item[scraped_field]
                else:
                    mapped_item[chatbot_field] = ""
            mapped_data.append(mapped_item)
        
        return mapped_data
    
    def _check_rate_limit(self, domain: str) -> bool:
        """Check if we can make a request to this domain"""
        import time
        current_time = time.time()
        
        if domain not in self.rate_limits:
            self.rate_limits[domain] = []
        
        # Remove requests older than 1 minute
        self.rate_limits[domain] = [
            req_time for req_time in self.rate_limits[domain] 
            if current_time - req_time < 60
        ]
        
        # Check if we're under the rate limit
        if len(self.rate_limits[domain]) < self.max_requests_per_minute:
            self.rate_limits[domain].append(current_time)
            return True
        
        logger.warning(f"Rate limit exceeded for {domain}")
        return False
    
    def _wait_for_rate_limit(self, domain: str):
        """Wait if we've hit the rate limit"""
        if domain in self.rate_limits and len(self.rate_limits[domain]) >= self.max_requests_per_minute:
            import time
            oldest_request = min(self.rate_limits[domain])
            wait_time = 60 - (time.time() - oldest_request)
            if wait_time > 0:
                logger.info(f"Waiting {wait_time:.1f} seconds for rate limit reset on {domain}")
                time.sleep(wait_time)
    
    def auto_fill_chatbot_form(self, chatbot_id: int, form_data: List[Dict], user_id: int = 1):
        """Automatically fill and submit chatbot forms"""
        from models import ChatbotFlow, ChatbotResponse, Item, Organization, User
        
        chatbot = ChatbotFlow.query.get(chatbot_id)
        if not chatbot:
            print(f"Chatbot {chatbot_id} not found")
            return False
        
        created_items = []
        
        for data in form_data:
            try:
                # Create chatbot response
                response = ChatbotResponse(
                    flow_id=chatbot_id,
                    session_id=f"collector_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    user_id=user_id,
                    responses=data,
                    completed=True,
                    completed_at=datetime.utcnow()
                )
                
                db.session.add(response)
                db.session.commit()
                
                # Create actual items based on chatbot flow type
                item = self._create_item_from_chatbot_data(chatbot, data, user_id)
                if item:
                    created_items.append(item)
                
                print(f"Successfully created chatbot response and item for {data}")
                
            except Exception as e:
                print(f"Error creating chatbot response: {e}")
                db.session.rollback()
        
        return created_items
    
    def _create_item_from_chatbot_data(self, chatbot, data: Dict, user_id: int):
        """Create actual items from chatbot data"""
        try:
            # Determine item type based on chatbot flow
            flow_type = getattr(chatbot, 'flow_type', 'item')
            
            if flow_type == 'organization':
                # Create organization
                org = Organization(
                    name=data.get('organization_name', data.get('name', 'Unknown')),
                    description=data.get('description', ''),
                    organization_type=data.get('organization_type', 'company'),
                    contact_email=data.get('contact_email', ''),
                    contact_phone=data.get('contact_phone', ''),
                    website=data.get('website_url', ''),
                    address=data.get('location', data.get('address', '')),
                    is_public=True,
                    created_by=user_id
                )
                db.session.add(org)
                db.session.commit()
                return org
                
            elif flow_type == 'user':
                # Create user (if needed)
                # Note: This might not be needed as users are typically created through registration
                pass
                
            else:
                # Create regular item
                item = Item(
                    title=data.get('title', data.get('name', 'Unknown Item')),
                    description=data.get('description', ''),
                    category=data.get('category', 'product'),
                    price=float(data.get('price', 0)) if data.get('price') else None,
                    location=data.get('location', data.get('address', '')),
                    contact_info=data.get('contact_phone', ''),
                    is_available=True,
                    profile_id=user_id,  # Assuming user has a profile
                    creator_type='user',
                    creator_id=user_id,
                    creator_name=data.get('creator_name', 'Data Collector')
                )
                db.session.add(item)
                db.session.commit()
                return item
                
        except Exception as e:
            print(f"Error creating item from chatbot data: {e}")
            db.session.rollback()
            return None
    
    def collect_internal_data(self, collector: DataCollector) -> int:
        """Collect data from internal database based on collector subcategory"""
        try:
            collected_count = 0
            
            if collector.data_type == 'organizations':
                # Filter organizations by subcategory
                if collector.subcategory:
                    from models import OrganizationType
                    org_type = OrganizationType.query.filter_by(name=collector.subcategory).first()
                    if org_type:
                        organizations = Organization.query.filter_by(organization_type_id=org_type.id).all()
                    else:
                        organizations = []
                else:
                    organizations = Organization.query.all()
                
                print(f"Found {len(organizations)} organizations matching subcategory '{collector.subcategory}'")
                collected_count = len(organizations)
                
            elif collector.data_type == 'users':
                # Filter users by subcategory (user role/tag)
                if collector.subcategory:
                    from models import Role, Tag
                    # Try to find by role first
                    role = Role.query.filter_by(name=collector.subcategory).first()
                    if role:
                        users = User.query.join(User.roles).filter(Role.id == role.id).all()
                    else:
                        # Try to find by tag
                        tag = Tag.query.filter_by(name=collector.subcategory).first()
                        if tag:
                            # This would need a many-to-many relationship between User and Tag
                            # For now, we'll use a simple approach
                            users = User.query.filter(User.tags.contains(tag.name)).all()
                        else:
                            users = []
                else:
                    users = User.query.all()
                
                print(f"Found {len(users)} users matching subcategory '{collector.subcategory}'")
                collected_count = len(users)
                
            elif collector.data_type == 'items':
                # Filter items by subcategory (item type)
                if collector.subcategory:
                    from models import ItemType
                    item_type = ItemType.query.filter_by(name=collector.subcategory).first()
                    if item_type:
                        items = Item.query.filter_by(item_type_id=item_type.id).all()
                    else:
                        items = []
                else:
                    items = Item.query.all()
                
                print(f"Found {len(items)} items matching subcategory '{collector.subcategory}'")
                collected_count = len(items)
                
            elif collector.data_type == 'needs':
                # Filter needs by subcategory (based on need type)
                if collector.subcategory:
                    # For needs, we'll filter by the need type in the description or title
                    needs = Need.query.filter(
                        Need.description.contains(collector.subcategory) |
                        Need.title.contains(collector.subcategory)
                    ).all()
                else:
                    needs = Need.query.all()
                
                print(f"Found {len(needs)} needs matching subcategory '{collector.subcategory}'")
                collected_count = len(needs)
            
            return collected_count
            
        except Exception as e:
            print(f"Error collecting internal data: {e}")
            return 0

    def run_collector(self, collector_id: int):
        """Run a specific collector"""
        from flask import current_app
        with current_app.app_context():
            try:
                collector = DataCollector.query.get(collector_id)
                if not collector or not collector.is_active:
                    return False
                
                try:
                    # Parse collector configuration
                    config = collector.filter_rules or {}
                    url = config.get('url', '')
                    selectors = config.get('selectors', {})
                    field_mapping = config.get('field_mapping', {})
                    use_selenium = config.get('use_selenium', False)
                    chatbot_id = config.get('chatbot_id')
                    
                    # Check if this is a web scraping collector or internal collector
                    if not url or not selectors:
                        # This is an internal collector - collect data based on subcategory
                        print(f"Collector {collector_id} is an internal collector (no web scraping)")
                        collected_count = self.collect_internal_data(collector)
                        collector.last_run = datetime.utcnow()
                        collector.success_count += 1
                        db.session.commit()
                        print(f"Internal collector {collector_id} completed successfully, collected {collected_count} items")
                        return True
                    
                    # Scrape data from external website
                    scraped_data = self.scrape_website(url, selectors, use_selenium)
                    
                    if not scraped_data:
                        print(f"No data scraped for collector {collector_id}")
                        return False
                    
                    # Map data to chatbot fields
                    if field_mapping and chatbot_id:
                        mapped_data = self.map_data_to_chatbot_fields(scraped_data, field_mapping)
                        
                        # Auto-fill chatbot form
                        self.auto_fill_chatbot_form(chatbot_id, mapped_data)
                    
                    # Update collector stats
                    collector.last_run = datetime.utcnow()
                    collector.success_count += 1
                    db.session.commit()
                    
                    print(f"Collector {collector_id} completed successfully")
                    return True
                    
                except Exception as e:
                    print(f"Error running collector {collector_id}: {e}")
                    collector.error_count += 1
                    collector.last_error = str(e)
                    db.session.commit()
                    return False
            finally:
                # CRITICAL FIX: Always remove session after collector runs
                # This prevents connection leaks from background threads
                try:
                    db.session.remove()
                    logger.info(f"Database session cleaned up for collector {collector_id}")
                except Exception as cleanup_error:
                    logger.warning(f"Error during session cleanup: {cleanup_error}")
    
    def start_scheduled_collectors(self):
        """Start all scheduled collectors"""
        collectors = DataCollector.query.filter_by(is_active=True).all()
        
        for collector in collectors:
            config = collector.filter_rules or {}
            schedule_type = config.get('schedule_type', 'manual')
            schedule_value = config.get('schedule_value', '')
            
            if schedule_type == 'manual':
                continue
            
            # Schedule the collector
            if schedule_type == 'seconds':
                schedule.every(int(schedule_value)).seconds.do(self.run_collector, collector.id)
            elif schedule_type == 'minutes':
                schedule.every(int(schedule_value)).minutes.do(self.run_collector, collector.id)
            elif schedule_type == 'hours':
                schedule.every(int(schedule_value)).hours.do(self.run_collector, collector.id)
            elif schedule_type == 'days':
                schedule.every(int(schedule_value)).days.do(self.run_collector, collector.id)
            elif schedule_type == 'cron':
                # Custom cron-like scheduling
                schedule.every().day.at(schedule_value).do(self.run_collector, collector.id)
        
        # Start the scheduler in a separate thread with proper cleanup
        if not hasattr(self, '_scheduler_thread') or not self._scheduler_thread or not self._scheduler_thread.is_alive():
            self._scheduler_running = True
            
            def run_scheduler():
                try:
                    while self._scheduler_running:
                        schedule.run_pending()
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"Scheduler thread error: {e}")
                finally:
                    logger.info("Scheduler thread stopped")
            
            self._scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            self._scheduler_thread.start()
            print("Scheduled collectors started")
    
    def stop_scheduled_collectors(self):
        """Stop the scheduler thread gracefully"""
        if hasattr(self, '_scheduler_running'):
            self._scheduler_running = False
            if hasattr(self, '_scheduler_thread') and self._scheduler_thread and self._scheduler_thread.is_alive():
                self._scheduler_thread.join(timeout=2.0)
                logger.info("Scheduler thread stopped gracefully")
        
        # Clean up webdriver instances
        self.cleanup_webdrivers()
    
    def cleanup_webdrivers(self):
        """Clean up all webdriver instances"""
        for driver_id, driver in self.drivers.items():
            try:
                driver.quit()
                logger.info(f"Cleaned up webdriver {driver_id}")
            except Exception as e:
                logger.warning(f"Error cleaning up webdriver {driver_id}: {e}")
        
        self.drivers.clear()
        logger.info("All webdriver instances cleaned up")
    
    def test_collector(self, collector_config) -> Dict[str, Any]:
        """Test a collector and return results"""
        # Handle both collector ID (int) and config dict
        if isinstance(collector_config, int):
            # Testing existing collector by ID
            collector = DataCollector.query.get(collector_config)
            if not collector:
                return {'success': False, 'error': 'Collector not found'}
            
            config = collector.filter_rules or {}
            url = config.get('url', '')
            selectors = config.get('selectors', {})
            use_selenium = config.get('use_selenium', False)
            
            # Check if this is a web scraping collector
            if not url or not selectors:
                return {
                    'success': False, 
                    'error': 'This collector is configured for internal data filtering, not web scraping. It cannot be tested with the web scraping engine.',
                    'collector_type': 'internal'
                }
        else:
            # Testing new collector configuration
            url = collector_config.get('url', '')
            selectors = collector_config.get('selectors', {})
            use_selenium = collector_config.get('use_selenium', False)
        
        try:
            if not url or not selectors:
                return {'success': False, 'error': 'Missing URL or selectors'}
            
            # Test scrape
            scraped_data = self.scrape_website(url, selectors, use_selenium)
            
            return {
                'success': True,
                'data_count': len(scraped_data),
                'sample_data': scraped_data[:3] if scraped_data else [],
                'message': f'Successfully scraped {len(scraped_data)} items'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cleanup_resources(self):
        """Clean up resources to prevent memory leaks"""
        try:
            logger.info("Starting resource cleanup...")
            
            # Stop all scheduled tasks
            if self._scheduler_running:
                self.stop_scheduled_collectors()
            
            # Close all webdriver instances
            for driver_id, driver in self.drivers.items():
                try:
                    driver.quit()
                    logger.info(f"Closed webdriver {driver_id}")
                except Exception as e:
                    logger.warning(f"Error closing webdriver {driver_id}: {e}")
            
            self.drivers.clear()
            
            # Clear running collectors
            self.running_collectors.clear()
            
            # Clear rate limits
            self.rate_limits.clear()
            
            # Close database connections if any
            try:
                if hasattr(self, 'db_session'):
                    self.db_session.close()
            except Exception as e:
                logger.warning(f"Error closing database session: {e}")
            
            logger.info("Resource cleanup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
    
    def register_cleanup(self):
        """Register cleanup function for graceful shutdown"""
        if not self._cleanup_registered:
            import atexit
            atexit.register(self.cleanup_resources)
            self._cleanup_registered = True
            logger.info("Cleanup function registered")

# Global instance (RE-ENABLED FOR TESTING)
advanced_collector = AdvancedDataCollector()

# Register cleanup on import (RE-ENABLED FOR TESTING)
advanced_collector.register_cleanup()
