#!/usr/bin/env python3
"""
MASTER DATA VERIFICATION SCRIPT
===============================
Verify the imported master data in Coruscant database
"""

import pymongo
import ssl
import os

# MongoDB connection config
config = {
    'host': 'coruscant.my-firstcare.com',
    'port': 27023,
    'username': 'opera_admin',
    'password': 'Sim!443355',
    'authSource': 'admin',
    'tls': True,
    'tlsAllowInvalidCertificates': True,
    'tlsAllowInvalidHostnames': True,
    'tlsCAFile': 'ssl/ca-latest.pem',
    'tlsCertificateKeyFile': 'ssl/client-combined-latest.pem'
}

def main():
    try:
        print("🔍 Connecting to Coruscant MongoDB...")
        client = pymongo.MongoClient(**config)
        db = client.AMY
        
        print("✅ Connected successfully!\n")
        
        print('🩸 BLOOD GROUPS SAMPLE:')
        print('=' * 50)
        blood_count = db.blood_groups.count_documents({})
        print(f"Total records: {blood_count}")
        
        for doc in db.blood_groups.find().limit(3):
            name_en = next((item['name'] for item in doc.get('name', []) if item.get('code') == 'en'), 'N/A')
            name_th = next((item['name'] for item in doc.get('name', []) if item.get('code') == 'th'), 'N/A')
            print(f'• {name_en} | {name_th} | Active: {doc.get("is_active", False)}')
        
        print('\n🎨 HUMAN SKIN COLORS SAMPLE:')
        print('=' * 50)
        skin_count = db.human_skin_colors.count_documents({})
        print(f"Total records: {skin_count}")
        
        for doc in db.human_skin_colors.find().limit(3):
            name_en = next((item['name'] for item in doc.get('name', []) if item.get('code') == 'en'), 'N/A')
            name_th = next((item['name'] for item in doc.get('name', []) if item.get('code') == 'th'), 'N/A')
            print(f'• {name_en} | {name_th} | Active: {doc.get("is_active", False)}')
        
        print('\n🌍 NATIONS SAMPLE:')
        print('=' * 50)
        nations_count = db.nations.count_documents({})
        print(f"Total records: {nations_count}")
        
        for doc in db.nations.find().limit(5):
            name_en = next((item.get('name', 'N/A') for item in doc.get('name', []) if item.get('code') == 'en'), doc.get('en_name', 'N/A'))
            name_th = next((item.get('name', 'N/A') for item in doc.get('name', []) if item.get('code') == 'th' and item.get('name')), 'N/A')
            print(f'• {name_en} | {name_th} | Active: {doc.get("is_active", False)}')
        
        print(f'\n📊 SUMMARY:')
        print('=' * 50)
        print(f'✅ Blood Groups: {blood_count} records')
        print(f'✅ Human Skin Colors: {skin_count} records') 
        print(f'✅ Nations: {nations_count} records')
        print(f'✅ Total Master Data Records: {blood_count + skin_count + nations_count}')
        
        client.close()
        print('\n🎉 Master data verification completed successfully!')
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == "__main__":
    main() 