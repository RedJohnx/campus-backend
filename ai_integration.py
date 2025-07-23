"""
AI Integration module for Campus Assets system.
Handles GROQ API integration for natural language processing.
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify
import requests

from database import get_db
from models import ResourceModel, DepartmentModel
from auth import require_auth, require_role
from resources import ensure_department_exists, update_department_locations, update_department_stats
from datetime import datetime, date
from bson import ObjectId

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
ai_bp = Blueprint('ai', __name__)

# GROQ API Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama3-8b-8192')

# ============================================================================
# AI-POWERED NATURAL LANGUAGE CRUD
# ============================================================================
@ai_bp.route('/crud', methods=['POST'])
@require_role('admin')
def ai_crud_operation():
    """Process natural language CRUD with enhanced error handling."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        instruction = data.get('instruction')
        department = data.get('department')
        
        if not instruction:
            return jsonify({'error': 'Instruction is required'}), 400
        
        if not department:
            return jsonify({'error': 'Department is required'}), 400
        
        # Check if GROQ API key is available
        if not GROQ_API_KEY:
            return jsonify({'error': 'GROQ API key not configured. Please set GROQ_API_KEY in environment variables.'}), 500
        
        logger.info(f"Processing AI CRUD instruction: {instruction} for department: {department}")
        
        # Process instruction with AI
        result = process_crud_instruction(instruction, department, str(request.current_user['_id']))
        
        if result['success']:
            return jsonify({
                'message': 'CRUD operation completed successfully',
                'operation': result['operation'],
                'details': result['details'],
                'data': result.get('data', {})
            }), 200
        else:
            return jsonify({
                'error': result['error'],
                'missing_fields': result.get('missing_fields', []),
                'suggestions': result.get('suggestions', [])
            }), 400
            
    except Exception as e:
        logger.error(f"Error processing AI CRUD operation: {e}")
        return jsonify({'error': f'Failed to process CRUD operation: {str(e)}'}), 500

