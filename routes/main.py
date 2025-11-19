"""Main page routes"""
from flask import Blueprint, render_template, request
from database import get_currency_settings
from utils import calculate_monthly_projections

main_bp = Blueprint('main', __name__)

def is_htmx_request():
    """Check if the request is from HTMX"""
    return request.headers.get('HX-Request') == 'true'

@main_bp.route('/')
@main_bp.route('/dashboard')
def dashboard():
    # Default to empty projections - will be loaded via JavaScript with "until-now"
    projections = []
    currency = get_currency_settings()
    template = 'dashboard/dashboard_partial.html' if is_htmx_request() else 'dashboard/dashboard.html'
    return render_template(template, projections=projections, currency=currency)

@main_bp.route('/income')
def income():
    from database import recurring_income_collection, one_time_income_collection
    
    recurring = list(recurring_income_collection.find().sort('created_at', -1))
    one_time = list(one_time_income_collection.find().sort('date', -1))
    currency = get_currency_settings()
    template = 'income/income_partial.html' if is_htmx_request() else 'income/income.html'
    return render_template(template, recurring=recurring, one_time=one_time, currency=currency)

@main_bp.route('/expenses')
def expenses():
    from database import recurring_expense_collection, one_time_expense_collection
    
    recurring = list(recurring_expense_collection.find().sort('created_at', -1))
    one_time = list(one_time_expense_collection.find().sort('date', -1))
    currency = get_currency_settings()
    template = 'expenses/expenses_partial.html' if is_htmx_request() else 'expenses/expenses.html'
    return render_template(template, recurring=recurring, one_time=one_time, currency=currency)

@main_bp.route('/settings')
def settings():
    currency = get_currency_settings()
    template = 'settings/settings_partial.html' if is_htmx_request() else 'settings/settings.html'
    return render_template(template, currency=currency)

