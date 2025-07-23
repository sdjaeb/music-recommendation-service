# pyspark_jobs/process_weekly_trends.py
import os
import sys
import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, year, month
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, TimestampType
)

def read_secret(secret_name: str) -> str:
    """Reads a secret from a file path specified by an environment variable."""
    secret_path = os.getenv(secret_name)
    if not secret_path or not os.path.exists(secret_path):
        print(f"Error: Secret file path for {secret_name} not found or env var not set.", file=sys.stderr)
        sys.exit(1)
    with open(secret_path, 'r') as f:
        return f.read().strip()

# --- Argument Parsing ---
parser = argparse.ArgumentParser()
parser.add_argument("--input-path", required=True, help="The S3A path to the weekly trends CSV file.")
args = parser.parse_args()

# --- Spark Session Setup ---
minio_access_key = read_secret('MINIO_ACCESS_KEY_FILE')
minio_secret_key = read_secret('MINIO_SECRET_KEY_FILE')

spark = SparkSession.builder \
    .appName("WeeklyTrendsIngestion") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", minio_access_key) \
    .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .getOrCreate()

# --- Configuration ---
BRONZE_ZONE_BASE = "s3a://data/bronze"
FACT_TABLE_PATH = f"{BRONZE_ZONE_BASE}/fact_listening_events"

# --- Schema Definition ---
LISTENING_EVENTS_SCHEMA = StructType([
    StructField("event_id", StringType(), False),
    StructField("user_id", LongType(), False),
    StructField("track_id", LongType(), False),
    StructField("event_type", StringType(), True),
    StructField("timestamp", TimestampType(), True)
])

# --- Main Processing Logic ---
print(f"--- Processing weekly trends from {args.input_path} ---")

df = spark.read.csv(args.input_path, header=True, schema=LISTENING_EVENTS_SCHEMA)
df_with_partitions = df.withColumn("event_date", to_date(col("timestamp"))) \
                       .withColumn("year", year(col("event_date"))) \
                       .withColumn("month", month(col("event_date")))

print(f"Appending to Delta table: {FACT_TABLE_PATH}")
df_with_partitions.write.format("delta").mode("append").option("mergeSchema", "false").save(FACT_TABLE_PATH)

print(f"--- Finished processing weekly trends ---")
spark.stop()