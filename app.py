from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')

CORS(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    favorites = db.relationship('Favorite', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hotspot_id = db.Column(db.String(20), nullable=False)
    hotspot_name = db.Column(db.String(200), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables within app context if they don't exist
with app.app_context():
    db.create_all()

EBIRD_API_BASE = "https://api.ebird.org/v2"

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/observations', methods=['POST'])
def get_observations():
    try:
        data = request.json
        # apiKey is no longer expected from client
        api_key = os.environ.get('EBIRD_API_KEY')
        location_id = data.get('locationId')
        species_code = data.get('speciesCode')
        days_back = data.get('daysBack', 30)
        
        if not api_key:
             return jsonify({'error': 'Server configuration error: API key missing'}), 500

        if not location_id or not species_code:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        url = f"{EBIRD_API_BASE}/data/obs/{location_id}/recent/{species_code}"
        params = {'back': days_back}
        headers = {'X-eBirdApiToken': api_key}
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            # Debugging output
            print(f"eBird API Error: {response.status_code}")
            print(f"URL: {url}")
            print(f"Headers (masked): {headers.keys()}")
            print(f"Response: {response.text}")
            
            return jsonify({
                'error': f'eBird API error: {response.status_code}',
                'message': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/nearby', methods=['POST'])
def get_nearby_observations():
    try:
        data = request.json
        api_key = os.environ.get('EBIRD_API_KEY')
        
        lat = data.get('lat')
        lng = data.get('lng')
        species_code = data.get('speciesCode')
        dist = data.get('dist', 25)
        days_back = data.get('daysBack', 14)

        if not api_key:
             return jsonify({'error': 'Server configuration error: API key missing'}), 500

        if not lat or not lng or not species_code:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        url = f"{EBIRD_API_BASE}/data/nearest/geo/recent/{species_code}"
        params = {
            'lat': lat,
            'lng': lng,
            'dist': dist,
            'back': days_back,
            'sort': 'date'
        }
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

@app.route('/api/hotspot/info', methods=['GET'])
def get_hotspot_info():
    try:
        loc_id = request.args.get('locId')
        api_key = os.environ.get('EBIRD_API_KEY')
        
        if not api_key:
             return jsonify({'error': 'Server configuration error: API key missing'}), 500

        if not loc_id:
            return jsonify({'error': 'Missing locId parameter'}), 400
        
        url = f"{EBIRD_API_BASE}/ref/hotspot/info/{loc_id}"
        headers = {'X-eBirdApiToken': api_key}
        
        # Determine if we simply forward reaponse or parse text/csv?
        # The API usually returns CSV unless fmt=json is adding? documentation says ref/hotspot/info/{locId} 
        # let's try assuming json support or handle CSV if needed.
        # Actually documentation says "Returns the location record for the specified location ID."
        # Usually supports ?fmt=json
        
        response = requests.get(url, params={'fmt': 'json'}, headers=headers)
        
        if response.status_code == 200:
             return jsonify(response.json())
        else:
            return jsonify({'error': f'eBird error {response.status_code}', 'message': response.text}), response.status_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/hotspot/nearby', methods=['GET'])
def get_nearby_hotspots():
    try:
        lat = request.args.get('lat')
        lng = request.args.get('lng')
        dist = request.args.get('dist', 25)
        api_key = os.environ.get('EBIRD_API_KEY')

        if not api_key:
             return jsonify({'error': 'Server configuration error: API key missing'}), 500
        
        if not lat or not lng:
             return jsonify({'error': 'Missing lat/lng parameters'}), 400

        url = f"{EBIRD_API_BASE}/ref/hotspot/geo"
        params = {
            'lat': lat,
            'lng': lng,
            'dist': dist,
            'fmt': 'json'
        }
        headers = {'X-eBirdApiToken': api_key}
        
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
             return jsonify({'error': f'eBird error {response.status_code}', 'message': response.text}), response.status_code
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notable', methods=['POST'])
def get_notable_observations():
    try:
        data = request.json
        api_key = os.environ.get('EBIRD_API_KEY')
        
        lat = data.get('lat')
        lng = data.get('lng')
        dist = data.get('dist', 25)
        days_back = data.get('daysBack', 14)

        if not api_key:
             return jsonify({'error': 'Server configuration error: API key missing'}), 500

        if not lat or not lng:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        url = f"{EBIRD_API_BASE}/data/obs/geo/recent/notable"
        params = {
            'lat': lat,
            'lng': lng,
            'dist': dist,
            'back': days_back,
            'detail': 'full'
        }
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

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400

    try:
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return jsonify({'message': 'Registration successful', 'user': {'id': new_user.id, 'username': new_user.username}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        return jsonify({'message': 'Login successful', 'user': {'id': user.id, 'username': user.username}})
    
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/user', methods=['GET'])
def get_current_user():
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'user': {'id': current_user.id, 'username': current_user.username}})
    else:
        return jsonify({'authenticated': False})

@app.route('/api/favorites', methods=['GET', 'POST'])
@login_required
def manage_favorites():
    if request.method == 'GET':
        favs = Favorite.query.filter_by(user_id=current_user.id).all()
        return jsonify([{'id': f.hotspot_id, 'name': f.hotspot_name} for f in favs])
    
    if request.method == 'POST':
        data = request.json
        hotspot_id = data.get('id')
        hotspot_name = data.get('name')
        
        if not hotspot_id or not hotspot_name:
            return jsonify({'error': 'Missing id or name'}), 400
            
        existing = Favorite.query.filter_by(user_id=current_user.id, hotspot_id=hotspot_id).first()
        if existing:
            return jsonify({'message': 'Already in favorites'})
            
        new_fav = Favorite(user_id=current_user.id, hotspot_id=hotspot_id, hotspot_name=hotspot_name)
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({'message': 'Added to favorites'})

@app.route('/api/favorites/<hotspot_id>', methods=['DELETE'])
@login_required
def delete_favorite(hotspot_id):
    fav = Favorite.query.filter_by(user_id=current_user.id, hotspot_id=hotspot_id).first()
    if fav:
        db.session.delete(fav)
        db.session.commit()
        return jsonify({'message': 'Deleted'})
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)