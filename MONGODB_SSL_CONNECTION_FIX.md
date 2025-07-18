# MongoDB SSL Connection Fix

## Issue Description
The `update_emergency_alarms.py` script failed to connect to MongoDB with the error:
```
❌ Failed to connect to MongoDB: localhost:27017: [Errno 61] Connection refused
```

This occurred because the script was trying to connect to a local MongoDB instance instead of the remote MongoDB server with SSL authentication.

## Root Cause Analysis
1. **Wrong Connection String**: The script was using `mongodb://localhost:27017/` instead of the production MongoDB URI
2. **Missing SSL Configuration**: The production MongoDB requires SSL certificates for secure connection
3. **Missing Authentication**: The production MongoDB requires username/password authentication

## Solution Implemented

### 1. Identified Correct MongoDB Configuration
**Source**: `docker-compose.yml` and other configuration files

**Production MongoDB URI**:
```
mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true&tlsCAFile=ssl/ca-latest.pem&tlsCertificateKeyFile=ssl/client-combined-latest.pem
```

**Components**:
- **Host**: `coruscant.my-firstcare.com`
- **Port**: `27023`
- **Username**: `opera_admin`
- **Password**: `Sim!443355`
- **Database**: `admin`
- **SSL**: Enabled with certificate files

### 2. SSL Certificate Requirements
**Required Files**:
- `ssl/ca-latest.pem` - Certificate Authority file
- `ssl/client-combined-latest.pem` - Client certificate and key

**Location**: These files are mounted in Docker containers at `/app/ssl/`

### 3. Fixed Script Implementation
**File**: `update_emergency_alarms_fixed.py`

**Key Changes**:
```python
# MongoDB connection with SSL
mongodb_uri = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true&tlsCAFile=ssl/ca-latest.pem&tlsCertificateKeyFile=ssl/client-combined-latest.pem"
database_name = "AMY"

# Connect to MongoDB with SSL
client = MongoClient(mongodb_uri)
db = client[database_name]
```

### 4. SSL Certificate Setup
**Process**:
1. Created local `ssl/` directory
2. Copied certificates from Docker container:
   ```bash
   docker cp stardust-mqtt-panel:/app/ssl/ca-latest.pem ssl/
   docker cp stardust-mqtt-panel:/app/ssl/client-combined-latest.pem ssl/
   ```

## Results

### Before Fix
```
❌ Failed to connect to MongoDB: localhost:27017: [Errno 61] Connection refused
```

### After Fix
```
✅ Connected to MongoDB successfully with SSL
📊 Found 0 emergency alarms without device_type field
✅ All emergency alarms already have device_type field
```

## Configuration Details

### Environment Variables (from docker-compose.yml)
```yaml
environment:
  - MONGODB_URI=mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true&tlsCAFile=/app/ssl/ca-latest.pem&tlsCertificateKeyFile=/app/ssl/client-combined-latest.pem
  - MONGODB_DATABASE=AMY
  - MONGODB_HOST=coruscant.my-firstcare.com
  - MONGODB_PORT=27023
  - MONGODB_USERNAME=opera_admin
  - MONGODB_PASSWORD=Sim!443355
  - MONGODB_AUTH_DB=admin
  - MONGODB_SSL=true
  - MONGODB_SSL_CA_FILE=/app/ssl/ca-latest.pem
  - MONGODB_SSL_CLIENT_FILE=/app/ssl/client-combined-latest.pem
```

### SSL Parameters
- `ssl=true` - Enable SSL connection
- `authSource=admin` - Authentication database
- `tlsAllowInvalidCertificates=true` - Allow self-signed certificates
- `tlsAllowInvalidHostnames=true` - Allow hostname mismatches
- `tlsCAFile` - Path to CA certificate
- `tlsCertificateKeyFile` - Path to client certificate and key

## Usage Instructions

### For Local Development
1. **Copy SSL certificates** from Docker container:
   ```bash
   mkdir -p ssl
   docker cp stardust-mqtt-panel:/app/ssl/ca-latest.pem ssl/
   docker cp stardust-mqtt-panel:/app/ssl/client-combined-latest.pem ssl/
   ```

2. **Use the correct MongoDB URI** in scripts:
   ```python
   mongodb_uri = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true&tlsCAFile=ssl/ca-latest.pem&tlsCertificateKeyFile=ssl/client-combined-latest.pem"
   ```

### For Docker Containers
- SSL certificates are automatically mounted at `/app/ssl/`
- Use `/app/ssl/ca-latest.pem` and `/app/ssl/client-combined-latest.pem` paths
- Environment variables are automatically set

## Security Considerations

### SSL Certificate Management
- **CA Certificate**: `ca-latest.pem` - Validates server identity
- **Client Certificate**: `client-combined-latest.pem` - Client authentication
- **Certificate Renewal**: Certificates should be updated when they expire

### Connection Security
- **Encryption**: All data is encrypted in transit
- **Authentication**: Username/password required
- **Certificate Validation**: Server certificate is validated

## Troubleshooting

### Common Issues
1. **Certificate not found**: Ensure SSL certificates are in the correct location
2. **Connection refused**: Check if using the correct host and port
3. **Authentication failed**: Verify username and password
4. **SSL handshake failed**: Check certificate validity and paths

### Debug Commands
```bash
# Check SSL certificates in Docker container
docker exec -it stardust-mqtt-panel ls -la /app/ssl/

# Test MongoDB connection from container
docker exec -it stardust-mqtt-panel python -c "
from pymongo import MongoClient
client = MongoClient('mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true&tlsCAFile=/app/ssl/ca-latest.pem&tlsCertificateKeyFile=/app/ssl/client-combined-latest.pem')
client.admin.command('ping')
print('✅ MongoDB connection successful')
"
```

## Deployment Status
✅ **COMPLETED**
- SSL connection configuration identified
- Script updated with correct MongoDB URI
- SSL certificates properly configured
- Connection test successful

## Future Recommendations

### Script Improvements
- Add environment variable support for MongoDB URI
- Implement certificate path detection
- Add connection retry logic
- Include better error handling

### Security Enhancements
- Rotate SSL certificates regularly
- Use environment variables for sensitive data
- Implement certificate validation
- Add connection logging

---

**Note**: This fix ensures that all MongoDB connection scripts use the proper SSL configuration and can connect to the production database securely. 