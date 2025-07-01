FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app

# Create directories for credentials and outputs
RUN mkdir -p /app/credentials

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create entrypoint script
RUN echo '#!/bin/bash\n\
if [ ! -f "/app/credentials/token.json" ] && [ -f "/app/credentials/credentials.json" ]; then\n\
    echo "Google Drive authentication required. Follow the instructions below:"\n\
fi\n\
exec python /app/scripts/run_workflow.py "$@"' > /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]