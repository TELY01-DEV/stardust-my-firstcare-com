# Geographic & Hospital Data Import Guide

## Overview
This guide explains how to import Province, District, Sub-district, and Hospital data to the Coruscant MongoDB cluster.

## Files Required
The following JSON files must be present in the `docs/JSON-DB-IMPORT/import_script/` directory:
- `AMY_25_10_2024.provinces.json` ✅ 
- `AMY_25_10_2024.districts.json` ✅
- `AMY_25_10_2024.sub_districts.json` ✅
- `AMY_25_10_2024.hospitals.json` ✅

## Import Script
Use the specialized import script: `import_geo_hospital_data.py`

## Prerequisites
1. **MongoDB Connection**: Ensure you have access to the Coruscant cluster
2. **SSL Certificates**: Make sure SSL certificates are available in the `ssl/` directory:
   - `ssl/ca-latest.pem`
   - `ssl/client-combined-latest.pem`
3. **Dependencies**: Install required Python packages:
   ```bash
   pip install pymongo
   ```

## Environment Variables (Optional)
You can override the default connection settings using environment variables:
```bash
export MONGODB_HOST="coruscant.my-firstcare.com"
export MONGODB_PORT="27023"
export MONGODB_USERNAME="opera_admin"
export MONGODB_PASSWORD="Sim!443355"
export MONGODB_AUTH_DB="admin"
```

## Running the Import

### Method 1: From Project Root
```bash
cd /path/to/stardust-my-firstcare-com
python docs/JSON-DB-IMPORT/import_script/import_geo_hospital_data.py
```

### Method 2: From Import Script Directory
```bash
cd docs/JSON-DB-IMPORT/import_script/
python import_geo_hospital_data.py
```

## Import Process
The script will:

1. **🔍 Discovery**: Find and validate all required JSON files
2. **🔐 Connection**: Connect to Coruscant cluster with SSL
3. **📊 Preview**: Show current vs new record counts for each collection
4. **⚠️ Confirmation**: Ask for confirmation before proceeding
5. **📦 Import**: Process data in hierarchical order:
   - Provinces → Districts → Sub-districts → Hospitals
6. **📊 Indexing**: Create appropriate indexes for each collection
7. **📈 Summary**: Display final import statistics

## Data Collections

### Target Collections in AMY Database:
- **`provinces`**: Provincial administrative divisions
- **`districts`**: District-level administrative divisions  
- **`sub_districts`**: Sub-district administrative units
- **`hospitals`**: Hospital facility information

### Indexes Created:
- **Provinces**: `province_code` (unique), `province_name`
- **Districts**: `(province_code, district_code)` (unique), `district_name`, `province_code`
- **Sub-districts**: `(province_code, district_code, sub_district_code)` (unique), `sub_district_name`
- **Hospitals**: `hospital_code` (unique), `hospital_name`, `province_code`, `hospital_type`, `is_active`

## Safety Features
- **Backup Warning**: Script asks for confirmation before replacing existing data
- **Batch Processing**: Imports data in batches of 1000 records
- **Error Handling**: Continues processing even if individual batches fail
- **Progress Tracking**: Shows detailed progress for each collection
- **Rollback Safe**: Only drops existing collections after user confirmation

## Expected Data Volumes
Based on current files:
- **Provinces**: ~77 records
- **Districts**: ~900+ records  
- **Sub-districts**: ~7,000+ records
- **Hospitals**: ~1,000+ records

## Troubleshooting

### Connection Issues
- Verify SSL certificates are in the correct location
- Check network connectivity to `coruscant.my-firstcare.com:27023`
- Verify MongoDB credentials

### Import Failures
- Check JSON file format and encoding (UTF-8)
- Ensure sufficient disk space on MongoDB server
- Verify write permissions on target database

### SSL Certificate Issues
```bash
# Verify certificates exist
ls -la ssl/ca-latest.pem ssl/client-combined-latest.pem
```

## Post-Import Verification
After successful import, verify the data:
```python
# Connect to MongoDB and check counts
db.provinces.countDocuments({})
db.districts.countDocuments({})
db.sub_districts.countDocuments({})
db.hospitals.countDocuments({})
```

## Data Relationships
The imported data maintains hierarchical relationships:
```
Province (77)
├── District (900+)
    ├── Sub-district (7,000+)
        └── Hospital (1,000+)
```

## Success Criteria
✅ All 4 collections imported successfully  
✅ Indexes created for optimal query performance  
✅ Data counts match source JSON files  
✅ No duplicate key errors  
✅ Hierarchical relationships maintained  

---
*Last Updated: October 25, 2024*
*Script: `import_geo_hospital_data.py`* 