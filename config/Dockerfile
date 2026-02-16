# Dockerfile for CubeSat Raspberry Pi Component
# FIX: Updated to Python 3.11 for security patches
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        git \
        curl \
        gnupg \
        build-essential \
        libatlas-base-dev \
        libhdf5-serial-dev \
        libjasper-dev \
        libqtgui4 \
        libqt4-test \
        pkg-config \
        zip \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY raspberry-pi-code/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install OpenCV with optimizations for Raspberry Pi
RUN pip install opencv-python-headless

# Copy project files
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/images /app/telemetry /app/updates /app/backups /app/certs

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose necessary ports
EXPOSE 5000

# Run the flight controller
CMD ["python", "raspberry-pi-code/flight_controller.py"]