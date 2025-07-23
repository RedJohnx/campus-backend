"""
Export and Download functionality testing script for Campus Assets system.
Tests CSV, Excel, PDF, JSON exports with various filtering options.
"""

import requests
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:5000"
TIMEOUT = 60  # Longer timeout for export operations

class ExportTestSuite:
    """Comprehensive export functionality testing."""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.auth_token = None
        self.current_user = None
        self.test_results = []
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"📥 {title}")
        print(f"{'='*60}")
    
    def print_section(self, title):
        print(f"\n{'-'*40}")
        print(f"📋 {title}")
        print(f"{'-'*40}")
    
    def print_success(self, message):
        print(f"✅ {message}")
    
    def print_error(self, message):
        print(f"❌ {message}")
    
    def print_info(self, message):
        print(f"ℹ️  {message}")
    
    def print_warning(self, message):
        print(f"⚠️  {message}")
    
    def make_request(self, method, endpoint, save_file=None, **kwargs):
        """Make HTTP request to export endpoints."""
        try:
            url = f"{self.base_url}{endpoint}"
            
            # Add auth token if available
            if self.auth_token:
                if 'headers' not in kwargs:
                    kwargs['headers'] = {}
                kwargs['headers']['Authorization'] = f"Bearer {self.auth_token}"
            
            print(f"🔄 Making {method} request to: {endpoint}")
            response = getattr(self.session, method.lower())(url, timeout=TIMEOUT, **kwargs)
            
            print(f"📥 Response Status: {response.status_code}")
            print(f"📏 Content Length: {len(response.content)} bytes")
            
            # Save file if requested and response is successful
            if save_file and response.status_code == 200:
                with open(save_file, 'wb') as f:
                    f.write(response.content)
                self.print_success(f"File saved: {save_file}")
            
            return response
            
        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return None
    
    def authenticate(self):
        """Authenticate with the system."""
        print("🔐 Authentication Required")
        
        email = input("Enter admin email: ").strip()
        password = input("Enter password: ").strip()
        
        login_data = {
            "email": email,
            "password": password
        }
        
        response = self.make_request("POST", "/api/auth/login", json=login_data)
        
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data.get('token')
            self.current_user = data.get('user')
            
            self.print_success("Authentication successful!")
            self.print_info(f"User: {self.current_user.get('name', 'Unknown')}")
            self.print_info(f"Role: {self.current_user.get('role', 'Unknown')}")
            return True
        else:
            self.print_error("Authentication failed!")
            return False
    
    def test_csv_exports(self):
        """Test CSV export functionality."""
        self.print_section("CSV Export Testing")
        
        # Test 1: Basic CSV export (all data)
        print("\n📄 Testing Basic CSV Export")
        response = self.make_request("GET", "/api/export/csv", save_file="export_test_all.csv")
        
        if response and response.status_code == 200:
            self.print_success("Basic CSV export successful")
            self.print_info(f"Content-Type: {response.headers.get('Content-Type')}")
            
            # Check if Content-Disposition header is present
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                self.print_info(f"Download filename: {content_disposition}")
        else:
            error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
            self.print_error(f"Basic CSV export failed: {error_msg}")
        
        # Test 2: Filtered CSV export (by department)
        print("\n📄 Testing Filtered CSV Export (Department)")
        department = input("Enter department for filtering (or press Enter to skip): ").strip()
        
        if department:
            params = {'department': department}
            filename = f"export_test_{department.replace(' ', '_').replace('&', 'and')}.csv"
            response = self.make_request("GET", "/api/export/csv", params=params, save_file=filename)
            
            if response and response.status_code == 200:
                self.print_success(f"Filtered CSV export successful for {department}")
            else:
                error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
                self.print_error(f"Filtered CSV export failed: {error_msg}")
        
        # Test 3: CSV Template export
        print("\n📄 Testing CSV Template Export")
        response = self.make_request("GET", "/api/export/csv/template", save_file="import_template.csv")
        
        if response and response.status_code == 200:
            self.print_success("CSV template export successful")
        else:
            self.print_error("CSV template export failed")
    
    def test_excel_exports(self):
        """Test Excel export functionality."""
        self.print_section("Excel Export Testing")
        
        # Test 1: Basic Excel export
        print("\n📊 Testing Basic Excel Export")
        response = self.make_request("GET", "/api/export/excel", save_file="export_test_all.xlsx")
        
        if response and response.status_code == 200:
            self.print_success("Basic Excel export successful")
            self.print_info(f"Content-Type: {response.headers.get('Content-Type')}")
            
            # Try to read the Excel file to verify it's valid
            try:
                import pandas as pd
                df = pd.read_excel("export_test_all.xlsx")
                self.print_info(f"Excel file verified: {len(df)} rows read")
            except Exception as e:
                self.print_warning(f"Could not verify Excel file: {e}")
        else:
            error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
            self.print_error(f"Basic Excel export failed: {error_msg}")
        
        # Test 2: Filtered Excel export
        print("\n📊 Testing Filtered Excel Export")
        location = input("Enter location for filtering (or press Enter to skip): ").strip()
        
        if location:
            params = {'location': location}
            filename = f"export_test_{location.replace(' ', '_')}.xlsx"
            response = self.make_request("GET", "/api/export/excel", params=params, save_file=filename)
            
            if response and response.status_code == 200:
                self.print_success(f"Filtered Excel export successful for {location}")
            else:
                error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
                self.print_error(f"Filtered Excel export failed: {error_msg}")
    
    def test_pdf_exports(self):
        """Test PDF export functionality."""
        self.print_section("PDF Export Testing")
        
        # Test 1: Basic PDF export
        print("\n📄 Testing Basic PDF Export")
        response = self.make_request("GET", "/api/export/pdf", save_file="export_test_all.pdf")
        
        if response and response.status_code == 200:
            self.print_success("Basic PDF export successful")
            self.print_info(f"Content-Type: {response.headers.get('Content-Type')}")
            
            # Check if file is actually a PDF
            if response.content.startswith(b'%PDF'):
                self.print_info("PDF format verified")
            else:
                self.print_warning("File may not be valid PDF format")
        else:
            error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
            self.print_error(f"Basic PDF export failed: {error_msg}")
        
        # Test 2: Filtered PDF export
        print("\n📄 Testing Filtered PDF Export")
        device_type = input("Enter device type for filtering (or press Enter to skip): ").strip()
        
        if device_type:
            params = {'device_type': device_type}
            filename = f"export_test_{device_type.replace(' ', '_')}.pdf"
            response = self.make_request("GET", "/api/export/pdf", params=params, save_file=filename)
            
            if response and response.status_code == 200:
                self.print_success(f"Filtered PDF export successful for {device_type}")
            else:
                error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
                self.print_error(f"Filtered PDF export failed: {error_msg}")
    
    def test_json_exports(self):
        """Test JSON export functionality."""
        self.print_section("JSON Export Testing")
        
        # Test 1: Basic JSON export
        print("\n🔗 Testing Basic JSON Export")
        response = self.make_request("GET", "/api/export/json", save_file="export_test_all.json")
        
        if response and response.status_code == 200:
            self.print_success("Basic JSON export successful")
            
            # Try to parse JSON to verify it's valid
            try:
                json_data = response.json() if hasattr(response, 'json') else json.loads(response.text)
                if isinstance(json_data, dict) and 'resources' in json_data:
                    self.print_info(f"JSON structure verified: {len(json_data['resources'])} resources")
                else:
                    self.print_info("JSON export successful but structure may be different")
            except json.JSONDecodeError:
                self.print_warning("Could not parse JSON response")
        else:
            error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
            self.print_error(f"Basic JSON export failed: {error_msg}")
        
        # Test 2: JSON export with statistics
        print("\n🔗 Testing JSON Export with Statistics")
        params = {'include_stats': 'true'}
        response = self.make_request("GET", "/api/export/json", params=params, save_file="export_test_with_stats.json")
        
        if response and response.status_code == 200:
            self.print_success("JSON export with statistics successful")
        else:
            error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
            self.print_error(f"JSON export with stats failed: {error_msg}")
    
    def test_bulk_exports(self):
        """Test bulk export functionality."""
        self.print_section("Bulk Export Testing")
        
        print("\n📦 Testing Bulk Export (ZIP)")
        response = self.make_request("GET", "/api/export/bulk", save_file="export_test_bulk.zip")
        
        if response and response.status_code == 200:
            self.print_success("Bulk export successful")
            self.print_info(f"Content-Type: {response.headers.get('Content-Type')}")
            
            # Check if file is actually a ZIP
            if response.content.startswith(b'PK'):
                self.print_info("ZIP format verified")
                
                # Try to list ZIP contents
                try:
                    import zipfile
                    with zipfile.ZipFile("export_test_bulk.zip", 'r') as zip_file:
                        file_list = zip_file.namelist()
                        self.print_info(f"ZIP contents: {', '.join(file_list)}")
                except Exception as e:
                    self.print_warning(f"Could not read ZIP contents: {e}")
            else:
                self.print_warning("File may not be valid ZIP format")
        else:
            error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
            self.print_error(f"Bulk export failed: {error_msg}")
    
    def test_department_exports(self):
        """Test department-specific export functionality."""
        self.print_section("Department-Specific Export Testing")
        
        # Get department name
        department = input("Enter department name for testing: ").strip()
        
        if not department:
            self.print_warning("Skipping department export tests - no department specified")
            return
        
        # Test 1: Department Excel export
        print(f"\n🏢 Testing Department Excel Export ({department})")
        endpoint = f"/api/export/department/{department}"
        params = {'format': 'excel'}
        filename = f"dept_export_{department.replace(' ', '_').replace('&', 'and')}.xlsx"
        
        response = self.make_request("GET", endpoint, params=params, save_file=filename)
        
        if response and response.status_code == 200:
            self.print_success(f"Department Excel export successful for {department}")
        else:
            error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
            self.print_error(f"Department Excel export failed: {error_msg}")
        
        # Test 2: Department PDF export
        print(f"\n🏢 Testing Department PDF Export ({department})")
        params = {'format': 'pdf'}
        filename = f"dept_export_{department.replace(' ', '_').replace('&', 'and')}.pdf"
        
        response = self.make_request("GET", endpoint, params=params, save_file=filename)
        
        if response and response.status_code == 200:
            self.print_success(f"Department PDF export successful for {department}")
        else:
            error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
            self.print_error(f"Department PDF export failed: {error_msg}")
        
        # Test 3: Department CSV export
        print(f"\n🏢 Testing Department CSV Export ({department})")
        params = {'format': 'csv'}
        filename = f"dept_export_{department.replace(' ', '_').replace('&', 'and')}.csv"
        
        response = self.make_request("GET", endpoint, params=params, save_file=filename)
        
        if response and response.status_code == 200:
            self.print_success(f"Department CSV export successful for {department}")
        else:
            error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
            self.print_error(f"Department CSV export failed: {error_msg}")
    
    def test_filtered_exports(self):
        """Test advanced filtered export functionality."""
        self.print_section("Advanced Filtered Export Testing")
        
        print("📅 Testing Date Range Filtered Export")
        start_date = input("Enter start date (YYYY-MM-DD) or press Enter to skip: ").strip()
        end_date = input("Enter end date (YYYY-MM-DD) or press Enter to skip: ").strip()
        
        if start_date or end_date:
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            # Test CSV with date filter
            response = self.make_request("GET", "/api/export/csv", params=params, save_file="export_test_date_filtered.csv")
            
            if response and response.status_code == 200:
                self.print_success("Date filtered CSV export successful")
            else:
                error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
                self.print_error(f"Date filtered export failed: {error_msg}")
        
        print("\n🔍 Testing Multiple Filter Combination")
        filters = {}
        
        dept_filter = input("Department filter (or press Enter): ").strip()
        if dept_filter:
            filters['department'] = dept_filter
        
        loc_filter = input("Location filter (or press Enter): ").strip()
        if loc_filter:
            filters['location'] = loc_filter
        
        device_filter = input("Device type filter (or press Enter): ").strip()
        if device_filter:
            filters['device_type'] = device_filter
        
        if filters:
            response = self.make_request("GET", "/api/export/excel", params=filters, save_file="export_test_multi_filtered.xlsx")
            
            if response and response.status_code == 200:
                self.print_success("Multi-filter Excel export successful")
                self.print_info(f"Filters applied: {filters}")
            else:
                error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
                self.print_error(f"Multi-filter export failed: {error_msg}")
    
    def test_export_performance(self):
        """Test export performance and file sizes."""
        self.print_section("Export Performance Testing")
        
        formats = [
            ('csv', '/api/export/csv'),
            ('excel', '/api/export/excel'),
            ('json', '/api/export/json')
        ]
        
        performance_results = []
        
        for format_name, endpoint in formats:
            print(f"\n⏱️ Testing {format_name.upper()} export performance...")
            
            start_time = time.time()
            response = self.make_request("GET", endpoint)
            end_time = time.time()
            
            response_time = round((end_time - start_time) * 1000, 2)  # Convert to milliseconds
            
            if response and response.status_code == 200:
                file_size = len(response.content)
                status = "✅ SUCCESS"
                
                performance_results.append({
                    'format': format_name.upper(),
                    'response_time': response_time,
                    'file_size': file_size,
                    'status': status
                })
                
                print(f"   {status} - {response_time}ms - {file_size:,} bytes")
            else:
                print(f"   ❌ FAILED - {response_time}ms")
        
        # Performance summary
        if performance_results:
            print(f"\n📊 Performance Summary:")
            fastest = min(performance_results, key=lambda x: x['response_time'])
            largest = max(performance_results, key=lambda x: x['file_size'])
            
            print(f"   Fastest Export: {fastest['format']} ({fastest['response_time']}ms)")
            print(f"   Largest File: {largest['format']} ({largest['file_size']:,} bytes)")
            
            avg_time = sum(r['response_time'] for r in performance_results) / len(performance_results)
            print(f"   Average Response Time: {avg_time:.2f}ms")
    
    def cleanup_test_files(self):
        """Clean up generated test files."""
        print("\n🧹 Cleaning up test files...")
        
        test_files = [
            "export_test_all.csv",
            "export_test_all.xlsx", 
            "export_test_all.pdf",
            "export_test_all.json",
            "export_test_bulk.zip",
            "import_template.csv",
            "export_test_with_stats.json",
            "export_test_date_filtered.csv",
            "export_test_multi_filtered.xlsx"
        ]
        
        # Add dynamic filenames
        for file_pattern in ["export_test_*.csv", "export_test_*.xlsx", "export_test_*.pdf", "dept_export_*.*"]:
            import glob
            test_files.extend(glob.glob(file_pattern))
        
        cleaned_count = 0
        for filename in test_files:
            if os.path.exists(filename):
                try:
                    os.remove(filename)
                    cleaned_count += 1
                except Exception as e:
                    self.print_warning(f"Could not remove {filename}: {e}")
        
        if cleaned_count > 0:
            self.print_success(f"Cleaned up {cleaned_count} test files")
        else:
            self.print_info("No test files to clean up")
    
    def run_comprehensive_test(self):
        """Run all export tests comprehensively."""
        self.print_header("Campus Assets Export & Download System Testing")
        
        # Check authentication
        if not self.authenticate():
            return False
        
        # Create exports directory for test files
        os.makedirs("exports_test", exist_ok=True)
        os.chdir("exports_test")
        
        try:
            # Run all test suites
            test_suites = [
                ("CSV Exports", self.test_csv_exports),
                ("Excel Exports", self.test_excel_exports),
                ("PDF Exports", self.test_pdf_exports),
                ("JSON Exports", self.test_json_exports),
                ("Bulk Exports", self.test_bulk_exports),
                ("Department Exports", self.test_department_exports),
                ("Filtered Exports", self.test_filtered_exports),
                ("Performance Testing", self.test_export_performance)
            ]
            
            for suite_name, test_function in test_suites:
                try:
                    print(f"\n{'🔄 Starting ' + suite_name + ' Testing'}")
                    test_function()
                    self.print_success(f"{suite_name} testing completed")
                except Exception as e:
                    self.print_error(f"{suite_name} testing failed: {e}")
            
            # Final summary
            print(f"\n{'='*60}")
            print(f"📊 Export Testing Summary")
            print(f"{'='*60}")
            print(f"✅ All export test suites completed")
            print(f"📁 Test files generated in: {os.getcwd()}")
            print(f"🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Ask about cleanup
            cleanup = input("\nClean up test files? (y/n): ").strip().lower()
            if cleanup in ['y', 'yes']:
                self.cleanup_test_files()
            
            return True
            
        finally:
            # Return to original directory
            os.chdir("..")
    
    def interactive_export_testing(self):
        """Interactive export testing menu."""
        self.print_header("Interactive Export Testing")
        
        if not self.authenticate():
            return
        
        while True:
            print("\n🏠 Export Testing Menu:")
            print("1. 📄 Test CSV Exports")
            print("2. 📊 Test Excel Exports")
            print("3. 📄 Test PDF Exports")
            print("4. 🔗 Test JSON Exports")
            print("5. 📦 Test Bulk Exports")
            print("6. 🏢 Test Department Exports")
            print("7. 🔍 Test Filtered Exports")
            print("8. ⏱️ Test Export Performance")
            print("9. 🧪 Run All Tests")
            print("10. 🚪 Exit")
            
            choice = input("\nEnter your choice (1-10): ").strip()
            
            if choice == '1':
                self.test_csv_exports()
            elif choice == '2':
                self.test_excel_exports()
            elif choice == '3':
                self.test_pdf_exports()
            elif choice == '4':
                self.test_json_exports()
            elif choice == '5':
                self.test_bulk_exports()
            elif choice == '6':
                self.test_department_exports()
            elif choice == '7':
                self.test_filtered_exports()
            elif choice == '8':
                self.test_export_performance()
            elif choice == '9':
                self.run_comprehensive_test()
            elif choice == '10':
                print("\n👋 Export testing completed!")
                break
            else:
                self.print_error("Invalid choice. Please try again.")

def main():
    """Main export testing execution."""
    print("Campus Assets - Export & Download Testing Suite")
    print("=" * 60)
    
    tester = ExportTestSuite()
    
    print("\nTesting Mode:")
    print("1. 🤖 Comprehensive Automated Testing")
    print("2. 🎮 Interactive Testing Menu")
    
    mode = input("\nSelect testing mode (1-2): ").strip()
    
    if mode == '1':
        tester.run_comprehensive_test()
    elif mode == '2':
        tester.interactive_export_testing()
    else:
        print("Invalid mode selected. Starting interactive testing...")
        tester.interactive_export_testing()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
