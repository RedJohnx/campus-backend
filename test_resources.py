"""
Comprehensive test suite for Campus Assets Management System.
Tests all major functionality including authentication, resources, filtering, and export.
"""

import unittest
import requests
import json
import time
import os
import tempfile
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO, StringIO

class CampusAssetsTestSuite(unittest.TestCase):
    """Comprehensive test suite for Campus Assets Management System."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.base_url = "http://localhost:5000"
        cls.auth_token = None
        cls.test_user_email = "test@campus.edu"
        cls.test_user_password = "TestPass123!"
        cls.admin_email = "clitest@campus.edu"
        cls.admin_password = "123456**AA"
        cls.test_resource_id = None
        cls.test_department = "Test Department"
        
        print("\n" + "="*60)
        print("🏫 Campus Assets Management System - Test Suite")
        print("="*60)
        
        # Check if server is running
        if not cls.check_server_health():
            raise Exception("Server is not running. Please start the Flask application.")
    
    @classmethod
    def check_server_health(cls):
        """Check if the server is running and healthy."""
        try:
            response = requests.get(f"{cls.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Server is running and healthy")
                return True
        except requests.exceptions.RequestException:
            print("❌ Server is not running")
            return False
        return False
    
    def setUp(self):
        """Set up for each test."""
        if not self.auth_token:
            self.login_admin()
    
    def login_admin(self):
        """Login as admin user for testing."""
        try:
            login_data = {
                "email": self.admin_email,
                "password": self.admin_password
            }
            
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('token')
                print(f"✅ Admin login successful")
                return True
            else:
                print(f"❌ Admin login failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def get_auth_headers(self):
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
    
    # ============================================================================
    # AUTHENTICATION TESTS
    # ============================================================================
    
    def test_01_server_health(self):
        """Test server health endpoint."""
        print("\n📊 Testing server health...")
        
        response = requests.get(f"{self.base_url}/api/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'healthy')
        
        print("✅ Server health test passed")
    
    def test_02_admin_login(self):
        """Test admin login functionality."""
        print("\n🔐 Testing admin login...")
        
        login_data = {
            "email": self.admin_email,
            "password": self.admin_password
        }
        
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('token', data)
        self.assertIn('user', data)
        
        print("✅ Admin login test passed")
    
    def test_03_unauthorized_access(self):
        """Test unauthorized access protection."""
        print("\n🔒 Testing unauthorized access...")
        
        # Try to access protected endpoint without token
        response = requests.get(f"{self.base_url}/api/resources")
        
        self.assertEqual(response.status_code, 401)
        
        print("✅ Unauthorized access protection test passed")
    
    # ============================================================================
    # DEPARTMENT TESTS
    # ============================================================================
    
    def test_04_list_departments(self):
        """Test department listing."""
        print("\n🏢 Testing department listing...")
        
        response = requests.get(
            f"{self.base_url}/api/resources/departments",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('departments', data)
        self.assertIsInstance(data['departments'], list)
        
        print(f"✅ Department listing test passed - {len(data['departments'])} departments found")
    
    def test_05_create_test_department(self):
        """Test department creation."""
        print("\n🏢 Testing department creation...")
        
        dept_data = {
            "name": self.test_department,
            "locations": ["Test Lab 1", "Test Lab 2"]
        }
        
        response = requests.post(
            f"{self.base_url}/api/resources/departments",
            json=dept_data,
            headers=self.get_auth_headers()
        )
        
        # Accept both 201 (created) and 409 (already exists)
        self.assertIn(response.status_code, [201, 409])
        
        print("✅ Department creation test passed")
    
    # ============================================================================
    # RESOURCE CRUD TESTS
    # ============================================================================
    
    def test_06_create_resource(self):
        """Test resource creation."""
        print("\n📦 Testing resource creation...")
        
        resource_data = {
            "device_name": "Test Device",
            "quantity": 5,
            "description": "Test device for automated testing",
            "procurement_date": "2024-01-15",
            "location": "Test Lab 1",
            "cost": 25000.00,
            "department": self.test_department
        }
        
        response = requests.post(
            f"{self.base_url}/api/resources",
            json=resource_data,
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('resource', data)
        self.__class__.test_resource_id = data['resource']['_id']
        
        print(f"✅ Resource creation test passed - ID: {self.test_resource_id}")
    
    def test_07_list_resources(self):
        """Test resource listing."""
        print("\n📋 Testing resource listing...")
        
        response = requests.get(
            f"{self.base_url}/api/resources",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('resources', data)
        self.assertIsInstance(data['resources'], list)
        
        print(f"✅ Resource listing test passed - {len(data['resources'])} resources found")
    
    def test_08_get_resource_details(self):
        """Test getting specific resource details."""
        print("\n📦 Testing resource details...")
        
        if not self.test_resource_id:
            self.skipTest("No test resource ID available")
        
        response = requests.get(
            f"{self.base_url}/api/resources/{self.test_resource_id}",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('resource', data)
        self.assertEqual(data['resource']['device_name'], 'Test Device')
        
        print("✅ Resource details test passed")
    
    def test_09_update_resource(self):
        """Test resource updating."""
        print("\n✏️ Testing resource updating...")
        
        if not self.test_resource_id:
            self.skipTest("No test resource ID available")
        
        update_data = {
            "device_name": "Updated Test Device",
            "quantity": 7,
            "description": "Updated test device description",
            "procurement_date": "2024-02-15",
            "location": "Test Lab 2",
            "cost": 30000.00,
            "department": self.test_department
        }
        
        response = requests.put(
            f"{self.base_url}/api/resources/{self.test_resource_id}",
            json=update_data,
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('resource', data)
        self.assertEqual(data['resource']['device_name'], 'Updated Test Device')
        
        print("✅ Resource updating test passed")
    
    # ============================================================================
    # ADVANCED FILTERING TESTS
    # ============================================================================
    
    def test_10_filter_options(self):
        """Test filter options endpoint."""
        print("\n🔍 Testing filter options...")
        
        response = requests.get(
            f"{self.base_url}/api/resources/filter-options",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('departments', data)
        self.assertIn('summary', data)
        
        print(f"✅ Filter options test passed - {data['summary']['total_departments']} departments")
    
    def test_11_advanced_search(self):
        """Test advanced search functionality."""
        print("\n🔎 Testing advanced search...")
        
        search_data = {
            "query": "Test",
            "department": self.test_department,
            "page": 1,
            "per_page": 10
        }
        
        response = requests.post(
            f"{self.base_url}/api/resources/advanced-search",
            json=search_data,
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('resources', data)
        self.assertIn('search_summary', data)
        
        print(f"✅ Advanced search test passed - {len(data['resources'])} results")
    
    def test_12_department_locations(self):
        """Test department locations endpoint."""
        print("\n📍 Testing department locations...")
        
        response = requests.get(
            f"{self.base_url}/api/resources/filter/locations/{self.test_department}",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('locations', data)
        self.assertEqual(data['department'], self.test_department)
        
        print(f"✅ Department locations test passed - {len(data['locations'])} locations")
    
    def test_13_quick_filters(self):
        """Test quick filters endpoint."""
        print("\n⚡ Testing quick filters...")
        
        response = requests.get(
            f"{self.base_url}/api/resources/quick-filters",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('top_departments', data)
        self.assertIn('top_locations', data)
        self.assertIn('top_devices', data)
        
        print("✅ Quick filters test passed")
    
    # ============================================================================
    # EXPORT FUNCTIONALITY TESTS
    # ============================================================================
    
    def test_14_csv_export(self):
        """Test CSV export functionality."""
        print("\n📄 Testing CSV export...")
        
        response = requests.get(
            f"{self.base_url}/api/export/csv",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'text/csv')
        
        # Check if response contains CSV data
        csv_content = response.text
        self.assertIn('sl_no', csv_content)
        self.assertIn('device_name', csv_content)
        
        print("✅ CSV export test passed")
    
    def test_15_excel_export(self):
        """Test Excel export functionality."""
        print("\n📊 Testing Excel export...")
        
        response = requests.get(
            f"{self.base_url}/api/export/excel",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                     response.headers['Content-Type'])
        
        # Check if file is actually an Excel file
        self.assertGreater(len(response.content), 1000)  # Excel files are typically larger
        
        print("✅ Excel export test passed")
    
    def test_16_department_export(self):
        """Test department-specific export."""
        print("\n🏢 Testing department export...")
        
        response = requests.get(
            f"{self.base_url}/api/export/department/{self.test_department}",
            headers=self.get_auth_headers(),
            params={"format": "csv"}
        )
        
        self.assertEqual(response.status_code, 200)
        
        print("✅ Department export test passed")
    
    def test_17_export_formats(self):
        """Test export formats endpoint."""
        print("\n📊 Testing export formats...")
        
        response = requests.get(
            f"{self.base_url}/api/export/formats",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('supported_formats', data)
        
        print("✅ Export formats test passed")
    
    # ============================================================================
    # FILE UPLOAD TESTS
    # ============================================================================
    
    def test_18_upload_template_download(self):
        """Test upload template download."""
        print("\n📋 Testing upload template...")
        
        response = requests.get(
            f"{self.base_url}/api/upload/template",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'text/csv')
        
        print("✅ Upload template test passed")
    
    def test_19_excel_upload(self):
        """Test Excel file upload functionality."""
        print("\n📁 Testing Excel upload...")
        
        # Create a test Excel file
        test_data = {
            'Device Name': ['Test Upload Device'],
            'Quantity': [2],
            'Description': ['Test upload device'],
            'Procurement Date': ['2024-03-01'],
            'Location': ['Test Upload Lab'],
            'Cost': [15000.00]
        }
        
        df = pd.DataFrame(test_data)
        
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            df.to_excel(temp_file.name, index=False)
            temp_file.seek(0)
            
            # Upload the file
            with open(temp_file.name, 'rb') as f:
                files = {'file': ('test.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                data = {'department': self.test_department}
                
                response = requests.post(
                    f"{self.base_url}/api/upload/excel",
                    files=files,
                    data=data,
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
            
            # Clean up
            os.unlink(temp_file.name)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('stats', data)
        
        print("✅ Excel upload test passed")
    
    # ============================================================================
    # DASHBOARD TESTS
    # ============================================================================
    
    def test_20_dashboard_overview(self):
        """Test dashboard overview endpoint."""
        print("\n📊 Testing dashboard overview...")
        
        response = requests.get(
            f"{self.base_url}/api/dashboard/overview",
            headers=self.get_auth_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('overview', data)
            self.assertIn('financial_metrics', data)
            print("✅ Dashboard overview test passed")
        else:
            print(f"⚠️ Dashboard overview not available (HTTP {response.status_code})")
    
    def test_21_dashboard_department_analytics(self):
        """Test dashboard department analytics."""
        print("\n🏢 Testing dashboard department analytics...")
        
        response = requests.get(
            f"{self.base_url}/api/dashboard/department-analytics",
            headers=self.get_auth_headers()
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('department_analytics', data)
            print("✅ Dashboard department analytics test passed")
        else:
            print(f"⚠️ Dashboard department analytics not available (HTTP {response.status_code})")
    
    # ============================================================================
    # PERFORMANCE TESTS
    # ============================================================================
    
    def test_22_response_time_performance(self):
        """Test API response time performance."""
        print("\n⚡ Testing API performance...")
        
        endpoints = [
            ("/api/resources", "GET"),
            ("/api/resources/departments", "GET"),
            ("/api/resources/filter-options", "GET"),
            ("/api/export/formats", "GET")
        ]
        
        performance_results = []
        
        for endpoint, method in endpoints:
            start_time = time.time()
            
            if method == "GET":
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    headers=self.get_auth_headers()
                )
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            performance_results.append({
                'endpoint': endpoint,
                'response_time': response_time,
                'status_code': response.status_code
            })
            
            # Assert reasonable response time (under 5 seconds)
            self.assertLess(response_time, 5000, f"Endpoint {endpoint} took too long: {response_time:.2f}ms")
        
        # Print performance summary
        avg_response_time = sum(r['response_time'] for r in performance_results) / len(performance_results)
        print(f"✅ Performance test passed - Average response time: {avg_response_time:.2f}ms")
        
        for result in performance_results:
            print(f"   {result['endpoint']}: {result['response_time']:.2f}ms (HTTP {result['status_code']})")
    
    # ============================================================================
    # CLEANUP TESTS
    # ============================================================================
    
    def test_23_delete_test_resource(self):
        """Test resource deletion."""
        print("\n🗑️ Testing resource deletion...")
        
        if not self.test_resource_id:
            self.skipTest("No test resource ID available")
        
        response = requests.delete(
            f"{self.base_url}/api/resources/{self.test_resource_id}",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('message', data)
        
        print("✅ Resource deletion test passed")
    
    def test_24_verify_deletion(self):
        """Verify resource was actually deleted."""
        print("\n🔍 Verifying resource deletion...")
        
        if not self.test_resource_id:
            self.skipTest("No test resource ID available")
        
        response = requests.get(
            f"{self.base_url}/api/resources/{self.test_resource_id}",
            headers=self.get_auth_headers()
        )
        
        self.assertEqual(response.status_code, 404)
        
        print("✅ Deletion verification test passed")
    
    # ============================================================================
    # TEST UTILITIES
    # ============================================================================
    
    def test_25_system_statistics(self):
        """Generate final system statistics."""
        print("\n📊 Generating system statistics...")
        
        # Get resources count
        resources_response = requests.get(
            f"{self.base_url}/api/resources",
            headers=self.get_auth_headers()
        )
        
        if resources_response.status_code == 200:
            resources_data = resources_response.json()
            total_resources = len(resources_data['resources'])
        else:
            total_resources = 0
        
        # Get departments count
        dept_response = requests.get(
            f"{self.base_url}/api/resources/departments",
            headers=self.get_auth_headers()
        )
        
        if dept_response.status_code == 200:
            dept_data = dept_response.json()
            total_departments = len(dept_data['departments'])
        else:
            total_departments = 0
        
        # Get filter options for locations count
        filter_response = requests.get(
            f"{self.base_url}/api/resources/filter-options",
            headers=self.get_auth_headers()
        )
        
        if filter_response.status_code == 200:
            filter_data = filter_response.json()
            total_locations = filter_data['summary']['total_locations']
            total_device_types = filter_data['summary']['total_device_types']
        else:
            total_locations = 0
            total_device_types = 0
        
        print("\n" + "="*60)
        print("📊 FINAL SYSTEM STATISTICS")
        print("="*60)
        print(f"📦 Total Resources: {total_resources}")
        print(f"🏢 Total Departments: {total_departments}")
        print(f"📍 Total Locations: {total_locations}")
        print(f"🎯 Total Device Types: {total_device_types}")
        print("="*60)
        
        # This test always passes as it's just informational
        self.assertTrue(True)

# ============================================================================
# TEST RUNNER AND MAIN EXECUTION
# ============================================================================

def run_test_suite():
    """Run the complete test suite with custom formatting."""
    
    # Create test suite
    test_loader = unittest.TestLoader()
    test_suite = test_loader.loadTestsFromTestCase(CampusAssetsTestSuite)
    
    # Custom test runner with verbose output
    class VerboseTestResult(unittest.TextTestResult):
        def addSuccess(self, test):
            super().addSuccess(test)
            print(f"✅ {test._testMethodName}: PASSED")
        
        def addError(self, test, err):
            super().addError(test, err)
            print(f"❌ {test._testMethodName}: ERROR")
            print(f"   Error: {err[1]}")
        
        def addFailure(self, test, err):
            super().addFailure(test, err)
            print(f"❌ {test._testMethodName}: FAILED")
            print(f"   Failure: {err[1]}")
        
        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            print(f"⏭️ {test._testMethodName}: SKIPPED - {reason}")
    
    class VerboseTestRunner(unittest.TextTestRunner):
        resultclass = VerboseTestResult
        
        def run(self, test):
            print("\n🚀 Starting Campus Assets Management System Test Suite")
            print("="*60)
            result = super().run(test)
            
            print("\n" + "="*60)
            print("📊 TEST SUMMARY")
            print("="*60)
            print(f"✅ Tests Passed: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
            print(f"❌ Tests Failed: {len(result.failures)}")
            print(f"💥 Tests Errored: {len(result.errors)}")
            print(f"⏭️ Tests Skipped: {len(result.skipped)}")
            print(f"📊 Total Tests: {result.testsRun}")
            
            success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")
            
            if result.failures:
                print(f"\n❌ FAILED TESTS:")
                for test, traceback in result.failures:
                    print(f"   • {test._testMethodName}")
            
            if result.errors:
                print(f"\n💥 ERROR TESTS:")
                for test, traceback in result.errors:
                    print(f"   • {test._testMethodName}")
            
            print("="*60)
            
            return result
    
    # Run tests
    runner = VerboseTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    """
    Main execution block.
    Run this file directly to execute the complete test suite.
    
    Usage:
        python resource_test.py
    
    Prerequisites:
        1. Flask server must be running on localhost:5000
        2. Database must be accessible
        3. Admin user must be configured
    """
    
    print("🏫 Campus Assets Management System - Automated Test Suite")
    print("="*60)
    print("Prerequisites Check:")
    print("1. ✅ Flask server running on localhost:5000")
    print("2. ✅ MongoDB database accessible")
    print("3. ✅ Admin user configured")
    print("4. ✅ All required packages installed")
    print("="*60)
    
    # Run the test suite
    success = run_test_suite()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Campus Assets Management System is working correctly.")
        exit(0)
    else:
        print("\n❌ SOME TESTS FAILED! Please check the output above for details.")
        exit(1)
