# Dockerfile for CubeSat Raspberry Pi Component
FROM python:3.9-slim

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
RUN mkdir -p /app/logs /app/data /app/images /app/telemetry /app/updates /app/backups

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose necessary ports (if any network services are added later)
EXPOSE 5000

# Run the flight controller
CMD ["python", "raspberry-pi-code/flight_controller.py"]