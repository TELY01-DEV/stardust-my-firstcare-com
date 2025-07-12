FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY web-panel/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared /app/shared

# Copy application code
COPY web-panel/app.py .
COPY web-panel/templates/ templates/
COPY web-panel/static/ static/

# Make the script executable
RUN chmod +x app.py

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"] 