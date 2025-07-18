FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/mqtt-monitor/web-panel/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY services/mqtt-monitor/shared /app/shared

# Copy application code
COPY services/mqtt-monitor/web-panel/app.py .
COPY services/mqtt-monitor/web-panel/templates/ templates/
COPY services/mqtt-monitor/web-panel/static/ static/

# Create SSL directory (for compatibility)
RUN mkdir -p /app/ssl

# Set MongoDB environment variables
ENV MONGODB_URI=mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin
ENV MONGODB_HOST=coruscant.my-firstcare.com
ENV MONGODB_PORT=27023
ENV MONGODB_USERNAME=opera_admin
ENV MONGODB_PASSWORD=Sim!443355
ENV MONGODB_AUTH_DB=admin
ENV MONGODB_DATABASE=AMY
ENV MONGODB_SSL_CA_FILE=/app/ssl/ca-latest.pem
ENV MONGODB_SSL_CLIENT_FILE=/app/ssl/client-combined-latest.pem
ENV MONGODB_SSL_CLIENT_CERT_FILE=/app/ssl/client-combined-latest.pem
ENV MONGODB_SSL_CLIENT_KEY_FILE=/app/ssl/client-combined-latest.pem
ENV MONGODB_SSL_CERT_REQS=CERT_REQUIRED
ENV MONGODB_SSL_CIPHERS=HIGH:!aNULL:!MD5

# Set Redis environment variables
ENV REDIS_URL=redis://redis:6374/1

# Set JWT environment variables
ENV JWT_AUTH_BASE_URL=http://localhost:5054
ENV JWT_SECRET_KEY=your-secret-key-here
ENV JWT_LOGIN_ENDPOINT=/auth/login
ENV JWT_ME_ENDPOINT=/auth/me

# Make the script executable
RUN chmod +x app.py

# Expose port
EXPOSE 8098

# Run the application
CMD ["python", "app.py"] 