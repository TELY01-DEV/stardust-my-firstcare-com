#!/usr/bin/env python3
"""
AVA4 Offline Monitor Script

This script runs periodically to check AVA4 device status and mark devices as offline
if no heartbeat is received within 1 minute.
"""

import pymongo
import ssl
from datetime import datetime, timedelta, timezone
import time
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB Configuration
MONGODB_URI = os.getenv('MONGODB_URI', "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true")
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', "AMY")

def connect_to_mongodb():
    """Connect to MongoDB with SSL"""
    try:
        client = pymongo.MongoClient(
            MONGODB_URI,
            tls=True,
            tlsCAFile='ssl/ca-latest.pem',
            tlsCertificateKeyFile='ssl/client-combined-latest.pem',
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info("✅ Successfully connected to MongoDB")
        return client
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        return None

def check_ava4_offline_status(client):
    """Check AVA4 devices for offline status"""
    try:
        db = client[MONGODB_DATABASE]
        ava4_status_collection = db.ava4_status
        
        # Calculate cutoff time (1 minute ago for AVA4 devices)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        
        logger.info(f"🔍 Checking AVA4 offline status (cutoff: {cutoff_time})")
        
        # Find all AVA4 devices
        ava4_devices = list(ava4_status_collection.find({}))
        
        online_count = 0
        offline_count = 0
        updated_count = 0
        
        for device in ava4_devices:
            ava4_mac = device.get('ava4_mac')
            last_heartbeat = device.get('last_heartbeat')
            current_status = device.get('status', 'Unknown')
            
            # Convert string timestamp to datetime if needed
            if isinstance(last_heartbeat, str):
                try:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                except:
                    last_heartbeat = datetime.now(timezone.utc)
            elif last_heartbeat and not last_heartbeat.tzinfo:
                # Make timezone-naive datetime timezone-aware
                last_heartbeat = last_heartbeat.replace(tzinfo=timezone.utc)
            
            if last_heartbeat and last_heartbeat >= cutoff_time:
                # Device is online
                if current_status != 'Online':
                    # Update status to Online
                    result = ava4_status_collection.update_one(
                        {'ava4_mac': ava4_mac},
                        {
                            '$set': {
                                'status': 'Online',
                                'updated_at': datetime.now(timezone.utc)
                            }
                        }
                    )
                    if result.modified_count > 0:
                        updated_count += 1
                        logger.info(f"✅ Updated {ava4_mac} status to Online")
                
                online_count += 1
            else:
                # Device is offline
                if current_status != 'Offline':
                    # Update status to Offline
                    result = ava4_status_collection.update_one(
                        {'ava4_mac': ava4_mac},
                        {
                            '$set': {
                                'status': 'Offline',
                                'offline_since': last_heartbeat if last_heartbeat else datetime.now(timezone.utc),
                                'updated_at': datetime.now(timezone.utc)
                            }
                        }
                    )
                    if result.modified_count > 0:
                        updated_count += 1
                        logger.warning(f"❌ Updated {ava4_mac} status to Offline (last heartbeat: {last_heartbeat})")
                
                offline_count += 1
        
        logger.info(f"📊 AVA4 Status Summary:")
        logger.info(f"   Total devices: {len(ava4_devices)}")
        logger.info(f"   Online devices: {online_count}")
        logger.info(f"   Offline devices: {offline_count}")
        logger.info(f"   Status updates: {updated_count}")
        
        return {
            'total': len(ava4_devices),
            'online': online_count,
            'offline': offline_count,
            'updated': updated_count
        }
        
    except Exception as e:
        logger.error(f"❌ Error checking AVA4 offline status: {e}")
        return None

def main():
    """Main monitoring loop"""
    logger.info("🚀 Starting AVA4 Offline Monitor")
    
    client = connect_to_mongodb()
    if not client:
        logger.error("❌ Failed to connect to MongoDB. Exiting.")
        return
    
    try:
        while True:
            try:
                # Check AVA4 offline status
                result = check_ava4_offline_status(client)
                
                if result:
                    logger.info(f"✅ AVA4 status check completed: {result['online']} online, {result['offline']} offline")
                else:
                    logger.error("❌ AVA4 status check failed")
                
                # Wait 30 seconds before next check
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("🛑 AVA4 Offline Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                time.sleep(30)  # Wait before retrying
                
    finally:
        client.close()
        logger.info("🔌 MongoDB connection closed")

if __name__ == "__main__":
    main() 