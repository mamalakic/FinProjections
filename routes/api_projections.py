"""API routes for financial projections"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from utils import calculate_monthly_projections, calculate_occurrences_in_range
from database import (
    recurring_income_collection, one_time_income_collection,
    recurring_expense_collection, one_time_expense_collection
)

api_projections_bp = Blueprint('api_projections', __name__, url_prefix='/api')

@api_projections_bp.route('/projections')
def get_projections():
    months = request.args.get('months', 12, type=int)
    projections = calculate_monthly_projections(months)
    
    cumulative = 0
    for proj in projections:
        cumulative += proj['net_amount']
        proj['cumulative_balance'] = round(cumulative, 2)
    
    return jsonify(projections)

@api_projections_bp.route('/projections/until-now')
def get_projections_until_now():
    """Calculate projections from earliest transaction until current month"""
    from database import db
    
    today = datetime.now().date()
    
    # Find earliest date from all transactions
    earliest_dates = []
    
    # Check recurring income
    earliest_recurring_income = recurring_income_collection.find_one(sort=[('start_date', 1)])
    if earliest_recurring_income:
        start_date = earliest_recurring_income['start_date']
        if isinstance(start_date, datetime):
            earliest_dates.append(start_date.date())
        else:
            earliest_dates.append(datetime.fromisoformat(start_date).date())
    
    # Check one-time income
    earliest_one_time_income = one_time_income_collection.find_one(sort=[('date', 1)])
    if earliest_one_time_income:
        date = earliest_one_time_income['date']
        if isinstance(date, datetime):
            earliest_dates.append(date.date())
        else:
            earliest_dates.append(datetime.fromisoformat(date).date())
    
    # Check recurring expenses
    earliest_recurring_expense = recurring_expense_collection.find_one(sort=[('start_date', 1)])
    if earliest_recurring_expense:
        start_date = earliest_recurring_expense['start_date']
        if isinstance(start_date, datetime):
            earliest_dates.append(start_date.date())
        else:
            earliest_dates.append(datetime.fromisoformat(start_date).date())
    
    # Check one-time expenses
    earliest_one_time_expense = one_time_expense_collection.find_one(sort=[('date', 1)])
    if earliest_one_time_expense:
        date = earliest_one_time_expense['date']
        if isinstance(date, datetime):
            earliest_dates.append(date.date())
        else:
            earliest_dates.append(datetime.fromisoformat(date).date())
    
    if not earliest_dates:
        return jsonify([])
    
    earliest_date = min(earliest_dates)
    months_diff = (today.year - earliest_date.year) * 12 + (today.month - earliest_date.month) + 1
    
    # Get investment portfolios
    investment_portfolios = list(db['investment_portfolio'].find({'active': True}))
    
    # Calculate projections from earliest date
    projections = []
    start_date = earliest_date.replace(day=1)
    
    for i in range(months_diff):
        month_start = start_date + relativedelta(months=i)
        month_end = month_start + relativedelta(months=1) - timedelta(days=1)
        
        if month_start > today:
            break
        
        # Calculate recurring income (exclude upcoming items)
        recurring_incomes = list(recurring_income_collection.find({'active': True, 'upcoming': {'$ne': True}}))
        total_recurring_income = 0
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
            total_recurring_income += income['amount'] * occurrences
        
        # Convert to datetime for MongoDB queries
        month_start_dt = datetime.combine(month_start, datetime.min.time())
        month_end_dt = datetime.combine(month_end, datetime.max.time())
        
        # Calculate one-time income (exclude upcoming items)
        one_time_incomes = list(one_time_income_collection.find({
            'date': {'$gte': month_start_dt, '$lte': month_end_dt},
            'upcoming': {'$ne': True}
        }))
        total_one_time_income = sum(income['amount'] for income in one_time_incomes)
        
        # Calculate investment income (monthly returns)
        total_investment_income = 0
        for portfolio in investment_portfolios:
            current_value = portfolio.get('current_value', 0)
            monthly_contrib = portfolio.get('monthly_contribution', 0)
            annual_return = portfolio.get('mean_return_percent', 7.0) / 100
            monthly_return = (1 + annual_return) ** (1/12) - 1
            
            # Calculate value for this month
            for month in range(i + 1):
                current_value = (current_value + monthly_contrib) * (1 + monthly_return)
            
            # Monthly gain is the return on current value
            if i > 0:
                prev_value = portfolio.get('current_value', 0)
                for month in range(i):
                    prev_value = (prev_value + monthly_contrib) * (1 + monthly_return)
                monthly_gain = current_value - prev_value - monthly_contrib
                total_investment_income += monthly_gain
        
        # Calculate recurring expenses (exclude upcoming items)
        recurring_expenses = list(recurring_expense_collection.find({'active': True, 'upcoming': {'$ne': True}}))
        total_recurring_expenses = 0
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
            total_recurring_expenses += expense['amount'] * occurrences
        
        # Calculate one-time expenses (exclude upcoming items)
        one_time_expenses = list(one_time_expense_collection.find({
            'date': {'$gte': month_start_dt, '$lte': month_end_dt},
            'upcoming': {'$ne': True}
        }))
        total_one_time_expenses = sum(expense['amount'] for expense in one_time_expenses)
        
        total_income = total_recurring_income + total_one_time_income + total_investment_income
        total_expenses = total_recurring_expenses + total_one_time_expenses
        net_amount = total_income - total_expenses
        
        projections.append({
            'month': month_start.strftime('%B %Y'),
            'month_date': month_start.isoformat(),
            'total_income': round(total_income, 2),
            'recurring_income': round(total_recurring_income, 2),
            'one_time_income': round(total_one_time_income, 2),
            'investment_income': round(total_investment_income, 2),
            'total_expenses': round(total_expenses, 2),
            'recurring_expenses': round(total_recurring_expenses, 2),
            'one_time_expenses': round(total_one_time_expenses, 2),
            'net_amount': round(net_amount, 2)
        })
    
    # Calculate cumulative balance
    cumulative = 0
    for proj in projections:
        cumulative += proj['net_amount']
        proj['cumulative_balance'] = round(cumulative, 2)
    
    return jsonify(projections)

