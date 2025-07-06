from bson import ObjectId
from datetime import datetime
from typing import Any, Dict, List, Union
import json

def convert_objectids_to_strings(obj: Any) -> Any:
    """Recursively convert ObjectId objects to strings in MongoDB documents"""
    try:
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            # Handle MongoDB JSON format with $oid
            if "$oid" in obj and len(obj) == 1:
                return obj["$oid"]  # Return the string directly
            else:
                return {key: convert_objectids_to_strings(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_objectids_to_strings(item) for item in obj]
        else:
            # Try to JSON serialize to catch any remaining ObjectIds
            try:
                json.dumps(obj)
                return obj
            except TypeError:
                # If it can't be serialized, convert to string
                return str(obj)
    except Exception as e:
        # Fallback: convert to string
        return str(obj)

def serialize_mongodb_response(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """Serialize MongoDB response for JSON output"""
    try:
        return convert_objectids_to_strings(data)
    except Exception as e:
        # Ultimate fallback: try to convert the entire structure to strings
        return json.loads(json.dumps(data, default=str)) 