# pyspark_jobs/process_weekly_trends.py
import argparse
from pyspark.sql.functions import col, to_date, year, month
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, TimestampType
)
from spark_utils import get_spark_session

# --- Argument Parsing ---
parser = argparse.ArgumentParser()
parser.add_argument("--input-path", required=True, help="The S3A path to the weekly trends CSV file.")
args = parser.parse_args()

# --- Spark Session Setup ---
spark = get_spark_session("WeeklyTrendsIngestion")

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