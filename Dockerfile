# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/backend

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY backend/phase1_intent_detection_routing/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code and knowledge base
# .dockerignore will handle excluding unnecessary files
COPY backend ./backend
COPY knowledge_base ./knowledge_base

# The application listens on a port provided by Render
EXPOSE 8020

# Command to run the application
CMD uvicorn phase1_intent_detection_routing.main:app --host 0.0.0.0 --port ${PORT:-8020}
