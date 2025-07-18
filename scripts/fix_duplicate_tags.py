#!/usr/bin/env python3
"""
Script to fix duplicate tags in OpenAPI spec by consolidating title case tags to lowercase
"""

import json
import requests
from collections import defaultdict

def fix_duplicate_tags():
    """Fix duplicate tags in OpenAPI spec"""
    
    # Get the current OpenAPI spec
    try:
        response = requests.get("http://localhost:5054/openapi.json")
        response.raise_for_status()
        openapi_spec = response.json()
    except Exception as e:
        print(f"Error fetching OpenAPI spec: {e}")
        return
    
    # Define tag mappings (title case -> lowercase)
    tag_mappings = {
        "FHIR R5": "fhir-r5",
        "Admin Panel": "admin",
        "AVA4 Device": "ava4",
        "Security Management": "security",
        "Qube-Vital": "qube-vital",
        "Device CRUD Operations": "device-crud",
        "Device Mapping": "device-mapping",
        "Kati Watch": "kati",
        "Hash Audit": "hash-audit",
        "Performance Monitoring": "performance",
        "Real-time Communication": "realtime",
        "Patient Medical Devices": "patient-devices",
        "Medical Device Lookup": "device-lookup",
        "Medical History": "ava4",  # This is part of AVA4 router
        "Authentication": "authentication",
        "Raw Documents": "admin"  # This is part of admin router
    }
    
    # Track changes
    changes_made = defaultdict(int)
    
    # Fix tags in paths
    for path, path_item in openapi_spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if isinstance(operation, dict) and "tags" in operation:
                original_tags = operation["tags"].copy()
                new_tags = []
                
                for tag in original_tags:
                    if tag in tag_mappings:
                        new_tag = tag_mappings[tag]
                        if new_tag not in new_tags:
                            new_tags.append(new_tag)
                            changes_made[f"{tag} -> {new_tag}"] += 1
                    else:
                        if tag not in new_tags:
                            new_tags.append(tag)
                
                operation["tags"] = new_tags
    
    # Fix tags in components (if any)
    if "components" in openapi_spec and "tags" in openapi_spec["components"]:
        for tag in openapi_spec["components"]["tags"]:
            if "name" in tag and tag["name"] in tag_mappings:
                tag["name"] = tag_mappings[tag["name"]]
    
    # Save the fixed spec
    with open("Fixed_OpenAPI_Spec.json", "w") as f:
        json.dump(openapi_spec, f, indent=2)
    
    # Print summary
    print("✅ Fixed duplicate tags in OpenAPI spec")
    print("\nChanges made:")
    for change, count in changes_made.items():
        print(f"  {change}: {count} occurrences")
    
    print(f"\nFixed spec saved to: Fixed_OpenAPI_Spec.json")
    
    # Update the main.py to serve the fixed spec
    update_main_py()
    
    return openapi_spec

def update_main_py():
    """Update main.py to serve the fixed OpenAPI spec"""
    
    # Read the current main.py
    with open("main.py", "r") as f:
        content = f.read()
    
    # Update the custom OpenAPI endpoint
    new_endpoint = '''# Custom OpenAPI endpoint to serve the fixed, consolidated spec
@app.get("/api/openapi.json", include_in_schema=False)
async def get_openapi_spec():
    """Serve the fixed OpenAPI specification with consolidated tags"""
    try:
        logger.info("📂 Serving fixed OpenAPI specification...")
        with open("Fixed_OpenAPI_Spec.json", "r") as f:
            openapi_schema = json.load(f)
        logger.info("✅ Served fixed OpenAPI specification with consolidated tags")
        return JSONResponse(content=openapi_schema)
    except FileNotFoundError:
        logger.warning("⚠️ Fixed OpenAPI spec not found, serving auto-generated schema")
        # Fallback to auto-generated schema if file not found
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        return JSONResponse(content=openapi_schema)
    except Exception as e:
        logger.error(f"❌ Error serving OpenAPI spec: {e}")
        raise HTTPException(status_code=500, detail="Error generating OpenAPI spec")'''
    
    # Replace the existing endpoint
    import re
    pattern = r'# Custom OpenAPI endpoint.*?raise HTTPException\(status_code=500, detail="Error generating OpenAPI spec"\)'
    content = re.sub(pattern, new_endpoint, content, flags=re.DOTALL)
    
    # Write back to main.py
    with open("main.py", "w") as f:
        f.write(content)
    
    print("✅ Updated main.py to serve fixed OpenAPI spec")

if __name__ == "__main__":
    fix_duplicate_tags() 