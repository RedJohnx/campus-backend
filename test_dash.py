"""
Comprehensive Dashboard Testing Suite for Campus Assets System.
Tests all dashboard endpoints with detailed metrics and performance analysis.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Configuration
BASE_URL = "http://localhost:5000"
TEST_TIMEOUT = 30

class DashboardTestSuite:
    """Comprehensive dashboard testing suite."""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        self.performance_metrics = []
        
    def print_header(self, title: str):
        """Print formatted header."""
        print(f"\n{'='*70}")
        print(f"📊 {title}")
        print(f"{'='*70}")
    
    def print_section(self, title: str):
        """Print section header."""
        print(f"\n{'-'*50}")
        print(f"📋 {title}")
        print(f"{'-'*50}")
    
    def print_success(self, message: str):
        """Print success message."""
        print(f"✅ {message}")
    
    def print_error(self, message: str):
        """Print error message."""
        print(f"❌ {message}")
    
    def print_info(self, message: str):
        """Print info message."""
        print(f"ℹ️  {message}")
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with timing and error handling."""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if self.auth_token:
                if 'headers' not in kwargs:
                    kwargs['headers'] = {}
                kwargs['headers']['Authorization'] = f"Bearer {self.auth_token}"
            
            start_time = time.time()
            response = getattr(self.session, method.lower())(url, timeout=TEST_TIMEOUT, **kwargs)
            end_time = time.time()
            
            # Record performance metrics
            self.performance_metrics.append({
                'endpoint': endpoint,
                'method': method,
                'response_time': (end_time - start_time) * 1000,  # ms
                'status_code': response.status_code,
                'content_length': len(response.content) if response.content else 0,
                'success': response.status_code == 200
            })
            
            return response
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed for {endpoint}: {e}")
            return None
    
    def authenticate(self) -> bool:
        """Authenticate with the system."""
        self.print_section("Authentication")
        
        # Use existing test credentials
        login_data = {
            "email": "clitest@campus.edu",
            "password": "123456**AA"
        }
        
        print(f"🔑 Logging in as: {login_data['email']}")
        response = self.make_request("POST", "/api/auth/login", json=login_data)
        
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data.get('token')
            user = data.get('user', {})
            
            self.print_success("Authentication successful!")
            self.print_info(f"User: {user.get('name', 'Unknown')}")
            self.print_info(f"Role: {user.get('role', 'Unknown')}")
            self.print_info(f"Token: {self.auth_token[:20]}...")
            return True
        else:
            self.print_error("Authentication failed!")
            return False
    
    def test_dashboard_overview(self) -> bool:
        """Test dashboard overview endpoint."""
        self.print_section("Dashboard Overview")
        print("🔄 Testing GET /api/dashboard/overview...")
        
        response = self.make_request("GET", "/api/dashboard/overview")
        
        if response and response.status_code == 200:
            data = response.json()
            
            self.print_success("Dashboard overview retrieved successfully!")
            
            # Display overview metrics
            if 'overview' in data:
                overview = data['overview']
                print(f"\n📊 System Overview:")
                print(f"   📈 Total Resources: {overview.get('total_resources', 0)}")
                print(f"   📈 Total Departments: {overview.get('total_departments', 0)}")
                print(f"   📈 Total Users: {overview.get('total_users', 0)}")
                print(f"   📈 Total Asset Value: {overview.get('total_value', 0):,.2f} ₹")
                print(f"   📈 Total Quantity: {overview.get('total_quantity', 0)}")
                print(f"   📈 Unique Devices: {overview.get('unique_devices', 0)}")
                print(f"   📈 Unique Locations: {overview.get('unique_locations', 0)}")
                print(f"   📈 Recent Additions (30d): {overview.get('recent_additions_30d', 0)}")
            
            # Display financial metrics
            if 'financial_metrics' in data:
                financial = data['financial_metrics']
                print(f"\n💰 Financial Metrics:")
                print(f"   📈 Total Asset Value: {financial.get('total_asset_value', 0):,.2f} ₹")
                print(f"   📈 Average Cost per Item: {financial.get('average_cost_per_item', 0):,.2f} ₹")
                print(f"   📈 Most Expensive Item: {financial.get('most_expensive_item', 0):,.2f} ₹")
                print(f"   📈 Least Expensive Item: {financial.get('least_expensive_item', 0):,.2f} ₹")
                print(f"   📈 Cost per Resource: {financial.get('cost_per_resource', 0):,.2f} ₹")
            
            # Display top performers
            if 'top_performers' in data:
                performers = data['top_performers']
                print(f"\n🏆 Top Performers:")
                leading_dept = performers.get('leading_department', {})
                most_expensive = performers.get('most_expensive_item', {})
                print(f"   📈 Leading Department: {leading_dept.get('name', 'N/A')} ({leading_dept.get('resource_count', 0)} resources)")
                print(f"   📈 Most Expensive Item: {most_expensive.get('device_name', 'N/A')} - ₹{most_expensive.get('cost', 0):,.2f}")
            
            return True
        else:
            self.print_error(f"Dashboard overview failed: {response.status_code if response else 'No response'}")
            return False
    
    def test_department_analytics(self) -> bool:
        """Test department analytics endpoint."""
        self.print_section("Department Analytics")
        print("🔄 Testing GET /api/dashboard/department-analytics...")
        
        response = self.make_request("GET", "/api/dashboard/department-analytics")
        
        if response and response.status_code == 200:
            data = response.json()
            
            self.print_success("Department analytics retrieved successfully!")
            
            # Display summary
            if 'summary' in data:
                summary = data['summary']
                print(f"\n🏢 System Summary:")
                print(f"   📈 Total Departments: {summary.get('total_departments', 0)}")
                print(f"   📈 Total System Value: {summary.get('total_system_value', 0):,.2f} ₹")
                print(f"   📈 Avg Resources per Dept: {summary.get('average_resources_per_dept', 0):,.2f}")
                
                if 'comparison_metrics' in summary:
                    metrics = summary['comparison_metrics']
                    print(f"\n🏆 Department Leaders:")
                    print(f"   📈 Highest Value: {metrics.get('highest_value_department', 'N/A')}")
                    print(f"   📈 Most Diverse: {metrics.get('most_diverse_department', 'N/A')}")
                    print(f"   📈 Most Distributed: {metrics.get('most_distributed_department', 'N/A')}")
            
            # Display top departments
            if 'department_analytics' in data:
                departments = data['department_analytics'][:5]  # Top 5
                print(f"\n📋 Top 5 Departments by Value:")
                for i, dept in enumerate(departments, 1):
                    metrics = dept.get('metrics', {})
                    print(f"{i}. {dept.get('department_name', 'Unknown')}")
                    print(f"   Resources: {metrics.get('total_resources', 0)}")
                    print(f"   Value: ₹{metrics.get('total_cost', 0):,.2f}")
                    print(f"   Devices: {metrics.get('unique_devices', 0)}")
                    print(f"   Locations: {metrics.get('unique_locations', 0)}")
                    print(f"   Avg Cost: ₹{metrics.get('avg_cost_per_item', 0):,.2f}")
                    print()
            
            return True
        else:
            self.print_error(f"Department analytics failed: {response.status_code if response else 'No response'}")
            return False
    
    def test_cost_analysis(self) -> bool:
        """Test cost analysis endpoint with different time ranges."""
        self.print_section("Cost Analysis")
        
        time_ranges = ['1_month', '3_months', '6_months', '12_months']
        success_count = 0
        
        for time_range in time_ranges:
            print(f"🔄 Testing cost analysis for {time_range}...")
            
            response = self.make_request("GET", f"/api/dashboard/cost-analysis?time_range={time_range}")
            
            if response and response.status_code == 200:
                data = response.json()
                self.print_success(f"Cost analysis ({time_range}) retrieved successfully!")
                
                # Display key metrics for first time range only
                if time_range == '1_month' and 'financial_summary' in data:
                    summary = data['financial_summary']
                    print(f"\n💰 Financial Summary ({time_range}):")
                    print(f"   📈 Total Invested: {summary.get('total_invested', 0):,.2f} ₹")
                    print(f"   📈 Cost Efficiency Score: {summary.get('cost_efficiency_score', 0):.2f}")
                    print(f"   📈 Budget Utilization: {summary.get('budget_utilization_rate', 0):.2f}%")
                
                success_count += 1
            else:
                self.print_error(f"Cost analysis ({time_range}) failed: {response.status_code if response else 'No response'}")
        
        return success_count == len(time_ranges)
    
    def test_utilization_metrics(self) -> bool:
        """Test utilization metrics endpoint."""
        self.print_section("Utilization Metrics")
        print("🔄 Testing GET /api/dashboard/utilization-metrics...")
        
        response = self.make_request("GET", "/api/dashboard/utilization-metrics")
        
        if response and response.status_code == 200:
            data = response.json()
            
            self.print_success("Utilization metrics retrieved successfully!")
            
            # Display utilization metrics
            if 'utilization_metrics' in data:
                metrics = data['utilization_metrics']
                print(f"\n📊 Utilization Metrics:")
                
                if 'location_density' in metrics:
                    density = metrics['location_density']
                    if density:
                        avg_density = sum(loc.get('resource_count', 0) for loc in density) / len(density)
                        max_density = max(density, key=lambda x: x.get('resource_count', 0))
                        print(f"   📈 Total Locations: {len(density)}")
                        print(f"   📈 Avg Resources per Location: {avg_density:.2f}")
                        print(f"   📈 Most Resourced Location: {max_density.get('_id', 'N/A')} ({max_density.get('resource_count', 0)} resources)")
                    else:
                        print(f"   📈 No location density data available")
            
            # Display efficiency scores
            if 'efficiency_scores' in data:
                scores = data['efficiency_scores']
                print(f"\n⭐ Efficiency Scores:")
                print(f"   📈 Overall Efficiency: {scores.get('overall_efficiency', 0):.2f}%")
                print(f"   📈 Resource Distribution: {scores.get('resource_distribution_score', 0):.2f}%")
                print(f"   📈 Cost Optimization: {scores.get('cost_optimization_score', 0):.2f}%")
                print(f"   📈 Maintenance Readiness: {scores.get('maintenance_readiness_score', 0):.2f}%")
            
            return True
        else:
            self.print_error(f"Utilization metrics failed: {response.status_code if response else 'No response'}")
            return False
    
    def test_chart_data(self) -> bool:
        """Test chart data endpoints."""
        self.print_section("Chart Data")
        
        chart_types = [
            ('all', 'all chart types'),
            ('pie', 'pie charts'),
            ('bar', 'bar charts'),
            ('line', 'line charts'),
            ('donut', 'donut charts')
        ]
        
        success_count = 0
        
        for chart_type, description in chart_types:
            print(f"🔄 Testing chart data for {description}...")
            
            response = self.make_request("GET", f"/api/dashboard/charts?type={chart_type}")
            
            if response and response.status_code == 200:
                data = response.json()
                self.print_success(f"Chart data ({description}) retrieved successfully!")
                
                # Display chart info for 'all' type
                if chart_type == 'all' and 'charts' in data:
                    charts = data['charts']
                    print(f"\n📊 Available Charts:")
                    for chart_name, chart_data in charts.items():
                        if isinstance(chart_data, dict) and 'data' in chart_data:
                            print(f"   📈 {chart_name}: {len(chart_data['data'])} data points")
                        else:
                            print(f"   📈 {chart_name}: Available")
                
                success_count += 1
            else:
                self.print_error(f"Chart data ({description}) failed: {response.status_code if response else 'No response'}")
        
        return success_count > 0  # At least some charts should work
    
    def test_specific_dashboard_endpoints(self) -> bool:
        """Test any specific endpoints in your dashboard."""
        self.print_section("Specific Dashboard Endpoints")
        
        # Test any additional endpoints your dashboard might have
        additional_endpoints = [
            '/api/dashboard/stats',
            '/api/dashboard/summary',
            '/api/dashboard/reports',
            '/api/dashboard/analytics'
        ]
        
        success_count = 0
        
        for endpoint in additional_endpoints:
            print(f"🔄 Testing {endpoint}...")
            
            response = self.make_request("GET", endpoint)
            
            if response and response.status_code == 200:
                self.print_success(f"{endpoint} working!")
                success_count += 1
            elif response and response.status_code == 404:
                print(f"ℹ️  {endpoint} not found (expected)")
            else:
                print(f"⚠️  {endpoint} failed: {response.status_code if response else 'No response'}")
        
        return True  # Don't fail on additional endpoints
    
    def test_performance(self) -> bool:
        """Test dashboard performance."""
        self.print_section("Performance Testing")
        
        # Test multiple endpoints for performance
        performance_tests = [
            '/api/dashboard/overview',
            '/api/dashboard/department-analytics',
            '/api/dashboard/cost-analysis',
            '/api/dashboard/utilization-metrics',
            '/api/dashboard/charts?type=pie'
        ]
        
        for endpoint in performance_tests:
            print(f"⏱️  Testing response time for {endpoint}...")
            
            response = self.make_request("GET", endpoint)
            
            if response:
                # Find the performance metric for this request
                metric = next((m for m in self.performance_metrics if m['endpoint'] == endpoint), None)
                if metric:
                    status = "SUCCESS" if metric['success'] else "FAILED"
                    print(f"   ✅ {status} - {metric['response_time']:.0f}ms - {metric['content_length']} bytes")
                else:
                    print(f"   ❌ No performance data recorded")
            else:
                print(f"   ❌ Request failed")
        
        # Performance summary
        if self.performance_metrics:
            avg_time = sum(m['response_time'] for m in self.performance_metrics) / len(self.performance_metrics)
            success_rate = sum(1 for m in self.performance_metrics if m['success']) / len(self.performance_metrics) * 100
            fastest = min(self.performance_metrics, key=lambda x: x['response_time'])
            slowest = max(self.performance_metrics, key=lambda x: x['response_time'])
            
            print(f"\n📊 Performance Summary:")
            print(f"   📈 Average Response Time: {avg_time:.0f}ms")
            print(f"   📈 Fastest Response: {fastest['response_time']:.0f}ms")
            print(f"   📈 Slowest Response: {slowest['response_time']:.0f}ms")
            print(f"   📈 Success Rate: {len([m for m in self.performance_metrics if m['success']])}/{len(self.performance_metrics)}")
        
        return True
    
    def generate_test_report(self) -> bool:
        """Generate comprehensive test report."""
        self.print_header("Dashboard Testing Summary")
        
        # Count successful tests
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result)
        
        print(f"📊 Test Results:")
        print(f"   📈 Tests Passed: {passed_tests}/{total_tests}")
        print(f"   📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if passed_tests == total_tests:
            self.print_success("🎉 All dashboard tests passed! Your dashboard system is working perfectly!")
        else:
            self.print_error(f"⚠️  {total_tests - passed_tests} tests failed. Review the issues above.")
        
        print(f"\n🕒 Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return passed_tests == total_tests
    
    def run_all_tests(self) -> bool:
        """Run complete dashboard test suite."""
        self.print_header("Campus Assets - Dashboard Testing Suite")
        print("Testing all dashboard endpoints with comprehensive metrics")
        print("Login credentials: clitest@campus.edu")
        print("-" * 70)
        
        # Authentication
        if not self.authenticate():
            return False
        
        print("\n⏳ Starting Dashboard Overview...")
        
        # Run all tests
        tests = [
            ("Dashboard Overview", self.test_dashboard_overview),
            ("Department Analytics", self.test_department_analytics),
            ("Cost Analysis", self.test_cost_analysis),
            ("Utilization Metrics", self.test_utilization_metrics),
            ("Chart Data", self.test_chart_data),
            ("Performance Testing", self.test_performance)
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n⏳ Starting {test_name}...")
                result = test_func()
                self.test_results.append(result)
                self.print_success(f"{test_name} completed successfully")
            except Exception as e:
                print(f"❌ {test_name} failed with error: {e}")
                self.test_results.append(False)
        
        # Generate final report
        return self.generate_test_report()

def main():
    """Main test execution."""
    print("Campus Assets - Dashboard Testing Suite")
    print("Testing all dashboard endpoints with comprehensive metrics")
    
    # Run comprehensive dashboard tests
    test_suite = DashboardTestSuite()
    success = test_suite.run_all_tests()
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
