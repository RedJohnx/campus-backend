#!/usr/bin/env python3
"""
Test script for AI Integration functionality.
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

class AIIntegrationTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.auth_token = None
        self.current_user = None

    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"🤖 {title}")
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

    def make_request(self, method, endpoint, **kwargs):
        """Make HTTP request."""
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
            return response
            
        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return None

    def authenticate(self):
        """Authenticate with the system."""
        print("🔐 Authentication Required")
        
        # Try with default admin credentials
        email = "clitest@campus.edu"
        password = "123456**AA"
        
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

    def test_ai_status(self):
        """Test AI status endpoint."""
        self.print_section("AI Status Check")
        
        response = self.make_request("GET", "/api/ai/status")
        
        if response and response.status_code == 200:
            data = response.json()
            
            self.print_success("AI Status endpoint working")
            print(f"   GROQ API Configured: {'✅' if data.get('groq_api_configured') else '❌'}")
            print(f"   GROQ Model: {data.get('groq_model', 'N/A')}")
            
            api_test = data.get('api_test', {})
            if api_test.get('success'):
                self.print_success("GROQ API connection test passed")
                print(f"   Response: {api_test.get('response', 'N/A')}")
            else:
                self.print_error("GROQ API connection test failed")
                if api_test.get('error'):
                    print(f"   Error: {api_test['error']}")
            
            return api_test.get('success', False)
        else:
            self.print_error("AI Status endpoint failed")
            return False

    def test_ai_chat(self):
        """Test AI chat functionality."""
        self.print_section("AI Chat Test")
        
        test_queries = [
            "Hello, can you help me with resource information?",
            "How many computers are available?",
            "What equipment is in the Electronics department?"
        ]
        
        for query in test_queries:
            print(f"\n🤖 Testing query: {query}")
            
            chat_data = {
                "query": query,
                "session_id": None
            }
            
            response = self.make_request("POST", "/api/ai/chat", json=chat_data)
            
            if response and response.status_code == 200:
                data = response.json()
                ai_response = data.get('response', '')
                
                self.print_success("Chat query successful")
                print(f"   AI Response: {ai_response[:150]}...")
                
                if data.get('resources'):
                    print(f"   Found {len(data['resources'])} relevant resources")
                    
            else:
                self.print_error("Chat query failed")
                if response:
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data.get('error', 'Unknown error')}")
                    except:
                        print(f"   HTTP Error: {response.status_code}")

    def test_ai_crud(self):
        """Test AI CRUD functionality."""
        self.print_section("AI CRUD Test")
        
        if not self.current_user or self.current_user.get('role') != 'admin':
            self.print_error("Admin role required for CRUD testing")
            return
        
        test_instructions = [
            {
                'instruction': 'Add 2 test devices to Test Department in Lab-001, cost 1000 each, description test equipment for AI integration',
                'department': 'Test Department'
            },
            {
                'instruction': 'Create 1 AI test projector in Computer Science department, location Lab-CS-101, cost 25000, description high-resolution projector for presentations',
                'department': 'Computer Science'
            }
        ]
        
        for test_case in test_instructions:
            print(f"\n🔮 Testing instruction: {test_case['instruction']}")
            
            crud_data = {
                "instruction": test_case['instruction'],
                "department": test_case['department']
            }
            
            response = self.make_request("POST", "/api/ai/crud", json=crud_data)
            
            if response and response.status_code == 200:
                data = response.json()
                
                self.print_success("CRUD operation successful")
                print(f"   Operation: {data.get('operation', 'N/A')}")
                print(f"   Details: {data.get('details', 'N/A')}")
                
                resource_data = data.get('data', {})
                if resource_data:
                    print(f"   Created: {resource_data.get('device_name', 'N/A')}")
                    print(f"   Quantity: {resource_data.get('quantity', 'N/A')}")
                    print(f"   Cost: ₹{resource_data.get('cost', 0):,.2f}")
                    
            else:
                self.print_error("CRUD operation failed")
                if response:
                    try:
                        error_data = response.json()
                        print(f"   Error: {error_data.get('error', 'Unknown error')}")
                        
                        missing_fields = error_data.get('missing_fields', [])
                        if missing_fields:
                            print(f"   Missing fields: {', '.join(missing_fields)}")
                            
                    except:
                        print(f"   HTTP Error: {response.status_code}")

    def run_comprehensive_test(self):
        """Run comprehensive AI integration test."""
        self.print_header("AI Integration Comprehensive Test")
        
        # Check server health
        print("\n🏥 Checking server health...")
        response = self.make_request("GET", "/health")
        if not response or response.status_code != 200:
            self.print_error("Server is not running or unhealthy")
            return False
        
        self.print_success("Server is healthy")
        
        # Authenticate
        if not self.authenticate():
            return False
        
        # Test AI status
        ai_working = self.test_ai_status()
        
        # Test AI chat
        self.test_ai_chat()
        
        # Test AI CRUD (if admin)
        self.test_ai_crud()
        
        # Summary
        self.print_header("Test Summary")
        if ai_working:
            self.print_success("AI Integration is working properly!")
        else:
            self.print_error("AI Integration has issues - check GROQ API configuration")
        
        return ai_working

def main():
    """Main test execution."""
    print("Campus Assets - AI Integration Testing Suite")
    print("=" * 60)
    
    # Check environment variables
    groq_key = os.getenv('GROQ_API_KEY')
    if not groq_key:
        print("❌ GROQ_API_KEY not found in environment variables")
        print("   Please set GROQ_API_KEY in your .env file")
        return
    
    print(f"✅ GROQ_API_KEY found: {groq_key[:20]}...")
    
    tester = AIIntegrationTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎉 All tests passed! AI Integration is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration.")

if __name__ == "__main__":
    main()