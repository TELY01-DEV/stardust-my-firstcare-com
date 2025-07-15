#!/usr/bin/env python3
"""
Integration script to connect emergency dashboard with MQTT monitor system
"""

import sys
import os
import requests
import json
import logging
from datetime import datetime

# Add parent directory to path to import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmergencyDashboardIntegrator:
    def __init__(self, dashboard_url="http://localhost:5056"):
        self.dashboard_url = dashboard_url
        self.websocket_server_url = "http://localhost:5055"  # Default websocket server
        
    def test_dashboard_connection(self):
        """Test connection to emergency dashboard"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/emergency-stats", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Emergency dashboard is accessible")
                return True
            else:
                logger.error(f"❌ Emergency dashboard returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to emergency dashboard: {e}")
            return False
    
    def test_websocket_connection(self):
        """Test connection to websocket server"""
        try:
            response = requests.get(f"{self.websocket_server_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ WebSocket server is accessible")
                return True
            else:
                logger.error(f"❌ WebSocket server returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to WebSocket server: {e}")
            return False
    
    def get_emergency_alerts(self):
        """Get current emergency alerts from dashboard"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/emergency-alerts", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    alerts = data.get('alerts', [])
                    logger.info(f"📊 Found {len(alerts)} emergency alerts")
                    return alerts
                else:
                    logger.error(f"❌ Failed to get alerts: {data.get('error')}")
                    return []
            else:
                logger.error(f"❌ Failed to get alerts: HTTP {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"❌ Error getting emergency alerts: {e}")
            return []
    
    def get_emergency_stats(self):
        """Get emergency statistics from dashboard"""
        try:
            response = requests.get(f"{self.dashboard_url}/api/emergency-stats", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    stats = data.get('stats', {})
                    logger.info(f"📈 Emergency Stats: {stats}")
                    return stats
                else:
                    logger.error(f"❌ Failed to get stats: {data.get('error')}")
                    return {}
            else:
                logger.error(f"❌ Failed to get stats: HTTP {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"❌ Error getting emergency stats: {e}")
            return {}
    
    def test_notification_service(self):
        """Test notification service"""
        try:
            # Import notification service
            from notification_service import notification_service
            
            logger.info("🧪 Testing notification service...")
            results = notification_service.test_notifications()
            logger.info(f"📧 Notification test results: {results}")
            
            return results
        except Exception as e:
            logger.error(f"❌ Error testing notification service: {e}")
            return {}
    
    def check_mongodb_connection(self):
        """Check MongoDB connection and emergency_alarm collection"""
        try:
            import pymongo
            
            # Try to connect to MongoDB
            client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
            db = client['AMY']
            
            # Check if emergency_alarm collection exists
            collections = db.list_collection_names()
            if 'emergency_alarm' in collections:
                count = db.emergency_alarm.count_documents({})
                logger.info(f"✅ MongoDB connected - emergency_alarm collection has {count} documents")
                return True
            else:
                logger.warning("⚠️ emergency_alarm collection not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            return False
    
    def run_full_integration_test(self):
        """Run complete integration test"""
        logger.info("🚀 Starting Emergency Dashboard Integration Test")
        logger.info("=" * 50)
        
        results = {
            'dashboard': False,
            'websocket': False,
            'mongodb': False,
            'notifications': False
        }
        
        # Test dashboard connection
        logger.info("1. Testing Emergency Dashboard Connection...")
        results['dashboard'] = self.test_dashboard_connection()
        
        # Test websocket connection
        logger.info("2. Testing WebSocket Server Connection...")
        results['websocket'] = self.test_websocket_connection()
        
        # Test MongoDB connection
        logger.info("3. Testing MongoDB Connection...")
        results['mongodb'] = self.check_mongodb_connection()
        
        # Test notification service
        logger.info("4. Testing Notification Service...")
        notification_results = self.test_notification_service()
        results['notifications'] = any(notification_results.values())
        
        # Get current data
        logger.info("5. Getting Current Emergency Data...")
        alerts = self.get_emergency_alerts()
        stats = self.get_emergency_stats()
        
        # Print summary
        logger.info("=" * 50)
        logger.info("📋 INTEGRATION TEST SUMMARY")
        logger.info("=" * 50)
        
        for component, status in results.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"{status_icon} {component.upper()}: {'PASS' if status else 'FAIL'}")
        
        logger.info("=" * 50)
        logger.info(f"📊 Current Emergency Alerts: {len(alerts)}")
        logger.info(f"📈 Emergency Stats: {stats}")
        
        if all(results.values()):
            logger.info("🎉 ALL TESTS PASSED - Emergency Dashboard is fully integrated!")
        else:
            logger.warning("⚠️ Some tests failed - Check the logs above for details")
        
        return results

def main():
    """Main function"""
    integrator = EmergencyDashboardIntegrator()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            integrator.run_full_integration_test()
        elif command == "dashboard":
            integrator.test_dashboard_connection()
        elif command == "websocket":
            integrator.test_websocket_connection()
        elif command == "mongodb":
            integrator.check_mongodb_connection()
        elif command == "notifications":
            integrator.test_notification_service()
        elif command == "alerts":
            alerts = integrator.get_emergency_alerts()
            print(json.dumps(alerts, indent=2, default=str))
        elif command == "stats":
            stats = integrator.get_emergency_stats()
            print(json.dumps(stats, indent=2))
        else:
            print("Usage: python integrate_with_mqtt.py [test|dashboard|websocket|mongodb|notifications|alerts|stats]")
    else:
        integrator.run_full_integration_test()

if __name__ == "__main__":
    main() 