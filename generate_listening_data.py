import requests
import json
import time
import random
from datetime import datetime

# Configuration
API_ENDPOINT = "http://localhost:8088/ingest/listening-event"
NUM_USERS = 50
NUM_TRACKS = 200
NUM_EVENTS = 2500

def generate_and_send_events():
    """Generates and sends a batch of simulated user listening events."""
    print(f"Starting data generation. Sending {NUM_EVENTS} events to {API_ENDPOINT}...")

    for i in range(NUM_EVENTS):
        user_id = random.randint(1, NUM_USERS)
        track_id = random.randint(101, 100 + NUM_TRACKS)
        
        # Simulate different event types with realistic probabilities
        event_type_roll = random.random()
        if event_type_roll < 0.7:
            event_type = "complete_listen" # 70% chance
        elif event_type_roll < 0.85:
            event_type = "like" # 15% chance
        else:
            event_type = "skip" # 15% chance

        payload = {
            "eventId": f"EVT-{int(time.time() * 1000)}-{i}",
            "userId": user_id,
            "trackId": track_id,
            "eventType": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(API_ENDPOINT, data=json.dumps(payload), headers=headers, timeout=5)
            response.raise_for_status()
            print(f"Successfully sent event {i+1}/{NUM_EVENTS}: {payload['eventId']}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending event {payload['eventId']}: {e}")
        
        time.sleep(random.uniform(0.01, 0.1)) # Simulate time between events

    print("Data generation complete.")

if __name__ == "__main__":
    generate_and_send_events()