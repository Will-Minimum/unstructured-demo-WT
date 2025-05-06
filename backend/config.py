import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration."""
    
    # Base directory for the application
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Directory to store uploaded files
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    
    # Unstructured API URL and key
    UNSTRUCTURED_API_URL = os.environ.get('UNSTRUCTURED_API_URL', 'https://api.unstructuredapp.io/general/v0/general')
    UNSTRUCTURED_API_KEY = os.environ.get('UNSTRUCTURED_API_KEY')
    
    # Claude API key (will be read from environment)
    ANTHROPIC_API_KEY = os.environ.get('CLAUDE_API_KEY', os.environ.get('ANTHROPIC_API_KEY'))
    
    # Logging configuration
    LOG_LEVEL = logging.DEBUG
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    LOG_FILE = os.path.join(LOGS_DIR, 'extraction_flow.log')
    
    # Make sure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # App settings
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # Extraction settings
    DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'claude-3-opus-20240229')
    
    # Ensure required directories exist
    @staticmethod
    def init_app(app):
        """Initialize the application with configuration."""
        # Ensure upload folder exists
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Ensure log directory exists
        log_dir = os.path.dirname(Config.LOG_FILE)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            
        # Log loaded environment variables for debugging
        if app.logger:
            app.logger.debug(f"UNSTRUCTURED_API_URL: {Config.UNSTRUCTURED_API_URL}")
            app.logger.debug(f"UNSTRUCTURED_API_KEY set: {bool(Config.UNSTRUCTURED_API_KEY)}")
            app.logger.debug(f"ANTHROPIC_API_KEY set: {bool(Config.ANTHROPIC_API_KEY)}")
