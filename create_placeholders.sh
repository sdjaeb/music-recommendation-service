#!/bin/bash

# This script creates the missing placeholder directories and configuration
# files required by the docker-compose.yml in the harmanpoc project.

PROJECT_ROOT="/Users/sdjaeb/dev/harmanpoc"

echo "Creating placeholder directories for dependent services..."
mkdir -p "$PROJECT_ROOT/airflow_dags"
mkdir -p "$PROJECT_ROOT/fastapi_app"
mkdir -p "$PROJECT_ROOT/grafana_provisioning/datasources"
mkdir -p "$PROJECT_ROOT/grafana_provisioning/dashboards"
mkdir -p "$PROJECT_ROOT/observability/dashboards"
mkdir -p "$PROJECT_ROOT/pyspark_jobs"
mkdir -p "$PROJECT_ROOT/webhook_listener_app"
mkdir -p "$PROJECT_ROOT/postgres-init"
mkdir -p "$PROJECT_ROOT/plugins"
mkdir -p "$PROJECT_ROOT/logs"

echo "Creating minimal placeholder files..."

# --- Placeholders for Python apps to provide a valid build context ---
touch "$PROJECT_ROOT/fastapi_app/Dockerfile"
touch "$PROJECT_ROOT/webhook_listener_app/Dockerfile"

# --- Minimal Loki Config ---
cat <<'EOF' > "$PROJECT_ROOT/observability/loki-config.yml"
auth_enabled: false
server:
  http_listen_port: 3100
ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 5m
  chunk_retain_period: 30s
schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h
storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    cache_ttl: 24h
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks
EOF

# --- Minimal Promtail Config ---
cat <<'EOF' > "$PROJECT_ROOT/observability/promtail-config.yml"
server:
  http_listen_port: 9080
  grpc_listen_port: 0
positions:
  filename: /tmp/positions.yaml
clients:
  - url: http://loki:3100/loki/api/v1/push
scrape_configs:
- job_name: containers
  static_configs:
  - targets:
      - localhost
    labels:
      job: containerlogs
  pipeline_stages:
  - docker: {}
  - labels:
      stream:
      container:
EOF

# --- Minimal Grafana Alloy Config ---
cat <<'EOF' > "$PROJECT_ROOT/config/grafana-alloy.river"
logging {
  level  = "info"
  format = "logfmt"
}
EOF

# --- Minimal Grafana Datasource Provisioning ---
cat <<'EOF' > "$PROJECT_ROOT/grafana_provisioning/datasources/datasources.yml"
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9091
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
EOF

echo "--------------------------------------------------"
echo "Setup complete!"
echo "Please ensure your 'secrets' directory is populated as previously discussed."
echo "You can now run 'docker-compose up --build' to start the platform."
echo "--------------------------------------------------"