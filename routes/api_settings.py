"""API routes for application settings"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_currency_settings, get_date_format, settings_collection

api_settings_bp = Blueprint('api_settings', __name__, url_prefix='/api/settings')

@api_settings_bp.route('/currency', methods=['GET'])
def get_currency():
    currency = get_currency_settings()
    return jsonify(currency)

@api_settings_bp.route('/currency', methods=['PUT'])
def update_currency():
    data = request.json
    settings_collection.update_one(
        {},
        {'$set': {
            'currency_code': data['code'],
            'currency_symbol': data['symbol'],
            'updated_at': datetime.utcnow()
        }},
        upsert=True
    )
    return jsonify({'success': True, 'currency': {'code': data['code'], 'symbol': data['symbol']}})

@api_settings_bp.route('/trading212', methods=['GET'])
def get_trading212_settings():
    """Get Trading212 API settings"""
    settings = settings_collection.find_one({})
    if settings and 'trading212_api_key' in settings:
        # Don't return the secret, only indicate if it's configured
        return jsonify({
            'configured': True,
            'environment': settings.get('trading212_environment', 'live')
        })
    return jsonify({'configured': False})

@api_settings_bp.route('/trading212', methods=['PUT'])
def update_trading212_settings():
    """Update Trading212 API settings"""
    data = request.json
    update_data = {
        'trading212_environment': data.get('environment', 'live'),
        'updated_at': datetime.utcnow()
    }
    
    if data.get('api_key'):
        update_data['trading212_api_key'] = data['api_key']
    if data.get('api_secret'):
        update_data['trading212_api_secret'] = data['api_secret']
    
    settings_collection.update_one(
        {},
        {'$set': update_data},
        upsert=True
    )
    return jsonify({'success': True})

@api_settings_bp.route('/trading212', methods=['DELETE'])
def delete_trading212_settings():
    """Remove Trading212 API settings"""
    settings_collection.update_one(
        {},
        {'$unset': {
            'trading212_api_key': '',
            'trading212_api_secret': '',
            'trading212_environment': ''
        }}
    )
    return jsonify({'success': True})

@api_settings_bp.route('/date-format', methods=['GET'])
def get_date_format_setting():
    date_format = get_date_format()
    return jsonify({'format': date_format})

@api_settings_bp.route('/date-format', methods=['PUT'])
def update_date_format():
    data = request.json
    settings_collection.update_one(
        {},
        {'$set': {
            'date_format': data['format'],
            'updated_at': datetime.utcnow()
        }},
        upsert=True
    )
    return jsonify({'success': True, 'format': data['format']})


