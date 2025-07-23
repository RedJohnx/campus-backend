#!/usr/bin/env python3
"""
Simple CRUD test for AI Integration.
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_crud():
    # First authenticate
    login_data = {
        "email": "test.admin1@campus.edu",
        "password": "AdminPass123!"
    }
    
    print("🔐 Authenticating...")
    response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
    
    if response.status_code != 200:
        print(f"❌ Authentication failed: {response.status_code}")
        return
    
    auth_data = response.json()
    token = auth_data.get('token')
    print(f"✅ Authentication successful")
    
    # Test CRUD operation
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    crud_data = {
        'instruction': 'Add 1 test whiteboard to Computer Science department in Lab-CS-101, cost 5000, description test whiteboard for AI integration',
        'department': 'Computer Science'
    }
    
    print("🔮 Testing CRUD operation...")
    print(f"Instruction: {crud_data['instruction']}")
    
    try:
        response = requests.post(f"{BASE_URL}/api/ai/crud", headers=headers, json=crud_data, timeout=60)
        print(f"📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ CRUD operation successful!")
            print(f"Operation: {data.get('operation', 'N/A')}")
            print(f"Details: {data.get('details', 'N/A')}")
            
            resource_data = data.get('data', {})
            if resource_data:
                print(f"Created Resource:")
                print(f"  - Device: {resource_data.get('device_name', 'N/A')}")
                print(f"  - Quantity: {resource_data.get('quantity', 'N/A')}")
                print(f"  - Cost: ₹{resource_data.get('cost', 0):,.2f}")
        else:
            print("❌ CRUD operation failed")
            try:
                error_data = response.json()
                print(f"Error: {error_data.get('error', 'Unknown error')}")
                
                missing_fields = error_data.get('missing_fields', [])
                if missing_fields:
                    print(f"Missing fields: {', '.join(missing_fields)}")
                    
                suggestions = error_data.get('suggestions', [])
                if suggestions:
                    print("Suggestions:")
                    for suggestion in suggestions:
                        print(f"  - {suggestion}")
                        
            except:
                print(f"Raw response: {response.text}")
                
    except requests.exceptions.Timeout:
        print("❌ Request timeout - CRUD operation took too long")
    except Exception as e:
        print(f"❌ Request error: {e}")

if __name__ == "__main__":
    test_crud()