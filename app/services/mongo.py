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
                "tlsCAFile": settings.mongodb_ssl_ca_file,
                "tlsCertificateKeyFile": settings.mongodb_ssl_client_file,
                "serverSelectionTimeoutMS": 10000,
                "connectTimeoutMS": 10000
            }
            
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
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def get_collection(self, collection_name: str):
        """Get a collection from the main database (AMY)"""
        if self.main_db is None:
            raise Exception("Main database not connected")
        return self.main_db[collection_name]
    
    def get_fhir_collection(self, collection_name: str):
        """Get a collection from the FHIR database (MFC_FHIR_R5)"""
        if self.fhir_db is None:
            raise Exception("FHIR database not connected")
        return self.fhir_db[collection_name]
    
    def get_database(self, db_type: str = "main"):
        """Get database instance by type"""
        if db_type == "fhir":
            if self.fhir_db is None:
                raise Exception("FHIR database not connected")
            return self.fhir_db
        else:
            if self.main_db is None:
                raise Exception("Main database not connected")
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