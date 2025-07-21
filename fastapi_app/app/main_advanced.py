# Description: Entry point for FastAPI application (Advanced Track).
# Source: Building Enterprise-Ready Data Platforms v2.4, Appendix A.3 (Conceptual); Highlighting OpenTelemetry.
#
# This version includes OpenTelemetry instrumentation for distributed tracing and metrics.
# It maintains Kafka production capabilities.
import os
import json
from datetime import datetime
from typing import Optional
import io
import time # For custom latency measurement example

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from kafka import KafkaProducer

# --- OpenTelemetry Imports and Setup ---
from opentelemetry import metrics, trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter, # For local debugging
    PeriodicExportingMetricReader,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor # For logs

# Resource for identifying the service
resource = Resource.create({
    "service.name": "fastapi-ingestor",
    "service.version": "1.0.0",
    "env.type": "local-dev"
})

# Configure OTLP Exporter endpoint (Grafana Alloy)
# This should match the otelcol.receiver.otlp config in alloy-config.river
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://grafana-alloy:4318")

# Metrics Provider (for custom metrics)
# Uses HTTP exporter for metrics, adjust endpoint for gRPC if needed (port 4317)
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=f"{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/metrics")
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter("fastapi.ingestion.app")

# Create counters for business metrics
financial_tx_counter = meter.create_counter(
    "financial.transactions.ingested",
    description="Number of financial transactions ingested",
    unit="1"
)
insurance_claim_counter = meter.create_counter(
    "insurance.claims.ingested",
    description="Number of insurance claims ingested",
    unit="1"
)
# Add a Histogram to track ingestion latency (Advanced Use Case 3 in OpenTelemetry)
ingestion_latency_histogram = meter.create_histogram(
    "ingestion.request.duration",
    description="Duration of data ingestion requests",
    unit="ms",
    boundaries=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0, 10000.0]
)

# Tracer Provider (for distributed tracing)
trace_exporter = OTLPSpanExporter(endpoint=f"{OTEL_EXPORTER_OTLP_ENDPOINT}/v1/traces")
trace.set_tracer_provider(TracerProvider(resource=resource))
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(trace_exporter)
)
tracer = trace.get_tracer(__name__) # Get a tracer instance

# Instrument logging to include trace/span IDs (Advanced Use Case 2 in OpenTelemetry)
LoggingInstrumentor().instrument(set_logging_format=True)


# --- Pydantic Models (common for all tracks) ---
class FinancialTransaction(BaseModel):
    transaction_id: str = Field(..., example="FT-20231026-001")
    timestamp: datetime = Field(..., example="2023-10-26T14:30:00Z")
    account_id: str = Field(..., example="ACC-001")
    amount: float = Field(..., gt=0, example=150.75)
    currency: str = Field(..., max_length=3, example="USD")
    transaction_type: str = Field(..., example="debit")
    merchant_id: Optional[str] = Field(None, example="MER-XYZ")
    category: Optional[str] = Field(None, example="groceries")
    is_flagged: Optional[bool] = Field(None, example=False) # Added for Delta Lake schema evolution demo

class InsuranceClaim(BaseModel):
    claim_id: str = Field(..., example="IC-20231026-001")
    timestamp: datetime = Field(..., example="2023-10-26T15:00:00Z")
    policy_number: str = Field(..., example="POL-987654")
    claim_amount: float = Field(..., gt=0, example=1000.00)
    claim_type: str = Field(..., example="auto")
    claim_status: str = Field(..., example="submitted")
    customer_id: str = Field(..., example="CUST-ABC")
    incident_date: datetime = Field(..., example="2023-09-15T08:00:00Z")


app = FastAPI(
    title="Financial/Insurance Data Ingestor API",
    description="API for ingesting various financial and insurance data into the data platform.",
    version="1.0.0",
)

# Instrument FastAPI application with OpenTelemetry (Basic Use Case in OpenTelemetry)
FastAPIInstrumentor.instrument_app(app)

# --- Kafka Producer Setup (same as Intermediate Track) ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:29092")
KAFKA_TOPIC_FINANCIAL = os.getenv("KAFKA_TOPIC_FINANCIAL", "raw_financial_transactions")
KAFKA_TOPIC_INSURANCE = os.getenv("KAFKA_TOPIC_INSURANCE", "raw_insurance_claims")

