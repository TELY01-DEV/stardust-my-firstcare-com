#!/usr/bin/env python3
"""
Fix Swagger Duplicate Tags Script
Consolidates duplicate "Admin" and "Admin Panel" tags in the OpenAPI specification
"""

import json
import re
from datetime import datetime

def fix_duplicate_tags():
    """Fix duplicate Admin tags in OpenAPI specification"""
    
    print("🔧 Fixing duplicate Admin tags in Swagger documentation...")
    
    # Read the current OpenAPI specification
    with open("Updated_MyFirstCare_API_OpenAPI_Spec.json", "r") as f:
        openapi_spec = json.load(f)
    
    # Track changes
    changes_made = 0
    
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
                
                # Process tags to consolidate Admin-related ones
                for tag in original_tags:
                    # Keep only one admin tag
                    if tag.lower() in ["admin", "admin panel"]:
                        if "Admin" not in new_tags:
                            new_tags.append("Admin")
                    else:
                        # Keep other tags as they are
                        if tag not in new_tags:
                            new_tags.append(tag)
                
                # Update tags if changed
                if new_tags != original_tags:
                    details["tags"] = new_tags
                    changes_made += 1
                    print(f"  ✅ Fixed tags for {method.upper()} {path}")
                    print(f"     Before: {original_tags}")
                    print(f"     After:  {new_tags}")
    
    # Update the description to reflect the fix
    current_description = openapi_spec.get("info", {}).get("description", "")
    
    # Add fix information to description
    fix_info = f"""
## 🔧 **Tag Consolidation Fix (Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})**

### ✅ **Fixed Issues**
- **Duplicate Admin Tags**: Consolidated "Admin" and "Admin Panel" tags into single "Admin" group
- **Swagger Organization**: Eliminated duplicate endpoint groups in documentation
- **Cleaner Interface**: Single organized Admin section in Swagger UI

### 📊 **Changes Made**
- **{changes_made} endpoints** updated with consolidated tags
- **Duplicate tag groups** eliminated
- **Consistent naming** across all admin endpoints

"""
    
    # Insert fix info after the main description
    if "## 🚨 **Known Issues & Limitations**" in current_description:
        # Insert before known issues section
        current_description = current_description.replace(
            "## 🚨 **Known Issues & Limitations**",
            fix_info + "## 🚨 **Known Issues & Limitations**"
        )
    else:
        # Append to end if no known issues section
        current_description += fix_info
    
    openapi_spec["info"]["description"] = current_description
    
    # Save the fixed specification
    output_file = "Fixed_MyFirstCare_API_OpenAPI_Spec.json"
    with open(output_file, "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    print(f"\n✅ Fixed OpenAPI specification saved to: {output_file}")
    print(f"📊 Total changes made: {changes_made} endpoints")
    
    return output_file

def update_app_openapi():
    """Update the main app to serve the fixed OpenAPI spec"""
    
    print("\n🔄 Updating main app to serve fixed OpenAPI spec...")
    
    # Read the main app file
    with open("main.py", "r") as f:
        app_content = f.read()
    
    # Check if we need to update the OpenAPI spec path
    if "Fixed_MyFirstCare_API_OpenAPI_Spec.json" not in app_content:
        # Replace the OpenAPI spec file reference
        app_content = app_content.replace(
            "Updated_MyFirstCare_API_OpenAPI_Spec.json",
            "Fixed_MyFirstCare_API_OpenAPI_Spec.json"
        )
        
        # Save the updated app
        with open("main.py", "w") as f:
            f.write(app_content)
        
        print("✅ Updated main.py to serve fixed OpenAPI spec")
    else:
        print("ℹ️  Main app already configured for fixed OpenAPI spec")

def create_summary():
    """Create a summary document of the tag fix"""
    
    summary = f"""# Swagger Duplicate Tags Fix Summary

## 📅 **Fix Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🎯 **Problem Identified**
The Swagger documentation had duplicate endpoint groups:
- **"Admin"** tag group
- **"Admin Panel"** tag group

This created confusion in the Swagger UI with endpoints appearing in multiple groups.

## ✅ **Solution Implemented**
1. **Consolidated Tags**: Merged "Admin" and "Admin Panel" tags into single "Admin" group
2. **Updated OpenAPI Spec**: Fixed all endpoint tag definitions
3. **Updated App**: Modified main.py to serve the fixed specification
4. **Documentation**: Added fix information to API description

## 📊 **Results**
- **Single Admin Group**: All admin endpoints now appear in one organized group
- **Cleaner Interface**: Eliminated duplicate endpoint listings
- **Better Organization**: Consistent tag naming across all endpoints
- **Improved UX**: Clearer navigation in Swagger UI

## 🔄 **Files Updated**
- `Fixed_MyFirstCare_API_OpenAPI_Spec.json` - Fixed OpenAPI specification
- `main.py` - Updated to serve fixed spec
- `SWAGGER_DUPLICATE_TAGS_FIX_SUMMARY.md` - This summary document

## 🚀 **Next Steps**
1. Restart the application to serve the fixed OpenAPI spec
2. Verify the Swagger UI shows single Admin group
3. Test that all endpoints are accessible and properly organized

## 📝 **Technical Details**
The fix involved:
- Scanning all endpoint definitions in the OpenAPI spec
- Identifying endpoints with both "admin" and "Admin Panel" tags
- Consolidating them into a single "Admin" tag
- Preserving all other tags (Authentication, AVA4 Device, etc.)
- Updating the API description with fix information

This ensures a clean, organized Swagger documentation interface.
"""
    
    with open("SWAGGER_DUPLICATE_TAGS_FIX_SUMMARY.md", "w") as f:
        f.write(summary)
    
    print("📄 Created fix summary: SWAGGER_DUPLICATE_TAGS_FIX_SUMMARY.md")

def main():
    """Main function to fix duplicate tags"""
    
    print("🔧 Swagger Duplicate Tags Fix")
    print("=" * 50)
    
    # Fix the duplicate tags
    output_file = fix_duplicate_tags()
    
    # Update the main app
    update_app_openapi()
    
    # Create summary
    create_summary()
    
    print("\n🎉 Duplicate tags fix completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Restart the application: docker-compose restart")
    print("2. Check Swagger UI at http://localhost:5054/docs")
    print("3. Verify single 'Admin' group in the documentation")
    print("4. Test that all endpoints are properly organized")

if __name__ == "__main__":
    main() 