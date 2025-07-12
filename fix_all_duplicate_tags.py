#!/usr/bin/env python3
"""
Fix All Duplicate Tags Script
Comprehensive fix for all duplicate tag groups in the OpenAPI specification
"""

import json
import re
from datetime import datetime

def get_tag_mapping():
    """Define mapping for consolidating duplicate tags"""
    
    tag_mapping = {
        # Authentication tags
        "authentication": "Authentication",
        "Authentication": "Authentication",
        
        # Admin tags
        "admin": "Admin",
        "Admin Panel": "Admin",
        
        # AVA4 tags
        "ava4": "AVA4 Device",
        "AVA4 Device": "AVA4 Device",
        
        # Kati tags
        "kati": "Kati Watch",
        "Kati Watch": "Kati Watch",
        
        # Qube-Vital tags
        "qube-vital": "Qube-Vital",
        "Qube-Vital": "Qube-Vital",
        
        # Device tags
        "device-mapping": "Device Mapping",
        "Device Mapping": "Device Mapping",
        "device-crud": "Device CRUD Operations",
        "Device CRUD Operations": "Device CRUD Operations",
        "device-lookup": "Medical Device Lookup",
        "Medical Device Lookup": "Medical Device Lookup",
        "patient-devices": "Patient Medical Devices",
        "Patient Medical Devices": "Patient Medical Devices",
        
        # Security tags
        "security": "Security Management",
        "Security Management": "Security Management",
        
        # Real-time tags
        "realtime": "Real-time Communication",
        "Real-time Communication": "Real-time Communication",
        
        # Performance tags
        "performance": "Performance Monitoring",
        "Performance Monitoring": "Performance Monitoring",
        
        # Analytics tags
        "analytics": "Analytics",
        
        # Reports tags
        "reports": "Reports",
        
        # Visualization tags
        "visualization": "Visualization",
        
        # Medical History tags
        "Medical History": "Medical History",
        
        # Raw Documents tags
        "Raw Documents": "Raw Documents",
        
        # Hash Audit tags
        "hash-audit": "Hash Audit",
        "Hash Audit": "Hash Audit",
        
        # FHIR R5 tags
        "fhir-r5": "FHIR R5",
        "FHIR R5": "FHIR R5"
    }
    
    return tag_mapping

