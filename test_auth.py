"""
Comprehensive authentication system testing with admin approval workflow.
Tests all auth endpoints with proper timing for manual approval.
"""

import requests
import json
import time
from datetime import datetime
import sys

BASE_URL = "http://localhost:5000"

class AuthenticationTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.test_users = []
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"🔐 {title}")
        print(f"{'='*60}")
    
    def print_success(self, message):
        print(f"✅ {message}")
    
    def print_error(self, message):
        print(f"❌ {message}")
    
    def print_info(self, message):
        print(f"ℹ️  {message}")
    
    def print_warning(self, message):
        print(f"⚠️  {message}")
    
    def make_request(self, method, endpoint, **kwargs):
        """Make HTTP request with error handling."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = getattr(self.session, method.lower())(url, timeout=30, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return None
    
    def test_server_health(self):
        """Test if server is running."""
        self.print_header("Server Health Check")
        
        response = self.make_request("GET", "/health")
        if response and response.status_code == 200:
            data = response.json()
            self.print_success("Server is healthy and running")
            self.print_info(f"Message: {data.get('message', 'N/A')}")
            return True
        else:
            self.print_error("Server is not responding")
            self.print_info("Please ensure Flask server is running: python app.py")
            return False
    
    def test_user_registration(self):
        """Test user registration with different roles."""
        self.print_header("User Registration Testing")
        
        # Test data for different user types
        test_users = [
            {
                "name": "Test Admin User",
                "email": "test.admin1@campus.edu",
                "password": "AdminPass123!",
                "role": "admin"
            },
            {
                "name": "Test Viewer User", 
                "email": "test.viewer1@campus.edu",
                "password": "ViewerPass123!",
                "role": "viewer"
            }
        ]
        
        registration_results = []
        
        for user_data in test_users:
            print(f"\n📝 Registering {user_data['role']} user: {user_data['email']}")
            
            response = self.make_request("POST", "/api/auth/register", json=user_data)
            
            if response:
                print(f"📥 Response Status: {response.status_code}")
                
                if response.status_code == 201:
                    data = response.json()
                    user_id = data.get('user', {}).get('id')
                    
                    self.print_success(f"{user_data['role'].title()} user registered successfully")
                    self.print_info(f"User ID: {user_id}")
                    
                    if user_data['role'] == 'admin':
                        self.print_warning("Admin account requires manual approval")
                        self.print_info("Please approve this user before proceeding with login tests")
                    else:
                        self.print_info("Viewer account is ready for immediate login")
                    
                    registration_results.append({
                        'user': user_data,
                        'user_id': user_id,
                        'status': 'success'
                    })
                    
                elif response.status_code == 409:
                    data = response.json()
                    self.print_warning(f"User already exists: {data.get('error', 'Unknown error')}")
                    registration_results.append({
                        'user': user_data,
                        'status': 'exists'
                    })
                else:
                    try:
                        error_data = response.json()
                        self.print_error(f"Registration failed: {error_data.get('error', 'Unknown error')}")
                    except:
                        self.print_error(f"Registration failed: HTTP {response.status_code}")
                    
                    registration_results.append({
                        'user': user_data,
                        'status': 'failed'
                    })
            else:
                self.print_error("No response from server")
                registration_results.append({
                    'user': user_data,
                    'status': 'no_response'
                })
        
        return registration_results
    
    def wait_for_admin_approval(self, email, wait_time=50):
        """Wait for admin approval with countdown."""
        self.print_header("Admin Approval Waiting Period")
        
        self.print_info(f"Waiting {wait_time} seconds for admin approval of: {email}")
        self.print_warning("Please use the admin approval system to approve the pending admin user")
        self.print_info("You can use CLI admin approval or database direct approval")
        
        # Countdown timer
        for remaining in range(wait_time, 0, -1):
            print(f"\r⏳ Waiting for approval... {remaining} seconds remaining", end="", flush=True)
            time.sleep(1)
        
        print(f"\n✅ Wait period completed. Proceeding with login test...")
    
    def test_user_login(self, registration_results):
        """Test user login for all registered users."""
        self.print_header("User Login Testing")
        
        login_results = []
        
        for reg_result in registration_results:
            if reg_result['status'] not in ['success', 'exists']:
                continue
                
            user_data = reg_result['user']
            
            # Wait for admin approval if needed
            if user_data['role'] == 'admin':
                self.wait_for_admin_approval(user_data['email'])
            
            print(f"\n🔑 Testing login for: {user_data['email']}")
            
            login_data = {
                "email": user_data['email'],
                "password": user_data['password']
            }
            
            response = self.make_request("POST", "/api/auth/login", json=login_data)
            
            if response:
                print(f"📥 Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get('token')
                    user_info = data.get('user', {})
                    
                    self.print_success(f"Login successful for {user_data['email']}")
                    self.print_info(f"Role: {user_info.get('role', 'Unknown')}")
                    self.print_info(f"Token length: {len(token) if token else 0} characters")
                    
                    login_results.append({
                        'email': user_data['email'],
                        'role': user_data['role'],
                        'token': token,
                        'user_info': user_info,
                        'status': 'success'
                    })
                    
                elif response.status_code == 403:
                    data = response.json()
                    error_msg = data.get('error', 'Forbidden')
                    
                    if "pending approval" in error_msg.lower():
                        self.print_warning(f"Admin approval still pending: {error_msg}")
                        self.print_info("Please approve the admin user and try again")
                    else:
                        self.print_error(f"Access forbidden: {error_msg}")
                    
                    login_results.append({
                        'email': user_data['email'],
                        'role': user_data['role'],
                        'status': 'pending_approval'
                    })
                    
                elif response.status_code == 404:
                    data = response.json()
                    self.print_error(f"User not found: {data.get('error', 'Unknown error')}")
                    
                    login_results.append({
                        'email': user_data['email'],
                        'role': user_data['role'],
                        'status': 'not_found'
                    })
                else:
                    try:
                        error_data = response.json()
                        self.print_error(f"Login failed: {error_data.get('error', 'Unknown error')}")
                    except:
                        self.print_error(f"Login failed: HTTP {response.status_code}")
                    
                    login_results.append({
                        'email': user_data['email'],
                        'role': user_data['role'],
                        'status': 'failed'
                    })
            else:
                self.print_error("No response from server")
                login_results.append({
                    'email': user_data['email'],
                    'role': user_data['role'],
                    'status': 'no_response'
                })
        
        return login_results
    
    def test_token_verification(self, login_results):
        """Test token verification for logged in users."""
        self.print_header("Token Verification Testing")
        
        for login_result in login_results:
            if login_result['status'] != 'success':
                continue
                
            email = login_result['email']
            token = login_result['token']
            
            print(f"\n🔍 Verifying token for: {email}")
            
            headers = {"Authorization": f"Bearer {token}"}
            response = self.make_request("GET", "/api/auth/verify", headers=headers)
            
            if response:
                print(f"📥 Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.print_success("Token verification successful")
                    self.print_info(f"User: {data.get('user', {}).get('email', 'Unknown')}")
                    self.print_info(f"Role: {data.get('user', {}).get('role', 'Unknown')}")
                else:
                    try:
                        error_data = response.json()
                        self.print_error(f"Token verification failed: {error_data.get('error', 'Unknown error')}")
                    except:
                        self.print_error(f"Token verification failed: HTTP {response.status_code}")
            else:
                self.print_error("No response from server")
    
    def test_logout(self, login_results):
        """Test logout functionality."""
        self.print_header("Logout Testing")
        
        for login_result in login_results:
            if login_result['status'] != 'success':
                continue
                
            email = login_result['email']
            token = login_result['token']
            
            print(f"\n🚪 Testing logout for: {email}")
            
            headers = {"Authorization": f"Bearer {token}"}
            response = self.make_request("POST", "/api/auth/logout", headers=headers)
            
            if response:
                print(f"📥 Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    self.print_success("Logout successful")
                else:
                    try:
                        error_data = response.json()
                        self.print_error(f"Logout failed: {error_data.get('error', 'Unknown error')}")
                    except:
                        self.print_error(f"Logout failed: HTTP {response.status_code}")
            else:
                self.print_error("No response from server")
    
    def generate_test_summary(self, registration_results, login_results):
        """Generate comprehensive test summary."""
        self.print_header("Authentication Test Summary")
        
        # Registration summary
        total_registrations = len(registration_results)
        successful_registrations = len([r for r in registration_results if r['status'] in ['success', 'exists']])
        
        print(f"\n📝 Registration Results:")
        print(f"   Total Attempts: {total_registrations}")
        print(f"   Successful: {successful_registrations}")
        print(f"   Success Rate: {(successful_registrations/total_registrations*100):.1f}%")
        
        # Login summary
        total_logins = len(login_results)
        successful_logins = len([r for r in login_results if r['status'] == 'success'])
        pending_approvals = len([r for r in login_results if r['status'] == 'pending_approval'])
        
        print(f"\n🔑 Login Results:")
        print(f"   Total Attempts: {total_logins}")
        print(f"   Successful: {successful_logins}")
        print(f"   Pending Approval: {pending_approvals}")
        print(f"   Success Rate: {(successful_logins/total_logins*100):.1f}%")
        
        # Overall assessment
        print(f"\n🎯 Overall Assessment:")
        if successful_logins > 0:
            self.print_success("Authentication system is functional")
            
            # Check if we have admin access
            admin_logins = [r for r in login_results if r.get('role') == 'admin' and r['status'] == 'success']
            if admin_logins:
                self.print_success("Admin authentication working - ready for resource testing")
                return admin_logins[0]['token']  # Return admin token for resource testing
            else:
                self.print_warning("No admin access available - resource testing may be limited")
        else:
            self.print_error("Authentication system needs attention")
        
        return None
    
    def run_comprehensive_auth_test(self):
        """Run complete authentication system test."""
        print("🔐 Campus Assets - Authentication System Testing")
        print("=" * 60)
        
        # Check server health
        if not self.test_server_health():
            return None
        
        # Test registration
        registration_results = self.test_user_registration()
        
        # Test login
        login_results = self.test_user_login(registration_results)
        
        # Test token verification
        self.test_token_verification(login_results)
        
        # Test logout
        self.test_logout(login_results)
        
        # Generate summary and return admin token if available
        admin_token = self.generate_test_summary(registration_results, login_results)
        
        return admin_token

def main():
    """Main test execution."""
    try:
        tester = AuthenticationTester()
        admin_token = tester.run_comprehensive_auth_test()
        
        if admin_token:
            print(f"\n🎉 Authentication testing completed successfully!")
            print(f"🔑 Admin token available for resource testing")
            print(f"💡 You can now run resource tests with this authenticated session")
        else:
            print(f"\n⚠️  Authentication testing completed with issues")
            print(f"💡 Please review the results above and fix any issues")
            
    except KeyboardInterrupt:
        print("\n\n👋 Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
