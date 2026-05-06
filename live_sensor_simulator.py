import time
import requests
import random
import sys

URL = 'http://127.0.0.1:5000/api/sensor-data'

def simulate_sensor():
    print("Starting Live Sensor Data Simulator...")
    print(f"Posting data to {URL} every 5 seconds. Press Ctrl+C to stop.")
    
    # Initial realistic values
    humidity = 60.0
    temp = 28.0
    moisture = 45.0
    
    try:
        while True:
            # Add some random walk to simulate live fluctuations
            humidity = max(20.0, min(95.0, humidity + random.uniform(-2.0, 2.0)))
            temp = max(15.0, min(45.0, temp + random.uniform(-1.0, 1.0)))
            moisture = max(10.0, min(90.0, moisture + random.uniform(-3.0, 3.0)))
            
            # Determine status based on conditions
            if moisture < 30 or temp > 35:
                status = "Warning"
            else:
                status = "Healthy"
                
            data = {
                "humidity": round(humidity, 1),
                "temperature": round(temp, 1),
                "soil_moisture_percent": round(moisture, 1),
                "soil_moisture_raw": int(1023 - (moisture / 100.0 * 1023)), # Simulated raw from 0 to 1023
                "status": status
            }
            
            try:
                response = requests.post(URL, json=data)
                if response.status_code == 201:
                    print(f"[{time.strftime('%H:%M:%S')}] Sent Data: H={data['humidity']}% T={data['temperature']}C M={data['soil_moisture_percent']}% -> {status}")
                else:
                    print(f"Failed to post data. Status code: {response.status_code}")
            except requests.exceptions.ConnectionError:
                print("Error: Could not connect to the server. Make sure it's running on port 5000.")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
        sys.exit(0)

if __name__ == '__main__':
    simulate_sensor() 