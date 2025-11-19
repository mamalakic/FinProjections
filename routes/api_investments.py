"""API routes for investment tracking"""
from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
from bson import ObjectId
from database import (
    recurring_income_collection,
    get_currency_settings
)

# Create a separate collection for investments
from database import db
investment_portfolio_collection = db['investment_portfolio']
investment_contributions_collection = db['investment_contributions']

api_investments_bp = Blueprint('api_investments', __name__)

# Main investments page
@api_investments_bp.route('/investments')
def investments():
    """Render the investments page"""
    # Get portfolio summary
    portfolios = list(investment_portfolio_collection.find())
    contributions = list(investment_contributions_collection.find())
    currency = get_currency_settings()
    
    # Check if this is an HTMX request
    is_htmx = request.headers.get('HX-Request') == 'true'
    template = 'investments/investments_partial.html' if is_htmx else 'investments/investments.html'
    
    return render_template(template, 
                         portfolios=portfolios, 
                         contributions=contributions,
                         currency=currency)

# Portfolio Management
@api_investments_bp.route('/api/investment-portfolio', methods=['GET'])
def get_portfolios():
    """Get all investment portfolios"""
    portfolios = list(investment_portfolio_collection.find())
    for portfolio in portfolios:
        portfolio['_id'] = str(portfolio['_id'])
    return jsonify(portfolios)

@api_investments_bp.route('/api/investment-portfolio/<id>', methods=['GET'])
def get_portfolio(id):
    """Get single portfolio"""
    portfolio = investment_portfolio_collection.find_one({'_id': ObjectId(id)})
    if portfolio:
        portfolio['_id'] = str(portfolio['_id'])
        return jsonify(portfolio)
    return jsonify({'error': 'Portfolio not found'}), 404

@api_investments_bp.route('/api/investment-portfolio', methods=['POST'])
def add_portfolio():
    """Add new investment portfolio (simple mode)"""
    data = request.json
    portfolio = {
        'name': data['name'],
        'type': data.get('type', 'simple'),  # 'simple' or 'detailed'
        'monthly_contribution': float(data.get('monthly_contribution', 0)),
        'mean_return_percent': float(data.get('mean_return_percent', 7.0)),
        'current_value': float(data.get('current_value', 0)),
        'start_date': datetime.strptime(data['start_date'], '%Y-%m-%d'),
        'active': True,
        'created_at': datetime.utcnow()
    }
    result = investment_portfolio_collection.insert_one(portfolio)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

@api_investments_bp.route('/api/investment-portfolio/<id>', methods=['PUT'])
def update_portfolio(id):
    """Update portfolio"""
    data = request.json
    update_data = {
        'name': data['name'],
        'monthly_contribution': float(data.get('monthly_contribution', 0)),
        'mean_return_percent': float(data.get('mean_return_percent', 7.0)),
        'current_value': float(data.get('current_value', 0)),
        'start_date': datetime.strptime(data['start_date'], '%Y-%m-%d'),
        'active': data.get('active', True),
        'updated_at': datetime.utcnow()
    }
    investment_portfolio_collection.update_one(
        {'_id': ObjectId(id)},
        {'$set': update_data}
    )
    return jsonify({'success': True})

@api_investments_bp.route('/api/investment-portfolio/<id>', methods=['DELETE'])
def delete_portfolio(id):
    """Delete portfolio"""
    investment_portfolio_collection.delete_one({'_id': ObjectId(id)})
    return jsonify({'success': True})

# Detailed Stock Management
@api_investments_bp.route('/api/investment-stocks', methods=['GET'])
def get_stocks():
    """Get all stocks in detailed portfolios"""
    stocks = list(db['investment_stocks'].find())
    for stock in stocks:
        stock['_id'] = str(stock['_id'])
    return jsonify(stocks)

@api_investments_bp.route('/api/investment-stocks', methods=['POST'])
def add_stock():
    """Add individual stock holding"""
    data = request.json
    stock = {
        'portfolio_id': data['portfolio_id'],
        'ticker': data['ticker'].upper(),
        'name': data.get('name', ''),
        'shares': float(data['shares']),
        'avg_price': float(data['avg_price']),
        'current_price': float(data.get('current_price', data['avg_price'])),
        'purchase_date': datetime.strptime(data['purchase_date'], '%Y-%m-%d'),
        'created_at': datetime.utcnow()
    }
    result = db['investment_stocks'].insert_one(stock)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

