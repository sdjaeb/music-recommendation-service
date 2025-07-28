from pyspark.sql import SparkSession
from pyspark.sql.functions import col

# Create a SparkSession
spark = SparkSession.builder.appName("ListeningDataAnalysis").getOrCreate()

# --- Load DataFrames ---
listening_df = spark.read.format("delta").load("s3a://data/bronze/fact_listening_events")
similarity_df = spark.read.format("delta").load("s3a://data/silver/song_similarity_by_playlist")

# --- Query 1: Calculate total 'like' events per user ---
user_likes_df = listening_df.filter(col("event_type") == "like") \
    .groupBy("user_id") \
    .count() \
    .withColumnRenamed("count", "total_likes_count")

# --- Query 2: Calculate 'like' events that have similarity data per user ---
# Get all unique tracks from the similarity model into a single column
similar_tracks_1 = similarity_df.select(col("track_id_1").alias("track_id"))
similar_tracks_2 = similarity_df.select(col("track_id_2").alias("track_id"))
all_similar_tracks = similar_tracks_1.union(similar_tracks_2).distinct()

# Find users who have liked tracks that are in the similarity model
relevant_users_df = listening_df.filter(col("event_type") == "like") \
    .join(all_similar_tracks, "track_id") \
    .groupBy("user_id") \
    .agg({"*": "count"}) \
    .withColumnRenamed("count(1)", "relevant_likes_count")

# --- Consolidate and Show Results ---
# Join the two aggregated DataFrames to get a consolidated view
consolidated_df = user_likes_df.join(relevant_users_df, "user_id", "left") \
    .na.fill(0, ["relevant_likes_count"]) \
    .select("user_id", "total_likes_count", "relevant_likes_count")

print("--- Top 5 Users by Total Likes ---")
consolidated_df.orderBy(col("total_likes_count").desc()).show(5)

print("\n--- Top 5 Users by Relevant Likes (Likes with similarity scores) ---")
consolidated_df.orderBy(col("relevant_likes_count").desc()).show(5)

# Stop the SparkSession
spark.stop()