def fix_all_duplicate_tags():
    """Fix all duplicate tags in OpenAPI specification"""
    
    print("🔧 Fixing ALL duplicate tags in Swagger documentation...")
    
    # Read the current OpenAPI specification
    with open("Fixed_MyFirstCare_API_OpenAPI_Spec.json", "r") as f:
        openapi_spec = json.load(f)
    
    # Get tag mapping
    tag_mapping = get_tag_mapping()
    
    # Track changes
    changes_made = 0
    tag_changes = {}
    
    # Process all paths
    paths = openapi_spec.get("paths", {})
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            # Check if this endpoint has tags
            if "tags" in details:
                original_tags = details["tags"].copy()
                new_tags = []
                
                # Process tags to consolidate duplicates
                for tag in original_tags:
                    # Map tag to consolidated version
                    consolidated_tag = tag_mapping.get(tag, tag)
                    
                    # Add to new tags if not already present
                    if consolidated_tag not in new_tags:
                        new_tags.append(consolidated_tag)
                
                # Update tags if changed
                if new_tags != original_tags:
                    details["tags"] = new_tags
                    changes_made += 1
                    
                    # Track tag changes for reporting
                    for old_tag in original_tags:
                        new_tag = tag_mapping.get(old_tag, old_tag)
                        if old_tag != new_tag:
                            if old_tag not in tag_changes:
                                tag_changes[old_tag] = new_tag
                    
                    print(f"  ✅ Fixed tags for {method.upper()} {path}")
                    print(f"     Before: {original_tags}")
                    print(f"     After:  {new_tags}")
    
    # Update the description to reflect the comprehensive fix
    current_description = openapi_spec.get("info", {}).get("description", "")
    
    # Add comprehensive fix information to description
    fix_info = f"""
## 🔧 **Comprehensive Tag Consolidation Fix (Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})**

### ✅ **Fixed Issues**
- **All Duplicate Tags**: Consolidated all duplicate tag groups across the entire API
- **Swagger Organization**: Eliminated all duplicate endpoint groups in documentation
- **Cleaner Interface**: Single organized sections for each functional area
- **Consistent Naming**: Standardized tag names across all endpoints

### 📊 **Changes Made**
- **{changes_made} endpoints** updated with consolidated tags
- **{len(tag_changes)} duplicate tag groups** eliminated
- **Consistent naming** across all functional areas

### 🔄 **Tag Consolidations**
"""
    
    # Add tag consolidation details
    for old_tag, new_tag in tag_changes.items():
        fix_info += f"- **{old_tag}** → **{new_tag}**\n"
    
    fix_info += """
### 📋 **Final Tag Structure**
- **Authentication**: Login, token management, user info
- **Admin**: All administrative operations and management
- **AVA4 Device**: AVA4 device integration and management
- **Kati Watch**: Kati watch device integration
- **Qube-Vital**: Qube-Vital device integration
- **Device Mapping**: Device mapping and relationships
- **Device CRUD Operations**: Device create, read, update, delete
- **Medical Device Lookup**: Device lookup and search
- **Patient Medical Devices**: Patient-device relationships
- **Security Management**: Security monitoring and alerts
- **Real-time Communication**: Real-time data and WebSocket
- **Performance Monitoring**: Performance metrics and monitoring
- **Analytics**: Analytics and reporting
- **Reports**: Report generation and management
- **Visualization**: Charts and data visualization
- **Medical History**: Medical records and history
- **Raw Documents**: Raw document access and analysis
- **Hash Audit**: Hash audit and blockchain integration
- **FHIR R5**: FHIR R5 compliance and integration

"""
    
    # Insert fix info before known issues section
    if "## 🚨 **Known Issues & Limitations**" in current_description:
        # Remove previous fix info if exists
        current_description = re.sub(
            r'## 🔧 \*\*.*?Fix.*?\*\*.*?(?=## 🚨 \*\*Known Issues)',
            '',
            current_description,
            flags=re.DOTALL
        )
        
        # Insert new fix info
        current_description = current_description.replace(
            "## 🚨 **Known Issues & Limitations**",
            fix_info + "## 🚨 **Known Issues & Limitations**"
        )
    else:
        # Append to end if no known issues section
        current_description += fix_info
    
    openapi_spec["info"]["description"] = current_description
    
    # Save the fixed specification
    output_file = "Final_MyFirstCare_API_OpenAPI_Spec.json"
    with open(output_file, "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    print(f"\n✅ Fixed OpenAPI specification saved to: {output_file}")
    print(f"📊 Total changes made: {changes_made} endpoints")
    print(f"🏷️  Tag consolidations: {len(tag_changes)} groups")
    
    return output_file

def update_app_openapi():
    """Update the main app to serve the final fixed OpenAPI spec"""
    
    print("\n🔄 Updating main app to serve final fixed OpenAPI spec...")
    
    # Read the main app file
    with open("main.py", "r") as f:
        app_content = f.read()
    
    # Update the OpenAPI spec file reference
    app_content = app_content.replace(
        "Fixed_MyFirstCare_API_OpenAPI_Spec.json",
        "Final_MyFirstCare_API_OpenAPI_Spec.json"
    )
    
    # Save the updated app
    with open("main.py", "w") as f:
        f.write(app_content)
    
    print("✅ Updated main.py to serve final fixed OpenAPI spec")

def create_comprehensive_summary():
    """Create a comprehensive summary document of the tag fix"""
    
    summary = f"""# Comprehensive Swagger Duplicate Tags Fix Summary

## 📅 **Fix Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 **Problem Identified**
The Swagger documentation had multiple duplicate endpoint groups:
- **Authentication**: "authentication" and "Authentication"
- **Admin**: "admin" and "Admin Panel"
- **AVA4**: "ava4" and "AVA4 Device"
- **Kati**: "kati" and "Kati Watch"
- **Qube-Vital**: "qube-vital" and "Qube-Vital"
- **Device Mapping**: "device-mapping" and "Device Mapping"
- **Device CRUD**: "device-crud" and "Device CRUD Operations"
- **Security**: "security" and "Security Management"
- **Real-time**: "realtime" and "Real-time Communication"
- **Performance**: "performance" and "Performance Monitoring"
- **Hash Audit**: "hash-audit" and "Hash Audit"
- **FHIR R5**: "fhir-r5" and "FHIR R5"

This created significant confusion in the Swagger UI with endpoints appearing in multiple groups.

## ✅ **Solution Implemented**
1. **Comprehensive Tag Mapping**: Created mapping for all duplicate tags
2. **Consolidated All Tags**: Merged all duplicate tags into single groups
3. **Updated OpenAPI Spec**: Fixed all endpoint tag definitions
4. **Updated App**: Modified main.py to serve the final fixed specification
5. **Documentation**: Added comprehensive fix information to API description

## 📊 **Results**
- **Single Group per Function**: Each functional area now has one organized group
- **Cleaner Interface**: Eliminated all duplicate endpoint listings
- **Better Organization**: Consistent tag naming across all endpoints
- **Improved UX**: Much clearer navigation in Swagger UI
- **Professional Appearance**: Clean, organized API documentation

## 🔄 **Files Updated**
- `Final_MyFirstCare_API_OpenAPI_Spec.json` - Final fixed OpenAPI specification
- `main.py` - Updated to serve final fixed spec
- `COMPREHENSIVE_SWAGGER_TAGS_FIX_SUMMARY.md` - This summary document

## 🚀 **Next Steps**
1. Restart the application to serve the final fixed OpenAPI spec
2. Verify the Swagger UI shows single groups for each functional area
3. Test that all endpoints are accessible and properly organized
4. Enjoy a clean, professional API documentation interface

## 📝 **Technical Details**
The comprehensive fix involved:
- Creating a complete tag mapping for all duplicate groups
- Scanning all endpoint definitions in the OpenAPI spec
- Identifying and consolidating all duplicate tags
- Preserving unique tags that don't have duplicates
- Updating the API description with comprehensive fix information
- Ensuring consistent naming across the entire API

This ensures a clean, organized, and professional Swagger documentation interface.
"""
    
    with open("COMPREHENSIVE_SWAGGER_TAGS_FIX_SUMMARY.md", "w") as f:
        f.write(summary)
    
    print("📄 Created comprehensive fix summary: COMPREHENSIVE_SWAGGER_TAGS_FIX_SUMMARY.md")

def main():
    """Main function to fix all duplicate tags"""
    
    print("🔧 Comprehensive Swagger Duplicate Tags Fix")
    print("=" * 60)
    
    # Fix all duplicate tags
    output_file = fix_all_duplicate_tags()
    
    # Update the main app
    update_app_openapi()
    
    # Create comprehensive summary
    create_comprehensive_summary()
    
    print("\n🎉 Comprehensive duplicate tags fix completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Restart the application: docker-compose restart")
    print("2. Check Swagger UI at http://localhost:5054/docs")
    print("3. Verify single groups for each functional area")
    print("4. Test that all endpoints are properly organized")
    print("5. Enjoy a clean, professional API documentation interface")

if __name__ == "__main__":
    main() 