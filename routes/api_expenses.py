"""API routes for expense management"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from datetime import datetime
from database import recurring_expense_collection, one_time_expense_collection

api_expenses_bp = Blueprint('api_expenses', __name__, url_prefix='/api')

@api_expenses_bp.route('/recurring-expense/<id>', methods=['GET'])
def get_recurring_expense(id):
    expense = recurring_expense_collection.find_one({'_id': ObjectId(id)})
    if not expense:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'id': str(expense['_id']),
        'name': expense['name'],
        'amount': expense['amount'],
        'frequency': expense['frequency'],
        'start_date': expense['start_date'].isoformat() if isinstance(expense['start_date'], datetime) else expense['start_date'],
        'end_date': expense['end_date'].isoformat() if expense.get('end_date') and isinstance(expense['end_date'], datetime) else expense.get('end_date'),
        'category': expense['category'],
        'payday': expense.get('payday'),
        'active': expense['active'],
        'upcoming': expense.get('upcoming', False)
    })

@api_expenses_bp.route('/recurring-expense', methods=['POST'])
def add_recurring_expense():
    data = request.json
    expense = {
        'name': data['name'],
        'amount': float(data['amount']),
        'frequency': data['frequency'],
        'start_date': datetime.strptime(data['start_date'], '%Y-%m-%d'),
        'end_date': datetime.strptime(data['end_date'], '%Y-%m-%d') if data.get('end_date') else None,
        'category': data['category'],
        'payday': int(data['payday']) if data.get('payday') else None,
        'active': True,
        'upcoming': data.get('upcoming', False),
        'created_at': datetime.utcnow()
    }
    result = recurring_expense_collection.insert_one(expense)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

@api_expenses_bp.route('/recurring-expense/<id>', methods=['PUT'])
def update_recurring_expense(id):
    data = request.json
    update_data = {
        'name': data['name'],
        'amount': float(data['amount']),
        'frequency': data['frequency'],
        'start_date': datetime.strptime(data['start_date'], '%Y-%m-%d'),
        'end_date': datetime.strptime(data['end_date'], '%Y-%m-%d') if data.get('end_date') else None,
        'category': data['category'],
        'payday': int(data['payday']) if data.get('payday') else None,
        'active': data.get('active', True),
        'upcoming': data.get('upcoming', False)
    }
    recurring_expense_collection.update_one({'_id': ObjectId(id)}, {'$set': update_data})
    return jsonify({'success': True})

@api_expenses_bp.route('/recurring-expense/<id>', methods=['DELETE'])
def delete_recurring_expense(id):
    recurring_expense_collection.delete_one({'_id': ObjectId(id)})
    return jsonify({'success': True})

@api_expenses_bp.route('/one-time-expense/<id>', methods=['GET'])
def get_one_time_expense(id):
    expense = one_time_expense_collection.find_one({'_id': ObjectId(id)})
    if not expense:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'id': str(expense['_id']),
        'name': expense['name'],
        'amount': expense['amount'],
        'date': expense['date'].isoformat() if isinstance(expense['date'], datetime) else expense['date'],
        'category': expense['category'],
        'notes': expense.get('notes', ''),
        'upcoming': expense.get('upcoming', False)
    })

@api_expenses_bp.route('/one-time-expense', methods=['POST'])
def add_one_time_expense():
    data = request.json
    expense = {
        'name': data['name'],
        'amount': float(data['amount']),
        'date': datetime.strptime(data['date'], '%Y-%m-%d'),
        'category': data['category'],
        'notes': data.get('notes', ''),
        'upcoming': data.get('upcoming', False),
        'created_at': datetime.utcnow()
    }
    result = one_time_expense_collection.insert_one(expense)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

@api_expenses_bp.route('/one-time-expense/<id>', methods=['PUT'])
def update_one_time_expense(id):
    data = request.json
    update_data = {
        'name': data['name'],
        'amount': float(data['amount']),
        'date': datetime.strptime(data['date'], '%Y-%m-%d'),
        'category': data['category'],
        'notes': data.get('notes', ''),
        'upcoming': data.get('upcoming', False)
    }
    one_time_expense_collection.update_one({'_id': ObjectId(id)}, {'$set': update_data})
    return jsonify({'success': True})

@api_expenses_bp.route('/one-time-expense/<id>', methods=['DELETE'])
def delete_one_time_expense(id):
    one_time_expense_collection.delete_one({'_id': ObjectId(id)})
    return jsonify({'success': True})

