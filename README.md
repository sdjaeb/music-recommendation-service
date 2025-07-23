# End-to-End Music Recommendation Data Pipeline

This project is a comprehensive Proof-of-Concept (POC) demonstrating a modern, end-to-end data pipeline. It features a C#/.NET 8 Minimal API as an event source, integrated into a full data engineering ecosystem including Kafka, Spark, Delta Lake, and a complete observability stack.

The primary goal is to showcase proficiency in a wide range of technologies and best practices, including:
-   **Backend Development:** Clean, testable C#/.NET Minimal APIs.
-   **Containerization:** Multi-service application management with Docker and Docker Compose.
-   **Data Engineering:** Batch and real-time event streaming, processing, and storage in a data lake.
-   **Observability:** The "three pillars" of metrics, logs, and traces.

## Core Components & Features

*   **Music Recommendation Service:** A .NET 8 Minimal API that serves static recommendations and produces an event to Kafka for each request.
*   **Real-time Streaming:** Apache Kafka serves as the central, durable message bus for all events.
*   **Stream Processing:** An Apache Spark streaming job consumes events from Kafka in real-time, parses them, and writes them to a Delta Lake table.
*   **Data Lake / Lakehouse:** MinIO provides S3-compatible object storage, with Delta Lake adding transactional reliability and ACID properties to the raw data.
*   **Orchestration:** Apache Airflow is included for scheduling, monitoring, and managing complex data workflows (e.g., running batch jobs).
*   **Observability Stack:**
    *   **Prometheus:** Collects and stores time-series metrics from all services.
    *   **Grafana:** For visualizing metrics from Prometheus and logs from Loki in powerful dashboards.
    *   **Loki:** Aggregates logs from all containers.

## Tech Stack

| Category          | Technology                                       |
| ----------------- | ------------------------------------------------ |
| **Backend**       | C# / .NET 8 (Minimal API)                        |
| **Streaming**     | Apache Kafka, Zookeeper                          |
| **Processing**    | Apache Spark 3.5                                 |
| **Storage**       | MinIO (S3-compatible), Delta Lake, PostgreSQL    |
| **Orchestration** | Apache Airflow                                   |
| **Observability** | Prometheus, Grafana, Loki, cAdvisor              |
| **Container**     | Docker, Docker Compose                           |
| **CI/CD**         | GitHub Actions                                   |

## Getting Started

### Prerequisites

*   Docker Desktop
*   Python 3.9+
*   .NET 8 SDK (for local development/testing)

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/sdjaeb/music-recommendation-service.git
    cd music-recommendation-service
    ```
 
2.  **Create Secrets:**
    The platform requires several secret files for database passwords and connection details. The following commands will create the `secrets` directory and populate it with the necessary files and default values.
    ```bash
    mkdir secrets
    
    # MinIO Credentials
    echo "minioadmin" > secrets/minio_user.txt
    echo "minioadmin" > secrets/minio_pass.txt

    # PostgreSQL Credentials for Airflow
    echo "airflow" > secrets/postgres_user.txt
    echo "airflow" > secrets/postgres_pass.txt

    # Redis Password for Airflow
    echo "redispass" > secrets/redis_pass.txt

    # Airflow Secrets
    echo "postgresql+psycopg2://airflow:airflow@postgres/airflow" > secrets/airflow_db_url.txt
    echo "redis://:redispass@redis:6379/0" > secrets/redis_url.txt
    python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' > secrets/airflow_fernet.txt
    ```

3.  **Set User ID and Run the Platform:**
    To avoid file permission issues between your host machine and the Airflow containers, set the `AIRFLOW_UID` environment variable to your current user ID.
    ```bash
    export AIRFLOW_UID=$(id -u)
    ```

    Use Docker Compose to build and start all services.
    ```bash
    docker-compose up --build -d
    ```

4.  **Set up the Python Environment:**
    This project uses `uv` for Python environment and package management.

    First, create and activate the virtual environment:
    ```bash
    # Create the virtual environment in ./.venv
    uv venv

    # Activate the environment for your current shell session
    source .venv/bin/activate
    ```
    Your shell prompt should now be prefixed with `(harmanpoc)`.

    Next, install the required Python packages:
    ```bash
    uv pip install tqdm
    ```

5.  **Generate Historical Data:**
    Now that your environment is active, run the data generation script. This may take a minute or two to complete.
    ```bash
    python generate_seed_data.py
    ```
    This will create a `generated_data/` directory containing dimension tables (`dim_*.csv`), relationship tables (`graph_*.csv`, `bridge_*.csv`), and the main fact table (`fact_listening_events_2024.csv`).

6.  **Generate Weekly Incremental Data (Optional):**
    To simulate ongoing data ingestion, you can generate weekly trend files for the year 2025. Each time you run the script, it will generate a new CSV containing one week of listening events.

    The script uses a state file (`data_generation_state.json`) to track its progress.

    ```bash
    python generate_weekly_trends.py
    ```

    To reset the process and delete all generated weekly data and the state file, use the `--truncate` flag:

    ```bash
    python generate_weekly_trends.py --truncate
    ```

    This will create a new file inside the `generated_data/weekly_trends/` directory, named like `trends_2025-01-07.csv`.

## How to Use the Pipeline (Initial Data Load)

Now that the historical data has been generated, you can use the provided Airflow DAG to ingest it into the data lake.

1.  **Create Airflow Connections:**
    *   Navigate to the Airflow UI at **http://localhost:8080**.
    *   Go to **Admin -> Connections**.
    *   Create a new connection for **MinIO**:
        *   Conn Id: `minio_default`
        *   Conn Type: `AWS`
        *   **AWS Access Key ID**: `minioadmin`
        *   **AWS Secret Access Key**: `minioadmin`
        *   In "Extra", enter: `{"endpoint_url": "http://minio:9000"}`
    *   Create a new connection for **Spark**:
        *   Conn Id: `spark_default`
        *   Conn Type: `Spark`
        *   Host: `spark://spark-master`
        *   Port: `7077`

2.  **Trigger the DAG:**
    *   On the main DAGs page, find the `initial_data_load` DAG and toggle it on.
    *   Click the "Play" button on the right side of the `initial_data_load` DAG row and select "Trigger DAG".

3.  **Monitor and Verify:**
    *   Click on the DAG name to watch the tasks execute.
    *   Once the run is successful, navigate to the MinIO UI at **http://localhost:9001**. You will see a `landing` bucket with the raw CSVs and a `data` bucket containing the new `bronze` Delta tables.

## How to Use the Pipeline (Weekly Incremental Load)

The weekly ingestion pipeline is designed to be automated. It runs daily, looking for new files to process.

1.  **Generate a Weekly Data File:**
    Run the script to generate a new CSV for the next week.
    ```bash
    python generate_weekly_trends.py
    ```
    This will create a new file like `trends_2025-01-07.csv` in `generated_data/weekly_trends/`.

2.  **Trigger the DAG:**
    *   On the main DAGs page in the Airflow UI, find the `weekly_trends_ingestion` DAG and toggle it on.
    *   The DAG is scheduled to run daily, but you can trigger it manually by clicking the "Play" button.
    *   The DAG will find the new file, upload it to MinIO, and run the Spark job. It uses an Airflow Variable to keep track of processed files so it won't re-process them on subsequent runs.

3.  **Resetting Processed Files (for development):**
    If you need to re-run the weekly ingestion for files that have already been processed, you can clear the state in Airflow:
    *   Go to **Admin -> Variables**.
    *   Delete the Variable with the key `processed_weekly_trends_files`.
    *   The next time the DAG runs, it will re-process all available weekly files.
