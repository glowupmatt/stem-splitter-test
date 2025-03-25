from dotenv import load_dotenv


import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Third-party imports
from flask import Flask
from flask_cors import CORS

# Local imports
from server.api.separate_routes import separate_routes
from server.api.download_stem_routes import download_stem_routes
from server.api.clean_bucket_routes import clean_bucket_routes

# Initialize Flask app
app = Flask(__name__)
app.url_map.strict_slashes = False
load_dotenv()

# Configure CORS
CORS(app, resources={
    r"/api/*": {
        "origins": [os.getenv("CORS_ORIGIN")],
        "methods": os.getenv("CORS_METHODS").split(","),
        "allow_headers": os.getenv("CORS_HEADERS").split(","),
        "supports_credentials": os.getenv("CORS_SUPPORTS_CREDENTIALS").lower() == "true",
        "expose_headers": os.getenv("CORS_EXPOSE_HEADERS").split(",")
    }
})

# Register blueprints
app.register_blueprint(separate_routes, url_prefix="/api/separate")
app.register_blueprint(download_stem_routes, url_prefix="/api/download_stem")
app.register_blueprint(clean_bucket_routes, url_prefix="/api/clean_bucket")