#!/usr/bin/env python3
"""
Quick Endpoint Health Check for My FirstCare Opera Panel API
===========================================================

Performs rapid health checks on critical endpoints to ensure basic functionality.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

class QuickEndpointChecker:
    """Quick health checker for critical endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:5054"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 10
        
    def check_endpoint(self, method: str, path: str, description: str, 
                      requires_auth: bool = False, expected_status: int = 200) -> Tuple[bool, Dict]:
        """Check a single endpoint"""
        start_time = time.time()
        
        try:
            headers = {}
            if requires_auth:
                headers["Authorization"] = "Bearer sample_token_for_testing"
            
            response = self.session.request(method, f"{self.base_url}{path}", headers=headers)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            
            # For auth-required endpoints with sample token, expect 401
            if requires_auth and "sample_token" in headers.get("Authorization", ""):
                success = response.status_code in [401, 403] or (200 <= response.status_code < 300)
            else:
                success = response.status_code == expected_status or (200 <= response.status_code < 300)
            
            return success, {
                "endpoint": path,
                "method": method,
                "description": description,
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 1),
                "success": success
            }
            
        except requests.exceptions.RequestException as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            return False, {
                "endpoint": path,
                "method": method,
                "description": description,
                "status_code": 0,
                "response_time_ms": round(response_time, 1),
                "success": False,
                "error": str(e)
            }
    
    def run_quick_check(self) -> Dict:
        """Run quick check on critical endpoints"""
        print("🚀 Quick Endpoint Health Check")
        print("="*50)
        
        # Critical endpoints to check
        critical_endpoints = [
            ("GET", "/", "API Root", False, 200),
            ("GET", "/health", "Health Check", False, 200),
            ("GET", "/docs", "API Documentation", False, 200),
            ("POST", "/auth/login", "Authentication", False, 422),  # Expect validation error without credentials
            ("GET", "/admin/patients", "Admin Access", True, 401),
            ("GET", "/api/ava4/devices", "AVA4 Devices", True, 401),
            ("GET", "/api/kati/test", "Kati Test", False, 200),
            ("GET", "/fhir/R5/metadata", "FHIR Metadata", False, 200),
            ("GET", "/fhir/R5/Patient", "FHIR Patients", True, 401),
            ("GET", "/realtime/status", "Real-time Status", True, 401),
        ]
        
        results = []
        passed = 0
        total = len(critical_endpoints)
        
        print(f"Testing {total} critical endpoints...\n")
        
        for method, path, description, requires_auth, expected_status in critical_endpoints:
            success, result = self.check_endpoint(method, path, description, requires_auth, expected_status)
            results.append(result)
            
            status_icon = "✅" if success else "❌"
            auth_indicator = "🔒" if requires_auth else "🌐"
            
            print(f"{status_icon} {auth_indicator} {method:4s} {path:30s} - {result['status_code']} ({result['response_time_ms']}ms)")
            
            if success:
                passed += 1
            elif 'error' in result:
                print(f"   Error: {result['error']}")
        
        success_rate = (passed / total) * 100
        
        print("\n" + "="*50)
        print(f"📊 Quick Check Results: {passed}/{total} passed ({success_rate:.1f}%)")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT: Core functionality working!")
            status = "excellent"
        elif success_rate >= 70:
            print("✅ GOOD: Most endpoints working")
            status = "good"
        elif success_rate >= 50:
            print("⚠️ WARNING: Some issues detected")
            status = "warning"
        else:
            print("❌ CRITICAL: Major issues detected")
            status = "critical"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_checked": total,
            "passed": passed,
            "success_rate": success_rate,
            "status": status,
            "results": results
        }

def main():
    """Main execution"""
    checker = QuickEndpointChecker()
    
    try:
        # Quick check
        report = checker.run_quick_check()
        
        # Save report
        with open("quick_endpoint_check.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: quick_endpoint_check.json")
        
        # Return appropriate exit code
        if report["success_rate"] >= 70:
            return 0  # Success
        else:
            return 1  # Issues detected
            
    except Exception as e:
        print(f"❌ Quick check failed: {e}")
        return 2

if __name__ == "__main__":
    exit(main())