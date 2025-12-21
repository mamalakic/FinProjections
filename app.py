from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

# Register blueprints
from routes.main import main_bp
from routes.api_income import api_income_bp
from routes.api_expenses import api_expenses_bp
from routes.api_projections import api_projections_bp
from routes.api_details import api_details_bp
from routes.api_settings import api_settings_bp
from routes.api_investments import api_investments_bp
from routes.api_wishlist import api_wishlist_bp

app.register_blueprint(main_bp)
app.register_blueprint(api_income_bp)
app.register_blueprint(api_expenses_bp)
app.register_blueprint(api_projections_bp)
app.register_blueprint(api_details_bp)
app.register_blueprint(api_settings_bp)
app.register_blueprint(api_investments_bp)
app.register_blueprint(api_wishlist_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
