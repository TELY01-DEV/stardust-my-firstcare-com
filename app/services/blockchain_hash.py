"""
Blockchain Hash Service for FHIR Resources
=========================================
Provides cryptographic hash generation and verification for FHIR resources
to ensure data integrity, immutability, and blockchain-style audit trails.

Features:
- SHA-256 based resource hashing
- Merkle tree construction for batched resources
- Hash chain verification for immutable audit trails  
- Digital signature support for resource authentication
- Integrity verification and tamper detection
- Comprehensive audit logging integration
"""

import hashlib
import json
import uuid
import time
import psutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from app.utils.structured_logging import get_logger

logger = get_logger(__name__)

@dataclass
class BlockchainHash:
    """Blockchain hash metadata for FHIR resources"""
    resource_hash: str
    previous_hash: Optional[str]
    timestamp: str
    nonce: str
    merkle_root: Optional[str]
    block_height: int
    signature: Optional[str]
    
@dataclass
class HashVerificationResult:
    """Result of hash verification"""
    is_valid: bool
    current_hash: str
    stored_hash: str
    tampered: bool
    message: str
    timestamp: str

class BlockchainHashService:
    """Service for generating and verifying blockchain hashes for FHIR resources"""
    
    def __init__(self):
        self.hash_algorithm = "sha256"
        self.hash_chain: List[str] = []
        self.genesis_hash = self._generate_genesis_hash()
        self._audit_service = None
        
    @property
    def audit_service(self):
        """Lazy load audit service to avoid circular imports"""
        if self._audit_service is None:
            try:
                from app.services.hash_audit_log import (
                    hash_audit_service, HashAuditOperation, HashAuditStatus, 
                    HashAuditSeverity, HashAuditMetrics, HashAuditContext
                )
                self._audit_service = hash_audit_service
                self.HashAuditOperation = HashAuditOperation
                self.HashAuditStatus = HashAuditStatus
                self.HashAuditSeverity = HashAuditSeverity
                self.HashAuditMetrics = HashAuditMetrics
                self.HashAuditContext = HashAuditContext
            except ImportError:
                logger.warning("Hash audit service not available")
                self._audit_service = None
        return self._audit_service
        
    def _generate_genesis_hash(self) -> str:
        """Generate the genesis hash for the blockchain"""
        genesis_data = {
            "resourceType": "Genesis",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "description": "FHIR R5 Blockchain Genesis Block"
        }
        return self._compute_hash(genesis_data)
    
    def _compute_hash(self, data: Any) -> str:
        """Compute SHA-256 hash of the given data"""
        try:
            # Convert data to deterministic JSON string
            if isinstance(data, dict):
                # Sort keys for deterministic hashing
                json_string = json.dumps(data, sort_keys=True, separators=(',', ':'))
            else:
                json_string = str(data)
            
            # Compute SHA-256 hash
            hash_object = hashlib.sha256(json_string.encode('utf-8'))
            return hash_object.hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to compute hash: {e}")
            raise
    
    def _normalize_fhir_resource(self, resource_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize FHIR resource for consistent hashing"""
        # Create a copy to avoid modifying original
        normalized = dict(resource_data)
        
        # Remove fields that shouldn't affect the hash
        fields_to_exclude = [
            'meta.lastUpdated',
            # Keep meta.versionId for audit logging - it's important for tracking
            'blockchain_hash',
            'blockchain_signature',
            'blockchain_timestamp'
        ]
        
        for field_path in fields_to_exclude:
            self._remove_nested_field(normalized, field_path)
        
        # Ensure consistent timestamp format
        if 'meta' in normalized and 'lastUpdated' in normalized['meta']:
            del normalized['meta']['lastUpdated']
            
        return normalized
    
    def _remove_nested_field(self, data: Dict[str, Any], field_path: str):
        """Remove nested field using dot notation"""
        keys = field_path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key in current and isinstance(current[key], dict):
                current = current[key]
            else:
                return
        
        if keys[-1] in current:
            del current[keys[-1]]
    
    async def generate_resource_hash(
        self,
        resource_data: Dict[str, Any],
        previous_hash: Optional[str] = None,
        include_merkle: bool = False,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        audit_context: Optional[Dict[str, Any]] = None
    ) -> BlockchainHash:
        """Generate blockchain hash for a FHIR resource with audit logging"""
        start_time = time.time()
        hash_computation_start = None
        
        try:
            # Normalize resource for consistent hashing
            normalized_resource = self._normalize_fhir_resource(resource_data)
            
            # Generate nonce for uniqueness
            nonce = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Use previous hash or genesis hash
            if previous_hash is None:
                previous_hash = self.get_latest_hash()
            
            # Create hash input structure
            hash_input = {
                "resource": normalized_resource,
                "previous_hash": previous_hash,
                "timestamp": timestamp,
                "nonce": nonce
            }
            
            # Compute resource hash with timing
            hash_computation_start = time.time()
            resource_hash = self._compute_hash(hash_input)
            hash_computation_time = (time.time() - hash_computation_start) * 1000
            
            # Generate Merkle root if requested
            merkle_root = None
            if include_merkle:
                merkle_root = self._compute_merkle_root([resource_hash])
            
            # Get block height
            chain_length_before = len(self.hash_chain)
            block_height = chain_length_before + 1
            
            # Create blockchain hash object
            blockchain_hash = BlockchainHash(
                resource_hash=resource_hash,
                previous_hash=previous_hash,
                timestamp=timestamp,
                nonce=nonce,
                merkle_root=merkle_root,
                block_height=block_height,
                signature=None  # To be added if digital signatures are needed
            )
            
            # Add to hash chain
            self.hash_chain.append(resource_hash)
            
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging
            if self.audit_service:
                try:
                    # Get system metrics
                    process = psutil.Process()
                    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                    cpu_usage = process.cpu_percent()
                    
                    # Create audit metrics
                    metrics = self.HashAuditMetrics(
                        execution_time_ms=execution_time,
                        hash_computation_time_ms=hash_computation_time,
                        resources_processed=1,
                        hashes_generated=1,
                        chain_length_before=chain_length_before,
                        chain_length_after=len(self.hash_chain),
                        memory_usage_mb=memory_usage,
                        cpu_usage_percent=cpu_usage
                    )
                    
                    # Create audit context
                    context = self.HashAuditContext(
                        fhir_resource_type=resource_data.get('resourceType'),
                        fhir_resource_id=resource_data.get('id'),
                        fhir_resource_version=resource_data.get('meta', {}).get('versionId'),
                        source_system=audit_context.get('source_system') if audit_context else None,
                        source_ip=audit_context.get('source_ip') if audit_context else None,
                        user_agent=audit_context.get('user_agent') if audit_context else None,
                        session_id=audit_context.get('session_id') if audit_context else None,
                        batch_id=audit_context.get('batch_id') if audit_context else None
                    )
                    
                    # Extract patient/organization/device IDs for indexing
                    if 'subject' in resource_data and 'reference' in resource_data['subject']:
                        subject_ref = resource_data['subject']['reference']
                        if subject_ref.startswith('Patient/'):
                            context.patient_id = subject_ref.replace('Patient/', '')
                    
                    # Extract organization ID for Organization resources or from references
                    if resource_data.get('resourceType') == 'Organization':
                        context.organization_id = resource_data.get('id')
                    elif 'managingOrganization' in resource_data and 'reference' in resource_data['managingOrganization']:
                        org_ref = resource_data['managingOrganization']['reference']
                        if org_ref.startswith('Organization/'):
                            context.organization_id = org_ref.replace('Organization/', '')
                    
                    # Extract device ID from Device resources or references
                    if resource_data.get('resourceType') == 'Device':
                        context.device_id = resource_data.get('id')
                    elif 'device' in resource_data and 'reference' in resource_data['device']:
                        device_ref = resource_data['device']['reference']
                        if device_ref.startswith('Device/'):
                            context.device_id = device_ref.replace('Device/', '')
                    
                    # Extract encounter ID from references
                    if 'encounter' in resource_data and 'reference' in resource_data['encounter']:
                        encounter_ref = resource_data['encounter']['reference']
                        if encounter_ref.startswith('Encounter/'):
                            context.encounter_id = encounter_ref.replace('Encounter/', '')
                    
                    # Log hash generation
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.HASH_GENERATE,
                        status=self.HashAuditStatus.SUCCESS,
                        blockchain_hash=resource_hash,
                        previous_hash=previous_hash,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Generated blockchain hash for {resource_data.get('resourceType', 'Unknown')} resource",
                        metrics=metrics,
                        context=context,
                        severity=self.HashAuditSeverity.LOW,
                        additional_data={
                            "block_height": block_height,
                            "merkle_root": merkle_root,
                            "nonce": nonce,
                            "include_merkle": include_merkle
                        }
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log hash generation audit: {audit_e}")
            
            logger.info(f"Generated blockchain hash: {resource_hash[:16]}... for resource type: {resource_data.get('resourceType', 'Unknown')}")
            
            return blockchain_hash
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging for failure
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(execution_time_ms=execution_time)
                    context = self.HashAuditContext(
                        fhir_resource_type=resource_data.get('resourceType'),
                        fhir_resource_id=resource_data.get('id')
                    )
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.HASH_GENERATE,
                        status=self.HashAuditStatus.FAILURE,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Failed to generate blockchain hash: {str(e)}",
                        error_details={"error": str(e), "error_type": type(e).__name__},
                        metrics=metrics,
                        context=context,
                        severity=self.HashAuditSeverity.HIGH
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log hash generation failure audit: {audit_e}")
            
            logger.error(f"Failed to generate resource hash: {e}")
            raise
    
    async def verify_resource_integrity(
        self,
        resource_data: Dict[str, Any],
        stored_hash: str,
        previous_hash: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        audit_context: Optional[Dict[str, Any]] = None
    ) -> HashVerificationResult:
        """Verify the integrity of a FHIR resource using its hash with audit logging"""
        start_time = time.time()
        verification_start = None
        
        try:
            # Normalize resource for comparison
            normalized_resource = self._normalize_fhir_resource(resource_data)
            
            # Extract original hash components if available
            original_nonce = resource_data.get('meta', {}).get('blockchain_nonce')
            original_timestamp = resource_data.get('meta', {}).get('blockchain_timestamp')
            
            if not original_nonce or not original_timestamp:
                result = HashVerificationResult(
                    is_valid=False,
                    current_hash="",
                    stored_hash=stored_hash,
                    tampered=True,
                    message="Missing blockchain metadata for verification",
                    timestamp=datetime.utcnow().isoformat() + "Z"
                )
                
                # Audit logging for missing metadata
                if self.audit_service:
                    try:
                        execution_time = (time.time() - start_time) * 1000
                        metrics = self.HashAuditMetrics(
                            execution_time_ms=execution_time,
                            resources_processed=1
                        )
                        context = self.HashAuditContext(
                            fhir_resource_type=resource_data.get('resourceType'),
                            fhir_resource_id=resource_data.get('id')
                        )
                        
                        await self.audit_service.log_hash_operation(
                            operation_type=self.HashAuditOperation.HASH_VERIFY,
                            status=self.HashAuditStatus.WARNING,
                            blockchain_hash=stored_hash,
                            user_id=user_id,
                            request_id=request_id,
                            message="Resource verification failed: missing blockchain metadata",
                            metrics=metrics,
                            context=context,
                            severity=self.HashAuditSeverity.MEDIUM
                        )
                    except Exception as audit_e:
                        logger.warning(f"Failed to log verification warning audit: {audit_e}")
                
                return result
            
            # Recreate hash input
            hash_input = {
                "resource": normalized_resource,
                "previous_hash": previous_hash,
                "timestamp": original_timestamp,
                "nonce": original_nonce
            }
            
            # Compute current hash with timing
            verification_start = time.time()
            current_hash = self._compute_hash(hash_input)
            verification_time = (time.time() - verification_start) * 1000
            
            # Compare hashes
            is_valid = current_hash == stored_hash
            tampered = not is_valid
            
            message = "Resource integrity verified" if is_valid else "Resource has been tampered with"
            
            result = HashVerificationResult(
                is_valid=is_valid,
                current_hash=current_hash,
                stored_hash=stored_hash,
                tampered=tampered,
                message=message,
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(
                        execution_time_ms=execution_time,
                        verification_time_ms=verification_time,
                        resources_processed=1,
                        hashes_verified=1
                    )
                    
                    context = self.HashAuditContext(
                        fhir_resource_type=resource_data.get('resourceType'),
                        fhir_resource_id=resource_data.get('id'),
                        fhir_resource_version=resource_data.get('meta', {}).get('versionId'),
                        source_system=audit_context.get('source_system') if audit_context else None,
                        source_ip=audit_context.get('source_ip') if audit_context else None,
                        user_agent=audit_context.get('user_agent') if audit_context else None,
                        session_id=audit_context.get('session_id') if audit_context else None
                    )
                    
                    status = self.HashAuditStatus.SUCCESS if is_valid else self.HashAuditStatus.FAILURE
                    severity = self.HashAuditSeverity.LOW if is_valid else self.HashAuditSeverity.CRITICAL
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.HASH_VERIFY,
                        status=status,
                        blockchain_hash=stored_hash,
                        previous_hash=previous_hash,
                        user_id=user_id,
                        request_id=request_id,
                        message=message,
                        metrics=metrics,
                        context=context,
                        severity=severity,
                        additional_data={
                            "computed_hash": current_hash,
                            "stored_hash": stored_hash,
                            "hashes_match": is_valid,
                            "tampered": tampered,
                            "original_nonce": original_nonce,
                            "original_timestamp": original_timestamp
                        }
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log verification audit: {audit_e}")
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging for failure
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(execution_time_ms=execution_time)
                    context = self.HashAuditContext(
                        fhir_resource_type=resource_data.get('resourceType'),
                        fhir_resource_id=resource_data.get('id')
                    )
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.HASH_VERIFY,
                        status=self.HashAuditStatus.FAILURE,
                        blockchain_hash=stored_hash,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Hash verification failed: {str(e)}",
                        error_details={"error": str(e), "error_type": type(e).__name__},
                        metrics=metrics,
                        context=context,
                        severity=self.HashAuditSeverity.HIGH
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log verification failure audit: {audit_e}")
            
            logger.error(f"Failed to verify resource integrity: {e}")
            return HashVerificationResult(
                is_valid=False,
                current_hash="",
                stored_hash=stored_hash,
                tampered=True,
                message=f"Verification failed: {str(e)}",
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
    
    def _compute_merkle_root(self, hashes: List[str]) -> str:
        """Compute Merkle root for a list of hashes"""
        if not hashes:
            return ""
        
        if len(hashes) == 1:
            return hashes[0]
        
        # Ensure even number of hashes
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])
        
        # Compute next level
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            next_level.append(self._compute_hash(combined))
        
        return self._compute_merkle_root(next_level)
    
    async def generate_batch_hash(
        self,
        resources: List[Dict[str, Any]],
        batch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        audit_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[BlockchainHash]]:
        """Generate blockchain hashes for a batch of resources with audit logging"""
        start_time = time.time()
        
        try:
            if not resources:
                raise ValueError("Cannot generate batch hash for empty resource list")
            
            batch_id = batch_id or str(uuid.uuid4())
            resource_hashes = []
            blockchain_hashes = []
            
            # Generate hash for each resource
            previous_hash = self.get_latest_hash()
            
            for resource in resources:
                blockchain_hash = await self.generate_resource_hash(
                    resource, 
                    previous_hash,
                    user_id=user_id,
                    request_id=request_id,
                    audit_context=audit_context
                )
                resource_hashes.append(blockchain_hash.resource_hash)
                blockchain_hashes.append(blockchain_hash)
                previous_hash = blockchain_hash.resource_hash
            
            # Compute Merkle root for the batch
            merkle_root = self._compute_merkle_root(resource_hashes)
            
            # Update blockchain hashes with Merkle root
            for blockchain_hash in blockchain_hashes:
                blockchain_hash.merkle_root = merkle_root
            
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging for batch operation
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(
                        execution_time_ms=execution_time,
                        resources_processed=len(resources),
                        hashes_generated=len(resource_hashes)
                    )
                    
                    context = self.HashAuditContext(
                        batch_id=batch_id,
                        batch_size=len(resources),
                        source_system=audit_context.get('source_system') if audit_context else None,
                        source_ip=audit_context.get('source_ip') if audit_context else None,
                        user_agent=audit_context.get('user_agent') if audit_context else None,
                        session_id=audit_context.get('session_id') if audit_context else None
                    )
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.BATCH_GENERATE,
                        status=self.HashAuditStatus.SUCCESS,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Generated batch hash for {len(resources)} resources",
                        metrics=metrics,
                        context=context,
                        severity=self.HashAuditSeverity.LOW,
                        additional_data={
                            "batch_id": batch_id,
                            "merkle_root": merkle_root,
                            "resource_types": [r.get('resourceType') for r in resources]
                        }
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log batch generation audit: {audit_e}")
            
            logger.info(f"Generated batch hash for {len(resources)} resources. Merkle root: {merkle_root[:16]}...")
            
            return merkle_root, blockchain_hashes
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging for failure
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(execution_time_ms=execution_time)
                    context = self.HashAuditContext(
                        batch_id=batch_id,
                        batch_size=len(resources) if resources else 0
                    )
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.BATCH_GENERATE,
                        status=self.HashAuditStatus.FAILURE,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Failed to generate batch hash: {str(e)}",
                        error_details={"error": str(e), "error_type": type(e).__name__},
                        metrics=metrics,
                        context=context,
                        severity=self.HashAuditSeverity.HIGH
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log batch generation failure audit: {audit_e}")
            
            logger.error(f"Failed to generate batch hash: {e}")
            raise
    
    def get_latest_hash(self) -> str:
        """Get the latest hash in the chain"""
        return self.hash_chain[-1] if self.hash_chain else self.genesis_hash
    
    async def verify_hash_chain(
        self, 
        start_index: int = 0,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify the integrity of the hash chain with audit logging"""
        start_time = time.time()
        
        try:
            if start_index >= len(self.hash_chain):
                result = {"valid": True, "message": "No hashes to verify"}
            else:
                invalid_hashes = []
                
                for i in range(start_index, len(self.hash_chain)):
                    current_hash = self.hash_chain[i]
                    
                    # Verify hash format
                    if not self._is_valid_hash_format(current_hash):
                        invalid_hashes.append({
                            "index": i,
                            "hash": current_hash,
                            "reason": "Invalid hash format"
                        })
                
                is_valid = len(invalid_hashes) == 0
                
                result = {
                    "valid": is_valid,
                    "chain_length": len(self.hash_chain),
                    "verified_count": len(self.hash_chain) - len(invalid_hashes),
                    "invalid_hashes": invalid_hashes,
                    "message": "Hash chain verified" if is_valid else f"Found {len(invalid_hashes)} invalid hashes"
                }
            
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(
                        execution_time_ms=execution_time,
                        hashes_verified=len(self.hash_chain) - start_index,
                        chain_length_before=len(self.hash_chain)
                    )
                    
                    status = self.HashAuditStatus.SUCCESS if result["valid"] else self.HashAuditStatus.WARNING
                    severity = self.HashAuditSeverity.LOW if result["valid"] else self.HashAuditSeverity.HIGH
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.CHAIN_VERIFY,
                        status=status,
                        user_id=user_id,
                        request_id=request_id,
                        message=result["message"],
                        metrics=metrics,
                        severity=severity,
                        additional_data={
                            "start_index": start_index,
                            "chain_length": result.get("chain_length"),
                            "verified_count": result.get("verified_count"),
                            "invalid_count": len(result.get("invalid_hashes", []))
                        }
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log chain verification audit: {audit_e}")
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging for failure
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(execution_time_ms=execution_time)
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.CHAIN_VERIFY,
                        status=self.HashAuditStatus.FAILURE,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Chain verification failed: {str(e)}",
                        error_details={"error": str(e), "error_type": type(e).__name__},
                        metrics=metrics,
                        severity=self.HashAuditSeverity.CRITICAL
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log chain verification failure audit: {audit_e}")
            
            logger.error(f"Failed to verify hash chain: {e}")
            return {
                "valid": False,
                "message": f"Hash chain verification failed: {str(e)}"
            }
    
    def _is_valid_hash_format(self, hash_value: str) -> bool:
        """Verify if a hash has valid SHA-256 format"""
        return (
            isinstance(hash_value, str) and
            len(hash_value) == 64 and
            all(c in '0123456789abcdef' for c in hash_value.lower())
        )
    
    def get_hash_chain_info(self) -> Dict[str, Any]:
        """Get information about the current hash chain"""
        return {
            "genesis_hash": self.genesis_hash,
            "chain_length": len(self.hash_chain),
            "latest_hash": self.get_latest_hash(),
            "hash_algorithm": self.hash_algorithm,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    
    async def export_hash_chain(
        self,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export the complete hash chain for backup or analysis with audit logging"""
        start_time = time.time()
        
        try:
            export_data = {
                "genesis_hash": self.genesis_hash,
                "hash_chain": self.hash_chain.copy(),
                "chain_info": self.get_hash_chain_info(),
                "exported_at": datetime.utcnow().isoformat() + "Z"
            }
            
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(
                        execution_time_ms=execution_time,
                        chain_length_before=len(self.hash_chain)
                    )
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.CHAIN_EXPORT,
                        status=self.HashAuditStatus.SUCCESS,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Exported hash chain with {len(self.hash_chain)} hashes",
                        metrics=metrics,
                        severity=self.HashAuditSeverity.MEDIUM,  # Export is medium severity for security
                        additional_data={
                            "exported_hash_count": len(self.hash_chain),
                            "genesis_hash": self.genesis_hash,
                            "export_size_bytes": len(json.dumps(export_data))
                        }
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log chain export audit: {audit_e}")
            
            return export_data
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging for failure
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(execution_time_ms=execution_time)
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.CHAIN_EXPORT,
                        status=self.HashAuditStatus.FAILURE,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Failed to export hash chain: {str(e)}",
                        error_details={"error": str(e), "error_type": type(e).__name__},
                        metrics=metrics,
                        severity=self.HashAuditSeverity.HIGH
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log chain export failure audit: {audit_e}")
            
            logger.error(f"Failed to export hash chain: {e}")
            raise
    
    async def import_hash_chain(
        self, 
        chain_data: Dict[str, Any],
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> bool:
        """Import a hash chain from backup with audit logging"""
        start_time = time.time()
        
        try:
            if "genesis_hash" not in chain_data or "hash_chain" not in chain_data:
                raise ValueError("Invalid chain data format")
            
            # Verify imported chain integrity
            imported_genesis = chain_data["genesis_hash"]
            imported_chain = chain_data["hash_chain"]
            
            # Validate all hashes
            for hash_value in [imported_genesis] + imported_chain:
                if not self._is_valid_hash_format(hash_value):
                    raise ValueError(f"Invalid hash format in imported chain: {hash_value}")
            
            # Import the chain
            old_chain_length = len(self.hash_chain)
            self.genesis_hash = imported_genesis
            self.hash_chain = imported_chain.copy()
            
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(
                        execution_time_ms=execution_time,
                        chain_length_before=old_chain_length,
                        chain_length_after=len(self.hash_chain)
                    )
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.CHAIN_IMPORT,
                        status=self.HashAuditStatus.SUCCESS,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Successfully imported hash chain with {len(self.hash_chain)} hashes",
                        metrics=metrics,
                        severity=self.HashAuditSeverity.HIGH,  # Import is high severity for security
                        additional_data={
                            "imported_hash_count": len(imported_chain),
                            "imported_genesis": imported_genesis,
                            "old_chain_length": old_chain_length,
                            "new_chain_length": len(self.hash_chain)
                        }
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log chain import audit: {audit_e}")
            
            logger.info(f"Successfully imported hash chain with {len(self.hash_chain)} hashes")
            return True
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Audit logging for failure
            if self.audit_service:
                try:
                    metrics = self.HashAuditMetrics(execution_time_ms=execution_time)
                    
                    await self.audit_service.log_hash_operation(
                        operation_type=self.HashAuditOperation.CHAIN_IMPORT,
                        status=self.HashAuditStatus.FAILURE,
                        user_id=user_id,
                        request_id=request_id,
                        message=f"Failed to import hash chain: {str(e)}",
                        error_details={"error": str(e), "error_type": type(e).__name__},
                        metrics=metrics,
                        severity=self.HashAuditSeverity.CRITICAL
                    )
                except Exception as audit_e:
                    logger.warning(f"Failed to log chain import failure audit: {audit_e}")
            
            logger.error(f"Failed to import hash chain: {e}")
            return False

# Global blockchain hash service instance
blockchain_hash_service = BlockchainHashService() 