def call_groq_api(prompt: str, max_tokens: int = 1000) -> Optional[str]:
    """Call GROQ API with enhanced error handling."""
    try:
        if not GROQ_API_KEY:
            logger.error("GROQ API key not configured")
            return None
            
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
            'max_tokens': max_tokens,
            'temperature': 0.3  # Lower temperature for more consistent responses
        }
        
        logger.info(f"Making GROQ API request with model: {GROQ_MODEL}")
        response = requests.post(
            f'{GROQ_BASE_URL}/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        logger.info(f"GROQ API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            logger.info(f"GROQ API response received: {len(content)} characters")
            return content
        else:
            logger.error(f"GROQ API error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("GROQ API request timeout")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"GROQ API request error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error calling GROQ API: {e}")
        return None

# ============================================================================
# AI CHATBOT FOR RESOURCE QUERIES
# ============================================================================

@ai_bp.route('/chat', methods=['POST'])
@require_auth
def ai_chat():
    """AI chatbot with proper JSON serialization."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        query = data.get('query')
        session_id = data.get('session_id')
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Check if GROQ API key is available
        if not GROQ_API_KEY:
            return jsonify({'error': 'GROQ API key not configured. Please set GROQ_API_KEY in environment variables.'}), 500
        
        logger.info(f"Processing AI chat query: {query}")
        
        # Process query with AI
        result = process_chat_query(query, session_id, str(request.current_user['_id']))
        
        # Use custom encoder for JSON serialization
        response_data = {
            'response': result['response'],
            'session_id': result['session_id'],
            'resources': result.get('resources', []),
            'statistics': result.get('statistics')
        }
        
        return json.dumps(response_data, cls=CustomJSONEncoder), 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        logger.error(f"Error processing AI chat: {e}")
        return jsonify({'error': 'Failed to process chat query'}), 500
        
# ============================================================================
# AI PROCESSING FUNCTIONS
# ============================================================================

def process_crud_instruction(instruction: str, department: str, user_id: str) -> Dict[str, Any]:
    """
    Process natural language CRUD instruction using GROQ AI.
    """
    try:
        # Prepare context for AI
        context = get_resource_context(department)
        
        # Create AI prompt for CRUD operation
        prompt = create_crud_prompt(instruction, department, context)
        
        # Call GROQ API
        ai_response = call_groq_api(prompt, max_tokens=1500)
        
        if not ai_response:
            return {
                'success': False,
                'error': 'Failed to get AI response. Please check GROQ API configuration.'
            }
        
        logger.info(f"AI Response: {ai_response}")
        
        # Parse AI response
        parsed_result = parse_crud_response(ai_response)
        
        if not parsed_result['valid']:
            return {
                'success': False,
                'error': parsed_result['error'],
                'missing_fields': parsed_result.get('missing_fields', []),
                'suggestions': parsed_result.get('suggestions', [])
            }
        
        # Execute the CRUD operation
        execution_result = execute_crud_operation(
            parsed_result['operation'], 
            parsed_result['data'], 
            department, 
            user_id
        )
        
        return execution_result
        
    except Exception as e:
        logger.error(f"Error processing CRUD instruction: {e}")
        return {
            'success': False,
            'error': f'Failed to process instruction: {str(e)}'
        }

def process_chat_query(query: str, session_id: Optional[str], user_id: str) -> Dict[str, Any]:
    """
    Process chat query using AI for resource information retrieval.
    """
    try:
        # Get or create session
        if not session_id:
            session_id = create_chat_session(user_id)
        
        # Get relevant resources based on query
        relevant_resources = search_relevant_resources(query)
        
        # Create chat context
        context = create_chat_context(relevant_resources, query)
        
        # Create AI prompt for chat
        prompt = create_chat_prompt(query, context)
        
        # Call GROQ API
        ai_response = call_groq_api(prompt)
        
        if not ai_response:
            return {
                'response': 'I apologize, but I encountered an error processing your query. Please try again.',
                'session_id': session_id
            }
        
        # Store chat interaction
        store_chat_interaction(session_id, query, ai_response)
        
        # Generate statistics if requested
        statistics = generate_query_statistics(query, relevant_resources)
        
        return {
            'response': ai_response,
            'session_id': session_id,
            'resources': relevant_resources[:5],  # Limit to top 5
            'statistics': statistics
        }
        
    except Exception as e:
        logger.error(f"Error processing chat query: {e}")
        return {
            'response': 'I apologize, but I encountered an error processing your query. Please try again.',
            'session_id': session_id or 'error'
        }



# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_resource_context(department: str) -> Dict[str, Any]:
    """Get comprehensive context about existing resources for AI processing."""
    try:
        db = get_db()
        
        # Get department resources count
        total_resources = db.resources.count_documents({'department': department})
        
        # Get unique locations and devices for the department
        locations = db.resources.distinct('location', {'department': department})
        device_types = db.resources.distinct('device_name', {'department': department})
        
        # Get ALL resources for the department (not just sample)
        all_resources = list(db.resources.find({'department': department}))
        
        # Get department statistics
        dept_stats = list(db.resources.aggregate([
            {'$match': {'department': department}},
            {'$group': {
                '_id': None,
                'total_quantity': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'avg_cost': {'$avg': '$cost'},
                'max_cost': {'$max': '$cost'},
                'min_cost': {'$min': '$cost'}
            }}
        ]))
        
        stats = dept_stats[0] if dept_stats else {}
        
        # Get location-wise breakdown
        location_breakdown = list(db.resources.aggregate([
            {'$match': {'department': department}},
            {'$group': {
                '_id': '$location',
                'resource_count': {'$sum': '$quantity'},
                'device_types': {'$addToSet': '$device_name'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}}
            }},
            {'$sort': {'resource_count': -1}}
        ]))
        
        # Get device type breakdown
        device_breakdown = list(db.resources.aggregate([
            {'$match': {'department': department}},
            {'$group': {
                '_id': '$device_name',
                'total_quantity': {'$sum': '$quantity'},
                'locations': {'$addToSet': '$location'},
                'avg_cost': {'$avg': '$cost'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}}
            }},
            {'$sort': {'total_quantity': -1}}
        ]))
        
        return {
            'department': department,
            'total_resources': total_resources,
            'total_quantity': stats.get('total_quantity', 0),
            'total_cost': stats.get('total_cost', 0),
            'avg_cost': stats.get('avg_cost', 0),
            'max_cost': stats.get('max_cost', 0),
            'min_cost': stats.get('min_cost', 0),
            'locations': locations,
            'device_types': device_types,
            'all_resources': all_resources,  # Include all resources
            'location_breakdown': location_breakdown,
            'device_breakdown': device_breakdown
        }
        
    except Exception as e:
        logger.error(f"Error getting resource context: {e}")
        return {'department': department, 'error': str(e)}

def create_crud_prompt(instruction: str, department: str, context: Dict[str, Any]) -> str:
    """Create AI prompt for CRUD operation."""
    return f"""Extract information from this instruction and return ONLY a JSON object.

INSTRUCTION: "{instruction}"
DEPARTMENT: {department}

Extract these fields:
- device_name: the item being added (e.g., "laptop", "projector", "whiteboard")
- quantity: number as integer (e.g., "5 laptops" → 5)
- cost: price as number (e.g., "cost 5000" → 5000.0)
- location: where it goes (e.g., "Lab-CS-101")
- description: what was provided or generate one

Return this exact JSON format (complete the JSON properly):
{{"operation": "create", "valid": true, "data": {{"device_name": "whiteboard", "quantity": 1, "description": "test whiteboard", "location": "Lab-CS-101", "cost": 5000.0, "procurement_date": null}}, "confidence": 0.95}}

ONLY return the JSON object. No other text."""

def create_chat_prompt(query: str, context: Dict[str, Any]) -> str:
    """Create AI prompt for chat response with comprehensive database context."""
    resources_summary = ""
    if context.get('resources'):
        total_resources = len(context['resources'])
        resources_summary = f"""
AVAILABLE RESOURCES ({total_resources} found):
"""
        # Show more resources for better context
        display_count = min(15, total_resources)
        for i, resource in enumerate(context['resources'][:display_count], 1):
            resources_summary += f"""
{i}. {resource.get('device_name', 'Unknown')}
   - Quantity: {resource.get('quantity', 0)}
   - Location: {resource.get('location', 'Unknown')}
   - Department: {resource.get('department', 'Unknown')}
   - Cost: ₹{resource.get('cost', 0):,.2f}
   - Description: {resource.get('description', 'No description')}
"""
        
        if total_resources > display_count:
            resources_summary += f"\n... and {total_resources - display_count} more resources"
    
    # Add department and location summaries
    dept_summary = ""
    if context.get('departments'):
        dept_summary = f"""
DEPARTMENTS ({len(context['departments'])}): {', '.join(context['departments'])}
"""
    
    location_summary = ""
    if context.get('locations'):
        location_summary = f"""
LOCATIONS ({len(context['locations'])}): {', '.join(context['locations'][:20])}
"""
        if len(context['locations']) > 20:
            location_summary += f"... and {len(context['locations']) - 20} more locations"
    
    device_summary = ""
    if context.get('device_types'):
        device_summary = f"""
DEVICE TYPES ({len(context['device_types'])}): {', '.join(context['device_types'][:15])}
"""
        if len(context['device_types']) > 15:
            device_summary += f"... and {len(context['device_types']) - 15} more device types"
    
    return f"""
You are an AI assistant for a college resource management system.
Answer the user's query about laboratory resources in a helpful and informative way.

DATABASE CONTEXT:
{dept_summary}
{location_summary}
{device_summary}

{resources_summary}

USER QUERY: "{query}"

INSTRUCTIONS:
- Provide a clear, helpful answer about the resources
- Include specific details like quantities, costs, and locations when relevant
- If asked about departments, list all departments with their resource counts
- If asked about locations, provide location details with departments
- If asked about devices, provide device information with quantities and locations
- Be conversational but informative
- Format costs in Indian Rupees (₹)
- Use the comprehensive database context provided above
- If you don't have specific information, say so clearly
"""


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime and ObjectId objects."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

def search_relevant_resources(query: str) -> List[Dict[str, Any]]:
    """Search for resources relevant to the query with comprehensive database access."""
    try:
        db = get_db()
        
        # Create search filter based on query keywords
        search_terms = query.lower().split()
        
        # Check for specific queries about departments or locations
        if any(word in query.lower() for word in ['department', 'departments', 'dept']):
            # Return department information
            departments = list(db.resources.aggregate([
                {'$group': {
                    '_id': '$department',
                    'resource_count': {'$sum': '$quantity'},
                    'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                    'unique_devices': {'$addToSet': '$device_name'},
                    'unique_locations': {'$addToSet': '$location'}
                }},
                {'$sort': {'resource_count': -1}}
            ]))
            
            # Convert to resource-like format for consistency
            resources = []
            for dept in departments:
                resources.append({
                    '_id': f"dept_{dept['_id']}",
                    'department': dept['_id'],
                    'device_name': f"Department Summary",
                    'quantity': dept['resource_count'],
                    'cost': dept['total_cost'],
                    'location': f"{len(dept['unique_locations'])} locations",
                    'description': f"Total devices: {len(dept['unique_devices'])}, Total resources: {dept['resource_count']}"
                })
            return resources
        
        if any(word in query.lower() for word in ['location', 'locations', 'where']):
            # Return location information
            locations = list(db.resources.aggregate([
                {'$group': {
                    '_id': {'location': '$location', 'department': '$department'},
                    'resource_count': {'$sum': '$quantity'},
                    'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                    'device_types': {'$addToSet': '$device_name'}
                }},
                {'$sort': {'resource_count': -1}},
                {'$limit': 100}  # Get more locations
            ]))
            
            # Convert to resource-like format
            resources = []
            for loc in locations:
                resources.append({
                    '_id': f"loc_{loc['_id']['location']}_{loc['_id']['department']}",
                    'department': loc['_id']['department'],
                    'location': loc['_id']['location'],
                    'device_name': f"Location Summary",
                    'quantity': loc['resource_count'],
                    'cost': loc['total_cost'],
                    'description': f"Device types: {len(loc['device_types'])}, Total resources: {loc['resource_count']}"
                })
            return resources
        
        # Build comprehensive search filter for regular queries
        search_conditions = []
        
        for term in search_terms:
            search_conditions.extend([
                {'device_name': {'$regex': term, '$options': 'i'}},
                {'description': {'$regex': term, '$options': 'i'}},
                {'location': {'$regex': term, '$options': 'i'}},
                {'department': {'$regex': term, '$options': 'i'}}
            ])
        
        search_filter = {'$or': search_conditions} if search_conditions else {}
        
        # Get more comprehensive results
        if not search_terms or len(query.strip()) < 3:
            # Return a representative sample from all departments
            resources = list(db.resources.find({}).limit(100))
        else:
            resources = list(db.resources.find(search_filter).limit(200))  # Much higher limit
        
        # Convert ObjectId and datetime objects to strings
        for resource in resources:
            resource['_id'] = str(resource['_id'])
            if 'created_at' in resource and isinstance(resource['created_at'], datetime):
                resource['created_at'] = resource['created_at'].isoformat()
            if 'updated_at' in resource and isinstance(resource['updated_at'], datetime):
                resource['updated_at'] = resource['updated_at'].isoformat()
            if 'procurement_date' in resource and isinstance(resource['procurement_date'], (datetime, date)):
                resource['procurement_date'] = resource['procurement_date'].isoformat()
            if 'created_by' in resource and isinstance(resource['created_by'], ObjectId):
                resource['created_by'] = str(resource['created_by'])
            if 'updated_by' in resource and isinstance(resource['updated_by'], ObjectId):
                resource['updated_by'] = str(resource['updated_by'])
            
        return resources
        
    except Exception as e:
        logger.error(f"Error searching resources: {e}")
        return []


def create_chat_context(resources: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """Create context for chat AI prompt."""
    return {
        'query': query,
        'resource_count': len(resources),
        'resources': resources,
        'departments': list(set(r['department'] for r in resources)),
        'locations': list(set(r['location'] for r in resources)),
        'device_types': list(set(r['device_name'] for r in resources))
    }

def create_chat_session(user_id: str) -> str:
    """Create a new chat session."""
    try:
        from bson import ObjectId
        
        session_id = str(ObjectId())
        db = get_db()
        
        session_doc = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now(),
            'messages': []
        }
        
        db.chat_sessions.insert_one(session_doc)
        return session_id
        
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        return str(ObjectId())

def store_chat_interaction(session_id: str, query: str, response: str):
    """Store chat interaction in database."""
    try:
        db = get_db()
        
        message = {
            'timestamp': datetime.now(),
            'user_message': query,
            'ai_response': response
        }
        
        db.chat_sessions.update_one(
            {'session_id': session_id},
            {'$push': {'messages': message}}
        )
        
    except Exception as e:
        logger.error(f"Error storing chat interaction: {e}")

def generate_query_statistics(query: str, resources: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Generate statistics for query results."""
    try:
        if not resources:
            return None
            
        total_cost = sum(r['cost'] * r['quantity'] for r in resources)
        total_quantity = sum(r['quantity'] for r in resources)
        
        return {
            'total_resources': len(resources),
            'total_cost': total_cost,
            'total_quantity': total_quantity,
            'departments': len(set(r['department'] for r in resources)),
            'locations': len(set(r['location'] for r in resources)),
            'device_types': len(set(r['device_name'] for r in resources))
        }
        
    except Exception as e:
        logger.error(f"Error generating statistics: {e}")
        return None

def parse_crud_response(response: str) -> Dict[str, Any]:
    """Parse AI response for CRUD operations with robust JSON extraction."""
    try:
        # Clean the response - sometimes AI adds extra text
        response = response.strip()
        logger.info(f"Raw AI response: {response}")
        
        # Try multiple methods to extract JSON
        json_str = None
        
        # Method 1: Look for JSON block markers
        json_block_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_block_match:
            json_str = json_block_match.group(1)
            logger.info("Found JSON in code block")
        
        # Method 2: Look for the first complete JSON object
        if not json_str:
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                logger.info("Found JSON object")
        
        # Method 3: Try the entire response as JSON
        if not json_str:
            json_str = response
            logger.info("Using entire response as JSON")
        
        # Clean up common JSON issues
        json_str = json_str.replace('\n', ' ').replace('\r', '')
        json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
        json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
        
        # Fix incomplete JSON - add missing closing braces
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        if open_braces > close_braces:
            json_str += '}' * (open_braces - close_braces)
            logger.info(f"Added {open_braces - close_braces} missing closing braces")
        
        logger.info(f"Cleaned JSON string: {json_str}")
        
        parsed = json.loads(json_str)
        
        if not parsed.get('valid', True):  # Default to True if not specified
            return {
                'valid': False,
                'error': parsed.get('error', 'Invalid operation'),
                'missing_fields': parsed.get('missing_fields', []),
                'suggestions': parsed.get('suggestions', [])
            }
        
        # Validate required fields for the operation
        operation = parsed.get('operation')
        data = parsed.get('data', {})
        
        if operation == 'create':
            required_fields = ['device_name', 'quantity', 'description', 'location', 'cost']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return {
                    'valid': False,
                    'error': f'Missing required fields: {", ".join(missing_fields)}',
                    'missing_fields': missing_fields
                }
        
        return {
            'valid': True,
            'operation': operation,
            'data': data,
            'search_criteria': parsed.get('search_criteria', {}),
            'confidence': parsed.get('confidence', 0.8)
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Response was: {response}")
        
        # Fallback: Try to extract key information manually
        return extract_crud_info_manually(response)
        
    except Exception as e:
        logger.error(f"Error parsing response: {e}")
        return {
            'valid': False,
            'error': f'Error parsing response: {str(e)}'
        }

def extract_crud_info_manually(response: str) -> Dict[str, Any]:
    """Manually extract CRUD information when JSON parsing fails."""
    try:
        logger.info("Attempting manual extraction of CRUD information")
        
        # Look for operation type
        operation = 'create'  # Default to create
        if 'update' in response.lower():
            operation = 'update'
        elif 'delete' in response.lower():
            operation = 'delete'
        elif 'read' in response.lower() or 'search' in response.lower():
            operation = 'read'
        
        # Try to extract key information using regex
        device_match = re.search(r'device[_\s]*name["\s]*:?\s*["\']([^"\']+)["\']?', response, re.IGNORECASE)
        quantity_match = re.search(r'quantity["\s]*:?\s*(\d+)', response, re.IGNORECASE)
        cost_match = re.search(r'cost["\s]*:?\s*(\d+(?:\.\d+)?)', response, re.IGNORECASE)
        location_match = re.search(r'location["\s]*:?\s*["\']([^"\']+)["\']?', response, re.IGNORECASE)
        description_match = re.search(r'description["\s]*:?\s*["\']([^"\']+)["\']?', response, re.IGNORECASE)
        
        data = {}
        if device_match:
            data['device_name'] = device_match.group(1).strip()
        if quantity_match:
            data['quantity'] = int(quantity_match.group(1))
        if cost_match:
            data['cost'] = float(cost_match.group(1))
        if location_match:
            data['location'] = location_match.group(1).strip()
        if description_match:
            data['description'] = description_match.group(1).strip()
        
        # Check if we have enough information
        required_fields = ['device_name', 'quantity', 'cost', 'location']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return {
                'valid': False,
                'error': f'Could not extract required fields: {", ".join(missing_fields)}',
                'missing_fields': missing_fields,
                'suggestions': ['Please provide a clearer instruction with all required details']
            }
        
        # Add default description if missing
        if 'description' not in data:
            data['description'] = f"{data['device_name']} - Added via AI integration"
        
        return {
            'valid': True,
            'operation': operation,
            'data': data,
            'confidence': 0.6  # Lower confidence for manual extraction
        }
        
    except Exception as e:
        logger.error(f"Manual extraction failed: {e}")
        return {
            'valid': False,
            'error': f'Failed to parse AI response: {str(e)}'
        }

def execute_crud_operation(operation: str, data: Dict[str, Any], department: str, user_id: str) -> Dict[str, Any]:
    """Execute the parsed CRUD operation."""
    try:
        db = get_db()
        
        if operation == 'create':
            return execute_create_operation(data, department, user_id, db)
        elif operation == 'update':
            return execute_update_operation(data, department, user_id, db)
        elif operation == 'delete':
            return execute_delete_operation(data, department, user_id, db)
        elif operation == 'read':
            return execute_read_operation(data, department, db)
        else:
            return {
                'success': False,
                'error': f'Unsupported operation: {operation}'
            }
        
    except Exception as e:
        logger.error(f"Error executing CRUD operation: {e}")
        return {
            'success': False,
            'error': f'Failed to execute operation: {str(e)}'
        }

def execute_create_operation(data: Dict[str, Any], department: str, user_id: str, db) -> Dict[str, Any]:
    """Execute create operation."""
    try:
        # Add department to data before validation
        data['department'] = department
        
        # Validate resource data
        validation_errors = ResourceModel.validate_resource_data(data)
        if validation_errors:
            return {
                'success': False,
                'error': 'Validation failed',
                'missing_fields': validation_errors
            }
        
        # Ensure department exists
        success, message = ensure_department_exists(department)
        if not success:
            return {
                'success': False,
                'error': f'Department error: {message}'
            }
        
        # Add location to department if new
        update_department_locations(department, data['location'])
        
        # Create resource document
        resource_doc = ResourceModel.create_resource_document(data, user_id)
        
        # Insert into database
        result = db.resources.insert_one(resource_doc)
        resource_doc['_id'] = str(result.inserted_id)
        
        # Update department statistics
        update_department_stats(department)
        
        logger.info(f"AI CRUD: Created resource {resource_doc['device_name']} in {department}")
        
        return {
            'success': True,
            'operation': 'create',
            'details': f"Successfully created {data['quantity']} {data['device_name']}(s) in {data['location']}",
            'data': {
                'resource_id': str(result.inserted_id),
                'device_name': data['device_name'],
                'quantity': data['quantity'],
                'location': data['location'],
                'cost': data['cost']
            }
        }
        
    except Exception as e:
        logger.error(f"Error in create operation: {e}")
        return {
            'success': False,
            'error': f'Failed to create resource: {str(e)}'
        }

def execute_update_operation(data: Dict[str, Any], department: str, user_id: str, db) -> Dict[str, Any]:
    """Execute update operation."""
    try:
        # For now, return a placeholder - update operations need search criteria
        return {
            'success': False,
            'error': 'Update operations require specific search criteria. Please specify which resource to update.'
        }
        
    except Exception as e:
        logger.error(f"Error in update operation: {e}")
        return {
            'success': False,
            'error': f'Failed to update resource: {str(e)}'
        }

def execute_delete_operation(data: Dict[str, Any], department: str, user_id: str, db) -> Dict[str, Any]:
    """Execute delete operation."""
    try:
        # For now, return a placeholder - delete operations need search criteria
        return {
            'success': False,
            'error': 'Delete operations require specific search criteria. Please specify which resource to delete.'
        }
        
    except Exception as e:
        logger.error(f"Error in delete operation: {e}")
        return {
            'success': False,
            'error': f'Failed to delete resource: {str(e)}'
        }

def execute_read_operation(data: Dict[str, Any], department: str, db) -> Dict[str, Any]:
    """Execute read operation."""
    try:
        # Build search filter
        search_filter = {'department': department}
        
        if data.get('device_name'):
            search_filter['device_name'] = {'$regex': data['device_name'], '$options': 'i'}
        if data.get('location'):
            search_filter['location'] = {'$regex': data['location'], '$options': 'i'}
        
        # Execute search
        resources = list(db.resources.find(search_filter).limit(10))
        
        # Convert ObjectIds to strings
        for resource in resources:
            resource['_id'] = str(resource['_id'])
            if 'created_by' in resource:
                resource['created_by'] = str(resource['created_by'])
            if 'updated_by' in resource:
                resource['updated_by'] = str(resource['updated_by'])
        
        return {
            'success': True,
            'operation': 'read',
            'details': f"Found {len(resources)} resources matching criteria",
            'data': {
                'resources': resources,
                'count': len(resources)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in read operation: {e}")
        return {
            'success': False,
            'error': f'Failed to read resources: {str(e)}'
        }

# ============================================================================
# COMPREHENSIVE DATABASE QUERY ENDPOINT
# ============================================================================

@ai_bp.route('/query-database', methods=['POST'])
@require_auth
def query_database():
    """Comprehensive database query endpoint for AI with full database access."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        query = data.get('query', '').lower()
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        db = get_db()
        result = {}
        
        # Department queries
        if any(word in query for word in ['department', 'departments', 'dept']):
            departments = list(db.resources.aggregate([
                {'$group': {
                    '_id': '$department',
                    'resource_count': {'$sum': '$quantity'},
                    'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                    'unique_devices': {'$addToSet': '$device_name'},
                    'unique_locations': {'$addToSet': '$location'},
                    'avg_cost': {'$avg': '$cost'}
                }},
                {'$sort': {'resource_count': -1}}
            ]))
            
            result['departments'] = []
            for dept in departments:
                result['departments'].append({
                    'name': dept['_id'],
                    'resource_count': dept['resource_count'],
                    'total_cost': dept['total_cost'],
                    'unique_devices_count': len(dept['unique_devices']),
                    'unique_locations_count': len(dept['unique_locations']),
                    'average_cost': dept['avg_cost'],
                    'device_types': dept['unique_devices'],
                    'locations': dept['unique_locations']
                })
        
        # Location queries
        if any(word in query for word in ['location', 'locations', 'where', 'place']):
            locations = list(db.resources.aggregate([
                {'$group': {
                    '_id': {'location': '$location', 'department': '$department'},
                    'resource_count': {'$sum': '$quantity'},
                    'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                    'device_types': {'$addToSet': '$device_name'},
                    'avg_cost': {'$avg': '$cost'}
                }},
                {'$sort': {'resource_count': -1}}
            ]))
            
            result['locations'] = []
            for loc in locations:
                result['locations'].append({
                    'location': loc['_id']['location'],
                    'department': loc['_id']['department'],
                    'resource_count': loc['resource_count'],
                    'total_cost': loc['total_cost'],
                    'device_types_count': len(loc['device_types']),
                    'average_cost': loc['avg_cost'],
                    'device_types': loc['device_types']
                })
        
        # Device queries
        if any(word in query for word in ['device', 'devices', 'equipment', 'item']):
            devices = list(db.resources.aggregate([
                {'$group': {
                    '_id': '$device_name',
                    'total_quantity': {'$sum': '$quantity'},
                    'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                    'departments': {'$addToSet': '$department'},
                    'locations': {'$addToSet': '$location'},
                    'avg_cost': {'$avg': '$cost'},
                    'max_cost': {'$max': '$cost'},
                    'min_cost': {'$min': '$cost'}
                }},
                {'$sort': {'total_quantity': -1}}
            ]))
            
            result['devices'] = []
            for device in devices:
                result['devices'].append({
                    'device_name': device['_id'],
                    'total_quantity': device['total_quantity'],
                    'total_cost': device['total_cost'],
                    'departments_count': len(device['departments']),
                    'locations_count': len(device['locations']),
                    'average_cost': device['avg_cost'],
                    'max_cost': device['max_cost'],
                    'min_cost': device['min_cost'],
                    'departments': device['departments'],
                    'locations': device['locations']
                })
        
        # Overall statistics
        total_stats = list(db.resources.aggregate([
            {'$group': {
                '_id': None,
                'total_resources': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'avg_cost': {'$avg': '$cost'},
                'unique_departments': {'$addToSet': '$department'},
                'unique_locations': {'$addToSet': '$location'},
                'unique_devices': {'$addToSet': '$device_name'}
            }}
        ]))
        
        if total_stats:
            stats = total_stats[0]
            result['overall_statistics'] = {
                'total_resources': stats['total_resources'],
                'total_cost': stats['total_cost'],
                'average_cost': stats['avg_cost'],
                'total_departments': len(stats['unique_departments']),
                'total_locations': len(stats['unique_locations']),
                'total_device_types': len(stats['unique_devices']),
                'departments': stats['unique_departments'],
                'locations': stats['unique_locations'],
                'device_types': stats['unique_devices']
            }
        
        return jsonify({
            'query': query,
            'results': result,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        return jsonify({'error': f'Failed to query database: {str(e)}'}), 500

# ============================================================================
# TEST AND STATUS ENDPOINTS
# ============================================================================

@ai_bp.route('/status', methods=['GET'])
@require_auth
def ai_status():
    """Check AI integration status."""
    try:
        status = {
            'groq_api_configured': bool(GROQ_API_KEY),
            'groq_model': GROQ_MODEL,
            'api_base_url': GROQ_BASE_URL
        }
        
        if GROQ_API_KEY:
            # Test API connection
            test_response = call_groq_api("Hello, this is a test. Please respond with 'AI integration working'.", max_tokens=50)
            status['api_test'] = {
                'success': bool(test_response),
                'response': test_response[:100] if test_response else None
            }
        else:
            status['api_test'] = {
                'success': False,
                'error': 'GROQ API key not configured'
            }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error checking AI status: {e}")
        return jsonify({'error': f'Failed to check AI status: {str(e)}'}), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@ai_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return jsonify({'error': 'Bad request'}), 400

@ai_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error'}), 500
