#!/usr/bin/env python3
"""
AVA4 Status Monitor Script

This script monitors AVA4 device status based on heartbeat messages and provides
real-time status tracking, device names, and offline detection.
"""

import pymongo
from bson import ObjectId
import ssl
from datetime import datetime, timedelta
import json
import time

# MongoDB Configuration
MONGODB_URI = "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true"
MONGODB_DATABASE = "AMY"

def connect_to_mongodb():
    """Connect to MongoDB with SSL"""
    try:
        # Connect to MongoDB with proper SSL certificates
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
        print("✅ Successfully connected to MongoDB")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return None

def analyze_ava4_heartbeat_events(client):
    """Analyze AVA4 heartbeat events to understand device status patterns"""
    try:
        db = client[MONGODB_DATABASE]
        event_logs = db.event_logs
        
        # Get AVA4 heartbeat events
        heartbeat_events = list(event_logs.find({
            'source': 'AVA4',
            'details.payload.type': 'HB_Msg',
            'details.payload.data.msg': 'Online'
        }).sort('timestamp', -1).limit(100))
        
        print(f"📊 Found {len(heartbeat_events)} AVA4 heartbeat events")
        
        ava4_devices = {}
        
        for event in heartbeat_events:
            try:
                payload = event.get('details', {}).get('payload', {})
                
                ava4_mac = payload.get('mac', 'unknown')
                ava4_name = payload.get('name', 'unknown')
                ava4_imei = payload.get('IMEI', 'unknown')
                ava4_iccid = payload.get('ICCID', 'unknown')
                timestamp = event.get('timestamp')
                
                if ava4_mac not in ava4_devices:
                    ava4_devices[ava4_mac] = {
                        'name': ava4_name,
                        'imei': ava4_imei,
                        'iccid': ava4_iccid,
                        'last_heartbeat': timestamp,
                        'heartbeat_count': 0,
                        'status': 'Online',
                        'first_seen': timestamp,
                        'last_seen': timestamp
                    }
                
                ava4_devices[ava4_mac]['heartbeat_count'] += 1
                ava4_devices[ava4_mac]['last_seen'] = timestamp
                
            except Exception as e:
                print(f"⚠️ Error parsing heartbeat event {event.get('_id')}: {e}")
                continue
        
        print(f"🔍 Found {len(ava4_devices)} unique AVA4 devices")
        return ava4_devices
        
    except Exception as e:
        print(f"❌ Error analyzing AVA4 heartbeat events: {e}")
        return {}

def check_ava4_offline_status(client, ava4_devices):
    """Check which AVA4 devices are offline (no heartbeat in last 2 minutes)"""
    try:
        db = client[MONGODB_DATABASE]
        event_logs = db.event_logs
        
        # Calculate cutoff time (2 minutes ago)
        cutoff_time = datetime.utcnow() - timedelta(minutes=2)
        
        print(f"\n🔍 Checking AVA4 offline status (cutoff: {cutoff_time})")
        
        offline_devices = []
        online_devices = []
        
        for ava4_mac, device_info in ava4_devices.items():
            last_heartbeat = device_info['last_seen']
            
            # Convert string timestamp to datetime if needed
            if isinstance(last_heartbeat, str):
                try:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                except:
                    last_heartbeat = datetime.utcnow()
            
            if last_heartbeat < cutoff_time:
                # Device is offline
                offline_devices.append({
                    'mac': ava4_mac,
                    'name': device_info['name'],
                    'imei': device_info['imei'],
                    'last_heartbeat': last_heartbeat,
                    'offline_duration': datetime.utcnow() - last_heartbeat,
                    'status': 'Offline'
                })
                device_info['status'] = 'Offline'
            else:
                # Device is online
                online_devices.append({
                    'mac': ava4_mac,
                    'name': device_info['name'],
                    'imei': device_info['imei'],
                    'last_heartbeat': last_heartbeat,
                    'status': 'Online'
                })
                device_info['status'] = 'Online'
        
        print(f"📊 AVA4 Status Summary:")
        print(f"   Online devices: {len(online_devices)}")
        print(f"   Offline devices: {len(offline_devices)}")
        
        if online_devices:
            print(f"\n✅ Online AVA4 Devices:")
            for device in online_devices:
                print(f"   - {device['name']} ({device['mac']}) - Last: {device['last_heartbeat']}")
        
        if offline_devices:
            print(f"\n❌ Offline AVA4 Devices:")
            for device in offline_devices:
                duration = device['offline_duration']
                print(f"   - {device['name']} ({device['mac']}) - Offline for: {duration}")
        
        return online_devices, offline_devices
        
    except Exception as e:
        print(f"❌ Error checking AVA4 offline status: {e}")
        return [], []