@api_investments_bp.route('/api/investment-stocks/<id>', methods=['PUT'])
def update_stock(id):
    """Update stock holding"""
    data = request.json
    update_data = {
        'ticker': data['ticker'].upper(),
        'name': data.get('name', ''),
        'shares': float(data['shares']),
        'avg_price': float(data['avg_price']),
        'current_price': float(data.get('current_price', data['avg_price'])),
        'purchase_date': datetime.strptime(data['purchase_date'], '%Y-%m-%d'),
        'updated_at': datetime.utcnow()
    }
    db['investment_stocks'].update_one(
        {'_id': ObjectId(id)},
        {'$set': update_data}
    )
    return jsonify({'success': True})

@api_investments_bp.route('/api/investment-stocks/<id>', methods=['DELETE'])
def delete_stock(id):
    """Delete stock holding"""
    db['investment_stocks'].delete_one({'_id': ObjectId(id)})
    return jsonify({'success': True})

# Import from Trading212 CSV
@api_investments_bp.route('/api/investment-import', methods=['POST'])
def import_stocks():
    """Import stocks from CSV (Trading212 format) - Legacy endpoint"""
    data = request.json
    portfolio_id = data['portfolio_id']
    csv_data = data['csv_data']
    
    # Parse CSV (simplified - assumes Trading212 format)
    # Format: Ticker,Name,Shares,Average Price,Current Price
    imported = 0
    for line in csv_data.strip().split('\n')[1:]:  # Skip header
        parts = line.split(',')
        if len(parts) >= 4:
            stock = {
                'portfolio_id': portfolio_id,
                'ticker': parts[0].strip().upper(),
                'name': parts[1].strip() if len(parts) > 1 else '',
                'shares': float(parts[2].strip()),
                'avg_price': float(parts[3].strip()),
                'current_price': float(parts[4].strip()) if len(parts) > 4 else float(parts[3].strip()),
                'purchase_date': datetime.utcnow(),
                'created_at': datetime.utcnow()
            }
            db['investment_stocks'].insert_one(stock)
            imported += 1
    
    return jsonify({'success': True, 'imported': imported})

