#!/usr/bin/env python3
"""
Opera GodEye System Testing & Validation Script
Tests all components of the updated Opera GodEye panel
"""

import requests
import json
import time
import sys
from datetime import datetime
import websocket
import threading

class OperaGodEyeTester:
    def __init__(self):
        self.base_url = "http://103.13.30.89:8098"  # Opera GodEye Panel
        self.stardust_url = "http://103.13.30.89:5054"  # Stardust API
        self.test_results = []
        self.start_time = datetime.now()
        
    def log_test(self, test_name, status, message="", data=None):
        """Log test results"""
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        
        # Print result
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {message}")
        
    def test_web_panel_accessibility(self):
        """Test if the web panel is accessible"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                self.log_test("Web Panel Accessibility", "PASS", 
                            f"Panel accessible (Status: {response.status_code})")
                return True
            else:
                self.log_test("Web Panel Accessibility", "FAIL", 
                            f"Panel returned status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Web Panel Accessibility", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_stardust_api_accessibility(self):
        """Test if Stardust API is accessible"""
        try:
            response = requests.get(f"{self.stardust_url}/health", timeout=10)
            if response.status_code == 200:
                self.log_test("Stardust API Accessibility", "PASS", 
                            f"API accessible (Status: {response.status_code})")
                return True
            else:
                self.log_test("Stardust API Accessibility", "FAIL", 
                            f"API returned status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Stardust API Accessibility", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_device_status_endpoints(self):
        """Test device status API endpoints"""
        endpoints = [
            "/test/device-status/summary",
            "/test/device-status/recent",
            "/test/device-status/alerts",
            "/test/device-status/health/overview"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(f"Device Status Endpoint: {endpoint}", "PASS", 
                                f"Endpoint working (Data: {len(data) if isinstance(data, list) else 'object'})",
                                data)
                else:
                    self.log_test(f"Device Status Endpoint: {endpoint}", "FAIL", 
                                f"Status {response.status_code}")
            except Exception as e:
                self.log_test(f"Device Status Endpoint: {endpoint}", "FAIL", f"Error: {str(e)}")
    
    def test_mqtt_monitor_endpoints(self):
        """Test MQTT monitor specific endpoints"""
        endpoints = [
            "/api/statistics",
            "/api/collection-stats",
            "/test/transactions",
            "/test/schema"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(f"MQTT Monitor Endpoint: {endpoint}", "PASS", 
                                f"Endpoint working (Data: {len(data) if isinstance(data, list) else 'object'})",
                                data)
                else:
                    self.log_test(f"MQTT Monitor Endpoint: {endpoint}", "FAIL", 
                                f"Status {response.status_code}")
            except Exception as e:
                self.log_test(f"MQTT Monitor Endpoint: {endpoint}", "FAIL", f"Error: {str(e)}")
    
    def test_websocket_connection(self):
        """Test WebSocket connection"""
        try:
            # Test WebSocket connection to Opera GodEye panel
            ws_url = f"ws://103.13.30.89:8097"
            
            def on_message(ws, message):
                self.log_test("WebSocket Message", "PASS", f"Received message: {message[:100]}...")
                ws.close()
            
            def on_error(ws, error):
                self.log_test("WebSocket Connection", "FAIL", f"WebSocket error: {str(error)}")
            
            def on_close(ws, close_status_code, close_msg):
                pass
            
            def on_open(ws):
                self.log_test("WebSocket Connection", "PASS", "WebSocket connected successfully")
                # Send a test message
                ws.send(json.dumps({"type": "ping", "timestamp": time.time()}))
            
            ws = websocket.WebSocketApp(ws_url,
                                      on_open=on_open,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)
            
            # Run WebSocket in a separate thread
            wst = threading.Thread(target=ws.run_forever)
            wst.daemon = True
            wst.start()
            
            # Wait for connection
            time.sleep(5)
            
        except Exception as e:
            self.log_test("WebSocket Connection", "FAIL", f"WebSocket test error: {str(e)}")
    
    def test_static_assets(self):
        """Test if static assets are accessible"""
        assets = [
            "/static/css/style.css",
            "/static/js/app.js",
            "/static/MFC Theme Palette.svg"
        ]
        
        for asset in assets:
            try:
                response = requests.get(f"{self.base_url}{asset}", timeout=10)
                if response.status_code == 200:
                    self.log_test(f"Static Asset: {asset}", "PASS", 
                                f"Asset accessible (Size: {len(response.content)} bytes)")
                else:
                    self.log_test(f"Static Asset: {asset}", "FAIL", 
                                f"Asset returned status {response.status_code}")
            except Exception as e:
                self.log_test(f"Static Asset: {asset}", "FAIL", f"Error: {str(e)}")
    
    def test_database_connectivity(self):
        """Test database connectivity through API"""
        try:
            # Test device status summary which requires database access
            response = requests.get(f"{self.base_url}/test/device-status/summary", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Database Connectivity", "PASS", 
                            f"Database accessible (Devices: {len(data.get('devices', []))})",
                            data)
            else:
                self.log_test("Database Connectivity", "FAIL", 
                            f"Database test failed (Status: {response.status_code})")
        except Exception as e:
            self.log_test("Database Connectivity", "FAIL", f"Database error: {str(e)}")
    
    def test_device_data_integrity(self):
        """Test device data integrity and structure"""
        try:
            response = requests.get(f"{self.base_url}/test/device-status/recent", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Check data structure
                if isinstance(data, list) and len(data) > 0:
                    device = data[0]
                    required_fields = ['device_id', 'device_type', 'online_status', 'last_update']
                    missing_fields = [field for field in required_fields if field not in device]
                    
                    if not missing_fields:
                        self.log_test("Device Data Integrity", "PASS", 
                                    f"Data structure valid (Devices: {len(data)})",
                                    data[:3])  # Show first 3 devices
                    else:
                        self.log_test("Device Data Integrity", "FAIL", 
                                    f"Missing fields: {missing_fields}")
                else:
                    self.log_test("Device Data Integrity", "WARNING", 
                                "No device data available")
            else:
                self.log_test("Device Data Integrity", "FAIL", 
                            f"Data integrity test failed (Status: {response.status_code})")
        except Exception as e:
            self.log_test("Device Data Integrity", "FAIL", f"Data integrity error: {str(e)}")
    
    def test_performance(self):
        """Test system performance"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/test/device-status/summary", timeout=10)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if response_time < 1000:  # Less than 1 second
                self.log_test("API Performance", "PASS", 
                            f"Response time: {response_time:.2f}ms")
            elif response_time < 3000:  # Less than 3 seconds
                self.log_test("API Performance", "WARNING", 
                            f"Slow response time: {response_time:.2f}ms")
            else:
                self.log_test("API Performance", "FAIL", 
                            f"Very slow response time: {response_time:.2f}ms")
        except Exception as e:
            self.log_test("API Performance", "FAIL", f"Performance test error: {str(e)}")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Count results
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        warning_tests = len([r for r in self.test_results if r["status"] == "WARNING"])
        
        # Generate report
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "warnings": warning_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "duration_seconds": duration,
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat()
            },
            "test_results": self.test_results
        }
        
        # Save report
        with open("opera_godeye_test_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("🎯 OPERA GODEYE SYSTEM TEST REPORT")
        print("="*60)
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️  Warnings: {warning_tests}")
        print(f"📈 Success Rate: {report['test_summary']['success_rate']:.1f}%")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print("="*60)
        
        if failed_tests == 0:
            print("🎉 All critical tests passed! System is operational.")
        else:
            print("⚠️  Some tests failed. Please review the detailed report.")
        
        print(f"📄 Detailed report saved to: opera_godeye_test_report.json")
        
        return report
    
    def run_all_tests(self):
        """Run all system tests"""
        print("🚀 Starting Opera GodEye System Testing & Validation")
        print("="*60)
        
        # Run tests in logical order
        self.test_web_panel_accessibility()
        self.test_stardust_api_accessibility()
        self.test_static_assets()
        self.test_device_status_endpoints()
        self.test_mqtt_monitor_endpoints()
        self.test_database_connectivity()
        self.test_device_data_integrity()
        self.test_websocket_connection()
        self.test_performance()
        
        # Generate and return report
        return self.generate_report()

def main():
    """Main test execution"""
    tester = OperaGodEyeTester()
    report = tester.run_all_tests()
    
    # Exit with appropriate code
    failed_tests = len([r for r in tester.test_results if r["status"] == "FAIL"])
    sys.exit(1 if failed_tests > 0 else 0)

if __name__ == "__main__":
    main() 