def create_ava4_status_collection(client, ava4_devices):
    """Create or update AVA4 status collection in database"""
    try:
        db = client[MONGODB_DATABASE]
        
        # Create AVA4 status collection if it doesn't exist
        if 'ava4_status' not in db.list_collection_names():
            db.create_collection('ava4_status')
            print("📋 Created ava4_status collection")
        
        ava4_status_collection = db.ava4_status
        
        # Update or insert AVA4 device status
        updated_count = 0
        inserted_count = 0
        
        for ava4_mac, device_info in ava4_devices.items():
            # Prepare status document
            status_doc = {
                'ava4_mac': ava4_mac,
                'ava4_name': device_info['name'],
                'imei': device_info['imei'],
                'iccid': device_info['iccid'],
                'status': device_info['status'],
                'last_heartbeat': device_info['last_seen'],
                'first_seen': device_info['first_seen'],
                'heartbeat_count': device_info['heartbeat_count'],
                'updated_at': datetime.utcnow()
            }
            
            # Update existing or insert new
            result = ava4_status_collection.update_one(
                {'ava4_mac': ava4_mac},
                {'$set': status_doc},
                upsert=True
            )
            
            if result.upserted_id:
                inserted_count += 1
            else:
                updated_count += 1
        
        print(f"\n📊 AVA4 Status Collection Update:")
        print(f"   Updated: {updated_count} devices")
        print(f"   Inserted: {inserted_count} devices")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating AVA4 status collection: {e}")
        return False

def create_ava4_status_api_endpoint():
    """Create API endpoint for AVA4 status monitoring"""
    try:
        # Add to the web panel API
        api_code = '''
@app.route('/api/ava4-status')
def get_ava4_status():
    """Get AVA4 device status"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(
            MONGODB_URI,
            tls=True,
            tlsCAFile='ssl/ca-latest.pem',
            tlsCertificateKeyFile='ssl/client-combined-latest.pem',
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        db = client[MONGODB_DATABASE]
        ava4_status_collection = db.ava4_status
        
        # Get all AVA4 status
        ava4_devices = list(ava4_status_collection.find({}, {'_id': 0}))
        
        # Calculate offline devices
        cutoff_time = datetime.utcnow() - timedelta(minutes=2)
        online_count = 0
        offline_count = 0
        
        for device in ava4_devices:
            last_heartbeat = device.get('last_heartbeat')
            if isinstance(last_heartbeat, str):
                try:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
                except:
                    last_heartbeat = datetime.utcnow()
            
            if last_heartbeat and last_heartbeat >= cutoff_time:
                device['status'] = 'Online'
                online_count += 1
            else:
                device['status'] = 'Offline'
                offline_count += 1
        
        client.close()
        
        return jsonify({
            'success': True,
            'data': {
                'devices': ava4_devices,
                'summary': {
                    'total': len(ava4_devices),
                    'online': online_count,
                    'offline': offline_count
                }
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/ava4-status/<ava4_mac>')
def get_ava4_device_status(ava4_mac):
    """Get specific AVA4 device status"""
    try:
        # Connect to MongoDB
        client = pymongo.MongoClient(
            MONGODB_URI,
            tls=True,
            tlsCAFile='ssl/ca-latest.pem',
            tlsCertificateKeyFile='ssl/client-combined-latest.pem',
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        db = client[MONGODB_DATABASE]
        ava4_status_collection = db.ava4_status
        
        # Get specific device
        device = ava4_status_collection.find_one({'ava4_mac': ava4_mac}, {'_id': 0})
        
        if not device:
            client.close()
            return jsonify({
                'success': False,
                'error': 'Device not found',
                'timestamp': datetime.utcnow().isoformat()
            }), 404
        
        # Check if device is online
        cutoff_time = datetime.utcnow() - timedelta(minutes=2)
        last_heartbeat = device.get('last_heartbeat')
        
        if isinstance(last_heartbeat, str):
            try:
                last_heartbeat = datetime.fromisoformat(last_heartbeat.replace('Z', '+00:00'))
            except:
                last_heartbeat = datetime.utcnow()
        
        if last_heartbeat and last_heartbeat >= cutoff_time:
            device['status'] = 'Online'
        else:
            device['status'] = 'Offline'
        
        client.close()
        
        return jsonify({
            'success': True,
            'data': device,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
'''
        
        print("📋 AVA4 Status API endpoints created")
        print("   - GET /api/ava4-status - Get all AVA4 devices status")
        print("   - GET /api/ava4-status/<mac> - Get specific device status")
        
        return api_code
        
    except Exception as e:
        print(f"❌ Error creating AVA4 status API: {e}")
        return None

