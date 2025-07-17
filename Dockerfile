# Use Python 3.11 slim image for better performance
FROM python:3.11-slim

# Build timestamp to invalidate cache
ARG BUILD_DATE
ENV BUILD_DATE=${BUILD_DATE}
LABEL build_date=${BUILD_DATE}

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p temp downloads transcriptions

# Set permissions
RUN chmod +x /app
RUN chmod +x /app/check_env.py

# Create startup script
RUN echo '#!/bin/bash\npython /app/check_env.py\nexec "$@"' > /app/start.sh && chmod +x /app/start.sh

# Expose port
EXPOSE 8000

# Improved health check with more detailed output
HEALTHCHECK --interval=15s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8000/health || (echo "Health check failed" && exit 1)

# Run the application with environment check and more verbose logging
CMD ["/app/start.sh", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"] 