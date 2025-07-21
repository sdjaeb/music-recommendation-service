# Description: Entry point for FastAPI application (Starter Track).
# Source: Building Enterprise-Ready Data Platforms v2.4, Appendix A.1 (Conceptual).
#
# This version stores data directly to PostgreSQL or MinIO.
import os
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import psycopg2
from minio import Minio

app = FastAPI(
    title="Financial/Insurance Data Ingestor API (Starter)",
    description="API for ingesting various financial and insurance data into the data platform.",
    version="1.0.0",
)

# Database/MinIO configuration
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgres")

# PostgreSQL config
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "main_db")

# MinIO config
MINIO_HOST = os.getenv("MINIO_HOST", "localhost")
MINIO_PORT = os.getenv("MINIO_PORT", "9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "raw-data-bucket")

# Global client objects
pg_conn = None
minio_client = None

# Pydantic Models (common for all tracks)
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
    global pg_conn, minio_client
    if DATABASE_TYPE == "postgres":
        try:
            pg_conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB
            )
            print(f"PostgreSQL connected to {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
            # Create table if not exists (simplified for demo)
            with pg_conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS financial_transactions (
                        transaction_id VARCHAR(255) PRIMARY KEY,
                        timestamp TIMESTAMP,
                        account_id VARCHAR(255),
                        amount NUMERIC,
                        currency VARCHAR(3),
                        transaction_type VARCHAR(50),
                        merchant_id VARCHAR(255),
                        category VARCHAR(255)
                    );
                """)
                pg_conn.commit()
                print("PostgreSQL table 'financial_transactions' ensured.")
        except Exception as e:
            print(f"Failed to connect to PostgreSQL: {e}")
            raise HTTPException(status_code=500, detail=f"Could not connect to PostgreSQL: {e}")
    elif DATABASE_TYPE == "minio":
        try:
            minio_client = Minio(
                f"{MINIO_HOST}:{MINIO_PORT}",
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=False # Use secure=True for HTTPS
            )
            if not minio_client.bucket_exists(MINIO_BUCKET):
                minio_client.make_bucket(MINIO_BUCKET)
                print(f"MinIO bucket '{MINIO_BUCKET}' created.")
            print(f"MinIO client connected to {MINIO_HOST}:{MINIO_PORT}")
        except Exception as e:
            print(f"Failed to connect to MinIO: {e}")
            raise HTTPException(status_code=500, detail=f"Could not connect to MinIO: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if pg_conn:
        pg_conn.close()
        print("PostgreSQL connection closed.")
    if minio_client:
        print("MinIO client connection implicitly closed.")

@app.get("/health", tags=["Monitoring"])
async def health_check():
    status_details = {"status": "healthy"}
    if DATABASE_TYPE == "postgres":
        try:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT 1")
            status_details["db_status"] = "connected"
        except Exception:
            status_details["status"] = "degraded"
            status_details["db_status"] = "disconnected"
    elif DATABASE_TYPE == "minio":
        try:
            minio_client.bucket_exists(MINIO_BUCKET)
            status_details["minio_status"] = "connected"
        except Exception:
            status_details["status"] = "degraded"
            status_details["minio_status"] = "disconnected"
    return status_details

@app.post("/ingest-financial-transaction/", status_code=status.HTTP_200_OK, tags=["Ingestion"])
async def ingest_financial_transaction(transaction: FinancialTransaction):
    try:
        if DATABASE_TYPE == "postgres":
            with pg_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO financial_transactions (transaction_id, timestamp, account_id, amount, currency, transaction_type, merchant_id, category)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (transaction_id) DO UPDATE SET
                        timestamp = EXCLUDED.timestamp,
                        account_id = EXCLUDED.account_id,
                        amount = EXCLUDED.amount,
                        currency = EXCLUDED.currency,
                        transaction_type = EXCLUDED.transaction_type,
                        merchant_id = EXCLUDED.merchant_id,
                        category = EXCLUDED.category;
                    """,
                    (transaction.transaction_id, transaction.timestamp, transaction.account_id,
                     transaction.amount, transaction.currency, transaction.transaction_type,
                     transaction.merchant_id, transaction.category)
                )
                pg_conn.commit()
            print(f"Financial transaction {transaction.transaction_id} ingested to PostgreSQL.")
        elif DATABASE_TYPE == "minio":
            object_name = f"financial_transactions/{transaction.transaction_id}.json"
            data_bytes = json.dumps(transaction.dict(by_alias=True, exclude_unset=True), default=str).encode('utf-8')
            minio_client.put_object(
                MINIO_BUCKET,
                object_name,
                io.BytesIO(data_bytes),
                len(data_bytes),
                content_type="application/json"
            )
            print(f"Financial transaction {transaction.transaction_id} ingested to MinIO at {object_name}.")
        return {"message": "Financial transaction ingested successfully", "transaction_id": transaction.transaction_id}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to ingest transaction: {e}")

@app.post("/ingest-insurance-claim/", status_code=status.HTTP_200_OK, tags=["Ingestion"])
async def ingest_insurance_claim(claim: InsuranceClaim):
    # This example only implements financial transactions for Starter Track simplicity.
    # In a real scenario, you'd add similar logic for insurance claims.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Insurance claim ingestion not implemented in Starter Track.")