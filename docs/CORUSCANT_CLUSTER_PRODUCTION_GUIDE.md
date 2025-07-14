# 🏭 Coruscant MongoDB Cluster - Production Server Configuration

## 🚨 **PRODUCTION ENVIRONMENT SETUP**

Since you're working on a production server, here are the specific configurations and security considerations:

---

### **Credentials:**
- **Username**: `opera_admin`
- **Password**: `Sim!443355`
- **Auth Database**: `admin`

---

## 🌐 **Production Connection Strings**

### **For External Applications:**
```
mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin
```

### **For MongoDB Compass (Production) - WORKING CONFIG:**
```
mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true&tls=true&tlsCAFile=ssl/ca-latest.pem&tlsCertificateKeyFile=ssl/client-combined-latest.pem
```

## 🔒 **Production Security Requirements**

### **SSL Certificates (MANDATORY):**
```
📁 Certificate Locations (Local & Production):
/ssl/
├── client-combined-latest.pem       (Client Certificate + Private Key - Latest)
└── client-combined.pem             (Client Certificate + Private Key - Backup)
```

### **Network Security:**
- ✅ Port 27023 is open for external connections
- ✅ SSL/TLS encryption enforced
- ✅ Client certificate authentication required
- ✅ Self-signed certificates (allow invalid certificates)

---

## 🏗️ **Production Environment Variables**

### **For Applications (.env file):**
```bash
# MongoDB Production Configuration
MONGODB_URI=mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin
MONGODB_HOST=coruscant.my-firstcare.com
MONGODB_PORT=27023
MONGODB_USERNAME=opera_admin
MONGODB_PASSWORD=Sim!443355
MONGODB_AUTH_DB=admin
MONGODB_SSL=true
MONGODB_SSL_CA_FILE=/ssl/ca.pem
MONGODB_SSL_CLIENT_FILE=/ssl/client-combined.pem

# Production Settings
NODE_ENV=production
SSL_VALIDATE=false
```

---

## 🐍 **Production Python Configuration**

### **Production PyMongo Setup:**
```python
import os
from pymongo import MongoClient
import ssl

# Production configuration
MONGODB_CONFIG = {
    "host": os.getenv("MONGODB_HOST", "coruscant.my-firstcare.com"),
    "port": int(os.getenv("MONGODB_PORT", 27023)),
    "username": os.getenv("MONGODB_USERNAME", "opera_admin"),
    "password": os.getenv("MONGODB_PASSWORD", "Sim!443355"),
    "authSource": os.getenv("MONGODB_AUTH_DB", "admin"),
    "tls": True,
    "tlsAllowInvalidCertificates": True,
    "tlsAllowInvalidHostnames": True,
    "tlsCAFile": "ssl/ca-latest.pem",
    "tlsCertificateKeyFile": "ssl/client-combined-latest.pem",
    "serverSelectionTimeoutMS": 10000,
    "connectTimeoutMS": 10000
}

def get_production_client():
    """Get MongoDB client for production environment"""
    try:
        client = MongoClient(**MONGODB_CONFIG)
        # Test connection
        client.admin.command('ping')
        print("✅ Connected to production MongoDB cluster")
        return client
    except Exception as e:
        print(f"❌ Production connection failed: {e}")
        raise

# Usage
client = get_production_client()
```

---

## ⚛️ **Production Node.js/React Configuration**

### **Production Node.js Setup:**
```javascript
const { MongoClient } = require('mongodb');
const fs = require('fs');
const path = require('path');

// Production configuration
const PRODUCTION_CONFIG = {
  uri: process.env.MONGODB_URI || "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin",
  options: {
    useUnifiedTopology: true,
    ssl: true,
    sslValidate: false,
    sslCA: fs.readFileSync(path.join(__dirname, 'ssl/ca.pem')),
    sslCert: fs.readFileSync(path.join(__dirname, 'ssl/client-combined.pem')),
    sslKey: fs.readFileSync(path.join(__dirname, 'ssl/client-combined.pem')),
    authSource: 'admin',
    serverSelectionTimeoutMS: 10000,
    connectTimeoutMS: 10000
  }
};

async function getProductionClient() {
  try {
    const client = new MongoClient(PRODUCTION_CONFIG.uri, PRODUCTION_CONFIG.options);
    await client.connect();
    console.log("✅ Connected to production MongoDB cluster");
    return client;
  } catch (error) {
    console.error("❌ Production connection failed:", error);
    throw error;
  }
}

module.exports = { getProductionClient };
```