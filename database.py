"""Database connection and collections"""
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection
mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['budget_tracker']

# Collections
settings_collection = db['settings']
recurring_income_collection = db['recurring_income']
one_time_income_collection = db['one_time_income']
recurring_expense_collection = db['recurring_expense']
one_time_expense_collection = db['one_time_expense']
payday_adjustment_collection = db['payday_adjustment']

# Helper function to get current currency settings
def get_currency_settings():
    settings = settings_collection.find_one()
    if not settings:
        settings = {
            'currency_code': 'USD',
            'currency_symbol': '$',
            'created_at': datetime.utcnow()
        }
        settings_collection.insert_one(settings)
    return {
        'code': settings['currency_code'],
        'symbol': settings['currency_symbol']
    }


