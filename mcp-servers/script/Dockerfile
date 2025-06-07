FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for NLTK
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt')"

# Copy server code
COPY . .

# MCP server standard port
EXPOSE 8080

# Run the server
CMD ["python", "server.py"]