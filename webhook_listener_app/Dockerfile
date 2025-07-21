# webhook_listener_app/Dockerfile
# This Dockerfile builds an image for the simple Flask-based MinIO webhook listener.

# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask application code into the container
COPY app.py .

# Expose the port that the Flask app will listen on
EXPOSE 8081

# Command to run the Flask application using Gunicorn for production or Flask's dev server for simple demo
# For this simple demo, we'll use Flask's built-in development server (debug=True in app.py)
CMD ["python", "app.py"]

