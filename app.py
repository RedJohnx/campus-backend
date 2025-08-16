"""
Main Flask application entry point for Campus Assets system.
"""
from flask import Flask
from flask_cors import CORS
from config import Config
from database import init_db
import os

def create_app():
    """Application factory pattern for Flask app creation."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize CORS with more permissive settings
    CORS(app, resources={r"/api/*": {"origins": "*", "supports_credentials": True}}, 
         allow_headers=["Content-Type", "Authorization", "Accept"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    # Initialize database
    init_db()
    
    # Register blueprints with explicit URL prefixes
    from auth import auth_bp
    from resources import resources_bp
    from file_processor import file_upload_bp
    from ai_integration import ai_bp
    from dashboard import dashboard_bp
    from export import export_bp

    # Ensure URL prefixes are properly set
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(resources_bp, url_prefix='/api/resources')
    app.register_blueprint(file_upload_bp, url_prefix='/api/upload')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(export_bp, url_prefix='/api/export')

    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

    @app.route('/')
    def index():
        """Root endpoint for basic server check."""
        return {'message': 'Campus Assets API is running', 'status': 'healthy'}

    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        return {'status': 'healthy', 'message': 'Campus Assets API is running'}
    
    @app.after_request
    def after_request(response):
        """Add CORS headers to all responses."""
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response

    return app

# Create app instance for testing and imports
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

