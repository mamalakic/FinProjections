"""API routes for income management"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from datetime import datetime
from database import recurring_income_collection, one_time_income_collection

api_income_bp = Blueprint('api_income', __name__, url_prefix='/api')

@api_income_bp.route('/recurring-income/<id>', methods=['GET'])
def get_recurring_income(id):
    income = recurring_income_collection.find_one({'_id': ObjectId(id)})
    if not income:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'id': str(income['_id']),
        'name': income['name'],
        'amount': income['amount'],
        'frequency': income['frequency'],
        'start_date': income['start_date'].isoformat() if isinstance(income['start_date'], datetime) else income['start_date'],
        'end_date': income['end_date'].isoformat() if income.get('end_date') and isinstance(income['end_date'], datetime) else income.get('end_date'),
        'payday': income.get('payday'),
        'active': income['active'],
        'upcoming': income.get('upcoming', False)
    })

@api_income_bp.route('/recurring-income', methods=['POST'])
def add_recurring_income():
    data = request.json
    income = {
        'name': data['name'],
        'amount': float(data['amount']),
        'frequency': data['frequency'],
        'start_date': datetime.strptime(data['start_date'], '%Y-%m-%d'),
        'end_date': datetime.strptime(data['end_date'], '%Y-%m-%d') if data.get('end_date') else None,
        'payday': int(data['payday']) if data.get('payday') else None,
        'active': True,
        'upcoming': data.get('upcoming', False),
        'created_at': datetime.utcnow()
    }
    result = recurring_income_collection.insert_one(income)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

@api_income_bp.route('/recurring-income/<id>', methods=['PUT'])
def update_recurring_income(id):
    data = request.json
    update_data = {
        'name': data['name'],
        'amount': float(data['amount']),
        'frequency': data['frequency'],
        'start_date': datetime.strptime(data['start_date'], '%Y-%m-%d'),
        'end_date': datetime.strptime(data['end_date'], '%Y-%m-%d') if data.get('end_date') else None,
        'payday': int(data['payday']) if data.get('payday') else None,
        'active': data.get('active', True),
        'upcoming': data.get('upcoming', False)
    }
    recurring_income_collection.update_one({'_id': ObjectId(id)}, {'$set': update_data})
    return jsonify({'success': True})

@api_income_bp.route('/recurring-income/<id>', methods=['DELETE'])
def delete_recurring_income(id):
    recurring_income_collection.delete_one({'_id': ObjectId(id)})
    return jsonify({'success': True})

@api_income_bp.route('/one-time-income/<id>', methods=['GET'])
def get_one_time_income(id):
    income = one_time_income_collection.find_one({'_id': ObjectId(id)})
    if not income:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'id': str(income['_id']),
        'name': income['name'],
        'amount': income['amount'],
        'date': income['date'].isoformat() if isinstance(income['date'], datetime) else income['date'],
        'category': income['category'],
        'notes': income.get('notes', ''),
        'upcoming': income.get('upcoming', False)
    })

@api_income_bp.route('/one-time-income', methods=['POST'])
def add_one_time_income():
    data = request.json
    income = {
        'name': data['name'],
        'amount': float(data['amount']),
        'date': datetime.strptime(data['date'], '%Y-%m-%d'),
        'category': data['category'],
        'notes': data.get('notes', ''),
        'upcoming': data.get('upcoming', False),
        'created_at': datetime.utcnow()
    }
    result = one_time_income_collection.insert_one(income)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

@api_income_bp.route('/one-time-income/<id>', methods=['PUT'])
def update_one_time_income(id):
    data = request.json
    update_data = {
        'name': data['name'],
        'amount': float(data['amount']),
        'date': datetime.strptime(data['date'], '%Y-%m-%d'),
        'category': data['category'],
        'notes': data.get('notes', ''),
        'upcoming': data.get('upcoming', False)
    }
    one_time_income_collection.update_one({'_id': ObjectId(id)}, {'$set': update_data})
    return jsonify({'success': True})

@api_income_bp.route('/one-time-income/<id>', methods=['DELETE'])
def delete_one_time_income(id):
    one_time_income_collection.delete_one({'_id': ObjectId(id)})
    return jsonify({'success': True})

