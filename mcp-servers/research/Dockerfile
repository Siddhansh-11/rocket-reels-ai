FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY . .

# MCP server standard port
EXPOSE 8080

# Run the server
CMD ["python", "server.py"]