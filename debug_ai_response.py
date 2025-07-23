#!/usr/bin/env python3
"""
Debug AI response to see what's being returned.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama3-8b-8192"

def test_groq_directly():
    """Test GROQ API directly to see what it returns."""
    
    prompt = """Extract information from this instruction and return ONLY a JSON object.

INSTRUCTION: "Add 1 test whiteboard to Computer Science department in Lab-CS-101, cost 5000, description test whiteboard for AI integration"
DEPARTMENT: Computer Science

Extract these fields:
- device_name: the item being added (e.g., "laptop", "projector", "whiteboard")
- quantity: number as integer (e.g., "5 laptops" → 5)
- cost: price as number (e.g., "cost 5000" → 5000.0)
- location: where it goes (e.g., "Lab-CS-101")
- description: what was provided or generate one

Return this exact JSON format (complete the JSON properly):
{"operation": "create", "valid": true, "data": {"device_name": "whiteboard", "quantity": 1, "description": "test whiteboard", "location": "Lab-CS-101", "cost": 5000.0, "procurement_date": null}, "confidence": 0.95}

ONLY return the JSON object. No other text."""
    
    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': GROQ_MODEL,
        'messages': [
            {
                'role': 'system',
                'content': 'You are an AI assistant for a college resource management system. Provide accurate, helpful responses in the requested format.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ],
        'max_tokens': 1500,
        'temperature': 0.1  # Very low temperature for consistent JSON
    }
    
    print("🔄 Testing GROQ API directly...")
    
    try:
        response = requests.post(
            f'{GROQ_BASE_URL}/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            print("✅ GROQ API Response:")
            print("=" * 60)
            print(ai_response)
            print("=" * 60)
            
            # Try to parse as JSON
            import json
            try:
                parsed = json.loads(ai_response)
                print("✅ Valid JSON!")
                print(f"Operation: {parsed.get('operation', 'NOT FOUND')}")
                print(f"Valid: {parsed.get('valid', 'NOT FOUND')}")
                print(f"Data: {parsed.get('data', 'NOT FOUND')}")
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                
                # Try to extract JSON manually
                import re
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    print(f"Extracted JSON: {json_str}")
                    
                    # Fix incomplete JSON
                    open_braces = json_str.count('{')
                    close_braces = json_str.count('}')
                    if open_braces > close_braces:
                        json_str += '}' * (open_braces - close_braces)
                        print(f"Fixed JSON: {json_str}")
                    
                    try:
                        parsed = json.loads(json_str)
                        print("✅ Fixed JSON is valid!")
                        print(f"Operation: {parsed.get('operation', 'NOT FOUND')}")
                        print(f"Data: {parsed.get('data', 'NOT FOUND')}")
                    except Exception as e2:
                        print(f"❌ Fixed JSON is still invalid: {e2}")
                
        else:
            print(f"❌ GROQ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_groq_directly()