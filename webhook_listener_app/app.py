# webhook_listener_app/app.py
# This is a simple Flask application that acts as a webhook listener for MinIO events.
# When MinIO is configured to send notifications (e.g., on object creation),
# it will send an HTTP POST request to this application.
# This demonstrates how event-driven architectures can be built using MinIO events.

from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

# IMPORTANT NOTE: For the `webhook_listener` service to pass its healthcheck
# (as defined in `docker-compose.yml`), it needs a `/health` endpoint.
@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for the Flask application.
    """
    return jsonify({"status": "healthy", "message": "MinIO Webhook Listener is running!"}), 200

@app.route('/minio-event', methods=['POST'])
def minio_event():
    """
    Receives MinIO event notifications via a POST request.
    Prints the received event payload to the console.
    """
    try:
        event = request.json # Get the JSON payload from the request body
        if event:
            print("\n" + "="*30)
            print("Received MinIO Event:")
            # Pretty print the JSON event for better readability in logs
            print(json.dumps(event, indent=2))
            print("="*30 + "\n")

            # You can add logic here to process the event, e.g.:
            # - Trigger another data pipeline (e.g., an Airflow DAG via API)
            # - Update a metadata catalog
            # - Start a serverless function (Lambda/Cloud Function)
            # - Log details to a central logging system
            
            # Example: Extracting bucket and object key
            if 'Records' in event and len(event['Records']) > 0:
                record = event['Records'][0]
                event_name = record.get('eventName', 'N/A')
                bucket_name = record['s3']['bucket']['name']
                object_key = record['s3']['object']['key']
                etag = record['s3']['object']['eTag']
                size = record['s3']['object']['size']
                print(f"Event Name: {event_name}")
                print(f"Bucket: {bucket_name}")
                print(f"Object Key: {object_key}")
                print(f"ETag: {etag}")
                print(f"Size: {size} bytes")
                
                # Further conditional logic based on event type or object key
                if object_key.endswith('.parquet'):
                    print(f"Recognized a new Parquet file: {object_key}. Could trigger Spark job.")
            
            return jsonify({"status": "success", "message": "MinIO Event received and processed"}), 200
        else:
            print("Received empty or non-JSON MinIO Event.")
            return jsonify({"status": "error", "message": "Invalid event format"}), 400
    except Exception as e:
        print(f"An error occurred while processing MinIO event: {e}")
        return jsonify({"status": "error", "message": f"Internal server error: {e}"}), 500

if __name__ == '__main__':
    # Flask app will listen on all interfaces (0.0.0.0) on port 8081
    # as configured in the conceptual docker-compose.yml snippet.
    print("MinIO Webhook Listener starting...")
    app.run(host='0.0.0.0', port=8081, debug=True)

