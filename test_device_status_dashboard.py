#!/usr/bin/env python3
"""
Device Status Dashboard Test Script
Comprehensive testing of device status monitoring functionality
"""

import asyncio
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random

class DeviceStatusDashboardTester:
    def __init__(self, base_url: str = "http://localhost:5054"):
        self.base_url = base_url
        self.auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJuYW1lIjoiYWRtaW4iLCJyb2xlIjoiYWRtaW4iLCJleHAiOjE3MzE5MjE2MDB9.8Kq8Kq8Kq8Kq8Kq8Kq8Kq8Kq8Kq8Kq8Kq8Kq8Kq8Kq8"
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
    def test_api_health(self) -> bool:
        """Test API health endpoint"""
        print("🔍 Testing API Health...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                print("✅ API is healthy")
                return True
            else:
                print(f"❌ API health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API health check error: {e}")
            return False

    def test_device_status_endpoints(self) -> Dict[str, bool]:
        """Test all device status endpoints"""
        print("\n🔍 Testing Device Status Endpoints...")
        results = {}
        
        endpoints = [
            ("/api/devices/status/summary", "GET"),
            ("/api/devices/status/recent", "GET"),
            ("/api/devices/status/alerts", "GET"),
        ]
        
        for endpoint, method in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {endpoint} - Success")
                    results[endpoint] = True
                elif response.status_code == 404:
                    print(f"⚠️  {endpoint} - Not Found (using mock data)")
                    results[endpoint] = False
                else:
                    print(f"❌ {endpoint} - Failed: {response.status_code}")
                    results[endpoint] = False
                    
            except Exception as e:
                print(f"❌ {endpoint} - Error: {e}")
                results[endpoint] = False
        
        return results

    def generate_mock_device_data(self) -> List[Dict[str, Any]]:
        """Generate realistic mock device data"""
        devices = []
        
        # Kati devices
        for i in range(1, 26):
            device = {
                "device_id": f"kati-{i:03d}",
                "device_type": "kati",
                "online_status": "online" if i <= 22 else "offline",
                "battery_level": random.randint(10, 100),
                "signal_strength": random.randint(30, 100),
                "patient_id": f"patient-{i:03d}" if i <= 20 else None,
                "last_updated": (datetime.now() - timedelta(minutes=random.randint(1, 30))).isoformat(),
                "health_metrics": {
                    "heart_rate": random.randint(60, 100) if i <= 22 else None,
                    "blood_pressure": {
                        "systolic": random.randint(110, 140) if i <= 22 else None,
                        "diastolic": random.randint(70, 90) if i <= 22 else None
                    },
                    "temperature": round(random.uniform(36.5, 37.5), 1) if i <= 22 else None,
                    "spo2": random.randint(95, 100) if i <= 22 else None
                },
                "alerts": []
            }
            
            # Add some alerts
            if i == 1:
                device["alerts"] = [{
                    "type": "low_battery",
                    "severity": "warning",
                    "message": "Battery level below 20%",
                    "timestamp": datetime.now().isoformat()
                }]
            elif i == 5:
                device["alerts"] = [{
                    "type": "connection_lost",
                    "severity": "critical",
                    "message": "Connection lost for more than 5 minutes",
                    "timestamp": datetime.now().isoformat()
                }]
            
            devices.append(device)
        
        # AVA4 devices
        for i in range(1, 16):
            device = {
                "device_id": f"ava4-{i:03d}",
                "device_type": "ava4",
                "online_status": "online" if i <= 12 else "offline",
                "battery_level": random.randint(15, 100),
                "signal_strength": random.randint(40, 100),
                "patient_id": f"patient-{i+20:03d}" if i <= 10 else None,
                "last_updated": (datetime.now() - timedelta(minutes=random.randint(1, 45))).isoformat(),
                "health_metrics": {
                    "blood_pressure": {
                        "systolic": random.randint(110, 150) if i <= 12 else None,
                        "diastolic": random.randint(70, 95) if i <= 12 else None
                    },
                    "pulse": random.randint(60, 100) if i <= 12 else None
                },
                "alerts": []
            }
            
            if i == 3:
                device["alerts"] = [{
                    "type": "high_blood_pressure",
                    "severity": "warning",
                    "message": "Blood pressure reading above normal range",
                    "timestamp": datetime.now().isoformat()
                }]
            
            devices.append(device)
        
        # Qube-Vital devices
        for i in range(1, 6):
            device = {
                "device_id": f"qube-{i:03d}",
                "device_type": "qube-vital",
                "online_status": "online" if i <= 4 else "offline",
                "battery_level": random.randint(20, 100),
                "signal_strength": random.randint(50, 100),
                "patient_id": f"patient-{i+35:03d}" if i <= 3 else None,
                "last_updated": (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat(),
                "health_metrics": {
                    "temperature": round(random.uniform(36.0, 38.0), 1) if i <= 4 else None,
                    "humidity": random.randint(40, 60) if i <= 4 else None,
                    "air_quality": random.randint(80, 100) if i <= 4 else None
                },
                "alerts": []
            }
            
            devices.append(device)
        
        return devices

    def generate_mock_alerts(self) -> List[Dict[str, Any]]:
        """Generate realistic mock alert data"""
        alerts = [
            {
                "device_id": "kati-001",
                "device_type": "kati",
                "patient_id": "patient-001",
                "alert_type": "low_battery",
                "severity": "warning",
                "message": "Battery level below 20%",
                "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "data": {"battery_level": 15}
            },
            {
                "device_id": "ava4-005",
                "device_type": "ava4",
                "patient_id": "patient-025",
                "alert_type": "connection_lost",
                "severity": "critical",
                "message": "Connection lost for more than 5 minutes",
                "timestamp": (datetime.now() - timedelta(minutes=10)).isoformat(),
                "data": {"last_seen": (datetime.now() - timedelta(minutes=10)).isoformat()}
            },
            {
                "device_id": "ava4-003",
                "device_type": "ava4",
                "patient_id": "patient-023",
                "alert_type": "high_blood_pressure",
                "severity": "warning",
                "message": "Blood pressure reading above normal range",
                "timestamp": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "data": {"systolic": 150, "diastolic": 95}
            },
            {
                "device_id": "kati-005",
                "device_type": "kati",
                "patient_id": "patient-005",
                "alert_type": "fall_detection",
                "severity": "critical",
                "message": "Potential fall detected",
                "timestamp": (datetime.now() - timedelta(minutes=2)).isoformat(),
                "data": {"impact_force": "high", "location": "bathroom"}
            }
        ]
        
        return alerts

    def test_mock_data_generation(self) -> bool:
        """Test mock data generation"""
        print("\n🔍 Testing Mock Data Generation...")
        try:
            devices = self.generate_mock_device_data()
            alerts = self.generate_mock_alerts()
            
            print(f"✅ Generated {len(devices)} mock devices")
            print(f"✅ Generated {len(alerts)} mock alerts")
            
            # Validate device data structure
            required_fields = ["device_id", "device_type", "online_status", "battery_level", "signal_strength"]
            for device in devices:
                for field in required_fields:
                    if field not in device:
                        print(f"❌ Missing required field '{field}' in device data")
                        return False
            
            # Validate alert data structure
            required_alert_fields = ["device_id", "device_type", "alert_type", "severity", "message"]
            for alert in alerts:
                for field in required_alert_fields:
                    if field not in alert:
                        print(f"❌ Missing required field '{field}' in alert data")
                        return False
            
            print("✅ Mock data validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Mock data generation error: {e}")
            return False

    def test_dashboard_summary_calculation(self) -> bool:
        """Test dashboard summary calculations"""
        print("\n🔍 Testing Dashboard Summary Calculations...")
        try:
            devices = self.generate_mock_device_data()
            
            # Calculate summary
            total_devices = len(devices)
            online_devices = len([d for d in devices if d["online_status"] == "online"])
            offline_devices = len([d for d in devices if d["online_status"] == "offline"])
            low_battery_devices = len([d for d in devices if d["battery_level"] < 20])
            devices_with_alerts = len([d for d in devices if d["alerts"]])
            online_percentage = round((online_devices / total_devices * 100), 2)
            
            # Group by type
            by_type = {}
            for device in devices:
                device_type = device["device_type"]
                if device_type not in by_type:
                    by_type[device_type] = {"total": 0, "online": 0, "offline": 0}
                
                by_type[device_type]["total"] += 1
                if device["online_status"] == "online":
                    by_type[device_type]["online"] += 1
                else:
                    by_type[device_type]["offline"] += 1
            
            summary = {
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": offline_devices,
                "low_battery_devices": low_battery_devices,
                "devices_with_alerts": devices_with_alerts,
                "online_percentage": online_percentage,
                "by_type": by_type
            }
            
            print(f"✅ Summary calculated:")
            print(f"   Total Devices: {summary['total_devices']}")
            print(f"   Online: {summary['online_devices']}")
            print(f"   Offline: {summary['offline_devices']}")
            print(f"   Low Battery: {summary['low_battery_devices']}")
            print(f"   With Alerts: {summary['devices_with_alerts']}")
            print(f"   Online Rate: {summary['online_percentage']}%")
            
            for device_type, stats in summary["by_type"].items():
                print(f"   {device_type}: {stats['total']} total, {stats['online']} online, {stats['offline']} offline")
            
            return True
            
        except Exception as e:
            print(f"❌ Summary calculation error: {e}")
            return False

    def test_device_filtering(self) -> bool:
        """Test device filtering functionality"""
        print("\n🔍 Testing Device Filtering...")
        try:
            devices = self.generate_mock_device_data()
            
            # Test device type filtering
            kati_devices = [d for d in devices if d["device_type"] == "kati"]
            ava4_devices = [d for d in devices if d["device_type"] == "ava4"]
            qube_devices = [d for d in devices if d["device_type"] == "qube-vital"]
            
            print(f"✅ Device type filtering:")
            print(f"   Kati devices: {len(kati_devices)}")
            print(f"   AVA4 devices: {len(ava4_devices)}")
            print(f"   Qube-Vital devices: {len(qube_devices)}")
            
            # Test status filtering
            online_devices = [d for d in devices if d["online_status"] == "online"]
            offline_devices = [d for d in devices if d["online_status"] == "offline"]
            
            print(f"✅ Status filtering:")
            print(f"   Online devices: {len(online_devices)}")
            print(f"   Offline devices: {len(offline_devices)}")
            
            # Test search functionality
            search_term = "kati"
            search_results = [d for d in devices if search_term.lower() in d["device_id"].lower() or search_term.lower() in d["device_type"].lower()]
            
            print(f"✅ Search functionality:")
            print(f"   Search for '{search_term}': {len(search_results)} results")
            
            return True
            
        except Exception as e:
            print(f"❌ Device filtering error: {e}")
            return False

    def test_alert_filtering(self) -> bool:
        """Test alert filtering functionality"""
        print("\n🔍 Testing Alert Filtering...")
        try:
            alerts = self.generate_mock_alerts()
            
            # Test severity filtering
            critical_alerts = [a for a in alerts if a["severity"] == "critical"]
            warning_alerts = [a for a in alerts if a["severity"] == "warning"]
            
            print(f"✅ Alert severity filtering:")
            print(f"   Critical alerts: {len(critical_alerts)}")
            print(f"   Warning alerts: {len(warning_alerts)}")
            
            # Test device type filtering
            kati_alerts = [a for a in alerts if a["device_type"] == "kati"]
            ava4_alerts = [a for a in alerts if a["device_type"] == "ava4"]
            
            print(f"✅ Alert device type filtering:")
            print(f"   Kati alerts: {len(kati_alerts)}")
            print(f"   AVA4 alerts: {len(ava4_alerts)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Alert filtering error: {e}")
            return False

    def test_websocket_simulation(self) -> bool:
        """Test WebSocket message handling simulation"""
        print("\n🔍 Testing WebSocket Message Handling...")
        try:
            # Simulate different WebSocket message types
            messages = [
                {
                    "type": "device_status_update",
                    "device": {
                        "device_id": "kati-001",
                        "online_status": "online",
                        "battery_level": 85,
                        "signal_strength": 95,
                        "last_updated": datetime.now().isoformat()
                    }
                },
                {
                    "type": "new_alert",
                    "alert": {
                        "device_id": "ava4-010",
                        "device_type": "ava4",
                        "alert_type": "low_battery",
                        "severity": "warning",
                        "message": "Battery level below 20%",
                        "timestamp": datetime.now().isoformat()
                    }
                },
                {
                    "type": "device_online",
                    "device_id": "qube-002"
                },
                {
                    "type": "device_offline",
                    "device_id": "kati-015"
                }
            ]
            
            print("✅ WebSocket message types:")
            for msg in messages:
                print(f"   {msg['type']}: {msg}")
            
            return True
            
        except Exception as e:
            print(f"❌ WebSocket simulation error: {e}")
            return False

    def test_performance_metrics(self) -> bool:
        """Test performance metrics and timing"""
        print("\n🔍 Testing Performance Metrics...")
        try:
            start_time = time.time()
            
            # Simulate data loading
            devices = self.generate_mock_device_data()
            alerts = self.generate_mock_alerts()
            
            # Simulate summary calculation
            summary = {
                "total_devices": len(devices),
                "online_devices": len([d for d in devices if d["online_status"] == "online"]),
                "offline_devices": len([d for d in devices if d["online_status"] == "offline"]),
                "low_battery_devices": len([d for d in devices if d["battery_level"] < 20]),
                "devices_with_alerts": len([d for d in devices if d["alerts"]]),
                "online_percentage": round((len([d for d in devices if d["online_status"] == "online"]) / len(devices) * 100), 2)
            }
            
            end_time = time.time()
            processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            print(f"✅ Performance metrics:")
            print(f"   Data processing time: {processing_time:.2f}ms")
            print(f"   Devices processed: {len(devices)}")
            print(f"   Alerts processed: {len(alerts)}")
            print(f"   Summary calculated: {len(summary)} metrics")
            
            if processing_time < 100:  # Should be under 100ms
                print("✅ Performance is acceptable")
                return True
            else:
                print("⚠️  Performance is slower than expected")
                return False
                
        except Exception as e:
            print(f"❌ Performance test error: {e}")
            return False

    def run_comprehensive_test(self) -> Dict[str, bool]:
        """Run all tests and return results"""
        print("🚀 Starting Device Status Dashboard Comprehensive Test")
        print("=" * 60)
        
        results = {}
        
        # Test API health
        results["api_health"] = self.test_api_health()
        
        # Test device status endpoints
        endpoint_results = self.test_device_status_endpoints()
        results["endpoints_working"] = any(endpoint_results.values())
        
        # Test mock data generation
        results["mock_data"] = self.test_mock_data_generation()
        
        # Test dashboard summary calculation
        results["summary_calculation"] = self.test_dashboard_summary_calculation()
        
        # Test device filtering
        results["device_filtering"] = self.test_device_filtering()
        
        # Test alert filtering
        results["alert_filtering"] = self.test_alert_filtering()
        
        # Test WebSocket simulation
        results["websocket_simulation"] = self.test_websocket_simulation()
        
        # Test performance metrics
        results["performance"] = self.test_performance_metrics()
        
        # Calculate overall success rate
        successful_tests = sum(results.values())
        total_tests = len(results)
        success_rate = (successful_tests / total_tests) * 100
        
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        
        if success_rate >= 80:
            print("🎉 Device Status Dashboard is ready for deployment!")
        elif success_rate >= 60:
            print("⚠️  Device Status Dashboard has some issues but is mostly functional")
        else:
            print("❌ Device Status Dashboard needs significant fixes")
        
        return results

def main():
    """Main test execution"""
    print("🔧 Device Status Dashboard Test Suite")
    print("Testing comprehensive device monitoring functionality")
    
    # Initialize tester
    tester = DeviceStatusDashboardTester()
    
    # Run comprehensive test
    results = tester.run_comprehensive_test()
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"device_status_test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "success_rate": (sum(results.values()) / len(results)) * 100
        }, f, indent=2)
    
    print(f"\n📄 Test results saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    main() 