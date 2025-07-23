# Project Roadmap

This document outlines the development plan for the music recommendation data platform, detailing features from foundational data engineering to advanced machine learning.

---

## Phase 1: Data Generation & Ingestion

The foundation of any data product is rich, realistic data and a robust ingestion pipeline.

### 1.1. Generate Historical Data (2024)
-   **Complexity:** Medium
-   **Description:** Enhance the `generate_seed_data.py` script to produce a comprehensive, static historical dataset for the year 2024. This will serve as the initial state of our data lake.
-   **Implementation Steps:**
    -   [x] Generate a single, large `fact_listening_events_2024.csv` file.
    -   [x] Model user and song growth over the year.
    -   [x] Implement a popularity model to simulate trends (sleeper hits, genre events).
    -   [x] Generate dimension data (`dim_songs.csv`, `dim_users.csv`).
    -   [x] Generate relationship data (`graph_user_follows.csv`, `dim_playlists.csv`, `bridge_playlist_tracks.csv`).
    -   [x] Create an initial Airflow DAG to perform a one-time upload of these historical CSVs into partitioned Delta tables in MinIO (the "Bronze" layer).

### 1.2. Ingest Weekly Incremental Data (2025)
-   **Complexity:** Medium
-   **Description:** Simulate the ongoing operation of the service in 2025 by ingesting weekly data dumps. This demonstrates automated, incremental batch processing.
-   **Implementation Steps:**
    -   [x] Create a Python script (`generate_weekly_trends.py`) that generates a new `trends_YYYY-MM-DD.csv` file each time it's run.
    -   [x] Develop a new PySpark job (`process_weekly_trends.py`) to append incremental data.
    -   [x] Develop a new Airflow DAG (`dag_weekly_trends_ingestion`) scheduled to run daily.
    -   [x] The DAG scans for new local files, uploads them to MinIO, and triggers the Spark job to append the new data to the `fact_listening_events` Delta table.

---

## Phase 2: Recommendation Engine Enhancements

Build a sophisticated, hybrid recommendation model by combining multiple signals with different weights.

### 2.1. Create "Silver" Layer Analytical Tables
-   **Complexity:** Medium
-   **Description:** Develop Spark jobs (scheduled by Airflow) to transform raw Bronze data into cleaned, aggregated Silver tables that will power the recommendation models.
-   **Implementation Steps:**
    -   [ ] **Weekly Trending:** Create a `weekly_trending_tracks` table by aggregating play counts over a 7-day window.
    -   [ ] **Playlist Co-occurrence:** Create a `song_similarity_by_playlist` table by calculating which songs frequently appear in the same playlists.
    -   [ ] **Artist/Genre Masters:** Ensure `dim_songs` and `dim_users` are clean and available.

### 2.2. Implement Hybrid Recommendation Model
-   **Complexity:** High
-   **Description:** Evolve the `.NET` `RecommendationService` to fetch data from the Silver tables in MinIO and combine multiple recommendation strategies using a weighted scoring system.
-   **Implementation Steps:**
    -   [ ] **(Low Weight) Content-Based:** Recommend songs from the same artist or genre.
    -   [ ] **(Low Weight) Popularity-Based:** Include tracks from the `weekly_trending_tracks` table.
    -   [ ] **(Medium Weight) Playlist-Based:** Use the `song_similarity_by_playlist` table to find songs that are often playlisted together.
    -   [ ] **(Medium Weight) Social-Based:** Recommend songs liked by users that the current user follows, using the `graph_user_follows` data.
    -   [ ] **(High Weight) Collaborative Filtering:** Implement the existing "users who liked this also liked..." model, but run it on the full historical dataset.
    -   [ ] **(High Weight) Audio Feature Similarity:** Enrich `dim_songs` with audio features (e.g., tempo, danceability). Recommend songs with a similar "vibe" by calculating vector similarity.

---

## Phase 3: Analytics & Platform Maturity

Improve the operational and analytical capabilities of the platform.

### 3.1. Analytics and Visualization
-   **Complexity:** Medium
-   **Description:** Provide tools for ad-hoc analysis and monitoring of platform metrics.
-   **Implementation Steps:**
    -   [ ] **Add Jupyter Notebook Service:** Integrate a Jupyter/Spark-magic container into `docker-compose.yml` for interactive data exploration of the data lake.
    -   [ ] **Build an Analytical Dashboard:** Create a Grafana dashboard that queries the Silver tables (via a Spark Thrift Server or Trino) to visualize key metrics like "Top 10 Artists of the Month", "Genre Popularity Over Time", etc.

### 3.2. Operational Improvements
-   **Complexity:** High
-   **Description:** Add enterprise-grade features to ensure data quality and pipeline reliability.
-   **Implementation Steps:**
    -   [ ] **Schema Management:** Integrate a Schema Registry (like Confluent's) to enforce schemas for Kafka topics, preventing data corruption at the source.
    -   [ ] **Data Quality Checks:** Use a framework like Great Expectations within Airflow DAGs to run validation tests as data moves from Bronze to Silver layers (e.g., "user_id must not be null").