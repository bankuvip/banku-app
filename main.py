# Namecheap Shared Hosting deployment entry point
import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Set environment variables for production
os.environ['FLASK_ENV'] = 'production'
os.environ['PYTHONPATH'] = project_dir

# Configure for shared hosting
os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-production-secret-key-change-this')
os.environ['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')

# Import the Flask application
from app import app

if __name__ == '__main__':
    # For shared hosting, use the port provided by the hosting provider
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=False)
