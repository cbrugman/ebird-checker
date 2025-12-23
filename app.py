from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder='static')
CORS(app)

EBIRD_API_BASE = "https://api.ebird.org/v2"

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/observations', methods=['POST'])
def get_observations():
    try:
        data = request.json
        api_key = data.get('apiKey')
        location_id = data.get('locationId')
        species_code = data.get('speciesCode')
        days_back = data.get('daysBack', 30)
        
        if not api_key or not location_id or not species_code:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        url = f"{EBIRD_API_BASE}/data/obs/{location_id}/recent/{species_code}"
        params = {'back': days_back}
        headers = {'X-eBirdApiToken': api_key}
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'error': f'eBird API error: {response.status_code}',
                'message': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)