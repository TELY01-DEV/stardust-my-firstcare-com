import ssl
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from config import settings
from config import logger

class MongoDBService:
    def __init__(self):
        self.client = None
        self.main_db = None  # AMY database for legacy data
        self.fhir_db = None  # MFC_FHIR_R5 database for FHIR resources
        
    async def connect(self):
        """Connect to MongoDB with production SSL configuration"""
        try:
            # Check if SSL certificate files exist
            import os
            ssl_ca_exists = os.path.exists(settings.mongodb_ssl_ca_file)
            ssl_client_exists = os.path.exists(settings.mongodb_ssl_client_file)
            
            # Production MongoDB configuration
            mongodb_config = {
                "host": settings.mongodb_host,
                "port": settings.mongodb_port,
                "username": settings.mongodb_username,
                "password": settings.mongodb_password,
                "authSource": settings.mongodb_auth_db,
                "tls": settings.mongodb_ssl,
                "tlsAllowInvalidCertificates": True,
                "tlsAllowInvalidHostnames": True,
                "serverSelectionTimeoutMS": 10000,
                "connectTimeoutMS": 10000
            }
            
            # Only add SSL certificate files if they exist
            if ssl_ca_exists:
                mongodb_config["tlsCAFile"] = settings.mongodb_ssl_ca_file
                logger.info(f"✅ Using SSL CA file: {settings.mongodb_ssl_ca_file}")
            else:
                logger.warning(f"⚠️ SSL CA file not found: {settings.mongodb_ssl_ca_file}, proceeding without it")
                
            if ssl_client_exists:
                mongodb_config["tlsCertificateKeyFile"] = settings.mongodb_ssl_client_file
                logger.info(f"✅ Using SSL client file: {settings.mongodb_ssl_client_file}")
            else:
                logger.warning(f"⚠️ SSL client file not found: {settings.mongodb_ssl_client_file}, proceeding without it")
            
            # Create async client
            self.client = AsyncIOMotorClient(**mongodb_config)
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("✅ Connected to production MongoDB cluster")
            
            # Set databases
            self.main_db = self.client[settings.mongodb_main_db]  # AMY database
            self.fhir_db = self.client[settings.mongodb_fhir_db]  # MFC_FHIR_R5 database
            
            logger.info(f"📊 Main database: {settings.mongodb_main_db}")
            logger.info(f"🏥 FHIR database: {settings.mongodb_fhir_db}")
            
        except Exception as e:
            logger.error(f"❌ Production MongoDB connection failed: {e}")
            logger.warning(f"⚠️ Application will continue without MongoDB connection")
            logger.warning(f"⚠️ Database-dependent endpoints may not work properly")
            # Don't raise the exception - let the application start without MongoDB
            self.client = None
            self.main_db = None
            self.fhir_db = None
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def get_collection(self, collection_name: str):
        """Get a collection from the main database (AMY)"""
        if self.main_db is None:
            logger.warning(f"⚠️ MongoDB not connected, cannot access collection: {collection_name}")
            raise Exception("MongoDB not connected - check connection configuration")
        return self.main_db[collection_name]
    
    def get_fhir_collection(self, collection_name: str):
        """Get a collection from the FHIR database (MFC_FHIR_R5)"""
        if self.fhir_db is None:
            logger.warning(f"⚠️ MongoDB not connected, cannot access FHIR collection: {collection_name}")
            raise Exception("FHIR database not connected - check connection configuration")
        return self.fhir_db[collection_name]
    
    def get_database(self, db_type: str = "main"):
        """Get database instance by type"""
        if db_type == "fhir":
            if self.fhir_db is None:
                logger.warning(f"⚠️ FHIR database not connected")
                raise Exception("FHIR database not connected - check connection configuration")
            return self.fhir_db
        else:
            if self.main_db is None:
                logger.warning(f"⚠️ Main database not connected")
                raise Exception("Main database not connected - check connection configuration")
            return self.main_db
    
    async def health_check(self):
        """Health check for MongoDB connection"""
        try:
            if self.client:
                await self.client.admin.command('ping')
                return True
            return False
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False

# Global MongoDB service instance
mongodb_service = MongoDBService() 