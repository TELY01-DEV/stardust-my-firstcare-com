#!/usr/bin/env python3
import pymongo
from datetime import datetime, timedelta, timezone

# MongoDB connection
client = pymongo.MongoClient(
    "mongodb://opera_admin:Sim!443355@coruscant.my-firstcare.com:27023/admin?ssl=true&authSource=admin&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true"
)
db = client['AMY']

# Get emergency alerts from the last 24 hours
one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)

# Count emergency alerts
emergency_count = db.emergency_alarm.count_documents({
    'device_type': 'Kati_Watch',
    'timestamp': {'$gte': one_day_ago}
})

# Count SOS alerts
sos_count = db.emergency_alarm.count_documents({
    'device_type': 'Kati_Watch',
    'timestamp': {'$gte': one_day_ago},
    'topic': {'$regex': 'SOS', '$options': 'i'}
})

# Count fall detection alerts
fall_count = db.emergency_alarm.count_documents({
    'device_type': 'Kati_Watch',
    'timestamp': {'$gte': one_day_ago},
    'topic': {'$regex': 'fall', '$options': 'i'}
})

print(f"Emergency Alerts (last 24h): {emergency_count}")
print(f"SOS Alerts (last 24h): {sos_count}")
print(f"Fall Detection Alerts (last 24h): {fall_count}")

# Get some sample emergency alerts
sample_alerts = list(db.emergency_alarm.find({
    'device_type': 'Kati_Watch',
    'timestamp': {'$gte': one_day_ago}
}).sort('timestamp', -1).limit(5))

print(f"\nSample Emergency Alerts:")
for alert in sample_alerts:
    print(f"- Topic: {alert.get('topic', 'Unknown')}")
    print(f"  Device: {alert.get('device_id', 'Unknown')}")
    print(f"  Time: {alert.get('timestamp', 'Unknown')}")
    print(f"  Data: {alert.get('data', 'No data')}")
    print()

client.close() 