# simulate_data.py
# This script simulates a continuous stream of financial transactions and insurance claims
# by sending POST requests to the FastAPI ingestor. It's used to generate load
# and trigger various data pipeline components (Kafka, Spark, OpenTelemetry metrics).

import requests
import json
import time
import random
from datetime import datetime, timedelta

# Configuration for FastAPI endpoint
# IMPORTANT NOTE: This URL must match the exposed port in your docker-compose.yml for fastapi_ingestor.
# It's usually `http://localhost:8000` from your host machine.
FASTAPI_URL = "http://localhost:8000"
FINANCIAL_ENDPOINT = f"{FASTAPI_URL}/ingest-financial-transaction/"
INSURANCE_ENDPOINT = f"{FASTAPI_URL}/ingest-insurance-claim/"
MUSIC_ENDPOINT = f"{FASTAPI_URL}/ingest-music-event/"

# Control parameters
NUM_REQUESTS_PER_BATCH = 5 # Number of requests to send in each loop iteration
DELAY_SECONDS = 0.1      # Delay between each batch of requests

def generate_financial_transaction():
    """Generates a random financial transaction payload."""
    transaction_types = ["debit", "credit", "transfer", "refund"]
    currencies = ["USD", "EUR", "GBP", "JPY", "CAD"]
    merchants = ["MER-ABC", "MER-XYZ", "MER-123", "MER-DEF", "MER-GHI", None] # Include None for optional merchant
    categories = ["groceries", "electronics", "healthcare", "transport", "entertainment", None]

    transaction_id = f"FT-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{random.randint(1000, 9999)}"
    timestamp = datetime.now().isoformat(timespec='seconds') + 'Z'
    account_id = f"ACC-{random.randint(100, 999)}"
    amount = round(random.uniform(10.0, 5000.0), 2)
    currency = random.choice(currencies)
    transaction_type = random.choice(transaction_types)
    merchant_id = random.choice(merchants)
    category = random.choice(categories) if merchant_id else None # Category only if merchant exists

    return {
        "transaction_id": transaction_id,
        "timestamp": timestamp,
        "account_id": account_id,
        "amount": amount,
        "currency": currency,
        "transaction_type": transaction_type,
        "merchant_id": merchant_id,
        "category": category
    }

def generate_insurance_claim():
    """Generates a random insurance claim payload."""
    claim_types = ["auto", "home", "health", "life"]
    claim_statuses = ["submitted", "pending", "approved", "denied"]
    
    claim_id = f"IC-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{random.randint(1000, 9999)}"
    timestamp = datetime.now().isoformat(timespec='seconds') + 'Z'
    policy_number = f"POL-{random.randint(100000, 999999)}"
    claim_amount = round(random.uniform(100.0, 100000.0), 2)
    claim_type = random.choice(claim_types)
    claim_status = random.choice(claim_statuses)
    customer_id = f"CUST-{random.randint(1000, 9999)}"
    
    # Incident date is typically in the past
    incident_date = (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat(timespec='seconds') + 'Z'

    return {
        "claim_id": claim_id,
        "timestamp": timestamp,
        "policy_number": policy_number,
        "claim_amount": claim_amount,
        "claim_type": claim_type,
        "claim_status": claim_status,
        "customer_id": customer_id,
        "incident_date": incident_date
    }

def generate_music_event():
    """Generates a random music event payload."""
    event_types = ["play", "skip", "like", "complete"]
    
    event_id = f"ME-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}-{random.randint(1000, 9999)}"
    user_id = random.randint(1, 100)
    track_id = random.randint(101, 200)
    event_type = random.choice(event_types)
    timestamp = datetime.now().isoformat(timespec='seconds') + 'Z'

    return {
        "event_id": event_id,
        "user_id": user_id,
        "track_id": track_id,
        "event_type": event_type,
        "timestamp": timestamp
    }

def send_request(url, payload):
    """Sends a POST request to the specified URL with the given payload."""
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=5)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        event_id = payload.get('transaction_id') or payload.get('claim_id') or payload.get('event_id')
        print(f"Successfully sent to {url.split('/')[-2].replace('-',' ')}: {event_id}. Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending request to {url}: {e}")
    except json.JSONDecodeError:
        print(f"Error decoding JSON response from {url}. Response content: {response.text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print(f"Starting music event simulation. Sending {NUM_REQUESTS_PER_BATCH} requests every {DELAY_SECONDS} seconds...")
    print(f"Target FastAPI: {FASTAPI_URL}")

    while True:
        try:
            for _ in range(NUM_REQUESTS_PER_BATCH):
                music_data = generate_music_event()
                send_request(MUSIC_ENDPOINT, music_data)
            time.sleep(DELAY_SECONDS)
        except KeyboardInterrupt:
            print("\nSimulation stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred during simulation loop: {e}")
            time.sleep(5) # Wait before retrying in case of persistent error
