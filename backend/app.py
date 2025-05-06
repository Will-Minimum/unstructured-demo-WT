import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from controllers.extraction_controller import extraction_bp
from config import Config

def setup_logging():
    """Configure logging for the application."""
    # Clear any existing log file
    if os.path.exists(Config.LOG_FILE):
        open(Config.LOG_FILE, 'w').close()
    
    # Configure root logger
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Log to file
            logging.FileHandler(Config.LOG_FILE),
            # Also log to console
            logging.StreamHandler()
        ]
    )
    
    # Create a logger for this module
    logger = logging.getLogger(__name__)
    logger.info("Logging configured")
    logger.info(f"Log file: {Config.LOG_FILE}")

def create_app():
    """Create and configure the Flask application."""
    # Set up logging first
    setup_logging()
    
    # Get a logger for this function
    logger = logging.getLogger(__name__)
    logger.info("Creating Flask application")
    
    # Create the Flask app
    app = Flask(__name__)
    
    # Configure the app
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app)
    
    # Register blueprints
    app.register_blueprint(extraction_bp, url_prefix='/api')
    
    # Add a health check route
    @app.route('/api/health', methods=['GET'])
    def health_check():
        logger.info("Health check request received")
        return jsonify({'status': 'ok'})
    
    logger.info("Flask application created and configured")
    return app

# Create the application
app = create_app()

if __name__ == '__main__':
    # Run the application
    logging.getLogger(__name__).info("Starting Flask development server on port 5002")
    app.run(debug=True, host='0.0.0.0', port=5002)
