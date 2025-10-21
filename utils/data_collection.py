from datetime import datetime
from models import db, DataCollector, BankContent, Bank, Item, Organization, User, UserNeed

class DataCollectionEngine:
    """Automatic data collection engine"""
    
    def __init__(self):
        self.collectors = {}
    
    def load_active_collectors(self):
        """Load all active collectors"""
        try:
            self.collectors = {
                collector.id: collector 
                for collector in DataCollector.query.filter_by(is_active=True).all()
            }
        except Exception as e:
            print(f"Warning: Could not load collectors: {e}")
            self.collectors = {}
    
    def on_data_created(self, data_type, data_id):
        """Called when new data is created"""
        print(f"Data collection triggered: {data_type} ID {data_id}")
        
        relevant_collectors = self.get_collectors_for_type(data_type)
        
        for collector in relevant_collectors:
            if self.should_collect(collector, data_id):
                print(f"Running collector: {collector.name}")
                self.run_collector(collector.id, data_id)
    
    def get_collectors_for_type(self, data_type):
        """Get all collectors for a specific data type"""
        return [
            collector for collector in self.collectors.values()
            if collector.data_type == data_type
        ]
    
    def should_collect(self, collector, data_id):
        """Check if collector should collect this specific data"""
        if not collector.filter_rules:
            return True
        
        # Get the data object
        data_obj = self.get_data_object(collector.data_type, data_id)
        if not data_obj:
            return False
        
        # Apply filter rules
        return self.apply_filter_rules(collector.filter_rules, data_obj)
    
    def get_data_object(self, data_type, data_id):
        """Get the actual data object"""
        if data_type == 'organizations':
            return Organization.query.get(data_id)
        elif data_type == 'users':
            return User.query.get(data_id)
        elif data_type == 'items':
            return Item.query.get(data_id)
        elif data_type == 'needs':
            return UserNeed.query.get(data_id)
        return None
    
    def apply_filter_rules(self, rules, data_obj):
        """Apply filter rules to data object"""
        for field, value in rules.items():
            if not hasattr(data_obj, field):
                return False
            if getattr(data_obj, field) != value:
                return False
        return True
    
    def run_collector(self, collector_id, specific_id=None):
        """Run a specific collector"""
        collector = self.collectors.get(collector_id)
        if not collector:
            return
        
        try:
            if collector.data_type == 'organizations':
                data = self.collect_organizations(collector, specific_id)
            elif collector.data_type == 'users':
                data = self.collect_users(collector, specific_id)
            elif collector.data_type == 'items':
                data = self.collect_items(collector, specific_id)
            elif collector.data_type == 'needs':
                data = self.collect_needs(collector, specific_id)
            else:
                return
            
            self.update_banks(collector, data)
            self.update_collector_stats(collector, success=True)
            
        except Exception as e:
            print(f"Collector error: {str(e)}")
            self.update_collector_stats(collector, success=False, error=str(e))
    
    def collect_organizations(self, collector, specific_id=None):
        """Collect organization data"""
        query = Organization.query
        
        if specific_id:
            query = query.filter_by(id=specific_id)
        
        # Apply filter rules
        if collector.filter_rules:
            for field, value in collector.filter_rules.items():
                if hasattr(Organization, field):
                    query = query.filter(getattr(Organization, field) == value)
        
        return query.all()
    
    def collect_users(self, collector, specific_id=None):
        """Collect user data"""
        query = User.query
        
        if specific_id:
            query = query.filter_by(id=specific_id)
        
        # Apply filter rules
        if collector.filter_rules:
            for field, value in collector.filter_rules.items():
                if hasattr(User, field):
                    query = query.filter(getattr(User, field) == value)
        
        return query.all()
    
    def collect_items(self, collector, specific_id=None):
        """Collect item data"""
        query = Item.query
        
        if specific_id:
            query = query.filter_by(id=specific_id)
        
        # Apply filter rules
        if collector.filter_rules:
            for field, value in collector.filter_rules.items():
                if hasattr(Item, field):
                    query = query.filter(getattr(Item, field) == value)
        
        return query.all()
    
    def collect_needs(self, collector, specific_id=None):
        """Collect need data"""
        query = UserNeed.query
        
        if specific_id:
            query = query.filter_by(id=specific_id)
        
        # Apply filter rules
        if collector.filter_rules:
            for field, value in collector.filter_rules.items():
                if hasattr(UserNeed, field):
                    query = query.filter(getattr(UserNeed, field) == value)
        
        return query.all()
    
    def update_banks(self, collector, data):
        """Update banks with collected data"""
        # Get all banks connected to this collector
        connected_banks = Bank.query.join(BankCollector).filter(
            BankCollector.collector_id == collector.id,
            BankCollector.is_active == True
        ).all()
        
        for bank in connected_banks:
            for item in data:
                # Check if item already exists in bank
                existing = BankContent.query.filter_by(
                    bank_id=bank.id,
                    content_type=collector.data_type,
                    content_id=item.id
                ).first()
                
                if not existing:
                    # Add to bank
                    bank_content = BankContent(
                        bank_id=bank.id,
                        content_type=collector.data_type,
                        content_id=item.id,
                        added_by_collector=collector.id
                    )
                    db.session.add(bank_content)
                    
                    # Update bank statistics
                    bank.content_count += 1
                    bank.last_updated = datetime.utcnow()
        
        db.session.commit()
    
    def update_collector_stats(self, collector, success=True, error=None):
        """Update collector statistics"""
        collector.last_run = datetime.utcnow()
        
        if success:
            collector.success_count += 1
        else:
            collector.error_count += 1
            if error:
                collector.last_error = error
        
        db.session.commit()

# Global instance
collection_engine = DataCollectionEngine()
