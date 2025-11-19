"""API routes for month details and payday adjustments"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from utils import calculate_occurrences_in_range
from database import (
    recurring_income_collection, one_time_income_collection,
    recurring_expense_collection, one_time_expense_collection,
    payday_adjustment_collection
)

api_details_bp = Blueprint('api_details', __name__, url_prefix='/api')

@api_details_bp.route('/month-details/<year>/<month>')
def get_month_details(year, month):
    """Get detailed breakdown of a specific month"""
    year = int(year)
    month = int(month)
    month_start = datetime(year, month, 1).date()
    month_end = month_start + relativedelta(months=1) - timedelta(days=1)
    
    # Convert to datetime for MongoDB queries
    month_start_dt = datetime.combine(month_start, datetime.min.time())
    month_end_dt = datetime.combine(month_end, datetime.max.time())
    
    details = {
        'recurring_income': [],
        'one_time_income': [],
        'recurring_expenses': [],
        'one_time_expenses': []
    }
    
    # Get 1. recurring 2. one time a. income b. expenses of this month
    recurring_incomes = list(recurring_income_collection.find({'active': True}))
    for income in recurring_incomes:
        inc_start = income['start_date'] if isinstance(income['start_date'], datetime) else datetime.fromisoformat(income['start_date'])
        if isinstance(inc_start, datetime):
            inc_start = inc_start.date()
        inc_end = income.get('end_date')
        if inc_end:
            inc_end = inc_end if isinstance(inc_end, datetime) else datetime.fromisoformat(inc_end)
            if isinstance(inc_end, datetime):
                inc_end = inc_end.date()
        
        occurrences = calculate_occurrences_in_range(
            inc_start, inc_end, income['frequency'],
            month_start, month_end
        )
        if occurrences > 0:
            # Check for adjustment
            adjustment = payday_adjustment_collection.find_one({
                'recurring_type': 'income',
                'recurring_id': str(income['_id']),
                'year': year,
                'month': month
            })
            
            payday = adjustment['adjusted_day'] if adjustment else income.get('payday')
            
            details['recurring_income'].append({
                'id': str(income['_id']),
                'name': income['name'],
                'amount': income['amount'],
                'frequency': income['frequency'],
                'payday': payday,
                'has_adjustment': adjustment is not None
            })
    
    one_time_incomes = list(one_time_income_collection.find({
        'date': {'$gte': month_start_dt, '$lte': month_end_dt}
    }))
    for income in one_time_incomes:
        inc_date = income['date'] if isinstance(income['date'], datetime) else datetime.fromisoformat(income['date'])
        details['one_time_income'].append({
            'id': str(income['_id']),
            'name': income['name'],
            'amount': income['amount'],
            'date': inc_date.isoformat(),
            'day': inc_date.day,
            'category': income['category']
        })
    
    recurring_expenses = list(recurring_expense_collection.find({'active': True}))
    for expense in recurring_expenses:
        exp_start = expense['start_date'] if isinstance(expense['start_date'], datetime) else datetime.fromisoformat(expense['start_date'])
        if isinstance(exp_start, datetime):
            exp_start = exp_start.date()
        exp_end = expense.get('end_date')
        if exp_end:
            exp_end = exp_end if isinstance(exp_end, datetime) else datetime.fromisoformat(exp_end)
            if isinstance(exp_end, datetime):
                exp_end = exp_end.date()
        
        occurrences = calculate_occurrences_in_range(
            exp_start, exp_end, expense['frequency'],
            month_start, month_end
        )
        if occurrences > 0:
            adjustment = payday_adjustment_collection.find_one({
                'recurring_type': 'expense',
                'recurring_id': str(expense['_id']),
                'year': year,
                'month': month
            })
            
            payday = adjustment['adjusted_day'] if adjustment else expense.get('payday')
            
            details['recurring_expenses'].append({
                'id': str(expense['_id']),
                'name': expense['name'],
                'amount': expense['amount'],
                'frequency': expense['frequency'],
                'category': expense['category'],
                'payday': payday,
                'has_adjustment': adjustment is not None
            })
    
    one_time_expenses = list(one_time_expense_collection.find({
        'date': {'$gte': month_start_dt, '$lte': month_end_dt}
    }))
    for expense in one_time_expenses:
        exp_date = expense['date'] if isinstance(expense['date'], datetime) else datetime.fromisoformat(expense['date'])
        details['one_time_expenses'].append({
            'id': str(expense['_id']),
            'name': expense['name'],
            'amount': expense['amount'],
            'date': exp_date.isoformat(),
            'day': exp_date.day,
            'category': expense['category']
        })
    
    return jsonify(details)

@api_details_bp.route('/payday-adjustment', methods=['POST'])
def add_payday_adjustment():
    data = request.json
    
    existing = payday_adjustment_collection.find_one({
        'recurring_type': data['recurring_type'],
        'recurring_id': data['recurring_id'],
        'year': data['year'],
        'month': data['month']
    })
    
    if existing:
        payday_adjustment_collection.update_one(
            {'_id': existing['_id']},
            {'$set': {'adjusted_day': data['adjusted_day']}}
        )
    else:
        adjustment = {
            'recurring_type': data['recurring_type'],
            'recurring_id': data['recurring_id'],
            'year': data['year'],
            'month': data['month'],
            'adjusted_day': data['adjusted_day'],
            'created_at': datetime.utcnow()
        }
        payday_adjustment_collection.insert_one(adjustment)
    
    return jsonify({'success': True})


