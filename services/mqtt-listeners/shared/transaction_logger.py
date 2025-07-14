"""
Transaction Logging Service
Handles logging of data processing transactions to the Stardust API
"""

import os
import logging
import requests
import json
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class TransactionLogger:
    """Logs transactions to the Stardust API"""
    
    def __init__(self):
        # Stardust API configuration
        self.api_url = os.getenv('STARDUST_API_URL', 'https://stardust.my-firstcare.com')
        self.api_base_url = f"{self.api_url}/api/transactions"
        
        # Authentication (if needed)
        self.auth_token = os.getenv('STARDUST_AUTH_TOKEN', None)
        
    def log_transaction(self, operation: str, data_type: str, collection: str, 
                       patient_id: Optional[str] = None, details: Optional[str] = None, 
                       device_id: Optional[str] = None, status: str = "success") -> bool:
        """Log a transaction to the Stardust API"""
        try:
            # Prepare transaction data
            transaction_data = {
                "operation": operation,
                "data_type": data_type,
                "collection": collection,
                "patient_id": patient_id,
                "status": status,
                "details": details,
                "device_id": device_id
            }
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "MQTT-Listener/1.0"
            }
            
            # Add authentication if available
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Make API call
            response = requests.post(
                f"{self.api_base_url}/log",
                json=transaction_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info(f"Logged transaction: {operation} - {data_type}")
                    return True
                else:
                    logger.warning(f"Transaction logging failed: {result.get('message', 'Unknown error')}")
                    return False
            else:
                logger.warning(f"Transaction logging failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to log transaction: {e}")
            return False
    
    def log_data_storage(self, patient_id: str, data_type: str, collection: str, 
                        device_id: Optional[str] = None, details: Optional[str] = None) -> bool:
        """Log data storage transaction"""
        return self.log_transaction(
            operation="data_storage",
            data_type=data_type,
            collection=collection,
            patient_id=patient_id,
            device_id=device_id,
            details=details
        )
    
    def log_data_update(self, patient_id: str, data_type: str, collection: str, 
                       device_id: Optional[str] = None, details: Optional[str] = None) -> bool:
        """Log data update transaction"""
        return self.log_transaction(
            operation="data_update",
            data_type=data_type,
            collection=collection,
            patient_id=patient_id,
            device_id=device_id,
            details=details
        )
    
    def log_device_data(self, device_id: str, data_type: str, collection: str, 
                       patient_id: Optional[str] = None, details: Optional[str] = None) -> bool:
        """Log device data processing transaction"""
        return self.log_transaction(
            operation="device_data_processing",
            data_type=data_type,
            collection=collection,
            patient_id=patient_id,
            device_id=device_id,
            details=details
        ) 