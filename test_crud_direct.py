#!/usr/bin/env python3
"""
Test CRUD execution directly without AI parsing.
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_crud_direct():
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
    
    # Test direct resource creation (bypass AI)
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    resource_data = {
        'device_name': 'Test AI Whiteboard',
        'quantity': 1,
        'description': 'Test whiteboard created via direct API call',
        'location': 'Lab-CS-101',
        'cost': 5000.0,
        'department': 'Computer Science'
    }
    
    print("📦 Testing direct resource creation...")
    response = requests.post(f"{BASE_URL}/api/resources", headers=headers, json=resource_data)
    
    print(f"📥 Response Status: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        print("✅ Direct resource creation successful!")
        print(f"Resource ID: {data.get('resource', {}).get('_id', 'N/A')}")
        print(f"Device: {data.get('resource', {}).get('device_name', 'N/A')}")
    else:
        print("❌ Direct resource creation failed")
        try:
            error_data = response.json()
            print(f"Error: {error_data.get('error', 'Unknown error')}")
        except:
            print(f"Raw response: {response.text}")

if __name__ == "__main__":
    test_crud_direct()