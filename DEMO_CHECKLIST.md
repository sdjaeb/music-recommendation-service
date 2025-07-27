# Demo Checklist: End-to-End Data Platform

This document provides a step-by-step checklist for demonstrating the core features of the music recommendation data platform. It's designed to be followed sequentially to showcase our progress and capabilities.

---

### Introduction

*"Alright team, welcome to the demo of our new data platform. The goal today is to walk through the core ingestion capabilities we've built, showing how we handle both a large historical data load and ongoing, incremental updates. We'll follow this checklist to keep us on track."*

---

## Part 1: Platform Spin-Up and Health Check

*"First things first, let's get the entire platform running and verify all the components are healthy."*

-   [ ] **Step 1: Start the Services.**
    -   **Action:** Run the single command to bring all services online.
    -   **Command:** `docker-compose up --build -d`

-   [ ] **Step 2: Verify Services are Healthy.**
    -   **Action:** Do a quick tour of the service UIs to confirm everything is online. This is our command center.
    -   **Verification Points:**
        -   **Airflow (Orchestration):** `http://localhost:8080` - "This is where we manage our data pipelines."
        -   **Spark Master (Processing):** `http://localhost:8081` - "This shows our Spark cluster is alive and has workers ready for jobs."
        -   **MinIO (Data Lake Storage):** `http://localhost:9001` - "This is our data lake. We'll log in with `minioadmin`/`minioadmin`."
        -   **Grafana (Observability):** `http://localhost:3000` - "Our dashboard for metrics and logs."
        -   **Spark Application UI (Live Jobs):** `http://localhost:4040` - "While a Spark job is running from Airflow, we can monitor its progress live here."
        -   **Spark History Server (Job Analysis):** `http://localhost:18080` - "For digging into the details of completed Spark jobs."

---

## Part 2: Phase 1.1 - Historical Data Ingestion (The "Big Bang" Load)

*"Our first scenario is ingesting a full year of historical data. This seeds our data lake with a rich, foundational dataset."*

-   [ ] **Step 1: Generate Historical Data.**
    -   **Action:** Run the script to generate the 2024 dataset.
    -   **Command (Sample):** `python generate_seed_data.py --sample`
    -   **Command (Full):** `python generate_seed_data.py`
    -   **Demo Note:** *"The full data generation is powerful but can take over an hour and create a very large file. For our demo today, we'll use the `--sample` flag, which creates a smaller 30-day dataset instantly. This is also the recommended approach for quick local development."*
    -   **Verification:** "We can see the `generated_data` directory is now populated with our 2024 dataset CSVs."

-   [ ] **Step 2: Run the Ingestion DAG.**
    -   **Action:** Trigger the `initial_data_load` DAG. This pipeline will upload the raw files and then process them with Spark.
    -   **Instructions:** In the Airflow UI, unpause and trigger the `initial_data_load` DAG. The necessary connections are created automatically. The first task will also create the `landing` and `data` buckets in MinIO if they don't exist.

-   [ ] **Step 3: Verify the Results.**
    -   **Action:** Check that the data has landed and been processed correctly.
    -   **Verification Points:**
        -   **Airflow:** "The DAG run should show all green, indicating success."
        -   **MinIO Landing Zone:** "In the `landing` bucket, we can see the raw CSVs under the `historical_data/` prefix."
        -   **MinIO Bronze Layer:** "And most importantly, in the `data` bucket, we now have a `bronze/` directory containing our new Delta tables. This is our 'Bronze' layer—the raw, validated source of truth for our data lake."

---

## Part 3: Phase 1.2 - Incremental Weekly Ingestion (The "Steady State")

*"The historical data is in. Now let's simulate a new week of data arriving for 2025 to show how we handle ongoing, incremental updates."*

-   [ ] **Step 1: Generate a New Weekly File.**
    -   **Action:** Run the script to generate the first week of 2025 data.
    -   **Command:** `python generate_weekly_trends.py`
    -   **Verification:** "A new file, `trends_2025-01-07.csv`, has appeared in `generated_data/weekly_trends/`."

-   [ ] **Step 2: Run the Weekly Ingestion DAG.**
    -   **Action:** Trigger the `weekly_trends_ingestion` DAG. For the demo, we'll trigger it manually, but this would normally run on a schedule.
    -   **Instructions:** In the Airflow UI, unpause and trigger the `weekly_trends_ingestion` DAG.

-   [ ] **Step 3: Verify the Results.**
    -   **Action:** Confirm the new data was appended correctly to our main fact table.
    -   **Verification Points:**
        -   **Airflow:** "The weekly DAG run is successful."
        -   **MinIO Landing Zone:** "The new `trends_...csv` file is now in the `landing/weekly_trends/` path."
        -   **MinIO Bronze Layer:** "The `fact_listening_events` Delta table has been updated. We can verify this by looking at the transaction log (`_delta_log`) which shows a new version, or by running a query to count records where `year=2025`."

---

## Part 4: Phase 2.1 - Silver Layer Processing (Analytics)

*"Now that we have our raw Bronze data, let's create our first analytical table. We'll run a pipeline that calculates the top trending tracks from the last 7 days and saves them to a new 'Silver' table."*

-   [ ] **Step 1a: Run the Weekly Trends DAG.**
    -   **Action:** Trigger the `silver_layer_processing` DAG.
    -   **Instructions:** In the Airflow UI, unpause and trigger the `silver_layer_processing` DAG. While it's running, we can monitor the live Spark job in the Spark Application UI at `http://localhost:4040`.

-   [ ] **Step 1b: Run the Song Similarity DAG.**
    -   **Action:** Trigger the `silver_song_similarity_processing` DAG.
    -   **Demo Note:** *"Next, we'll compute another critical analytical table for our recommendation engine. This job finds pairs of songs that are frequently added to the same playlists by users, which is a powerful signal for 'what to play next'."*
    -   **Instructions:** In the Airflow UI, unpause and trigger the `silver_song_similarity_processing` DAG.

-   [ ] **Step 2: Verify the Silver Layer Results.**
    -   **Action:** Confirm the new aggregated table has been created in the Silver layer.
    -   **Verification Points:**
        -   **Airflow:** "Both Silver Layer DAG runs, `silver_layer_processing` and `silver_song_similarity_processing`, are successful."
        -   **MinIO Silver Layer:** "In the `data` bucket, we now have a `silver/` directory. Inside, we can see both of our new analytical tables:"
            -   **`weekly_trending_tracks`:** "This table contains the aggregated weekly play counts."
            -   **`song_similarity_by_playlist`:** "And this one contains the co-occurrence scores for song pairs."
        -   **Demo Note:** *"These Silver tables are cleaned, aggregated, and ready for direct use by our analytics dashboards and the recommendation model. They represent a single source of truth for these specific business concepts."*

---

## Part 5: Next Steps (Roadmap Preview)

-   [ ] **Phase 2: Silver Layer & Hybrid Recommendations.** "Our next step is to build on this bronze data. We'll continue creating cleaned, aggregated 'Silver' tables—like song similarity—which are enriched and ready for business analysis. These tables will directly feed a much more sophisticated recommendation model in our .NET service."
-   [ ] **Phase 3: Analytics & Maturity.** "Finally, we'll add a Jupyter notebook for ad-hoc data science and build out analytical dashboards in Grafana to monitor business KPIs, not just system health."