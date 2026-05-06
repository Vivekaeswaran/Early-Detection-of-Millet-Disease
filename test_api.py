import requests
import json

url = 'http://127.0.0.1:5000/api/sensor-data'
data = {
    "humidity": 75.5,
    "soil_moisture": 25.0,
    "status": "UNDER-IRRIGATED"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
