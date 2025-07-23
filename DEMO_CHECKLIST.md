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

-   [ ] **Step 2: Configure Airflow Connections.**
    -   **Action:** Perform the one-time setup to tell Airflow how to connect to Spark and MinIO.
    -   **Instructions:** In the Airflow UI, navigate to **Admin -> Connections** and create:
        1.  **`minio_default`**:
            -   **Conn Id:** `minio_default`
            -   **Conn Type:** `AWS`
            -   **AWS Access Key ID:** `minioadmin`
            -   **AWS Secret Access Key:** `minioadmin`
            -   **Extra:** `{"endpoint_url": "http://minio:9000"}`
        2.  **`spark_default`**: Type `Spark`, with Host: `spark://spark-master` and Port: `7077`.

-   [ ] **Step 3: Run the Ingestion DAG.**
    -   **Action:** Trigger the `initial_data_load` DAG. This pipeline will upload the raw files and then process them with Spark.
    -   **Instructions:** In the Airflow UI, unpause and trigger the `initial_data_load` DAG. The first task will automatically create the `landing` and `data` buckets in MinIO if they don't exist.

-   [ ] **Step 4: Verify the Results.**
    -   **Action:** Check that the data has landed and been processed correctly.
    -   **Verification Points:**
        -   **Airflow:** "The DAG run should show all green, indicating success."
        -   **MinIO Landing Zone:** "In the `landing` bucket, we can see the raw CSVs under the `historical_data/` prefix."
        -   **MinIO Bronze Layer:** "And most importantly, in the `data` bucket, we now have a `bronze/` directory containing our new Delta tables, like `dim_songs` and the partitioned `fact_listening_events`."

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

## Part 4: Next Steps (Roadmap Preview)

-   [ ] **Phase 2: Silver Layer & Hybrid Recommendations.** "Our next step is to build on this bronze data. We'll create cleaned, aggregated 'Silver' tables for things like weekly trending tracks and song similarity. These tables will directly feed a much more sophisticated recommendation model in our .NET service."
-   [ ] **Phase 3: Analytics & Maturity.** "Finally, we'll add a Jupyter notebook for ad-hoc data science and build out analytical dashboards in Grafana to monitor business KPIs, not just system health."