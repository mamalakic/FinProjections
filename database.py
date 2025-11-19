"""Database connection and collections"""
from pymongo import MongoClient
from datetime import datetime

mongo_client = MongoClient('mongodb://localhost:27017/')
db = mongo_client['budget_tracker']

settings_collection = db['settings']
recurring_income_collection = db['recurring_income']
one_time_income_collection = db['one_time_income']
recurring_expense_collection = db['recurring_expense']
one_time_expense_collection = db['one_time_expense']
payday_adjustment_collection = db['payday_adjustment']
wishlist_collection = db['wishlist']
wishlist_categories_collection = db['wishlist_categories']

def get_currency_settings():
    settings = settings_collection.find_one()
    if not settings:
        settings = {
            'currency_code': 'USD',
            'currency_symbol': '$',
            'date_format': 'DD/MM/YYYY',
            'created_at': datetime.utcnow()
        }
        settings_collection.insert_one(settings)
    return {
        'code': settings['currency_code'],
        'symbol': settings['currency_symbol']
    }

def get_date_format():
    settings = settings_collection.find_one()
    if not settings or 'date_format' not in settings:
        # Default to DD/MM/YYYY if not set
        settings_collection.update_one(
            {},
            {'$set': {'date_format': 'DD/MM/YYYY'}},
            upsert=True
        )
        return 'DD/MM/YYYY'
    return settings['date_format']

def get_wishlist_categories():
    """Get all wishlist categories (preset + custom)"""
    # Default preset categories
    preset_categories = [
        {'name': 'Electronics', 'icon': 'ri-smartphone-line', 'is_custom': False},
        {'name': 'Furniture', 'icon': 'ri-home-4-line', 'is_custom': False},
        {'name': 'Travel', 'icon': 'ri-flight-takeoff-line', 'is_custom': False},
        {'name': 'Vehicle', 'icon': 'ri-car-line', 'is_custom': False},
        {'name': 'Education', 'icon': 'ri-book-open-line', 'is_custom': False},
        {'name': 'Health', 'icon': 'ri-heart-pulse-line', 'is_custom': False},
        {'name': 'Entertainment', 'icon': 'ri-movie-2-line', 'is_custom': False},
        {'name': 'Other', 'icon': 'ri-more-line', 'is_custom': False}
    ]
    
    # Get custom categories from database
    custom_categories = list(wishlist_categories_collection.find())
    
    # Combine preset and custom categories
    all_categories = preset_categories.copy()
    for cat in custom_categories:
        all_categories.append({
            'name': cat['name'],
            'icon': cat.get('icon', 'ri-bookmark-line'),
            'is_custom': True,
            'id': str(cat['_id'])
        })
    
    return all_categories

