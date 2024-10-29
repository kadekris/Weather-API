import os
import requests
import redis
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv('VISUAL_CROSSING_API_KEY')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('REDIS_PORT', 6379)
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

cache = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri=f'redis://{REDIS_HOST}:{REDIS_PORT}'
)

@app.route('/weather', methods=['GET'])
@limiter.limit("10 per minute")  
def get_weather():
    city = request.args.get('city')
    if not city:
        return jsonify({"error": "Parameter 'city' tidak diberikan"}), 400

    cache_key = f"weather:{city}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return jsonify({"data": cached_data, "source": "cache"})

    try:
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}?key={API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        weather_data = response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Gagal mendapatkan data dari API cuaca", "details": str(e)}), 500

    cache.setex(cache_key, 43200, str(weather_data))  

    return jsonify({"data": weather_data, "source": "api"})

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint tidak ditemukan"}), 404

@app.errorhandler(429)
def ratelimit_exceeded(error):
    return jsonify({"error": "Terlalu banyak permintaan, coba lagi nanti"}), 429

if __name__ == '__main__':
    app.run(debug=True)