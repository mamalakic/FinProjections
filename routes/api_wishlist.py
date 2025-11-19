"""API routes for wishlist management"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from datetime import datetime
from database import wishlist_collection, wishlist_categories_collection, get_wishlist_categories
from utils import calculate_monthly_projections

api_wishlist_bp = Blueprint('api_wishlist', __name__, url_prefix='/api')

@api_wishlist_bp.route('/wishlist/<id>', methods=['GET'])
def get_wishlist_item(id):
    item = wishlist_collection.find_one({'_id': ObjectId(id)})
    if not item:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'id': str(item['_id']),
        'name': item['name'],
        'cost': item['cost'],
        'category': item['category'],
        'priority': item.get('priority', 'medium'),
        'target_date': item['target_date'].isoformat() if item.get('target_date') and isinstance(item['target_date'], datetime) else item.get('target_date'),
        'notes': item.get('notes', ''),
        'url': item.get('url', ''),
        'purchased': item.get('purchased', False),
        'purchased_date': item['purchased_date'].isoformat() if item.get('purchased_date') and isinstance(item['purchased_date'], datetime) else item.get('purchased_date')
    })

@api_wishlist_bp.route('/wishlist', methods=['POST'])
def add_wishlist_item():
    data = request.json
    item = {
        'name': data['name'],
        'cost': float(data['cost']),
        'category': data['category'],
        'priority': data.get('priority', 'medium'),
        'target_date': datetime.strptime(data['target_date'], '%Y-%m-%d') if data.get('target_date') else None,
        'notes': data.get('notes', ''),
        'url': data.get('url', ''),
        'purchased': False,
        'purchased_date': None,
        'created_at': datetime.utcnow()
    }
    result = wishlist_collection.insert_one(item)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

@api_wishlist_bp.route('/wishlist/<id>', methods=['PUT'])
def update_wishlist_item(id):
    data = request.json
    update_data = {
        'name': data['name'],
        'cost': float(data['cost']),
        'category': data['category'],
        'priority': data.get('priority', 'medium'),
        'target_date': datetime.strptime(data['target_date'], '%Y-%m-%d') if data.get('target_date') else None,
        'notes': data.get('notes', ''),
        'url': data.get('url', ''),
        'purchased': data.get('purchased', False)
    }
    
    # If marking as purchased, set purchased_date
    if data.get('purchased') and not wishlist_collection.find_one({'_id': ObjectId(id)}).get('purchased'):
        update_data['purchased_date'] = datetime.utcnow()
    
    wishlist_collection.update_one({'_id': ObjectId(id)}, {'$set': update_data})
    return jsonify({'success': True})

@api_wishlist_bp.route('/wishlist/<id>', methods=['DELETE'])
def delete_wishlist_item(id):
    wishlist_collection.delete_one({'_id': ObjectId(id)})
    return jsonify({'success': True})

@api_wishlist_bp.route('/wishlist/<id>/toggle-purchased', methods=['POST'])
def toggle_purchased(id):
    item = wishlist_collection.find_one({'_id': ObjectId(id)})
    if not item:
        return jsonify({'error': 'Not found'}), 404
    
    new_purchased = not item.get('purchased', False)
    update_data = {'purchased': new_purchased}
    
    if new_purchased:
        update_data['purchased_date'] = datetime.utcnow()
    else:
        update_data['purchased_date'] = None
    
    wishlist_collection.update_one({'_id': ObjectId(id)}, {'$set': update_data})
    return jsonify({'success': True, 'purchased': new_purchased})

@api_wishlist_bp.route('/wishlist-analysis', methods=['GET'])
def get_wishlist_analysis():
    """
    Analyze wishlist items against financial projections to provide insights:
    - Can afford now?
    - % of current balance
    - Months until affordable
    - Impact on savings
    """
    from routes.api_projections import get_projections_until_now
    from flask import current_app
    
    # Get all active wishlist items
    items = list(wishlist_collection.find({'purchased': {'$ne': True}}).sort('priority', 1))
    
    # Get projections until now for current balance
    with current_app.test_request_context():
        until_now_response = get_projections_until_now()
        until_now_projections = until_now_response.get_json()
    
    # Get future projections for affordability analysis
    future_projections = calculate_monthly_projections(months=24)
    
    if not until_now_projections and not future_projections:
        return jsonify({'items': [], 'summary': {}})
    
    # Get current cumulative balance from "until now" projections (what you have RIGHT NOW)
    current_balance = until_now_projections[-1].get('cumulative_balance', 0) if until_now_projections else 0
    
    # Use future projections for affordability timeline, but adjust them to start from current balance
    projections = future_projections
    
    # Adjust future projections to build on current balance
    if projections and current_balance != 0:
        # The future projections start from 0, so we need to add current_balance to each
        for proj in projections:
            proj['cumulative_balance'] = proj.get('cumulative_balance', 0) + current_balance
    
    # Calculate average monthly savings (net amount)
    avg_monthly_savings = sum(p['net_amount'] for p in projections[:6]) / min(6, len(projections)) if projections else 0
    
    analyzed_items = []
    total_wishlist_cost = 0
    
    for item in items:
        cost = item['cost']
        total_wishlist_cost += cost
        
        # Calculate affordability
        can_afford_now = current_balance >= cost
        balance_percentage = (cost / current_balance * 100) if current_balance > 0 else 0
        
        # Calculate months until affordable
        months_until_affordable = 0
        affordable_by_month = None
        cumulative_balance_when_affordable = 0
        
        if not can_afford_now and avg_monthly_savings > 0:
            # Find when cumulative balance will exceed cost
            for i, proj in enumerate(projections):
                if proj['cumulative_balance'] >= cost:
                    months_until_affordable = i + 1  # +1 because we're counting from now
                    affordable_by_month = proj['month']
                    cumulative_balance_when_affordable = proj['cumulative_balance']
                    break
            
            # If not found in projections, calculate beyond
            if not affordable_by_month and avg_monthly_savings > 0:
                remaining_needed = cost - current_balance
                months_until_affordable = int(remaining_needed / avg_monthly_savings) + 1
        
        # Calculate impact on balance
        balance_after_purchase = current_balance - cost
        
        # Calculate required monthly savings to afford by target date
        required_monthly_savings = None
        target_date = item.get('target_date')
        if target_date and not can_afford_now:
            if isinstance(target_date, str):
                target_date = datetime.fromisoformat(target_date)
            
            months_until_target = max(1, (target_date.year - datetime.now().year) * 12 + 
                                      (target_date.month - datetime.now().month))
            
            if months_until_target > 0:
                amount_needed = cost - current_balance
                required_monthly_savings = amount_needed / months_until_target
        
        analyzed_items.append({
            'id': str(item['_id']),
            'name': item['name'],
            'cost': cost,
            'category': item['category'],
            'priority': item.get('priority', 'medium'),
            'target_date': item['target_date'].isoformat() if item.get('target_date') and isinstance(item['target_date'], datetime) else item.get('target_date'),
            'notes': item.get('notes', ''),
            'url': item.get('url', ''),
            'can_afford_now': can_afford_now,
            'balance_percentage': round(balance_percentage, 1),
            'months_until_affordable': months_until_affordable,
            'affordable_by_month': affordable_by_month,
            'balance_after_purchase': round(balance_after_purchase, 2),
            'required_monthly_savings': round(required_monthly_savings, 2) if required_monthly_savings else None,
            'cumulative_balance_when_affordable': round(cumulative_balance_when_affordable, 2)
        })
    
    # Summary statistics
    summary = {
        'current_balance': round(current_balance, 2),
        'avg_monthly_savings': round(avg_monthly_savings, 2),
        'total_wishlist_cost': round(total_wishlist_cost, 2),
        'total_items': len(analyzed_items),
        'affordable_now': sum(1 for item in analyzed_items if item['can_afford_now']),
        'total_as_percentage': round((total_wishlist_cost / current_balance * 100) if current_balance > 0 else 0, 1)
    }
    
    return jsonify({
        'items': analyzed_items,
        'summary': summary
    })

@api_wishlist_bp.route('/wishlist-categories', methods=['GET'])
def get_categories():
    """Get all wishlist categories (preset + custom)"""
    categories = get_wishlist_categories()
    return jsonify({'categories': categories})

@api_wishlist_bp.route('/wishlist-categories', methods=['POST'])
def add_category():
    """Add a custom wishlist category"""
    data = request.json
    
    # Check if category already exists (case-insensitive)
    existing = wishlist_categories_collection.find_one({'name': {'$regex': f'^{data["name"]}$', '$options': 'i'}})
    if existing:
        return jsonify({'error': 'Category already exists'}), 400
    
    # Also check against preset categories
    preset_names = ['Electronics', 'Furniture', 'Travel', 'Vehicle', 'Education', 'Health', 'Entertainment', 'Other']
    if data['name'] in preset_names:
        return jsonify({'error': 'Category already exists'}), 400
    
    category = {
        'name': data['name'],
        'icon': data.get('icon', 'ri-bookmark-line'),
        'created_at': datetime.utcnow()
    }
    result = wishlist_categories_collection.insert_one(category)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

@api_wishlist_bp.route('/wishlist-categories/<id>', methods=['DELETE'])
def delete_category(id):
    """Delete a custom category"""
    # Get the category name first
    category = wishlist_categories_collection.find_one({'_id': ObjectId(id)})
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
    # Check if category is in use
    items_using_category = wishlist_collection.find_one({'category': category['name']})
    if items_using_category:
        return jsonify({'error': 'Cannot delete category that is in use'}), 400
    
    wishlist_categories_collection.delete_one({'_id': ObjectId(id)})
    return jsonify({'success': True})

