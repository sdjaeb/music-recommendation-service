# process_recommendation_events.py
# This Spark Streaming job connects to the 'music_recommendations' Kafka topic,
# parses the incoming JSON events, and writes the structured data to a Delta Lake
# table in MinIO, creating a persistent "bronze" layer in our data lake.

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, IntegerType, ArrayType, StringType

# --- MinIO/S3 Configuration ---
# A helper function to read credentials from files mounted by Docker secrets.
def read_secret(secret_name):
    secret_path = os.getenv(secret_name)
    if secret_path and os.path.exists(secret_path):
        with open(secret_path, 'r') as f:
            return f.read().strip()
    print(f"Warning: Could not read secret for {secret_name}")
    return None

# Read the MinIO credentials from the environment variables set in docker-compose.yml
minio_access_key = read_secret('MINIO_ACCESS_KEY_FILE')
minio_secret_key = read_secret('MINIO_SECRET_KEY_FILE')

# Define the schema for the incoming Kafka messages to ensure proper parsing.
# This schema must match the JSON structure produced by the MusicRecommendationService.
schema = StructType([
    StructField("requestedTrackId", IntegerType(), True),
    StructField("recommendations", ArrayType(IntegerType()), True),
    StructField("timestamp", StringType(), True) # Read as string, as it comes in ISO 8601 format
])

# Define paths for our data lake storage in MinIO
DELTA_TABLE_PATH = "s3a://data/bronze/recommendation_events"
CHECKPOINT_PATH = "s3a://data/_checkpoints/recommendation_events_checkpoint"

# Initialize a Spark Session with all S3A and Delta configurations applied during the build process.
# This is the most reliable method for ensuring the S3A client is configured correctly.
spark = SparkSession.builder \
    .appName("MusicRecommendationEventProcessor") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", minio_access_key) \
    .config("spark.hadoop.fs.s3a.secret.key", minio_secret_key) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    .config("spark.hadoop.fs.s3a.committer.name", "directory") \
    .config("spark.hadoop.fs.s3a.committer.staging.conflict-mode", "replace") \
    .config("spark.hadoop.fs.s3a.committer.staging.unique-filenames", "true") \
    .config("spark.sql.sources.commit.protocol.class", "org.apache.spark.internal.io.cloud.PathOutputCommitProtocol") \
    .getOrCreate()

# Create a streaming DataFrame that reads from the Kafka topic.
# "startingOffsets": "earliest" ensures we process all messages from the beginning.
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:29092") \
    .option("subscribe", "music_recommendations") \
    .option("startingOffsets", "earliest") \
    .load()

# Select the 'value' column (which contains the message payload), cast it to a string,
# and then parse the JSON data using the defined schema.
parsed_df = kafka_df.select(from_json(col("value").cast("string"), schema).alias("data")) \
    .select("data.*")

# --- Write to Console for easy debugging ---
console_query = parsed_df.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", "false") \
    .start()

# --- Write to Delta Table in MinIO ---
# The primary stream that persists the data to the data lake.
delta_query = parsed_df.writeStream \
    .outputMode("append") \
    .format("delta") \
    .option("checkpointLocation", CHECKPOINT_PATH) \
    .start(DELTA_TABLE_PATH)

spark.streams.awaitAnyTermination()
