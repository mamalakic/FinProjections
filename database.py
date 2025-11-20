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

# Demo data marker - all demo documents will have this field
DEMO_MARKER = {'is_demo_data': True}

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

def is_demo_mode_enabled():
    """Check if demo mode is currently enabled"""
    settings = settings_collection.find_one()
    return settings.get('demo_mode', False) if settings else False

def get_data_filter():
    """
    Get the appropriate filter for querying data based on demo mode.
    When demo mode is ON: only show demo data
    When demo mode is OFF: only show real data (exclude demo data)
    """
    if is_demo_mode_enabled():
        # Show only demo data
        return {'is_demo_data': True}
    else:
        # Show only real data (exclude demo data)
        return {'is_demo_data': {'$ne': True}}

def generate_demo_data():
    """Generate comprehensive demo data for showcasing the application"""
    from datetime import timedelta
    
    # Clear any existing demo data first
    clear_demo_data()
    
    now = datetime.utcnow()
    today = datetime(now.year, now.month, now.day)
    
    # Demo recurring income
    demo_recurring_income = [
        {
            'name': 'Monthly Salary',
            'amount': 4500.00,
            'frequency': 'monthly',
            'start_date': today - timedelta(days=365),
            'end_date': None,
            'payday': 25,
            'active': True,
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Freelance Work',
            'amount': 800.00,
            'frequency': 'monthly',
            'start_date': today - timedelta(days=180),
            'end_date': None,
            'payday': 15,
            'active': True,
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        }
    ]
    recurring_income_collection.insert_many(demo_recurring_income)
    
    # Demo one-time income
    demo_one_time_income = [
        {
            'name': 'Tax Refund',
            'amount': 1200.00,
            'date': today - timedelta(days=45),
            'category': 'Tax Return',
            'notes': 'Annual tax refund',
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Bonus',
            'amount': 2000.00,
            'date': today + timedelta(days=30),
            'category': 'Work Bonus',
            'notes': 'Year-end performance bonus',
            'upcoming': True,
            'created_at': now,
            **DEMO_MARKER
        }
    ]
    one_time_income_collection.insert_many(demo_one_time_income)
    
    # Demo recurring expenses
    demo_recurring_expenses = [
        {
            'name': 'Rent',
            'amount': 1200.00,
            'frequency': 'monthly',
            'start_date': today - timedelta(days=365),
            'end_date': None,
            'category': 'Housing',
            'payday': 1,
            'active': True,
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Utilities',
            'amount': 150.00,
            'frequency': 'monthly',
            'start_date': today - timedelta(days=365),
            'end_date': None,
            'category': 'Housing',
            'payday': 5,
            'active': True,
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Internet',
            'amount': 60.00,
            'frequency': 'monthly',
            'start_date': today - timedelta(days=365),
            'end_date': None,
            'category': 'Utilities',
            'payday': 10,
            'active': True,
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Gym Membership',
            'amount': 45.00,
            'frequency': 'monthly',
            'start_date': today - timedelta(days=180),
            'end_date': None,
            'category': 'Health',
            'payday': 15,
            'active': True,
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Streaming Services',
            'amount': 35.00,
            'frequency': 'monthly',
            'start_date': today - timedelta(days=365),
            'end_date': None,
            'category': 'Entertainment',
            'payday': 20,
            'active': True,
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Car Insurance',
            'amount': 120.00,
            'frequency': 'monthly',
            'start_date': today - timedelta(days=365),
            'end_date': None,
            'category': 'Transportation',
            'payday': 1,
            'active': True,
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        }
    ]
    recurring_expense_collection.insert_many(demo_recurring_expenses)
    
    # Demo one-time expenses
    demo_one_time_expenses = [
        {
            'name': 'New Laptop',
            'amount': 1200.00,
            'date': today - timedelta(days=60),
            'category': 'Electronics',
            'notes': 'Work laptop upgrade',
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Car Repair',
            'amount': 450.00,
            'date': today - timedelta(days=30),
            'category': 'Transportation',
            'notes': 'Brake replacement',
            'upcoming': False,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Vacation',
            'amount': 2500.00,
            'date': today + timedelta(days=90),
            'category': 'Travel',
            'notes': 'Summer vacation to Italy',
            'upcoming': True,
            'created_at': now,
            **DEMO_MARKER
        }
    ]
    one_time_expense_collection.insert_many(demo_one_time_expenses)
    
    # Demo wishlist items
    demo_wishlist = [
        {
            'name': 'New Smartphone',
            'cost': 999.00,
            'category': 'Electronics',
            'priority': 'high',
            'target_date': today + timedelta(days=60),
            'notes': 'iPhone 15 Pro',
            'url': 'https://www.apple.com',
            'purchased': False,
            'purchased_date': None,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Standing Desk',
            'cost': 450.00,
            'category': 'Furniture',
            'priority': 'medium',
            'target_date': today + timedelta(days=120),
            'notes': 'Ergonomic standing desk for home office',
            'url': '',
            'purchased': False,
            'purchased_date': None,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Weekend Getaway',
            'cost': 600.00,
            'category': 'Travel',
            'priority': 'low',
            'target_date': today + timedelta(days=180),
            'notes': 'Mountain cabin rental',
            'url': '',
            'purchased': False,
            'purchased_date': None,
            'created_at': now,
            **DEMO_MARKER
        },
        {
            'name': 'Gaming Console',
            'cost': 499.00,
            'category': 'Entertainment',
            'priority': 'low',
            'target_date': today + timedelta(days=240),
            'notes': 'PlayStation 5',
            'url': '',
            'purchased': False,
            'purchased_date': None,
            'created_at': now,
            **DEMO_MARKER
        }
    ]
    wishlist_collection.insert_many(demo_wishlist)
    
    # Demo investment portfolio
    demo_portfolio = {
        'name': 'Retirement Portfolio',
        'type': 'simple',
        'monthly_contribution': 500.00,
        'mean_return_percent': 8.5,
        'current_value': 25000.00,
        'start_date': today - timedelta(days=730),  # 2 years ago
        'active': True,
        'created_at': now,
        **DEMO_MARKER
    }
    db['investment_portfolio'].insert_one(demo_portfolio)
    
    return {
        'recurring_income': len(demo_recurring_income),
        'one_time_income': len(demo_one_time_income),
        'recurring_expenses': len(demo_recurring_expenses),
        'one_time_expenses': len(demo_one_time_expenses),
        'wishlist_items': len(demo_wishlist),
        'investment_portfolios': 1
    }

def clear_demo_data():
    """Remove all demo data from the database"""
    # Delete demo data from all collections
    recurring_income_collection.delete_many(DEMO_MARKER)
    one_time_income_collection.delete_many(DEMO_MARKER)
    recurring_expense_collection.delete_many(DEMO_MARKER)
    one_time_expense_collection.delete_many(DEMO_MARKER)
    wishlist_collection.delete_many(DEMO_MARKER)
    db['investment_portfolio'].delete_many(DEMO_MARKER)
    db['investment_stocks'].delete_many(DEMO_MARKER)
    
    return True

