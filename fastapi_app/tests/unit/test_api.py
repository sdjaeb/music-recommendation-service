# Description: Unit tests for FastAPI application.
# Source: Deep-Dive Addendum: IaC & CI/CD Recipes, Section 5.4.
#
# This tests the basic API endpoints and validation.
import pytest
from fastapi.testclient import TestClient
# Assuming your FastAPI app is structured like app.main.app
# If running this test directly, ensure your main.py is callable or adjust import
from fastapi_app.app.main import app # Adjust based on actual project structure if needed
from datetime import datetime

# Initialize TestClient
client = TestClient(app)

def test_read_main():
    """Tests the root health check endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json() # Check for message key
    assert response.json()["message"] == "Welcome to Advanced Data Ingestor API!" # Or appropriate message

def test_health_check_connected():
    """Tests the health check when Kafka is assumed to be connected."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy" # Or "degraded" if Kafka isn't mocked/connected
    # In a true unit test, Kafka connection would be mocked.
    # For simplicity here, we check for the expected status when components are assumed healthy.
    assert "kafka_status" in response.json()


def test_ingest_financial_transaction_valid_data():
    """Tests successful ingestion of valid financial transaction data."""
    transaction_data = {
        "transaction_id": "FT-VALID-001",
        "timestamp": datetime.now().isoformat(),
        "account_id": "ACC-VALID-001",
        "amount": 250.75,
        "currency": "EUR",
        "transaction_type": "purchase",
        "merchant_id": "MER-789",
        "category": "electronics"
    }
    response = client.post("/ingest-financial-transaction/", json=transaction_data)
    assert response.status_code == 200
    assert response.json()["message"] == "Financial transaction ingested successfully"
    assert response.json()["transaction_id"] == "FT-VALID-001"

def test_ingest_financial_transaction_invalid_data():
    """Tests rejection of invalid financial transaction data due to validation errors."""
    response = client.post("/ingest-financial-transaction/", json={
        "transaction_id": "FT-001",
        "timestamp": "invalid-date", # Invalid timestamp
        "account_id": "ACC-XYZ",
        "amount": "not-a-number", # Invalid amount
        "currency": "USD",
        "transaction_type": "debit"
    })
    assert response.status_code == 422 # Unprocessable Entity due to validation error
    assert "validation error" in response.text
    assert "timestamp" in response.text # Specific error detail
    assert "amount" in response.text    # Specific error detail

def test_ingest_insurance_claim_valid_data():
    """Tests successful ingestion of valid insurance claim data."""
    claim_data = {
        "claim_id": "IC-VALID-001",
        "timestamp": datetime.now().isoformat(),
        "policy_number": "POL-ABC-123",
        "claim_amount": 1500.00,
        "claim_type": "medical",
        "claim_status": "submitted",
        "customer_id": "CUST-VALID-001",
        "incident_date": (datetime.now().replace(day=1) - timedelta(days=5)).isoformat()
    }
    response = client.post("/ingest-insurance-claim/", json=claim_data)
    assert response.status_code == 200
    assert response.json()["message"] == "Insurance claim ingested successfully"
    assert response.json()["claim_id"] == "IC-VALID-001"

def test_ingest_insurance_claim_missing_required_field():
    """Tests rejection of insurance claim data with a missing required field."""
    # Missing 'claim_amount'
    response = client.post("/ingest-insurance-claim/", json={
        "claim_id": "IC-002",
        "timestamp": datetime.now().isoformat(),
        "policy_number": "POL-456",
        "claim_type": "home",
        "claim_status": "in_progress",
        "customer_id": "CUST-002",
        "incident_date": "2023-01-01T00:00:00Z"
    })
    assert response.status_code == 422
    assert "validation error" in response.text
    assert "claim_amount" in response.text
