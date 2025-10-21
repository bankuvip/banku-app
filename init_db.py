"""
Database Initialization Script for BankU Application

This script creates an empty database with all necessary tables.
Run this script to set up a fresh database for development or deployment.

Usage:
    python init_db.py
"""

from app import app
from models import db

def init_database():
    """Initialize the database with all tables"""
    with app.app_context():
        print("Creating database tables...")
        
        # Create all tables
        db.create_all()
        
        print("✓ Database tables created successfully!")
        print("\nTables created:")
        print("- Users and Authentication")
        print("- Profiles and Items")
        print("- Organizations")
        print("- Deals and Transactions")
        print("- Wallet and Earnings")
        print("- AI Matching and Needs")
        print("- Chatbots and Data Collectors")
        print("- Analytics and Feedback")
        print("- Permissions and Roles")
        print("- Notifications and Reviews")
        print("\nDatabase is ready to use!")

if __name__ == '__main__':
    print("BankU Database Initialization")
    print("=" * 50)
    
    init_database()