@api_investments_bp.route('/api/investment-import-trading212', methods=['POST'])
def import_trading212():
    """Import stocks from Trading212 CSV export"""
    from utils import parse_trading212_csv
    
    try:
        data = request.json
        portfolio_id = data['portfolio_id']
        csv_data = data['csv_data']
        
        # Parse the CSV using our utility function
        result = parse_trading212_csv(csv_data)
        
        holdings = result['holdings']
        summary = result['summary']
        
        # Check for errors
        if summary['errors']:
            return jsonify({
                'success': False,
                'error': f"Encountered {len(summary['errors'])} errors during parsing",
                'details': summary['errors'][:5]  # Return first 5 errors
            }), 400
        
        # Import holdings into database
        imported = 0
        for ticker, holding in holdings.items():
            # Check if stock already exists in this portfolio
            existing = db['investment_stocks'].find_one({
                'portfolio_id': portfolio_id,
                'ticker': ticker
            })
            
            if existing:
                # Update existing stock
                db['investment_stocks'].update_one(
                    {'_id': existing['_id']},
                    {'$set': {
                        'shares': holding['shares'],
                        'avg_price': holding['avg_price'],
                        'name': holding['name'],
                        'purchase_date': holding['last_transaction_date'],
                        'updated_at': datetime.utcnow()
                    }}
                )
            else:
                # Insert new stock
                stock = {
                    'portfolio_id': portfolio_id,
                    'ticker': ticker,
                    'name': holding['name'],
                    'shares': holding['shares'],
                    'avg_price': holding['avg_price'],
                    'current_price': holding['avg_price'],  # Will need to be updated manually or via API
                    'purchase_date': holding['last_transaction_date'],
                    'created_at': datetime.utcnow()
                }
                db['investment_stocks'].insert_one(stock)
            
            imported += 1
        
        return jsonify({
            'success': True,
            'imported': imported,
            'summary': {
                'total_rows': summary['total_rows'],
                'market_buys': summary['market_buys'],
                'market_sells': summary['market_sells'],
                'dividends': summary['dividends'],
                'unique_holdings': len(holdings)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Sync prices from Trading212 API
@api_investments_bp.route('/api/investment-sync-prices', methods=['POST'])
def sync_prices_from_trading212():
    """Sync current prices from Trading212 API"""
    from utils import get_trading212_client
    import json
    import os
    
    try:
        # Get Trading212 client
        client = get_trading212_client()
        if not client:
            return jsonify({
                'success': False,
                'error': 'Trading212 API not configured. Please add your API credentials in Settings.'
            }), 400
        
        # Get all positions from Trading212
        positions = client.get_positions()
        
        # Log positions response for price sync
        print("\n" + "="*80)
        print("TRADING212 API - PRICE SYNC - POSITIONS RESPONSE")
        print("="*80)
        print(f"Number of positions: {len(positions) if positions else 0}")
        print(f"Positions data:\n{json.dumps(positions, indent=2, default=str)}")
        print("="*80 + "\n")
        
        # Log to file
        log_file = os.path.join(os.path.dirname(__file__), '..', 'trading212_api_log.json')
        with open(log_file, 'a', encoding='utf-8') as f:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'endpoint': 'positions (price_sync)',
                'count': len(positions) if positions else 0,
                'data': positions
            }
            f.write(json.dumps(log_entry, indent=2, default=str) + '\n\n')
        print(f"✅ Logged positions to: {log_file}\n")
        
        if not positions:
            return jsonify({
                'success': True,
                'updated': 0,
                'message': 'No positions found in Trading212 account'
            })
        
        # Fetch instrument metadata to get company names
        try:
            instruments = client.get_instruments()
            # Create a mapping of ticker to instrument name
            instrument_map = {}
            for instrument in instruments:
                ticker_full = instrument.get('ticker', '')
                ticker_short = ticker_full.split('_')[0] if '_' in ticker_full else ticker_full
                name = instrument.get('name', '')
                instrument_map[ticker_full] = name
                instrument_map[ticker_short] = name
        except Exception as e:
            # If we can't fetch instruments, continue without names
            print(f"Warning: Could not fetch instruments: {e}")
            instrument_map = {}
        
        # Create a mapping of ticker to current price and name
        price_map = {}
        name_map = {}
        for position in positions:
            # Extract instrument data from nested structure
            instrument = position.get('instrument', {})
            ticker_full = instrument.get('ticker', '')
            current_price = position.get('currentPrice')
            name_from_api = instrument.get('name', '')
            
            # Extract just the ticker symbol (remove exchange suffix like _US_EQ)
            ticker_symbol = ticker_full.split('_')[0] if '_' in ticker_full else ticker_full
            
            if current_price:
                price_map[ticker_symbol] = current_price
            
            # Prefer name from API, fallback to instrument map
            name = name_from_api or instrument_map.get(ticker_full, '') or instrument_map.get(ticker_symbol, '')
            if name:
                name_map[ticker_symbol] = name
        
        # Update stocks in database
        updated = 0
        stocks = list(db['investment_stocks'].find())
        
        # Track portfolio values to update
        portfolio_values = {}
        
        for stock in stocks:
            ticker = stock['ticker']
            if ticker in price_map:
                new_price = price_map[ticker]
                update_data = {
                    'current_price': new_price,
                    'last_price_update': datetime.utcnow()
                }
                
                # Also update name if available and current name is empty
                if ticker in name_map and not stock.get('name'):
                    update_data['name'] = name_map[ticker]
                
                db['investment_stocks'].update_one(
                    {'_id': stock['_id']},
                    {'$set': update_data}
                )
                updated += 1
                
                # Calculate portfolio value
                portfolio_id = stock.get('portfolio_id')
                if portfolio_id:
                    position_value = stock['shares'] * new_price
                    if portfolio_id not in portfolio_values:
                        portfolio_values[portfolio_id] = 0.0
                    portfolio_values[portfolio_id] += position_value
        
        # Update portfolio current_values
        for portfolio_id, total_value in portfolio_values.items():
            investment_portfolio_collection.update_one(
                {'_id': ObjectId(portfolio_id)},
                {'$set': {
                    'current_value': round(total_value, 2),
                    'updated_at': datetime.utcnow()
                }}
            )
        
        return jsonify({
            'success': True,
            'updated': updated,
            'total_positions': len(positions),
            'portfolios_updated': len(portfolio_values),
            'message': f'Updated {updated} stock prices from Trading212'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_investments_bp.route('/api/investment-sync-from-trading212', methods=['POST'])
def sync_holdings_from_trading212():
    """Sync all holdings from Trading212 API to a portfolio (replaces existing data)"""
    from utils import get_trading212_client
    import json
    import os
    
    try:
        data = request.json
        portfolio_id = data.get('portfolio_id')
        replace_all = data.get('replace_all', True)  # Default to replacing all data
        
        if not portfolio_id:
            return jsonify({
                'success': False,
                'error': 'Portfolio ID is required'
            }), 400
        
        # Get Trading212 client
        client = get_trading212_client()
        if not client:
            return jsonify({
                'success': False,
                'error': 'Trading212 API not configured. Please add your API credentials in Settings.'
            }), 400
        
        # Get all positions from Trading212
        positions = client.get_positions()
        
        # Log positions response
        print("\n" + "="*80)
        print("TRADING212 API - POSITIONS RESPONSE")
        print("="*80)
        print(f"Number of positions: {len(positions) if positions else 0}")
        print(f"Positions data:\n{json.dumps(positions, indent=2, default=str)}")
        print("="*80 + "\n")
        
        # Log to file
        log_file = os.path.join(os.path.dirname(__file__), '..', 'trading212_api_log.json')
        with open(log_file, 'a', encoding='utf-8') as f:
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'endpoint': 'positions',
                'count': len(positions) if positions else 0,
                'data': positions
            }
            f.write(json.dumps(log_entry, indent=2, default=str) + '\n\n')
        print(f"✅ Logged positions to: {log_file}\n")
        
        if not positions:
            # If no positions in Trading212, optionally clear the portfolio
            if replace_all:
                deleted = db['investment_stocks'].delete_many({'portfolio_id': portfolio_id})
                # Update portfolio current_value to 0
                investment_portfolio_collection.update_one(
                    {'_id': ObjectId(portfolio_id)},
                    {'$set': {'current_value': 0, 'updated_at': datetime.utcnow()}}
                )
                return jsonify({
                    'success': True,
                    'imported': 0,
                    'deleted': deleted.deleted_count,
                    'message': 'No positions found in Trading212 account. Cleared portfolio.'
                })
            return jsonify({
                'success': True,
                'imported': 0,
                'message': 'No positions found in Trading212 account'
            })
        
        # Fetch instrument metadata to get company names
        try:
            instruments = client.get_instruments()
            
            # Log instruments response
            print("\n" + "="*80)
            print("TRADING212 API - INSTRUMENTS RESPONSE")
            print("="*80)
            print(f"Number of instruments: {len(instruments) if instruments else 0}")
            if instruments:
                # Log first 5 instruments as sample
                print(f"Sample instruments (first 5):\n{json.dumps(instruments[:5], indent=2, default=str)}")
            print("="*80 + "\n")
            
            # Log to file
            with open(log_file, 'a', encoding='utf-8') as f:
                log_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'endpoint': 'instruments',
                    'count': len(instruments) if instruments else 0,
                    'sample_data': instruments[:10] if instruments else []  # Log first 10
                }
                f.write(json.dumps(log_entry, indent=2, default=str) + '\n\n')
            print(f"✅ Logged instruments to: {log_file}\n")
            
            # Create a mapping of ticker to instrument name
            instrument_map = {}
            for instrument in instruments:
                ticker_full = instrument.get('ticker', '')
                ticker_short = ticker_full.split('_')[0] if '_' in ticker_full else ticker_full
                name = instrument.get('name', '')
                instrument_map[ticker_full] = name
                instrument_map[ticker_short] = name
                
            print(f"📋 Created instrument map with {len(instrument_map)} entries\n")
        except Exception as e:
            # If we can't fetch instruments, continue without names
            print(f"⚠️ Warning: Could not fetch instruments: {e}")
            instrument_map = {}
        
        # If replace_all is True, delete all existing stocks in this portfolio first
        deleted_count = 0
        if replace_all:
            deleted = db['investment_stocks'].delete_many({'portfolio_id': portfolio_id})
            deleted_count = deleted.deleted_count
        
        # Get account summary for additional portfolio information
        try:
            account_summary = client.get_account_summary()
            
            # Log account summary
            print("\n" + "="*80)
            print("TRADING212 API - ACCOUNT SUMMARY RESPONSE")
            print("="*80)
            print(f"Account data:\n{json.dumps(account_summary, indent=2, default=str)}")
            print("="*80 + "\n")
            
            # Log to file
            with open(log_file, 'a', encoding='utf-8') as f:
                log_entry = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'endpoint': 'account_summary',
                    'data': account_summary
                }
                f.write(json.dumps(log_entry, indent=2, default=str) + '\n\n')
            print(f"✅ Logged account summary to: {log_file}\n")
        except Exception as e:
            print(f"⚠️ Warning: Could not fetch account summary: {e}")
            account_summary = None
        
        # Import each position and calculate total portfolio value
        imported = 0
        total_portfolio_value = 0.0
        total_invested = 0.0  # Total amount invested (cost basis)
        
        print("\n" + "="*80)
        print("PROCESSING POSITIONS")
        print("="*80)
        
        for i, position in enumerate(positions, 1):
            # Extract instrument data from nested structure
            instrument = position.get('instrument', {})
            ticker_full = instrument.get('ticker', '')
            ticker = ticker_full.split('_')[0] if '_' in ticker_full else ticker_full
            name = instrument.get('name', '')
            
            # Extract position data
            quantity = position.get('quantity', 0)
            avg_price = position.get('averagePricePaid', 0)  # Note: it's averagePricePaid, not averagePrice
            current_price = position.get('currentPrice', avg_price)
            
            if quantity <= 0:
                continue
            
            # Use name from instrument, fallback to instrument_map if needed
            if not name:
                name = instrument_map.get(ticker_full, '') or instrument_map.get(ticker, '')
            
            # Calculate position value and cost
            position_value = quantity * current_price
            position_cost = quantity * avg_price
            total_portfolio_value += position_value
            total_invested += position_cost
            
            # Log each position being processed
            print(f"\n[{i}] Processing: {ticker_full}")
            print(f"    Ticker (short): {ticker}")
            print(f"    Name: {name or '(not found)'}")
            print(f"    Shares: {quantity}")
            print(f"    Avg Price: €{avg_price:.2f}")
            print(f"    Current Price: €{current_price:.2f}")
            print(f"    Position Value: €{position_value:.2f}")
            print(f"    Position Cost: €{position_cost:.2f}")
            print(f"    Gain/Loss: €{(position_value - position_cost):.2f}")
            
            # Insert new stock (deleted all old ones if replace_all=True)
            stock = {
                'portfolio_id': portfolio_id,
                'ticker': ticker,
                'name': name,
                'shares': quantity,
                'avg_price': avg_price,
                'current_price': current_price,
                'purchase_date': datetime.utcnow(),
                'last_price_update': datetime.utcnow(),
                'created_at': datetime.utcnow(),
                'synced_from_api': True  # Mark as API-synced
            }
            db['investment_stocks'].insert_one(stock)
            imported += 1
        
        print("\n" + "="*80)
        print(f"✅ Processed {imported} positions")
        print(f"💰 Total Portfolio Value: €{total_portfolio_value:.2f}")
        print(f"💵 Total Invested: €{total_invested:.2f}")
        print("="*80 + "\n")
        
        # Calculate actual return percentage based on performance
        actual_return_percent = 7.0  # Default
        if total_invested > 0 and total_portfolio_value > total_invested:
            # Calculate annualized return (assuming 1 year holding period as estimate)
            gain_percent = ((total_portfolio_value - total_invested) / total_invested) * 100
            actual_return_percent = gain_percent  # Use as mean return estimate
        
        # Update the portfolio with comprehensive data
        portfolio_update = {
            'current_value': round(total_portfolio_value, 2),
            'type': 'detailed',  # Mark as detailed since we have individual stocks
            'updated_at': datetime.utcnow(),
            'last_sync': datetime.utcnow()
        }
        
        # Only update mean_return_percent if we have a meaningful calculation
        if total_invested > 0:
            portfolio_update['mean_return_percent'] = round(actual_return_percent, 2)
        
        # Get the existing portfolio to check if start_date needs updating
        existing_portfolio = investment_portfolio_collection.find_one({'_id': ObjectId(portfolio_id)})
        if existing_portfolio:
            # Only set start_date if it doesn't exist or is in the future
            if 'start_date' not in existing_portfolio or existing_portfolio.get('start_date') > datetime.utcnow():
                portfolio_update['start_date'] = datetime.utcnow()
        
        investment_portfolio_collection.update_one(
            {'_id': ObjectId(portfolio_id)},
            {'$set': portfolio_update}
        )
        
        # Calculate gain/loss
        gain_loss = total_portfolio_value - total_invested
        gain_loss_percent = (gain_loss / total_invested * 100) if total_invested > 0 else 0
        
        message = f'Synced {imported} holdings from Trading212\n'
        message += f'Portfolio Value: €{total_portfolio_value:.2f}\n'
        message += f'Total Invested: €{total_invested:.2f}\n'
        message += f'Gain/Loss: €{gain_loss:.2f} ({gain_loss_percent:+.2f}%)'
        
        if replace_all and deleted_count > 0:
            message += f'\n(Replaced {deleted_count} old entries)'
        
        return jsonify({
            'success': True,
            'imported': imported,
            'deleted': deleted_count if replace_all else 0,
            'total_value': round(total_portfolio_value, 2),
            'total_invested': round(total_invested, 2),
            'gain_loss': round(gain_loss, 2),
            'gain_loss_percent': round(gain_loss_percent, 2),
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Recalculate portfolio values from stocks
@api_investments_bp.route('/api/investment-portfolio/<id>/recalculate', methods=['POST'])
def recalculate_portfolio_value(id):
    """Recalculate portfolio current_value from its stock holdings"""
    try:
        # Get all stocks in this portfolio
        stocks = list(db['investment_stocks'].find({'portfolio_id': id}))
        
        total_value = 0.0
        for stock in stocks:
            shares = stock.get('shares', 0)
            current_price = stock.get('current_price', stock.get('avg_price', 0))
            total_value += shares * current_price
        
        # Update portfolio
        investment_portfolio_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': {
                'current_value': round(total_value, 2),
                'updated_at': datetime.utcnow()
            }}
        )
        
        return jsonify({
            'success': True,
            'current_value': round(total_value, 2),
            'stock_count': len(stocks)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Calculate investment projections
@api_investments_bp.route('/api/investment-projections')
def get_investment_projections():
    """Calculate investment growth projections"""
    months = request.args.get('months', 12, type=int)
    portfolios = list(investment_portfolio_collection.find({'active': True}))
    
    projections = []
    for i in range(months):
        month_value = 0
        month_contributions = 0
        
        for portfolio in portfolios:
            current_value = portfolio.get('current_value', 0)
            monthly_contrib = portfolio.get('monthly_contribution', 0)
            annual_return = portfolio.get('mean_return_percent', 7.0) / 100
            monthly_return = (1 + annual_return) ** (1/12) - 1
            
            # Calculate value for this month
            for month in range(i + 1):
                current_value = (current_value + monthly_contrib) * (1 + monthly_return)
            
            month_value += current_value
            month_contributions += monthly_contrib
        
        projections.append({
            'month': i,
            'value': round(month_value, 2),
            'monthly_contribution': round(month_contributions, 2)
        })
    
    return jsonify(projections)


