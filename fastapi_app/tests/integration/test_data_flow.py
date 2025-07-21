# Description: Integration tests for data flow (FastAPI -> Kafka -> Spark -> Delta Lake).
# Source: Deep-Dive Addendum: IaC & CI/CD Recipes, Section 5.4.
#
# This example uses docker-compose command directly, but Testcontainers provides
# a more Pythonic way to manage test lifecycle.
import pytest
import requests
import subprocess
import time
from kafka import KafkaConsumer
import json
import os
from datetime import datetime
from minio import Minio # Assuming minio client library is installed

# Define the path to your test compose file
COMPOSE_FILE = os.path.join(os.path.dirname(__file__), '../../../docker_compose/docker-compose.test.yml')

@pytest.fixture(scope="module")
def docker_services(request):
    """Starts and stops docker-compose services for integration tests."""
    print(f"\nStarting Docker services from: {COMPOSE_FILE}")
    # Ensure services are down first
    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "down", "-v"], check=True)
    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "up", "--build", "-d"], check=True)

    # Wait for FastAPI to be healthy
    api_url = "http://localhost:8000"
    for _ in range(60): # Wait up to 60 seconds (increased from 30)
        try:
            response = requests.get(f"{api_url}/health")
            if response.status_code == 200 and response.json().get("status") == "healthy":
                print("FastAPI is healthy.")
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
    else:
        pytest.fail("FastAPI did not become healthy in time.")

    # Wait for Kafka to be healthy
    kafka_broker = "localhost:9092"
    print(f"Waiting for Kafka at {kafka_broker}...")
    # More robust check could involve kafka-topics --list or similar
    time.sleep(15) # Give Kafka some time to initialize

    # Wait for MinIO to be healthy and create test bucket
    minio_client = Minio("localhost:9000", access_key="test_user", secret_key="test_password", secure=False)
    bucket_name = "raw-data-bucket-test"
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            print(f"MinIO bucket '{bucket_name}' created.")
        print(f"MinIO healthy and bucket '{bucket_name}' ready.")
    except Exception as e:
        pytest.fail(f"MinIO setup failed: {e}")

    yield # Tests run here

    print("Stopping Docker services.")
    subprocess.run(["docker", "compose", "-f", COMPOSE_FILE, "down", "-v"], check=True)

def test_end_to_end_financial_transaction_flow(docker_services):
    """Tests ingestion via FastAPI, consumption via Kafka, and processing to Delta Lake."""
    api_url = "http://localhost:8000"
    kafka_topic = "raw_data_test" # As defined in docker-compose.test.yml
    kafka_broker = "localhost:9092"
    minio_host = "localhost:9000"
    minio_access_key = "test_user"
    minio_secret_key = "test_password"
    minio_bucket = "raw-data-bucket-test"
    spark_output_dir_prefix = "financial_data_delta_test" # Matches the path used in streaming_consumer_test.py

    # 1. Send data via FastAPI
    transaction_id = f"INT-FIN-{datetime.now().strftime('%H%M%S%f')}"
    transaction_data = {
        "transaction_id": transaction_id,
        "timestamp": datetime.now().isoformat(),
        "account_id": "ACC-INT-001",
        "amount": 123.45,
        "currency": "USD",
        "transaction_type": "deposit"
    }
    print(f"Sending transaction via FastAPI: {transaction_id}")
    response = requests.post(f"{api_url}/ingest-financial-transaction/", json=transaction_data)
    assert response.status_code == 200
    assert response.json()["message"] == "Financial transaction ingested successfully"

    # 2. Consume data from Kafka and verify (optional, for explicit check)
    # Give Kafka some time to receive the message
    time.sleep(2)
    consumer = KafkaConsumer(
        kafka_topic,
        bootstrap_servers=[kafka_broker],
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        group_id=f'test-consumer-group-{transaction_id}',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        consumer_timeout_ms=5000 # Timeout after 5 seconds if no messages
    )
    consumed_message = None
    for msg in consumer:
        consumed_message = msg.value
        print(f"Consumed from Kafka: {consumed_message}")
        if consumed_message.get("transaction_id") == transaction_data["transaction_id"]:
            break
    consumer.close()
    assert consumed_message is not None, "Did not consume message from Kafka"
    assert consumed_message["transaction_id"] == transaction_data["transaction_id"]

    # 3. Trigger Spark job to process from Kafka to Delta Lake
    # This assumes pyspark_jobs/streaming_consumer_test.py is a simple
    # Spark Structured Streaming job that reads from Kafka and writes to Delta Lake in MinIO.
    spark_submit_command = [
        "docker", "exec", "spark-test-runner", "spark-submit",
        "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,io.delta:delta-core_2.12:2.4.0",
        "--conf", "spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension",
        "--conf", "spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog",
        "--conf", f"spark.hadoop.fs.s3a.endpoint=http://{minio_host}",
        "--conf", f"spark.hadoop.fs.s3a.access.key={minio_access_key}",
        "--conf", f"spark.hadoop.fs.s3a.secret.key={minio_secret_key}",
        "--conf", "spark.hadoop.fs.s3a.path.style.access=true",
        "/opt/bitnami/spark/data/pyspark_jobs/streaming_consumer_test.py", # Full path within container
        kafka_topic,
        "kafka:29092", # Kafka broker for Spark
        f"s3a://{minio_bucket}/{spark_output_dir_prefix}" # S3a path for Delta Lake output
    ]
    print(f"Running Spark job: {' '.join(spark_submit_command)}")
    # Run in a separate process and wait for it to complete.
    # Set timeout for the spark-submit command
    try:
        spark_process = subprocess.run(spark_submit_command, capture_output=True, text=True, check=True, timeout=60)
        print("Spark job stdout:\n", spark_process.stdout)
        print("Spark job stderr:\n", spark_process.stderr)
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Spark job failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        pytest.fail("Spark job timed out.")

    # Give Spark time to write data (it's streaming, so it might take a moment)
    time.sleep(10)

    # 4. Verify data in Delta Lake (MinIO)
    # Re-initialize client to ensure fresh state
    minio_client_verify = Minio(minio_host, access_key=minio_access_key, secret_key=minio_secret_key, secure=False)

    # Use a direct Spark SQL query via spark-test-runner to confirm data in Delta Lake
    spark_sql_command = [
        "docker", "exec", "spark-test-runner", "spark-sql",
        "--packages", "io.delta:delta-core_2.12:2.4.0",
        "--conf", "spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension",
        "--conf", "spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog",
        "--conf", f"spark.hadoop.fs.s3a.endpoint=http://{minio_host}",
        "--conf", f"spark.hadoop.fs.s3a.access.key={minio_access_key}",
        "--conf", f"spark.hadoop.fs.s3a.secret.key={minio_secret_key}",
        "--conf", "spark.hadoop.fs.s3a.path.style.access=true",
        "-e", f"SELECT transaction_id FROM delta.`s3a://{minio_bucket}/{spark_output_dir_prefix}` WHERE transaction_id = '{transaction_id}' LIMIT 1;"
    ]
    print(f"Verifying data with Spark SQL: {' '.join(spark_sql_command)}")
    try:
        sql_process = subprocess.run(spark_sql_command, capture_output=True, text=True, check=True, timeout=30)
        print("Spark SQL stdout:\n", sql_process.stdout)
        print("Spark SQL stderr:\n", sql_process.stderr)
        assert transaction_id in sql_process.stdout, f"Transaction ID {transaction_id} not found in Delta Lake."
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Spark SQL verification failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        pytest.fail("Spark SQL verification timed out.")