producer = None

@app.on_event("startup")
async def startup_event():
    global producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            acks='all',
            retries=3
        )
        print(f"Kafka producer connected to {KAFKA_BROKER}")
    except Exception as e:
        print(f"Error initializing Kafka Producer: {e}")
        producer = None # Set to None if connection fails
        # raise HTTPException(status_code=500, detail=f"Could not connect to Kafka: {e}") # Re-raise if fatal

@app.on_event("shutdown")
async def shutdown_event():
    if producer:
        producer.flush()
        producer.close()
        print("Kafka producer closed.")
    # Ensure OpenTelemetry exporters are shut down
    if trace.get_tracer_provider():
        trace.get_tracer_provider().shutdown()
    if metrics.get_meter_provider():
        metrics.get_meter_provider().shutdown()


# --- API Endpoints ---
@app.get("/health", tags=["Monitoring"])
async def health_check():
    status_details = {"status": "healthy"}
    if producer:
        status_details["kafka_status"] = "connected" if producer.bootstrap_connected() else "disconnected"
    else:
        status_details["kafka_status"] = "not_initialized"

    if status_details["kafka_status"] == "disconnected" or status_details["kafka_status"] == "not_initialized":
        status_details["status"] = "degraded"
    return status_details


@app.post("/ingest-financial-transaction/", status_code=status.HTTP_200_OK, tags=["Ingestion"])
async def ingest_financial_transaction(transaction: FinancialTransaction):
    start_time = time.time() # For custom latency metric
    with tracer.start_as_current_span("ingest_financial_transaction_api"):
        if not producer:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kafka producer not initialized.")
        try:
            future = producer.send(KAFKA_TOPIC_FINANCIAL, value=transaction.dict(by_alias=True, exclude_unset=True))
            record_metadata = await asyncio.to_thread(future.get) # Await the delivery report
            trace.get_current_span().set_attribute("kafka.offset", record_metadata.offset)
            trace.get_current_span().set_attribute("kafka.topic", record_metadata.topic)
            print(f"Sent financial transaction to topic {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")

            # Increment custom metric (Basic Use Case in OpenTelemetry)
            financial_tx_counter.add(1, {
                "transaction.type": transaction.transaction_type,
                "currency": transaction.currency,
                "is_flagged": transaction.is_flagged # Add new attribute for schema evolution
            })
            return {"message": "Financial transaction ingested successfully", "transaction_id": transaction.transaction_id}
        except Exception as e:
            trace.get_current_span().record_exception(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send to Kafka: {e}")
        finally:
            duration_ms = (time.time() - start_time) * 1000
            ingestion_latency_histogram.record(duration_ms, {"endpoint": "/ingest-financial-transaction", "status": "success"})


@app.post("/ingest-insurance-claim/", status_code=status.HTTP_200_OK, tags=["Ingestion"])
async def ingest_insurance_claim(claim: InsuranceClaim):
    start_time = time.time() # For custom latency metric
    with tracer.start_as_current_span("ingest_insurance_claim_api"):
        if not producer:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Kafka producer not initialized.")
        try:
            future = producer.send(KAFKA_TOPIC_INSURANCE, value=claim.dict(by_alias=True, exclude_unset=True))
            record_metadata = await asyncio.to_thread(future.get) # Await the delivery report
            trace.get_current_span().set_attribute("kafka.offset", record_metadata.offset)
            trace.get_current_span().set_attribute("kafka.topic", record_metadata.topic)
            print(f"Sent insurance claim to topic {record_metadata.topic} partition {record_metadata.partition} offset {record_metadata.offset}")

            # Increment custom metric
            insurance_claim_counter.add(1, {
                "claim.type": claim.claim_type,
                "claim.status": claim.claim_status
            })
            return {"message": "Insurance claim ingested successfully", "claim_id": claim.claim_id}
        except Exception as e:
            trace.get_current_span().record_exception(e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to send to Kafka: {e}")
        finally:
            duration_ms = (time.time() - start_time) * 1000
            ingestion_latency_histogram.record(duration_ms, {"endpoint": "/ingest-insurance-claim", "status": "success"})