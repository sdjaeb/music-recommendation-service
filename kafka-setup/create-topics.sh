#!/bin/bash
# create-topics.sh

# This script waits for Kafka to be ready and then creates all the necessary topics
# for the data platform.

echo "Waiting for Kafka to be ready..."
# The `cub` command is part of the Confluent Docker images and is a utility
# to check for the availability of various Confluent Platform components.
# `kafka-ready` checks if the broker is ready to accept connections.
# Arguments: <broker_list> <num_brokers_to_wait_for> <timeout_in_seconds>
cub kafka-ready -b kafka:29092 1 60

# List of topics to be created
TOPICS=(
    "raw_financial_events"
    "raw_insurance_claims"
    "user_listening_history" # Topic for detailed user listening events
    "music_recommendations" # The new topic for harmanpoc
)

echo "Creating Kafka topics..."
for TOPIC in "${TOPICS[@]}"
do
  kafka-topics --create --if-not-exists \
    --topic "$TOPIC" \
    --bootstrap-server kafka:29092 \
    --partitions 1 \
    --replication-factor 1
  echo "Topic '$TOPIC' created."
done

echo "All Kafka topics created successfully."