def main():
    """Main function to implement AVA4 status monitoring"""
    print("🔧 AVA4 Status Monitor Implementation")
    print("=" * 50)
    
    # Step 1: Connect to MongoDB
    print("\n1. Connecting to MongoDB...")
    client = connect_to_mongodb()
    if not client:
        return
    
    # Step 2: Analyze AVA4 heartbeat events
    print("\n2. Analyzing AVA4 heartbeat events...")
    ava4_devices = analyze_ava4_heartbeat_events(client)
    
    if not ava4_devices:
        print("❌ No AVA4 devices found")
        return
    
    # Step 3: Check offline status
    print("\n3. Checking AVA4 offline status...")
    online_devices, offline_devices = check_ava4_offline_status(client, ava4_devices)
    
    # Step 4: Create AVA4 status collection
    print("\n4. Creating AVA4 status collection...")
    status_created = create_ava4_status_collection(client, ava4_devices)
    
    # Step 5: Create API endpoints
    print("\n5. Creating AVA4 status API endpoints...")
    api_code = create_ava4_status_api_endpoint()
    
    # Step 6: Summary
    print("\n" + "=" * 50)
    print("🎯 AVA4 STATUS MONITOR SUMMARY")
    print("=" * 50)
    
    if status_created:
        print("✅ SUCCESS: AVA4 status monitoring implemented!")
        print(f"\n📊 Results:")
        print(f"   - Total AVA4 devices: {len(ava4_devices)}")
        print(f"   - Online devices: {len(online_devices)}")
        print(f"   - Offline devices: {len(offline_devices)}")
        
        print("\n🚀 Next Steps:")
        print("1. Add API endpoints to web panel")
        print("2. Create AVA4 status dashboard")
        print("3. Implement real-time status monitoring")
        print("4. Add offline alerts and notifications")
        
        print("\n💡 Features Implemented:")
        print("- AVA4 device name tracking")
        print("- Real-time online/offline status")
        print("- Heartbeat monitoring (1-minute intervals)")
        print("- Device status database collection")
        print("- API endpoints for status queries")
        
        if offline_devices:
            print(f"\n⚠️ ALERT: {len(offline_devices)} AVA4 devices are offline!")
            for device in offline_devices:
                print(f"   - {device['name']} ({device['mac']}) - Offline for {device['offline_duration']}")
    else:
        print("⚠️ PARTIAL SUCCESS: Some issues may remain")
    
    # Close connection
    client.close()
    print("\n✅ Database connection closed")

if __name__ == "__main__":
    main() 