# Description: Entry point for FastAPI application (Intermediate Track).
# Source: Building Enterprise-Ready Data Platforms v2.4, Appendix A.2 (Conceptual).
#
# This version publishes data to Kafka topics.
import os
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from kafka import KafkaProducer # Requires kafka-python
import asyncio # For async producer interaction if needed (not strictly required for basic producer.send)

app = FastAPI(title="Intermediate Data Ingestor (Kafka Producer)")

# Kafka producer configuration
# Use 'kafka' as hostname inside Docker network, as defined in docker-compose.yml
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:29092")
KAFKA_TOPIC_FINANCIAL = os.getenv("KAFKA_TOPIC_FINANCIAL", "raw_financial_transactions")
KAFKA_TOPIC_INSURANCE = os.getenv("KAFKA_TOPIC_INSURANCE", "raw_insurance_claims")

producer = None

# Pydantic Models (same as Starter Track, for consistency)
class FinancialTransaction(BaseModel):
    transaction_id: str = Field(..., example="FT-20231026-001")
    timestamp: datetime = Field(..., example="2023-10-26T14:30:00Z")
    account_id: str = Field(..., example="ACC-001")
    amount: float = Field(..., gt=0, example=150.75)
    currency: str = Field(..., max_length=3, example="USD")
    transaction_type: str = Field(..., example="debit")
    merchant_id: Optional[str] = Field(None, example="MER-XYZ")
    category: Optional[str] = Field(None, example="groceries")

class InsuranceClaim(BaseModel):
    claim_id: str = Field(..., example="IC-20231026-001")
    timestamp: datetime = Field(..., example="2023-10-26T15:00:00Z")
    policy_number: str = Field(..., example="POL-987654")
    claim_amount: float = Field(..., gt=0, example=1000.00)
    claim_type: str = Field(..., example="auto")
    claim_status: str = Field(..., example="submitted")
    customer_id: str = Field(..., example="CUST-ABC")
    incident_date: datetime = Field(..., example="2023-09-15T08:00:00Z")


@app.on_event("startup")
async def startup_event():
    global producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'), # Handle datetime serialization
            acks='all', # Ensure all in-sync replicas have received the message
            retries=3
        )
        print(f"Kafka producer connected to {KAFKA_BROKER}")
    except Exception as e:
        print(f"Failed to connect to Kafka: {e}")
        raise HTTPException(status_code=500, detail=f"Could not connect to Kafka: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if producer:
        producer.flush() # Ensure all buffered records are sent
        producer.close()
        print("Kafka producer closed.")

@app.get("/", tags=["Monitoring"])
async def read_main():
    return {"message": "Welcome to Intermediate Data Ingestor API!"}

@app.get("/health", tags=["Monitoring"])
async def health_check():
    # In a real app, you'd check producer.bootstrap_connected() or similar
    if producer and producer.bootstrap_connected():
        return {"status": "healthy", "kafka_status": "connected"}
    return {"status": "degraded", "kafka_status": "disconnected"}

@app.post("/ingest-financial-transaction/", status_code=status.HTTP_200_OK, tags=["Ingestion"])
async def ingest_financial_transaction(transaction: FinancialTransaction):
    if not producer:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kafka producer not initialized.")
    try:
        # producer.send() returns a future; for async FastAPI, you can await it
        future = producer.send(KAFKA_TOPIC_FINANCIAL, value=transaction.dict(by_alias=True, exclude_unset=True))
        record_metadata = await asyncio.to_thread(future.get) # Await the delivery report in a thread pool
        print(f"Sent financial transaction to topic {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
        return {"message": "Financial transaction ingested successfully", "transaction_id": transaction.transaction_id}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send to Kafka: {e}")

@app.post("/ingest-insurance-claim/", status_code=status.HTTP_200_OK, tags=["Ingestion"])
async def ingest_insurance_claim(claim: InsuranceClaim):
    if not producer:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kafka producer not initialized.")
    try:
        future = producer.send(KAFKA_TOPIC_INSURANCE, value=claim.dict(by_alias=True, exclude_unset=True))
        record_metadata = await asyncio.to_thread(future.get) # Await the delivery report in a thread pool
        print(f"Sent insurance claim to topic {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")
        return {"message": "Insurance claim ingested successfully", "claim_id": claim.claim_id}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send to Kafka: {e}")