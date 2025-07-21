# run_weekly_trending_analysis.py
# A Spark batch job that reads the raw user listening history from the Bronze
# Delta table, calculates the top 10 most popular tracks from the last 7 days,
# and saves the result to a Silver Delta table.

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, window, count
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

def read_secret(secret_name):
    secret_path = os.getenv(secret_name)
    if secret_path and os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            return f.read().strip()
    return None

minio_access_key = read_secret('MINIO_ACCESS_KEY_FILE')
minio_secret_key = read_secret('MINIO_SECRET_KEY_FILE')

# Define paths for our data lake tables
BRONZE_TABLE_PATH = "s3a://data/bronze/user_listening_history" # Assuming a separate job writes here
SILVER_TABLE_PATH = "s3a://data/silver/weekly_trending_tracks"

spark = SparkSession.builder \
    .appName("WeeklyTrendingAnalysis") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", minio_access_key) \
    .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .getOrCreate()

print(f"Reading listening history from: {BRONZE_TABLE_PATH}")

# For this example, we'll assume a streaming job has populated the bronze table.
# We'll create a dummy DataFrame to simulate this. In a real scenario, you'd read from the table:
# listening_df = spark.read.format("delta").load(BRONZE_TABLE_PATH)

# For demonstration, let's create a dummy DataFrame
from datetime import datetime, timedelta
data = [(i % 10 + 101, datetime.utcnow() - timedelta(days=random.randint(0, 10))) for i in range(1000)]
listening_df = spark.createDataFrame(data, ["trackId", "timestamp"])

print("Calculating weekly trending tracks...")

# Filter for events in the last 7 days and count plays per track
trending_df = listening_df \
    .filter(col("timestamp") >= (datetime.utcnow() - timedelta(days=7))) \
    .groupBy("trackId") \
    .agg(count("*").alias("play_count")) \
    .orderBy(col("play_count").desc()) \
    .limit(10)

print("Top 10 Trending Tracks (Last 7 Days):")
trending_df.show()

print(f"Writing aggregated results to Silver table: {SILVER_TABLE_PATH}")
trending_df.write.format("delta").mode("overwrite").save(SILVER_TABLE_PATH)

print("--- Weekly trending analysis complete. ---")
spark.stop()