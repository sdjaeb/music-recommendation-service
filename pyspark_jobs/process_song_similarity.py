# pyspark_jobs/process_song_similarity.py
import argparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, lit

def process_song_similarity(spark, data_bucket):
    """
    Calculates song co-occurrence based on playlists and saves it to a Silver table.

    This job reads the playlist-track bridge table from the Bronze layer, performs a
    self-join to find pairs of songs that appear in the same playlists, counts their
    co-occurrences, and writes the result to a new Delta table in the Silver layer.
    """
    bronze_path = f"s3a://{data_bucket}/bronze"
    silver_path = f"s3a://{data_bucket}/silver"

    # 1. Read the bridge table from the Bronze layer
    print(f"Reading playlist-track data from {bronze_path}/bridge_playlist_tracks...")
    playlist_tracks_df = spark.read.format("delta").load(f"{bronze_path}/bridge_playlist_tracks")

    # 2. Create aliases for the self-join
    df1 = playlist_tracks_df.alias("df1")
    df2 = playlist_tracks_df.alias("df2")

    # 3. Perform the self-join to find co-occurring song pairs
    # The condition df1.track_id < df2.track_id is crucial to:
    #   a) Avoid duplicate pairs (song_A, song_B) and (song_B, song_A).
    #   b) Avoid self-pairs (song_A, song_A).
    print("Performing self-join to find co-occurring song pairs...")
    co_occurrence_df = df1.join(
        df2,
        (col("df1.playlist_id") == col("df2.playlist_id")) &
        (col("df1.track_id") < col("df2.track_id"))
    ).groupBy(
        col("df1.track_id").alias("track_id_1"),
        col("df2.track_id").alias("track_id_2")
    ).agg(
        count(lit(1)).alias("score")
    ).orderBy(col("score").desc())

    # 4. Write the result to the Silver layer
    output_path = f"{silver_path}/song_similarity_by_playlist"
    print(f"Writing song similarity scores to {output_path}...")
    co_occurrence_df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(output_path)

    print("Song similarity processing complete.")
    print(f"Top 10 most similar song pairs:")
    co_occurrence_df.show(10, truncate=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-bucket", type=str, required=True, help="Name of the MinIO bucket containing bronze and silver data.")
    args = parser.parse_args()

    spark = (
        SparkSession.builder.appName("SongSimilarityProcessing")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )

    process_song_similarity(spark, data_bucket=args.data_bucket)
    spark.stop()