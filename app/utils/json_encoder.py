from bson import ObjectId, Binary, Decimal128, Code, Regex
from bson.regex import Regex as BSONRegex
from bson.timestamp import Timestamp
from bson.dbref import DBRef
try:
    from bson.min_max_key import MinKey, MaxKey
except ImportError:
    # Fallback for older versions of pymongo
    MinKey = None
    MaxKey = None
from datetime import datetime, date, time, timezone
from decimal import Decimal
from typing import Any, Dict, List, Union, Set
import json
import uuid
import re
from enum import Enum

class MongoJSONEncoder(json.JSONEncoder):
    """
    Comprehensive JSON encoder for handling all MongoDB data types and edge cases.
    
    Supports:
    - ObjectId, datetime, date, time
    - Decimal128, Binary data, UUID
    - Regex patterns, Timestamp, DBRef
    - MinKey, MaxKey, Code objects
    - Nested dictionaries and lists
    - Sets, tuples, enums
    - Custom objects with __dict__
    """
    
    def default(self, obj):
        # MongoDB-specific types
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
        elif isinstance(obj, Decimal128):
            return float(str(obj))
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, Binary):
            # Handle binary data - convert to base64 for JSON
            import base64
            return {
                "$binary": {
                    "base64": base64.b64encode(obj).decode('utf-8'),
                    "subType": f"{obj.subtype:02x}"
                }
            }
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, (Regex, BSONRegex)):
            return {
                "$regex": obj.pattern,
                "$options": obj.flags if hasattr(obj, 'flags') else ""
            }
        elif isinstance(obj, re.Pattern):
            return {
                "$regex": obj.pattern,
                "$options": obj.flags
            }
        elif isinstance(obj, Timestamp):
            return {
                "$timestamp": {
                    "t": obj.time,
                    "i": obj.inc
                }
            }
        elif isinstance(obj, DBRef):
            return {
                "$ref": obj.collection,
                "$id": str(obj.id),
                "$db": obj.database
            }
        elif MinKey and MaxKey and isinstance(obj, (MinKey, MaxKey)):
            return {"$" + obj.__class__.__name__.lower(): 1}
        elif isinstance(obj, Code):
            return {
                "$code": str(obj),
                "$scope": getattr(obj, 'scope', {})
            }
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, tuple):
            return list(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif hasattr(obj, '__dict__'):
            # Handle custom objects
            return obj.__dict__
        else:
            # Fallback to string representation
            return str(obj)

def convert_objectids_to_strings(obj: Any) -> Any:
    """
    Recursively convert all MongoDB-specific types to JSON-serializable formats.
    
    This function handles:
    - Deep nested structures (dictionaries, lists, tuples)
    - All MongoDB BSON types
    - Python datetime objects
    - Sets and other iterables
    - Custom objects with __dict__
    - Field analysis data structures
    """
    try:
        # Handle None and basic types
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
            
        # Handle MongoDB ObjectId
        elif isinstance(obj, ObjectId):
            return str(obj)
            
        # Handle datetime objects
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
            
        # Handle MongoDB Decimal128
        elif isinstance(obj, Decimal128):
            return float(str(obj))
        elif isinstance(obj, Decimal):
            return float(obj)
            
        # Handle MongoDB Binary
        elif isinstance(obj, Binary):
            import base64
            return {
                "$binary": {
                    "base64": base64.b64encode(obj).decode('utf-8'),
                    "subType": f"{obj.subtype:02x}"
                }
            }
            
        # Handle UUID
        elif isinstance(obj, uuid.UUID):
            return str(obj)
            
        # Handle Regex patterns
        elif isinstance(obj, (Regex, BSONRegex)):
            return {
                "$regex": obj.pattern,
                "$options": getattr(obj, 'flags', '')
            }
        elif isinstance(obj, re.Pattern):
            return {
                "$regex": obj.pattern,
                "$options": obj.flags
            }
            
        # Handle MongoDB Timestamp
        elif isinstance(obj, Timestamp):
            return {
                "$timestamp": {
                    "t": obj.time,
                    "i": obj.inc
                }
            }
            
        # Handle MongoDB DBRef
        elif isinstance(obj, DBRef):
            return {
                "$ref": obj.collection,
                "$id": convert_objectids_to_strings(obj.id),
                "$db": obj.database
            }
            
                 # Handle MongoDB MinKey/MaxKey
        elif MinKey and MaxKey and isinstance(obj, (MinKey, MaxKey)):
            return {"$" + obj.__class__.__name__.lower(): 1}
            
        # Handle MongoDB Code
        elif isinstance(obj, Code):
            return {
                "$code": str(obj),
                "$scope": convert_objectids_to_strings(getattr(obj, 'scope', {}))
            }
            
        # Handle dictionaries (including MongoDB documents)
        elif isinstance(obj, dict):
            # Special handling for MongoDB JSON format
            if "$oid" in obj and len(obj) == 1:
                return obj["$oid"]  # Return the string directly for simple ObjectId representations
            elif "$date" in obj and len(obj) == 1:
                return obj["$date"]  # Return the date string directly
            else:
                # Recursively process all key-value pairs
                result = {}
                for key, value in obj.items():
                    # Handle keys that might be ObjectIds (though unusual)
                    clean_key = str(key) if isinstance(key, ObjectId) else key
                    result[clean_key] = convert_objectids_to_strings(value)
                return result
                
        # Handle lists and tuples
        elif isinstance(obj, (list, tuple)):
            return [convert_objectids_to_strings(item) for item in obj]
            
        # Handle sets
        elif isinstance(obj, set):
            return [convert_objectids_to_strings(item) for item in obj]
            
        # Handle enums
        elif isinstance(obj, Enum):
            return convert_objectids_to_strings(obj.value)
            
        # Handle objects with __dict__ (custom classes)
        elif hasattr(obj, '__dict__'):
            return convert_objectids_to_strings(obj.__dict__)
            
        # Handle other iterables (but not strings)
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
            try:
                return [convert_objectids_to_strings(item) for item in obj]
            except (TypeError, ValueError):
                # If iteration fails, convert to string
                return str(obj)
                
        else:
            # Final fallback - try JSON serialization test
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                # If it can't be serialized, convert to string
                return str(obj)
                
    except Exception as e:
        # Ultimate fallback: convert to string with error info for debugging
        return f"<serialization_error: {str(obj)[:100]}>"

def serialize_mongodb_response(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Main entry point for MongoDB response serialization.
    
    This function:
    1. Converts all MongoDB types to JSON-serializable formats
    2. Handles nested structures recursively
    3. Preserves original data structure
    4. Provides comprehensive error handling
    
    Args:
        data: Any MongoDB document, list, or data structure
        
    Returns:
        JSON-serializable version of the input data
    """
    try:
        # Use the comprehensive converter
        return convert_objectids_to_strings(data)
    except Exception as e:
        # Multi-layer fallback approach
        try:
            # Try using the JSON encoder as a fallback
            return json.loads(json.dumps(data, cls=MongoJSONEncoder))
        except Exception as e2:
            # Final fallback - convert entire structure using default string conversion
            try:
                return json.loads(json.dumps(data, default=str))
            except Exception as e3:
                # Absolute last resort - return error structure
                return {
                    "serialization_error": True,
                    "original_type": str(type(data)),
                    "error_message": str(e3),
                    "data_preview": str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                }

def serialize_field_analysis(field_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Specialized serialization for field analysis data structures.
    
    Field analysis often contains:
    - Sets of data types
    - Sample values with ObjectIds
    - Mixed data type lists
    - Count statistics
    """
    try:
        serialized = {}
        for field_name, analysis in field_analysis.items():
            serialized_analysis = {}
            
            for key, value in analysis.items():
                if key == "data_types" and isinstance(value, set):
                    # Convert set to sorted list for consistency
                    serialized_analysis[key] = sorted(list(value))
                elif key == "sample_values" and isinstance(value, list):
                    # Serialize each sample value
                    serialized_analysis[key] = [
                        convert_objectids_to_strings(sample) for sample in value
                    ]
                else:
                    # Standard serialization for other fields
                    serialized_analysis[key] = convert_objectids_to_strings(value)
                    
            serialized[field_name] = serialized_analysis
            
        return serialized
    except Exception as e:
        # Fallback to standard serialization
        return convert_objectids_to_strings(field_analysis)

def create_mongodb_compatible_response(
    success: bool,
    message: str,
    data: Any = None,
    request_id: str = None,
    errors: List[Dict] = None
) -> Dict[str, Any]:
    """
    Create a standardized response structure that's guaranteed to be JSON-serializable.
    
    This function ensures that all MongoDB-specific types are properly converted
    before creating the response structure.
    """
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if data is not None:
        response["data"] = serialize_mongodb_response(data)
        
    if request_id:
        response["request_id"] = request_id
        
    if errors:
        response["errors"] = serialize_mongodb_response(errors)
        response["error_count"] = len(errors)
        
    return response 