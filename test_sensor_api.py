import requests
import json

url = 'http://127.0.0.1:5000/api/sensor-data'
data = {
    "humidity": 65.5,
    "temperature": 28.4,
    "soil_moisture": 42.1,
    "status": "Healthy"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
    print("Make sure the Flask server is running on http://127.0.0.1:5000")
