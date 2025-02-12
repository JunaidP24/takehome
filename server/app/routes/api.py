from flask import Blueprint, jsonify
from flask_cors import CORS
import traceback
from app.services.ecfr_service import ECFRService

api = Blueprint('api', __name__)
CORS(api)  # Enable CORS for the API blueprint
ecfr_service = ECFRService()

@api.route('/titles', methods=['GET'])
def get_titles():
    """Get all eCFR titles"""
    try:
        titles = ecfr_service.get_all_titles()
        return jsonify(titles)
    except Exception as e:
        print("Error in /titles route:", str(e))  # Basic logging
        print("Traceback:", traceback.format_exc())  # Detailed stack trace
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@api.route('/titles/<int:title_number>/analysis', methods=['GET'])
def analyze_title(title_number):
    """Get analysis for a specific title"""
    try:
        analysis = ecfr_service.analyze_title(title_number)
        return jsonify(analysis)
    except Exception as e:
        print(f"Error in /titles/{title_number}/analysis route:", str(e))
        print("Traceback:", traceback.format_exc())
        return jsonify({
            'error': str(e),
            'title_number': title_number
        }), 500 