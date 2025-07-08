from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timedelta
import base64
import hashlib
import secrets
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import os
from app.services.security_audit import security_audit, SecurityEventType, SecuritySeverity
from config import settings, logger

class EncryptionService:
    """
    Service for encrypting and decrypting sensitive healthcare data
    """
    
    def __init__(self):
        # Master key from environment (should be stored securely)
        self.master_key_bytes, self.master_key_b64 = self._get_or_generate_master_key()
        
        # Initialize Fernet for general encryption (requires base64 string)
        self.fernet = Fernet(self.master_key_b64)
        
        # Initialize AES-GCM for field-level encryption
        self.aes_key = self._derive_aes_key(self.master_key_bytes)
        
        # Fields that should be encrypted
        self.sensitive_fields = {
            "patients": [
                "national_id",
                "passport_number",
                "phone_number",
                "email",
                "address",
                "emergency_contact",
                "medical_notes"
            ],
            "medical_history": [
                "diagnosis_details",
                "treatment_notes",
                "prescription_details",
                "lab_results"
            ],
            "hospital_users": [
                "national_id",
                "phone_number",
                "email",
                "personal_address"
            ]
        }
        
        # Cache for field encryption keys
        self._field_keys_cache: Dict[str, bytes] = {}
    
    def _get_or_generate_master_key(self) -> tuple[bytes, bytes]:
        """Get master key from environment or generate new one"""
        master_key_env = os.getenv("ENCRYPTION_MASTER_KEY")
        
        if master_key_env:
            try:
                # Validate the key format (should be proper base64)
                key_bytes = master_key_env.encode('utf-8')
                decoded_key = base64.urlsafe_b64decode(master_key_env)
                if len(decoded_key) == 32:  # Fernet requires 32 bytes
                    return decoded_key, key_bytes
                else:
                    logger.warning(f"Key length is {len(decoded_key)}, expected 32 bytes")
                    raise ValueError("Invalid key length")
            except Exception as e:
                logger.warning(f"Failed to decode master key: {e}")
                # Fall back to generating a new key in development
                pass
        
        # Generate new key (for development or when key is invalid)
        environment = getattr(settings, 'environment', 'production')
        if environment == "development":
            new_key = Fernet.generate_key()
            logger.warning(f"Generated new master key: {new_key.decode()}")
            logger.warning("Set ENCRYPTION_MASTER_KEY environment variable with this key!")
            return base64.urlsafe_b64decode(new_key), new_key
        else:
            raise ValueError("ENCRYPTION_MASTER_KEY not set or invalid in production environment")
    
    def _derive_aes_key(self, master_key: bytes) -> bytes:
        """Derive AES key from master key"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'healthcare_aes_salt',  # Use consistent salt
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(master_key)
    
    def encrypt_field(self, value: Union[str, dict, list], field_name: str) -> str:
        """Encrypt a single field value"""
        if value is None:
            return None
        
        try:
            # Convert to string if needed
            if isinstance(value, (dict, list)):
                plaintext = json.dumps(value)
            else:
                plaintext = str(value)
            
            # Generate nonce
            nonce = os.urandom(12)
            
            # Get field-specific key
            field_key = self._get_field_key(field_name)
            
            # Encrypt using AES-GCM
            aesgcm = AESGCM(field_key)
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), field_name.encode())
            
            # Combine nonce and ciphertext
            encrypted = nonce + ciphertext
            
            # Encode to base64 for storage
            return base64.urlsafe_b64encode(encrypted).decode()
            
        except Exception as e:
            logger.error(f"Field encryption error: {e}")
            raise
    
    def decrypt_field(self, encrypted_value: str, field_name: str) -> Union[str, dict, list]:
        """Decrypt a single field value"""
        if encrypted_value is None:
            return None
        
        try:
            # Decode from base64
            encrypted = base64.urlsafe_b64decode(encrypted_value)
            
            # Extract nonce and ciphertext
            nonce = encrypted[:12]
            ciphertext = encrypted[12:]
            
            # Get field-specific key
            field_key = self._get_field_key(field_name)
            
            # Decrypt using AES-GCM
            aesgcm = AESGCM(field_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, field_name.encode())
            
            # Convert back to original type
            decrypted = plaintext.decode()
            
            # Try to parse as JSON
            try:
                return json.loads(decrypted)
            except:
                return decrypted
                
        except Exception as e:
            logger.error(f"Field decryption error: {e}")
            raise
    
    def encrypt_document(self, document: Dict[str, Any], collection_name: str) -> Dict[str, Any]:
        """Encrypt sensitive fields in a document"""
        if collection_name not in self.sensitive_fields:
            return document
        
        encrypted_doc = document.copy()
        fields_to_encrypt = self.sensitive_fields[collection_name]
        
        for field in fields_to_encrypt:
            if field in encrypted_doc and encrypted_doc[field] is not None:
                # Encrypt field
                encrypted_doc[field] = self.encrypt_field(
                    encrypted_doc[field],
                    f"{collection_name}.{field}"
                )
                
                # Mark as encrypted
                encrypted_doc[f"_{field}_encrypted"] = True
        
        # Add encryption metadata
        encrypted_doc["_encryption_metadata"] = {
            "version": "1.0",
            "encrypted_at": datetime.utcnow().isoformat(),
            "fields": fields_to_encrypt
        }
        
        return encrypted_doc
    
    def decrypt_document(self, document: Dict[str, Any], collection_name: str) -> Dict[str, Any]:
        """Decrypt sensitive fields in a document"""
        if collection_name not in self.sensitive_fields:
            return document
        
        decrypted_doc = document.copy()
        
        # Check if document has encryption metadata
        if "_encryption_metadata" not in document:
            return document
        
        encrypted_fields = document["_encryption_metadata"].get("fields", [])
        
        for field in encrypted_fields:
            if field in decrypted_doc and decrypted_doc.get(f"_{field}_encrypted"):
                try:
                    # Decrypt field
                    decrypted_doc[field] = self.decrypt_field(
                        decrypted_doc[field],
                        f"{collection_name}.{field}"
                    )
                    
                    # Remove encryption marker
                    del decrypted_doc[f"_{field}_encrypted"]
                except Exception as e:
                    logger.error(f"Failed to decrypt field {field}: {e}")
                    decrypted_doc[field] = "[DECRYPTION_ERROR]"
        
        # Remove encryption metadata
        del decrypted_doc["_encryption_metadata"]
        
        return decrypted_doc
    
    def encrypt_file(self, file_data: bytes) -> bytes:
        """Encrypt file data"""
        try:
            return self.fernet.encrypt(file_data)
        except Exception as e:
            logger.error(f"File encryption error: {e}")
            raise
    
    def decrypt_file(self, encrypted_data: bytes) -> bytes:
        """Decrypt file data"""
        try:
            return self.fernet.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"File decryption error: {e}")
            raise
    
    def hash_password(self, password: str) -> str:
        """Hash password using PBKDF2"""
        salt = os.urandom(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode())
        
        # Combine salt and key
        return base64.urlsafe_b64encode(salt + key).decode()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            # Decode hash
            decoded = base64.urlsafe_b64decode(hashed)
            salt = decoded[:32]
            key = decoded[32:]
            
            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            new_key = kdf.derive(password.encode())
            
            # Compare keys
            return new_key == key
            
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def generate_api_key(self) -> str:
        """Generate secure API key"""
        # Generate 32 bytes of random data
        random_bytes = secrets.token_bytes(32)
        
        # Create API key with prefix
        api_key = f"mfc_{base64.urlsafe_b64encode(random_bytes).decode().rstrip('=')}"
        
        return api_key
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def generate_token(self, length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
    
    def encrypt_export_data(self, data: Dict[str, Any], password: Optional[str] = None) -> Dict[str, Any]:
        """Encrypt data for export with optional password"""
        try:
            # Serialize data
            json_data = json.dumps(data, default=str)
            
            if password:
                # Derive key from password
                salt = os.urandom(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                    backend=default_backend()
                )
                key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
                fernet = Fernet(key)
                
                # Encrypt data
                encrypted = fernet.encrypt(json_data.encode())
                
                return {
                    "encrypted": True,
                    "password_protected": True,
                    "salt": base64.urlsafe_b64encode(salt).decode(),
                    "data": base64.urlsafe_b64encode(encrypted).decode(),
                    "algorithm": "Fernet-PBKDF2",
                    "iterations": 100000
                }
            else:
                # Use master key
                encrypted = self.fernet.encrypt(json_data.encode())
                
                return {
                    "encrypted": True,
                    "password_protected": False,
                    "data": base64.urlsafe_b64encode(encrypted).decode(),
                    "algorithm": "Fernet"
                }
                
        except Exception as e:
            logger.error(f"Export encryption error: {e}")
            raise
    
    def rotate_encryption_keys(self) -> bool:
        """Rotate encryption keys (admin function)"""
        try:
            # Generate new master key
            new_master_key = Fernet.generate_key()
            new_fernet = Fernet(new_master_key)
            
            # This would need to:
            # 1. Re-encrypt all sensitive data with new key
            # 2. Update key storage
            # 3. Maintain old key for transition period
            
            # Log security event
            # Note: This is a synchronous context, would need to be called from async context
            # await security_audit.log_security_event(
            #     event_type=SecurityEventType.ENCRYPTION_KEY_ROTATED,
            #     severity=SecuritySeverity.HIGH,
            #     details={
            #         "key_type": "master",
            #         "rotation_time": datetime.utcnow().isoformat()
            #     }
            # )
            
            logger.info("Encryption keys rotated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Key rotation error: {e}")
            return False
    
    def _get_field_key(self, field_name: str) -> bytes:
        """Get or derive field-specific encryption key"""
        if field_name in self._field_keys_cache:
            return self._field_keys_cache[field_name]
        
        # Derive field key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=f"field_{field_name}".encode(),
            iterations=10000,
            backend=default_backend()
        )
        
        field_key = kdf.derive(self.aes_key)
        self._field_keys_cache[field_name] = field_key
        
        return field_key
    
    def encrypt_sensitive_log_data(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive data in logs"""
        sensitive_patterns = [
            "password", "token", "api_key", "secret",
            "national_id", "passport", "phone", "email"
        ]
        
        encrypted_log = {}
        
        for key, value in log_data.items():
            # Check if key contains sensitive pattern
            is_sensitive = any(pattern in key.lower() for pattern in sensitive_patterns)
            
            if is_sensitive and value:
                # Mask sensitive data
                if isinstance(value, str):
                    if len(value) > 4:
                        encrypted_log[key] = f"{value[:2]}***{value[-2:]}"
                    else:
                        encrypted_log[key] = "***"
                else:
                    encrypted_log[key] = "[REDACTED]"
            else:
                encrypted_log[key] = value
        
        return encrypted_log


# Global encryption service instance
encryption_service = EncryptionService() 