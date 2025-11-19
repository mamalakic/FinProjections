"""Utility functions for calculations"""
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import csv
from io import StringIO
from collections import defaultdict
import base64
import requests

def get_next_occurrence(start_date, frequency, current_date=None):
    """Calculate next occurrence based on frequency"""
    if current_date is None:
        current_date = datetime.now().date()
    
    if frequency == 'monthly':
        return start_date + relativedelta(months=1)
    elif frequency == 'weekly':
        return start_date + timedelta(weeks=1)
    elif frequency == 'biweekly':
        return start_date + timedelta(weeks=2)
    elif frequency == 'yearly':
        return start_date + relativedelta(years=1)
    return start_date

def calculate_occurrences_in_range(start_date, end_date, frequency, range_start, range_end):
    """Calculate how many times a recurring item occurs in a date range"""
    if end_date and end_date < range_start:
        return 0
    
    actual_start = max(start_date, range_start)
    actual_end = min(end_date, range_end) if end_date else range_end
    
    if actual_start > actual_end:
        return 0
    
    # For monthly frequency, check if the recurring item should occur in this month
    if frequency == 'monthly':
        # A monthly recurring item occurs once per month if it's active in that month
        # Check if the start_date is on or before the range_end, and end_date (if exists) is on or after range_start
        if start_date <= range_end and (not end_date or end_date >= range_start):
            return 1
        return 0
    elif frequency == 'weekly':
        # Calculate number of weeks in the range
        delta = actual_end - actual_start
        return (delta.days // 7) + 1
    elif frequency == 'biweekly':
        # Calculate number of bi-weeks in the range
        delta = actual_end - actual_start
        return (delta.days // 14) + 1
    elif frequency == 'yearly':
        # A yearly recurring item occurs once per year
        # Check if it should occur in this date range
        if start_date <= range_end and (not end_date or end_date >= range_start):
            # Check if the anniversary falls within the range
            years_diff = range_start.year - start_date.year
            if years_diff >= 0:
                anniversary = start_date.replace(year=range_start.year)
                if range_start <= anniversary <= range_end:
                    return 1
            return 0
        return 0
    
    return 0

def calculate_monthly_projections(months=12):
    """Calculate financial projections for the next N months"""
    from database import (
        recurring_income_collection, one_time_income_collection,
        recurring_expense_collection, one_time_expense_collection, db
    )
    
    projections = []
    today = datetime.now().date()
    
    # Start from the first day of the current month
    current_month_start = today.replace(day=1)
    
    # Get investment portfolios
    investment_portfolios = list(db['investment_portfolio'].find({'active': True}))
    
    for i in range(months):
        month_start = current_month_start + relativedelta(months=i)
        month_end = month_start + relativedelta(months=1) - timedelta(days=1)
        
        # Convert to datetime for MongoDB queries
        month_start_dt = datetime.combine(month_start, datetime.min.time())
        month_end_dt = datetime.combine(month_end, datetime.max.time())
        
        # Calculate recurring income (exclude upcoming items)
        recurring_incomes = list(recurring_income_collection.find({'active': True, 'upcoming': {'$ne': True}}))
        total_recurring_income = 0
        for income in recurring_incomes:
            start_date = income['start_date'] if isinstance(income['start_date'], datetime) else datetime.fromisoformat(income['start_date'])
            if isinstance(start_date, datetime):
                start_date = start_date.date()
            end_date = income.get('end_date')
            if end_date:
                end_date = end_date if isinstance(end_date, datetime) else datetime.fromisoformat(end_date)
                if isinstance(end_date, datetime):
                    end_date = end_date.date()
            
            occurrences = calculate_occurrences_in_range(
                start_date, end_date, income['frequency'],
                month_start, month_end
            )
            total_recurring_income += income['amount'] * occurrences
        
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
            start_date = expense['start_date'] if isinstance(expense['start_date'], datetime) else datetime.fromisoformat(expense['start_date'])
            if isinstance(start_date, datetime):
                start_date = start_date.date()
            end_date = expense.get('end_date')
            if end_date:
                end_date = end_date if isinstance(end_date, datetime) else datetime.fromisoformat(end_date)
                if isinstance(end_date, datetime):
                    end_date = end_date.date()
            
            occurrences = calculate_occurrences_in_range(
                start_date, end_date, expense['frequency'],
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
    
    return projections


def parse_trading212_csv(csv_data):
    """
    Parse Trading212 CSV export and calculate current holdings.
    
    Returns a dictionary with:
    - holdings: dict of {ticker: {shares, avg_price, name, isin, last_transaction_date}}
    - transactions: list of all processed transactions
    - summary: statistics about the import
    """
    reader = csv.DictReader(StringIO(csv_data))
    
    # Track holdings per ticker
    holdings = defaultdict(lambda: {
        'shares': 0.0,
        'total_cost': 0.0,
        'avg_price': 0.0,
        'name': '',
        'isin': '',
        'ticker': '',
        'last_transaction_date': None,
        'transactions': []
    })
    
    transactions = []
    stats = {
        'total_rows': 0,
        'market_buys': 0,
        'market_sells': 0,
        'dividends': 0,
        'deposits': 0,
        'other': 0,
        'errors': []
    }
    
    for row in reader:
        stats['total_rows'] += 1
        action = row.get('Action', '').strip()
        
        # Skip non-stock transactions
        if action in ['Deposit', 'Interest on cash', 'Lending interest', 'Currency conversion fee']:
            if action == 'Deposit':
                stats['deposits'] += 1
            else:
                stats['other'] += 1
            continue
        
        # Process stock transactions
        ticker = row.get('Ticker', '').strip()
        if not ticker:
            continue
            
        try:
            shares_str = row.get('No. of shares', '0').strip()
            shares = float(shares_str) if shares_str else 0.0
            
            price_str = row.get('Price / share', '0').strip()
            price = float(price_str) if price_str else 0.0
            
            # Parse transaction date
            time_str = row.get('Time', '').strip()
            transaction_date = None
            if time_str:
                try:
                    transaction_date = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        transaction_date = datetime.strptime(time_str.split()[0], '%Y-%m-%d')
                    except ValueError:
                        transaction_date = datetime.utcnow()
            else:
                transaction_date = datetime.utcnow()
            
            name = row.get('Name', '').strip()
            isin = row.get('ISIN', '').strip()
            
            # Process based on action type
            if action == 'Market buy':
                stats['market_buys'] += 1
                holdings[ticker]['shares'] += shares
                holdings[ticker]['total_cost'] += shares * price
                holdings[ticker]['name'] = name
                holdings[ticker]['isin'] = isin
                holdings[ticker]['ticker'] = ticker
                holdings[ticker]['last_transaction_date'] = transaction_date
                holdings[ticker]['transactions'].append({
                    'action': 'buy',
                    'shares': shares,
                    'price': price,
                    'date': transaction_date
                })
                
            elif action == 'Market sell':
                stats['market_sells'] += 1
                holdings[ticker]['shares'] -= shares
                # Reduce total cost proportionally
                if holdings[ticker]['shares'] > 0:
                    holdings[ticker]['total_cost'] -= shares * price
                else:
                    holdings[ticker]['total_cost'] = 0
                holdings[ticker]['name'] = name
                holdings[ticker]['isin'] = isin
                holdings[ticker]['ticker'] = ticker
                holdings[ticker]['last_transaction_date'] = transaction_date
                holdings[ticker]['transactions'].append({
                    'action': 'sell',
                    'shares': shares,
                    'price': price,
                    'date': transaction_date
                })
                
            elif 'Dividend' in action:
                stats['dividends'] += 1
                # Dividends don't affect share count
                holdings[ticker]['name'] = name
                holdings[ticker]['isin'] = isin
                holdings[ticker]['ticker'] = ticker
                
            transactions.append({
                'action': action,
                'ticker': ticker,
                'name': name,
                'shares': shares,
                'price': price,
                'date': transaction_date
            })
            
        except (ValueError, KeyError) as e:
            stats['errors'].append(f"Error processing row {stats['total_rows']}: {str(e)}")
            continue
    
    # Calculate average prices and filter out zero holdings
    final_holdings = {}
    for ticker, data in holdings.items():
        if data['shares'] > 0.001:  # Keep only positive holdings (accounting for float precision)
            if data['total_cost'] > 0:
                data['avg_price'] = data['total_cost'] / data['shares']
            else:
                # If we don't have cost data, use the last transaction price
                if data['transactions']:
                    data['avg_price'] = data['transactions'][-1]['price']
                else:
                    data['avg_price'] = 0.0
            
            final_holdings[ticker] = {
                'ticker': ticker,
                'name': data['name'],
                'isin': data['isin'],
                'shares': round(data['shares'], 6),
                'avg_price': round(data['avg_price'], 2),
                'last_transaction_date': data['last_transaction_date']
            }
    
    return {
        'holdings': final_holdings,
        'transactions': transactions,
        'summary': stats
    }


class Trading212Client:
    """
    Client for interacting with Trading212 Public API.
    Based on: https://docs.trading212.com/api/section/general-information/quickstart
    """
    
    def __init__(self, api_key, api_secret, environment='live'):
        """
        Initialize Trading212 API client.
        
        Args:
            api_key: Your Trading212 API key
            api_secret: Your Trading212 API secret
            environment: 'live' or 'demo' (paper trading)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Set base URL based on environment
        if environment == 'demo':
            self.base_url = 'https://demo.trading212.com/api/v0'
        else:
            self.base_url = 'https://live.trading212.com/api/v0'
        
        # Create authorization header
        credentials = f"{api_key}:{api_secret}"
        encoded = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        self.headers = {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method, endpoint, **kwargs):
        """Make HTTP request to Trading212 API"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Trading212 API error: {str(e)}")
    
    def get_account_summary(self):
        """Get account summary including cash balance"""
        return self._make_request('GET', '/equity/account/summary')
    
    def get_positions(self):
        """
        Get all current positions.
        Returns list of positions with ticker, quantity, average price, current price, etc.
        """
        return self._make_request('GET', '/equity/positions')
    
    def get_instruments(self):
        """Get list of all tradable instruments"""
        return self._make_request('GET', '/equity/metadata/instruments')
    
    def get_exchanges(self):
        """Get list of all exchanges"""
        return self._make_request('GET', '/equity/metadata/exchanges')
    
    def get_historical_orders(self, limit=50, cursor=None):
        """
        Get historical orders with pagination.
        
        Args:
            limit: Number of orders to return (max 50)
            cursor: Pagination cursor from previous response
        """
        params = {'limit': limit}
        if cursor:
            params['cursor'] = cursor
        return self._make_request('GET', '/equity/history/orders', params=params)
    
    def place_market_order(self, ticker, quantity):
        """
        Place a market order.
        
        Args:
            ticker: Instrument ticker (e.g., 'AAPL_US_EQ')
            quantity: Number of shares (negative for sell)
        
        Note: Only available in live environment
        """
        data = {
            'ticker': ticker,
            'quantity': quantity
        }
        return self._make_request('POST', '/equity/orders/market', json=data)
    
    def get_position_by_ticker(self, ticker):
        """
        Get current position for a specific ticker.
        
        Args:
            ticker: The instrument ticker
            
        Returns:
            Position data or None if not found
        """
        positions = self.get_positions()
        for position in positions:
            if position.get('ticker') == ticker:
                return position
        return None


def get_trading212_client():
    """
    Get Trading212 API client from database settings.
    Returns None if not configured.
    """
    from database import settings_collection
    
    settings = settings_collection.find_one({})
    if not settings or 'trading212_api_key' not in settings:
        return None
    
    return Trading212Client(
        api_key=settings['trading212_api_key'],
        api_secret=settings['trading212_api_secret'],
        environment=settings.get('trading212_environment', 'live')
    )

