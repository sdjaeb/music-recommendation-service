# Description: Dockerfile for FastAPI application.
# Source: Building Enterprise-Ready Data Platforms v2.4, Appendix A.4 (Conceptual).
#
# This Dockerfile remains largely consistent across Intermediate and Advanced tracks,
# with additional dependencies for OpenTelemetry in the Advanced track.
FROM python:3.10-slim-buster
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/main.py /app/app/main.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]