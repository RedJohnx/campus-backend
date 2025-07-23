"""
Resource management module for Campus Assets system.
Handles CRUD operations for laboratory equipment and resources.
Includes advanced filtering and search capabilities (Task 6).
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import logging
from bson import ObjectId
from database import get_db
from models import ResourceModel, DepartmentModel, ValidationError, handle_database_error
from auth import require_auth, require_role
from config import Config
import re

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
resources_bp = Blueprint('resources', __name__)

# ============================================================================
# BASIC RESOURCE CRUD OPERATIONS
# ============================================================================

@resources_bp.route('', methods=['GET'])
@require_auth
def get_resources():
    """
    Get all resources with pagination and filtering.
    Supports filtering by department, location, and device type.
    """
    try:
        db = get_db()
        
        # Get query parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        department = request.args.get('department')
        location = request.args.get('location')
        device_name = request.args.get('device_name')
        search = request.args.get('search')
        
        # Build query filter
        query_filter = {}
        
        if department:
            query_filter['department'] = department
            
        if location:
            query_filter['location'] = location
            
        if device_name:
            query_filter['device_name'] = {'$regex': device_name, '$options': 'i'}
            
        if search:
            query_filter['$or'] = [
                {'device_name': {'$regex': search, '$options': 'i'}},
                {'description': {'$regex': search, '$options': 'i'}},
                {'location': {'$regex': search, '$options': 'i'}}
            ]
        
        # Get total count
        total_count = db.resources.count_documents(query_filter)
        
        # Get resources with pagination
        skip = (page - 1) * per_page
        
        resources = list(db.resources.find(query_filter)
                        .sort('sl_no', 1)
                        .skip(skip)
                        .limit(per_page))
        
        # Convert ObjectId to string
        for resource in resources:
            resource['_id'] = str(resource['_id'])
            if resource.get('created_by'):
                resource['created_by'] = str(resource['created_by'])
            if resource.get('updated_by'):
                resource['updated_by'] = str(resource['updated_by'])
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        return jsonify({
            'resources': resources,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            },
            'filters': {
                'department': department,
                'location': location,
                'device_name': device_name,
                'search': search
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving resources: {e}")
        return jsonify({'error': 'Failed to retrieve resources'}), 500

@resources_bp.route('', methods=['POST'])
@require_role('admin')
def create_resource():
    """
    Create a new resource.
    Only admin users can create resources.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate resource data
        validation_errors = ResourceModel.validate_resource_data(data)
        if validation_errors:
            return jsonify({'error': 'Validation failed', 'details': validation_errors}), 400
        
        # Check if department exists, create if not
        department_name = data['department']
        success, message = ensure_department_exists(department_name)
        if not success:
            return jsonify({'error': message}), 400
        
        # Add location to department if new
        update_department_locations(department_name, data['location'])
        
        # Create resource document
        user_id = str(request.current_user['_id'])
        resource_doc = ResourceModel.create_resource_document(data, user_id)
        
        # Insert into database
        db = get_db()
        result = db.resources.insert_one(resource_doc)
        resource_doc['_id'] = str(result.inserted_id)
        
        # Update department statistics
        update_department_stats(department_name)
        
        logger.info(f"Resource created: {resource_doc['device_name']} by user {user_id}")
        
        return jsonify({
            'message': 'Resource created successfully',
            'resource': resource_doc
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating resource: {e}")
        return jsonify({'error': 'Failed to create resource'}), 500

@resources_bp.route('/<resource_id>', methods=['GET'])
@require_auth
def get_resource(resource_id):
    """
    Get a specific resource by ID.
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(resource_id):
            return jsonify({'error': 'Invalid resource ID'}), 400
        
        db = get_db()
        resource = db.resources.find_one({'_id': ObjectId(resource_id)})
        
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404
        
        # Convert ObjectId to string
        resource['_id'] = str(resource['_id'])
        if resource.get('created_by'):
            resource['created_by'] = str(resource['created_by'])
        if resource.get('updated_by'):
            resource['updated_by'] = str(resource['updated_by'])
        
        return jsonify({'resource': resource}), 200
        
    except Exception as e:
        logger.error(f"Error retrieving resource: {e}")
        return jsonify({'error': 'Failed to retrieve resource'}), 500

@resources_bp.route('/<resource_id>', methods=['PUT'])
@require_role('admin')
def update_resource(resource_id):
    """
    Update an existing resource with enhanced error handling.
    Only admin users can update resources.
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(resource_id):
            return jsonify({'error': 'Invalid resource ID format'}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Log the incoming data for debugging
        logger.info(f"Update request for {resource_id} with data: {data}")
        
        db = get_db()
        
        # Check if resource exists
        existing_resource = db.resources.find_one({'_id': ObjectId(resource_id)})
        if not existing_resource:
            return jsonify({'error': 'Resource not found'}), 404
        
        # Create update document (only include provided fields)
        update_fields = {}
        
        # Only update fields that are provided
        if 'device_name' in data:
            update_fields['device_name'] = data['device_name']
        if 'quantity' in data:
            try:
                update_fields['quantity'] = int(data['quantity'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Quantity must be a valid integer'}), 400
        if 'description' in data:
            update_fields['description'] = data['description']
        if 'location' in data:
            update_fields['location'] = data['location']
        if 'cost' in data:
            try:
                update_fields['cost'] = float(data['cost'])
            except (ValueError, TypeError):
                return jsonify({'error': 'Cost must be a valid number'}), 400
        if 'department' in data:
            update_fields['department'] = data['department']
        if 'procurement_date' in data:
            if data['procurement_date']:
                try:
                    if isinstance(data['procurement_date'], str):
                        update_fields['procurement_date'] = datetime.fromisoformat(data['procurement_date'].replace('Z', '+00:00'))
                    else:
                        update_fields['procurement_date'] = data['procurement_date']
                except ValueError:
                    return jsonify({'error': 'Invalid procurement date format. Use YYYY-MM-DD'}), 400
        
        # Check if any valid fields were provided
        if not update_fields:
            return jsonify({'error': 'No valid fields provided for update'}), 400
        
        # Add update metadata
        update_fields['updated_at'] = datetime.now(timezone.utc)
        update_fields['updated_by'] = ObjectId(request.current_user['_id'])
        
        # Store old department for stats update
        old_department = existing_resource['department']
        
        # Check if department exists (if department is being updated)
        if 'department' in update_fields:
            department_name = update_fields['department']
            success, message = ensure_department_exists(department_name)
            if not success:
                return jsonify({'error': message}), 400
            
            # Add location to department if location is also being updated
            if 'location' in update_fields:
                update_department_locations(department_name, update_fields['location'])
        
        # Perform update
        result = db.resources.update_one(
            {'_id': ObjectId(resource_id)},
            {'$set': update_fields}
        )
        
        if result.modified_count > 0:
            # Update department statistics
            update_department_stats(old_department)
            if 'department' in update_fields and update_fields['department'] != old_department:
                update_department_stats(update_fields['department'])
            
            # Get updated resource
            updated_resource = db.resources.find_one({'_id': ObjectId(resource_id)})
            if updated_resource:
                updated_resource['_id'] = str(updated_resource['_id'])
                if updated_resource.get('created_by'):
                    updated_resource['created_by'] = str(updated_resource['created_by'])
                if updated_resource.get('updated_by'):
                    updated_resource['updated_by'] = str(updated_resource['updated_by'])
            
            logger.info(f"Resource updated successfully: {resource_id}")
            
            return jsonify({
                'message': 'Resource updated successfully',
                'resource': updated_resource,
                'updated_fields': list(update_fields.keys())
            }), 200
        else:
            return jsonify({'error': 'No changes were made to the resource'}), 200
        
    except Exception as e:
        logger.error(f"Error updating resource {resource_id}: {e}")
        return jsonify({'error': f'Failed to update resource: {str(e)}'}), 500


@resources_bp.route('/delete', methods=['DELETE'])
@require_role('admin')
def delete_resource_by_criteria():
    """
    Delete resource by department, location, device name, and quantity.
    Only admin users can delete resources.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Get required criteria
        department = data.get('department')
        location = data.get('location')
        device_name = data.get('device_name')
        quantity = data.get('quantity')
        
        # Validate required fields
        if not all([department, location, device_name]):
            return jsonify({
                'error': 'Department, location, and device_name are required',
                'required_fields': ['department', 'location', 'device_name', 'quantity (optional)']
            }), 400
        
        db = get_db()
        
        # Build search criteria
        search_criteria = {
            'department': department,
            'location': location,
            'device_name': device_name
        }
        
        # Add quantity criteria if provided
        if quantity is not None:
            search_criteria['quantity'] = int(quantity)
        
        # Find matching resources
        matching_resources = list(db.resources.find(search_criteria))
        
        if not matching_resources:
            return jsonify({
                'error': 'No resources found matching the specified criteria',
                'search_criteria': search_criteria
            }), 404
        
        if len(matching_resources) > 1 and quantity is None:
            # Multiple matches found, require quantity specification
            resource_details = []
            for resource in matching_resources:
                resource_details.append({
                    'id': str(resource['_id']),
                    'sl_no': resource.get('sl_no'),
                    'quantity': resource.get('quantity'),
                    'cost': resource.get('cost'),
                    'procurement_date': resource.get('procurement_date')
                })
            
            return jsonify({
                'error': 'Multiple resources found. Please specify quantity to identify exact resource.',
                'matching_resources': resource_details,
                'suggestion': 'Add "quantity" field to your request to specify which resource to delete'
            }), 400
        
        # Get the resource to delete
        resource_to_delete = matching_resources[0]
        resource_id = resource_to_delete['_id']
        
        # Store resource details for response
        deleted_resource_info = {
            'id': str(resource_id),
            'sl_no': resource_to_delete.get('sl_no'),
            'device_name': resource_to_delete.get('device_name'),
            'quantity': resource_to_delete.get('quantity'),
            'location': resource_to_delete.get('location'),
            'department': resource_to_delete.get('department'),
            'cost': resource_to_delete.get('cost')
        }
        
        # Delete the resource
        result = db.resources.delete_one({'_id': resource_id})
        
        if result.deleted_count > 0:
            # Update department statistics
            update_department_stats(department)
            
            # Log the deletion
            user_id = str(request.current_user['_id'])
            logger.info(f"Resource deleted by criteria - User: {user_id}, Resource: {deleted_resource_info}")
            
            return jsonify({
                'message': 'Resource deleted successfully',
                'deleted_resource': deleted_resource_info,
                'deletion_criteria': search_criteria,
                'deleted_by': user_id
            }), 200
        else:
            return jsonify({'error': 'Failed to delete resource'}), 500
        
    except ValueError as e:
        return jsonify({'error': f'Invalid data type: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error deleting resource by criteria: {e}")
        return jsonify({'error': 'Failed to delete resource'}), 500

@resources_bp.route('/<resource_id>', methods=['DELETE'])
@require_role('admin')
def delete_resource(resource_id):
    """
    Delete a specific resource by ID.
    Only admin users can delete resources.
    """
    try:
        # Validate ObjectId
        if not ObjectId.is_valid(resource_id):
            return jsonify({'error': 'Invalid resource ID format'}), 400
        
        db = get_db()
        
        # Check if resource exists
        resource = db.resources.find_one({'_id': ObjectId(resource_id)})
        if not resource:
            return jsonify({'error': 'Resource not found'}), 404
        
        # Store resource details for response
        department = resource.get('department')
        deleted_resource_info = {
            'id': str(resource['_id']),
            'sl_no': resource.get('sl_no'),
            'device_name': resource.get('device_name'),
            'quantity': resource.get('quantity'),
            'location': resource.get('location'),
            'department': department,
            'cost': resource.get('cost')
        }
        
        # Delete the resource
        result = db.resources.delete_one({'_id': ObjectId(resource_id)})
        
        if result.deleted_count > 0:
            # Update department statistics
            if department:
                update_department_stats(department)
            
            # Log the deletion
            user_id = str(request.current_user['_id'])
            logger.info(f"Resource deleted by ID - User: {user_id}, Resource ID: {resource_id}")
            
            return jsonify({
                'message': 'Resource deleted successfully',
                'deleted_resource': deleted_resource_info,
                'deleted_by': user_id
            }), 200
        else:
            return jsonify({'error': 'Failed to delete resource'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting resource {resource_id}: {e}")
        return jsonify({'error': f'Failed to delete resource: {str(e)}'}), 500

@resources_bp.route('/search-for-deletion', methods=['POST'])
@require_role('admin')
def search_resources_for_deletion():
    """
    Search resources by criteria to preview what would be deleted.
    Helps users identify exact resources before deletion.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Get search criteria
        department = data.get('department')
        location = data.get('location')
        device_name = data.get('device_name')
        quantity = data.get('quantity')
        
        # Validate required fields
        if not all([department, location, device_name]):
            return jsonify({
                'error': 'Department, location, and device_name are required for search'
            }), 400
        
        db = get_db()
        
        # Build search criteria
        search_criteria = {
            'department': department,
            'location': location,
            'device_name': device_name
        }
        
        # Add quantity criteria if provided
        if quantity is not None:
            search_criteria['quantity'] = int(quantity)
        
        # Find matching resources
        matching_resources = list(db.resources.find(search_criteria).sort('sl_no', 1))
        
        if not matching_resources:
            return jsonify({
                'message': 'No resources found matching the criteria',
                'search_criteria': search_criteria,
                'matches': []
            }), 200
        
        # Format resource details for preview
        resource_previews = []
        for resource in matching_resources:
            resource_previews.append({
                'id': str(resource['_id']),
                'sl_no': resource.get('sl_no'),
                'device_name': resource.get('device_name'),
                'quantity': resource.get('quantity'),
                'description': resource.get('description'),
                'location': resource.get('location'),
                'department': resource.get('department'),
                'cost': resource.get('cost'),
                'procurement_date': resource.get('procurement_date'),
                'total_value': resource.get('cost', 0) * resource.get('quantity', 0)
            })
        
        return jsonify({
            'message': f'Found {len(matching_resources)} matching resource(s)',
            'search_criteria': search_criteria,
            'matches': resource_previews,
            'deletion_note': 'Use the DELETE /api/resources/delete endpoint with the same criteria to delete these resources'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid data type: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error searching resources for deletion: {e}")
        return jsonify({'error': 'Failed to search resources'}), 500

@resources_bp.route('/deletion/departments', methods=['GET'])
@require_auth
def get_departments_for_deletion():
    """
    Get all departments with resource counts for deletion interface.
    """
    try:
        db = get_db()
        
        # Get departments with resource counts
        pipeline = [
            {'$group': {
                '_id': '$department',
                'resource_count': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'unique_devices': {'$addToSet': '$device_name'},
                'unique_locations': {'$addToSet': '$location'}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        departments_data = list(db.resources.aggregate(pipeline))
        
        departments = []
        for dept_data in departments_data:
            departments.append({
                'name': dept_data['_id'],
                'resource_count': dept_data['resource_count'],
                'total_cost': dept_data['total_cost'],
                'unique_devices_count': len(dept_data['unique_devices']),
                'unique_locations_count': len(dept_data['unique_locations'])
            })
        
        return jsonify({
            'departments': departments,
            'total_departments': len(departments)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving departments for deletion: {e}")
        return jsonify({'error': 'Failed to retrieve departments'}), 500

@resources_bp.route('/deletion/locations/<department_name>', methods=['GET'])
@require_auth
def get_locations_for_deletion(department_name):
    """
    Get all locations for a department with resource counts for deletion interface.
    """
    try:
        db = get_db()
        
        # Get locations with resource counts for the department
        pipeline = [
            {'$match': {'department': department_name}},
            {'$group': {
                '_id': '$location',
                'resource_count': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'device_types': {'$addToSet': '$device_name'},
                'resource_entries': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        locations_data = list(db.resources.aggregate(pipeline))
        
        locations = []
        for loc_data in locations_data:
            locations.append({
                'name': loc_data['_id'],
                'resource_count': loc_data['resource_count'],
                'total_cost': loc_data['total_cost'],
                'device_types_count': len(loc_data['device_types']),
                'resource_entries': loc_data['resource_entries']
            })
        
        return jsonify({
            'department': department_name,
            'locations': locations,
            'total_locations': len(locations)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving locations for deletion: {e}")
        return jsonify({'error': 'Failed to retrieve locations'}), 500

@resources_bp.route('/deletion/devices/<department_name>/<location_name>', methods=['GET'])
@require_auth
def get_devices_for_deletion(department_name, location_name):
    """
    Get all device types for a department and location with resource counts for deletion interface.
    """
    try:
        db = get_db()
        
        # Get device types with resource counts for the department and location
        pipeline = [
            {'$match': {
                'department': department_name,
                'location': location_name
            }},
            {'$group': {
                '_id': '$device_name',
                'total_quantity': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'resource_entries': {'$sum': 1},
                'avg_cost': {'$avg': '$cost'},
                'resources': {'$push': {
                    'id': {'$toString': '$_id'},
                    'sl_no': '$sl_no',
                    'quantity': '$quantity',
                    'cost': '$cost',
                    'description': '$description',
                    'total_value': {'$multiply': ['$cost', '$quantity']}
                }}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        devices_data = list(db.resources.aggregate(pipeline))
        
        devices = []
        for device_data in devices_data:
            devices.append({
                'device_name': device_data['_id'],
                'total_quantity': device_data['total_quantity'],
                'total_cost': device_data['total_cost'],
                'resource_entries': device_data['resource_entries'],
                'average_cost': device_data['avg_cost'],
                'resources': device_data['resources']
            })
        
        return jsonify({
            'department': department_name,
            'location': location_name,
            'devices': devices,
            'total_device_types': len(devices)
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving devices for deletion: {e}")
        return jsonify({'error': 'Failed to retrieve devices'}), 500

@resources_bp.route('/deletion/preview', methods=['POST'])
@require_role('admin')
def preview_deletion():
    """
    Preview resources that would be deleted based on hierarchical criteria.
    Shows detailed information before actual deletion.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Get hierarchical criteria
        department = data.get('department')
        location = data.get('location')
        device_name = data.get('device_name')
        quantity = data.get('quantity')  # Optional for filtering specific quantity
        
        # Validate required fields
        if not all([department, location, device_name]):
            return jsonify({
                'error': 'Department, location, and device_name are required'
            }), 400
        
        db = get_db()
        
        # Build search criteria
        search_criteria = {
            'department': department,
            'location': location,
            'device_name': device_name
        }
        
        # Add quantity criteria if provided
        if quantity is not None:
            search_criteria['quantity'] = int(quantity)
        
        # Find matching resources
        matching_resources = list(db.resources.find(search_criteria).sort('sl_no', 1))
        
        if not matching_resources:
            return jsonify({
                'found': False,
                'message': 'No resources found matching the criteria',
                'search_criteria': search_criteria,
                'matches': []
            }), 200
        
        # Format resource details for preview
        resource_previews = []
        total_value = 0
        total_quantity = 0
        
        for resource in matching_resources:
            resource_value = resource.get('cost', 0) * resource.get('quantity', 0)
            total_value += resource_value
            total_quantity += resource.get('quantity', 0)
            
            resource_previews.append({
                'id': str(resource['_id']),
                'sl_no': resource.get('sl_no'),
                'device_name': resource.get('device_name'),
                'quantity': resource.get('quantity'),
                'description': resource.get('description'),
                'location': resource.get('location'),
                'department': resource.get('department'),
                'cost': resource.get('cost'),
                'procurement_date': resource.get('procurement_date'),
                'total_value': resource_value,
                'created_at': resource.get('created_at'),
                'updated_at': resource.get('updated_at')
            })
        
        # Determine if multiple resources require quantity specification
        requires_quantity_selection = len(matching_resources) > 1 and quantity is None
        
        return jsonify({
            'found': True,
            'message': f'Found {len(matching_resources)} matching resource(s)',
            'search_criteria': search_criteria,
            'matches': resource_previews,
            'summary': {
                'total_resources': len(matching_resources),
                'total_quantity': total_quantity,
                'total_value': total_value,
                'requires_quantity_selection': requires_quantity_selection
            },
            'deletion_ready': not requires_quantity_selection,
            'next_step': 'Specify quantity to identify exact resource' if requires_quantity_selection else 'Ready for deletion'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': f'Invalid data type: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error previewing deletion: {e}")
        return jsonify({'error': 'Failed to preview deletion'}), 500

@resources_bp.route('/deletion/execute', methods=['DELETE'])
@require_role('admin')
def execute_hierarchical_deletion():
    """
    Execute hierarchical deletion based on department, location, device, and quantity.
    This is the main deletion endpoint for the hierarchical approach.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Get hierarchical criteria
        department = data.get('department')
        location = data.get('location')
        device_name = data.get('device_name')
        quantity = data.get('quantity')
        
        # Validate required fields
        if not all([department, location, device_name]):
            return jsonify({
                'error': 'Department, location, and device_name are required',
                'required_fields': ['department', 'location', 'device_name', 'quantity (optional)']
            }), 400
        
        db = get_db()
        
        # Build search criteria
        search_criteria = {
            'department': department,
            'location': location,
            'device_name': device_name
        }
        
        # Add quantity criteria if provided
        if quantity is not None:
            search_criteria['quantity'] = int(quantity)
        
        # Find matching resources
        matching_resources = list(db.resources.find(search_criteria))
        
        if not matching_resources:
            return jsonify({
                'success': False,
                'error': 'No resources found matching the specified criteria',
                'search_criteria': search_criteria
            }), 404
        
        if len(matching_resources) > 1 and quantity is None:
            # Multiple matches found, require quantity specification
            resource_options = []
            for resource in matching_resources:
                resource_options.append({
                    'id': str(resource['_id']),
                    'sl_no': resource.get('sl_no'),
                    'quantity': resource.get('quantity'),
                    'cost': resource.get('cost'),
                    'description': resource.get('description'),
                    'total_value': resource.get('cost', 0) * resource.get('quantity', 0)
                })
            
            return jsonify({
                'success': False,
                'error': 'Multiple resources found. Please specify quantity to identify exact resource.',
                'matching_resources': resource_options,
                'suggestion': 'Add "quantity" field to your request to specify which resource to delete',
                'search_criteria': search_criteria
            }), 400
        
        # Get the resource to delete
        resource_to_delete = matching_resources[0]
        resource_id = resource_to_delete['_id']
        
        # Store resource details for response
        deleted_resource_info = {
            'id': str(resource_id),
            'sl_no': resource_to_delete.get('sl_no'),
            'device_name': resource_to_delete.get('device_name'),
            'quantity': resource_to_delete.get('quantity'),
            'description': resource_to_delete.get('description'),
            'location': resource_to_delete.get('location'),
            'department': resource_to_delete.get('department'),
            'cost': resource_to_delete.get('cost'),
            'total_value': resource_to_delete.get('cost', 0) * resource_to_delete.get('quantity', 0),
            'procurement_date': resource_to_delete.get('procurement_date')
        }
        
        # Delete the resource
        result = db.resources.delete_one({'_id': resource_id})
        
        if result.deleted_count > 0:
            # Update department statistics
            update_department_stats(department)
            
            # Log the deletion
            user_id = str(request.current_user['_id'])
            logger.info(f"Hierarchical resource deletion - User: {user_id}, Resource: {deleted_resource_info}")
            
            return jsonify({
                'success': True,
                'message': 'Resource deleted successfully using hierarchical selection',
                'deleted_resource': deleted_resource_info,
                'deletion_criteria': search_criteria,
                'deleted_by': user_id,
                'deletion_method': 'hierarchical'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to delete resource from database'
            }), 500
        
    except ValueError as e:
        return jsonify({'error': f'Invalid data type: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error executing hierarchical deletion: {e}")
        return jsonify({'error': 'Failed to execute deletion'}), 500

# Helper function for updating department stats
def update_department_stats(department_name):
    """Update department statistics after resource changes."""
    try:
        db = get_db()
        
        # Calculate updated statistics
        pipeline = [
            {'$match': {'department': department_name}},
            {'$group': {
                '_id': None,
                'resource_count': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'unique_devices': {'$addToSet': '$device_name'},
                'unique_locations': {'$addToSet': '$location'}
            }}
        ]
        
        result = list(db.resources.aggregate(pipeline))
        
        if result:
            stats = result[0]
            # Update department document
            db.departments.update_one(
                {'name': department_name},
                {
                    '$set': {
                        'resource_count': stats['resource_count'],
                        'total_cost': stats['total_cost'],
                        'unique_devices_count': len(stats['unique_devices']),
                        'unique_locations_count': len(stats['unique_locations']),
                        'last_updated': datetime.now()
                    }
                },
                upsert=True
            )
        else:
            # No resources left for this department
            db.departments.update_one(
                {'name': department_name},
                {
                    '$set': {
                        'resource_count': 0,
                        'total_cost': 0,
                        'unique_devices_count': 0,
                        'unique_locations_count': 0,
                        'last_updated': datetime.now()
                    }
                },
                upsert=True
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating department stats: {e}")
        return False


# ============================================================================
# TASK 6: ADVANCED FILTERING AND SEARCH SYSTEM
# ============================================================================

@resources_bp.route('/filter-options', methods=['GET'])
@require_auth
def get_filter_options():
    """
    Get available filter options with hierarchical structure.
    Returns departments, locations per department, and device types.
    """
    try:
        db = get_db()
        
        # Get all departments with their locations
        departments_data = []
        departments = db.departments.find({}).sort('name', 1)
        
        for dept in departments:
            dept_name = dept['name']
            
            # Get unique locations for this department
            locations = db.resources.distinct('location', {'department': dept_name})
            locations.sort()
            
            # Get unique device types for this department
            device_types = db.resources.distinct('device_name', {'department': dept_name})
            device_types.sort()
            
            # Get resource count and total cost for this department
            stats = db.resources.aggregate([
                {'$match': {'department': dept_name}},
                {'$group': {
                    '_id': None,
                    'total_resources': {'$sum': '$quantity'},
                    'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                    'unique_devices': {'$addToSet': '$device_name'}
                }}
            ])
            
            stats_result = list(stats)
            if stats_result:
                dept_stats = stats_result[0]
                total_resources = dept_stats['total_resources']
                total_cost = dept_stats['total_cost']
                unique_devices_count = len(dept_stats['unique_devices'])
            else:
                total_resources = 0
                total_cost = 0.0
                unique_devices_count = 0
            
            departments_data.append({
                'name': dept_name,
                'locations': locations,
                'device_types': device_types,
                'stats': {
                    'total_resources': total_resources,
                    'total_cost': total_cost,
                    'unique_devices': unique_devices_count,
                    'locations_count': len(locations)
                }
            })
        
        return jsonify({
            'departments': departments_data,
            'summary': {
                'total_departments': len(departments_data),
                'total_locations': sum(len(dept['locations']) for dept in departments_data),
                'total_device_types': len(set(
                    device for dept in departments_data for device in dept['device_types']
                ))
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving filter options: {e}")
        return jsonify({'error': 'Failed to retrieve filter options'}), 500

@resources_bp.route('/advanced-search', methods=['POST'])
@require_auth
def advanced_search():
    """
    Advanced search with multiple filters and criteria.
    Supports complex filtering combinations.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Extract search parameters
        search_query = data.get('query', '').strip()
        department = data.get('department')
        location = data.get('location')
        device_type = data.get('device_type')
        cost_range = data.get('cost_range', {})
        quantity_range = data.get('quantity_range', {})
        date_range = data.get('date_range', {})
        
        # Pagination parameters
        page = int(data.get('page', 1))
        per_page = min(int(data.get('per_page', 20)), 100)
        sort_by = data.get('sort_by', 'sl_no')
        sort_order = 1 if data.get('sort_order', 'asc') == 'asc' else -1
        
        # Build MongoDB query
        query_filter = {}
        
        # Text search across multiple fields
        if search_query:
            search_terms = search_query.split()
            search_conditions = []
            
            for term in search_terms:
                term_conditions = [
                    {'device_name': {'$regex': term, '$options': 'i'}},
                    {'description': {'$regex': term, '$options': 'i'}},
                    {'location': {'$regex': term, '$options': 'i'}},
                    {'department': {'$regex': term, '$options': 'i'}}
                ]
                search_conditions.append({'$or': term_conditions})
            
            if len(search_conditions) == 1:
                query_filter.update(search_conditions[0])
            else:
                query_filter['$and'] = search_conditions
        
        # Department filter
        if department:
            query_filter['department'] = department
        
        # Location filter
        if location:
            query_filter['location'] = location
        
        # Device type filter
        if device_type:
            query_filter['device_name'] = {'$regex': device_type, '$options': 'i'}
        
        # Cost range filter
        if cost_range:
            cost_filter = {}
            if 'min' in cost_range and cost_range['min'] is not None:
                cost_filter['$gte'] = float(cost_range['min'])
            if 'max' in cost_range and cost_range['max'] is not None:
                cost_filter['$lte'] = float(cost_range['max'])
            if cost_filter:
                query_filter['cost'] = cost_filter
        
        # Quantity range filter
        if quantity_range:
            qty_filter = {}
            if 'min' in quantity_range and quantity_range['min'] is not None:
                qty_filter['$gte'] = int(quantity_range['min'])
            if 'max' in quantity_range and quantity_range['max'] is not None:
                qty_filter['$lte'] = int(quantity_range['max'])
            if qty_filter:
                query_filter['quantity'] = qty_filter
        
        # Date range filter
        if date_range:
            date_filter = {}
            if 'start' in date_range and date_range['start']:
                date_filter['$gte'] = datetime.fromisoformat(date_range['start'].replace('Z', '+00:00'))
            if 'end' in date_range and date_range['end']:
                date_filter['$lte'] = datetime.fromisoformat(date_range['end'].replace('Z', '+00:00'))
            if date_filter:
                query_filter['procurement_date'] = date_filter
        
        db = get_db()
        
        # Get total count
        total_count = db.resources.count_documents(query_filter)
        
        # Get paginated results
        skip = (page - 1) * per_page
        
        resources = list(db.resources.find(query_filter)
                        .sort(sort_by, sort_order)
                        .skip(skip)
                        .limit(per_page))
        
        # Convert ObjectId to string
        for resource in resources:
            resource['_id'] = str(resource['_id'])
            if resource.get('created_by'):
                resource['created_by'] = str(resource['created_by'])
            if resource.get('updated_by'):
                resource['updated_by'] = str(resource['updated_by'])
        
        # Calculate aggregations for search results
        aggregation_pipeline = [
            {'$match': query_filter},
            {'$group': {
                '_id': None,
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'total_quantity': {'$sum': '$quantity'},
                'avg_cost': {'$avg': '$cost'},
                'departments': {'$addToSet': '$department'},
                'locations': {'$addToSet': '$location'},
                'device_types': {'$addToSet': '$device_name'}
            }}
        ]
        
        aggregation_result = list(db.resources.aggregate(aggregation_pipeline))
        
        if aggregation_result:
            agg_data = aggregation_result[0]
            search_summary = {
                'total_cost': agg_data['total_cost'],
                'total_quantity': agg_data['total_quantity'],
                'average_cost': agg_data['avg_cost'],
                'departments_count': len(agg_data['departments']),
                'locations_count': len(agg_data['locations']),
                'device_types_count': len(agg_data['device_types'])
            }
        else:
            search_summary = {
                'total_cost': 0,
                'total_quantity': 0,
                'average_cost': 0,
                'departments_count': 0,
                'locations_count': 0,
                'device_types_count': 0
            }
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        return jsonify({
            'resources': resources,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            },
            'filters_applied': {
                'query': search_query,
                'department': department,
                'location': location,
                'device_type': device_type,
                'cost_range': cost_range,
                'quantity_range': quantity_range,
                'date_range': date_range
            },
            'search_summary': search_summary,
            'execution_time': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        return jsonify({'error': 'Failed to perform advanced search'}), 500

@resources_bp.route('/filter/locations/<department_name>', methods=['GET'])
@require_auth
def get_locations_for_department(department_name):
    """
    Get all locations for a specific department with resource counts.
    Dynamic location population based on selected department.
    """
    try:
        db = get_db()
        
        # Get locations with resource counts
        pipeline = [
            {'$match': {'department': department_name}},
            {'$group': {
                '_id': '$location',
                'resource_count': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'device_types': {'$addToSet': '$device_name'},
                'latest_procurement': {'$max': '$procurement_date'}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        locations_data = list(db.resources.aggregate(pipeline))
        
        locations = []
        for loc_data in locations_data:
            locations.append({
                'name': loc_data['_id'],
                'resource_count': loc_data['resource_count'],
                'total_cost': loc_data['total_cost'],
                'device_types_count': len(loc_data['device_types']),
                'device_types': loc_data['device_types'],
                'latest_procurement': loc_data['latest_procurement'].isoformat() if loc_data['latest_procurement'] else None
            })
        
        return jsonify({
            'department': department_name,
            'locations': locations,
            'summary': {
                'total_locations': len(locations),
                'total_resources': sum(loc['resource_count'] for loc in locations),
                'total_cost': sum(loc['total_cost'] for loc in locations)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving locations for department: {e}")
        return jsonify({'error': 'Failed to retrieve locations'}), 500

@resources_bp.route('/filter/devices/<department_name>/<location_name>', methods=['GET'])
@require_auth
def get_devices_for_location(department_name, location_name):
    """
    Get all device types for a specific department and location.
    Third tier of the filtering system.
    """
    try:
        db = get_db()
        
        # Get device types with details
        pipeline = [
            {'$match': {
                'department': department_name,
                'location': location_name
            }},
            {'$group': {
                '_id': '$device_name',
                'total_quantity': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}},
                'avg_cost': {'$avg': '$cost'},
                'resource_ids': {'$push': '$_id'},
                'descriptions': {'$addToSet': '$description'},
                'latest_procurement': {'$max': '$procurement_date'}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        devices_data = list(db.resources.aggregate(pipeline))
        
        devices = []
        for device_data in devices_data:
            devices.append({
                'device_name': device_data['_id'],
                'total_quantity': device_data['total_quantity'],
                'total_cost': device_data['total_cost'],
                'average_cost': device_data['avg_cost'],
                'resource_count': len(device_data['resource_ids']),
                'descriptions': list(device_data['descriptions']),
                'latest_procurement': device_data['latest_procurement'].isoformat() if device_data['latest_procurement'] else None
            })
        
        return jsonify({
            'department': department_name,
            'location': location_name,
            'devices': devices,
            'summary': {
                'total_device_types': len(devices),
                'total_quantity': sum(dev['total_quantity'] for dev in devices),
                'total_cost': sum(dev['total_cost'] for dev in devices)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving devices for location: {e}")
        return jsonify({'error': 'Failed to retrieve devices'}), 500

@resources_bp.route('/quick-filters', methods=['GET'])
@require_auth
def get_quick_filters():
    """
    Get commonly used filter options for quick access.
    Includes top departments, locations, and device types by resource count.
    """
    try:
        db = get_db()
        
        # Top 5 departments by resource count
        top_departments = list(db.resources.aggregate([
            {'$group': {
                '_id': '$department',
                'resource_count': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}}
            }},
            {'$sort': {'resource_count': -1}},
            {'$limit': 5}
        ]))
        
        # Top 10 locations by resource count
        top_locations = list(db.resources.aggregate([
            {'$group': {
                '_id': '$location',
                'resource_count': {'$sum': '$quantity'},
                'department': {'$first': '$department'}
            }},
            {'$sort': {'resource_count': -1}},
            {'$limit': 10}
        ]))
        
        # Top 10 device types by count
        top_devices = list(db.resources.aggregate([
            {'$group': {
                '_id': '$device_name',
                'resource_count': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}}
            }},
            {'$sort': {'resource_count': -1}},
            {'$limit': 10}
        ]))
        
        # Recent additions (last 30 days)
        recent_date = datetime.now() - timedelta(days=30)
        recent_resources = db.resources.count_documents({
            'created_at': {'$gte': recent_date}
        })
        
        return jsonify({
            'top_departments': [
                {
                    'name': dept['_id'],
                    'resource_count': dept['resource_count'],
                    'total_cost': dept['total_cost']
                } for dept in top_departments
            ],
            'top_locations': [
                {
                    'name': loc['_id'],
                    'resource_count': loc['resource_count'],
                    'department': loc['department']
                } for loc in top_locations
            ],
            'top_devices': [
                {
                    'name': device['_id'],
                    'resource_count': device['resource_count'],
                    'total_cost': device['total_cost']
                } for device in top_devices
            ],
            'recent_additions': recent_resources,
            'generated_at': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving quick filters: {e}")
        return jsonify({'error': 'Failed to retrieve quick filters'}), 500

# ============================================================================
# DEPARTMENT AND LOCATION MANAGEMENT
# ============================================================================

@resources_bp.route('/departments', methods=['GET'])
@require_auth
def get_departments():
    """
    Get all departments with their locations.
    """
    try:
        db = get_db()
        departments = list(db.departments.find({}).sort('name', 1))
        
        # Convert ObjectId to string
        for dept in departments:
            dept['_id'] = str(dept['_id'])
        
        return jsonify({'departments': departments}), 200
        
    except Exception as e:
        logger.error(f"Error retrieving departments: {e}")
        return jsonify({'error': 'Failed to retrieve departments'}), 500

@resources_bp.route('/departments/<department_name>/locations', methods=['GET'])
@require_auth
def get_department_locations(department_name):
    """
    Get all locations for a specific department.
    """
    try:
        db = get_db()
        department = db.departments.find_one({'name': department_name})
        
        if not department:
            return jsonify({'error': 'Department not found'}), 404
        
        # Also get locations from actual resources (dynamic locations)
        resource_locations = db.resources.distinct('location', {'department': department_name})
        
        # Combine and deduplicate
        all_locations = list(set(department.get('locations', []) + resource_locations))
        all_locations.sort()
        
        return jsonify({
            'department': department_name,
            'locations': all_locations
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving department locations: {e}")
        return jsonify({'error': 'Failed to retrieve department locations'}), 500

@resources_bp.route('/departments', methods=['POST'])
@require_role('admin')
def create_department():
    """
    Create a new department.
    Only admin users can create departments.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate department data
        validation_errors = DepartmentModel.validate_department_data(data)
        if validation_errors:
            return jsonify({'error': 'Validation failed', 'details': validation_errors}), 400
        
        # Check if department already exists
        db = get_db()
        existing_dept = db.departments.find_one({'name': data['name']})
        if existing_dept:
            return jsonify({'error': 'Department already exists'}), 409
        
        # Create department document
        dept_doc = DepartmentModel.create_department_document(data)
        
        # Insert into database
        result = db.departments.insert_one(dept_doc)
        dept_doc['_id'] = str(result.inserted_id)
        
        logger.info(f"Department created: {data['name']} by user {str(request.current_user['_id'])}")
        
        return jsonify({
            'message': 'Department created successfully',
            'department': dept_doc
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating department: {e}")
        return jsonify({'error': 'Failed to create department'}), 500

# ============================================================================
# LEGACY FILTERING AND SEARCH (for backward compatibility)
# ============================================================================

@resources_bp.route('/filters', methods=['GET'])
@require_auth
def get_filter_options_legacy():
    """
    Get available filter options for resources (legacy endpoint).
    """
    try:
        db = get_db()
        
        # Get unique departments
        departments = db.resources.distinct('department')
        departments.sort()
        
        # Get unique locations
        locations = db.resources.distinct('location')
        locations.sort()
        
        # Get unique device names
        device_names = db.resources.distinct('device_name')
        device_names.sort()
        
        return jsonify({
            'departments': departments,
            'locations': locations,
            'device_names': device_names
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving filter options: {e}")
        return jsonify({'error': 'Failed to retrieve filter options'}), 500

@resources_bp.route('/search', methods=['GET'])
@require_auth
def search_resources():
    """
    Advanced search functionality for resources (legacy endpoint).
    """
    try:
        db = get_db()
        
        # Get search parameters
        query = request.args.get('query', '')
        filters = {
            'department': request.args.get('department'),
            'location': request.args.get('location'),
            'device_type': request.args.get('device_type'),
            'min_cost': request.args.get('min_cost'),
            'max_cost': request.args.get('max_cost'),
            'min_quantity': request.args.get('min_quantity'),
            'max_quantity': request.args.get('max_quantity')
        }
        
        # Build search query
        search_filter = {}
        
        if query:
            search_filter['$or'] = [
                {'device_name': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}},
                {'location': {'$regex': query, '$options': 'i'}}
            ]
        
        # Apply filters
        for key, value in filters.items():
            if value:
                if key in ['min_cost', 'max_cost']:
                    cost_filter = search_filter.get('cost', {})
                    if key == 'min_cost':
                        cost_filter['$gte'] = float(value)
                    else:
                        cost_filter['$lte'] = float(value)
                    search_filter['cost'] = cost_filter
                elif key in ['min_quantity', 'max_quantity']:
                    quantity_filter = search_filter.get('quantity', {})
                    if key == 'min_quantity':
                        quantity_filter['$gte'] = int(value)
                    else:
                        quantity_filter['$lte'] = int(value)
                    search_filter['quantity'] = quantity_filter
                else:
                    search_filter[key] = value
        
        # Execute search
        resources = list(db.resources.find(search_filter).sort('sl_no', 1))
        
        # Convert ObjectId to string
        for resource in resources:
            resource['_id'] = str(resource['_id'])
        
        return jsonify({
            'resources': resources,
            'count': len(resources),
            'query': query,
            'filters': filters
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching resources: {e}")
        return jsonify({'error': 'Failed to search resources'}), 500

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def ensure_department_exists(department_name: str) -> tuple:
    """
    Ensure department exists in database, create if not.
    
    Args:
        department_name: Name of the department
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        db = get_db()
        existing_dept = db.departments.find_one({'name': department_name})
        
        if not existing_dept:
            # Create new department
            dept_doc = DepartmentModel.create_department_document({
                'name': department_name,
                'locations': []
            })
            result = db.departments.insert_one(dept_doc)
            logger.info(f"Auto-created department: {department_name} with ID: {result.inserted_id}")
            return True, f"Created new department: {department_name}"
        
        return True, "Department already exists"
        
    except Exception as e:
        logger.error(f"Error ensuring department exists: {e}")
        return False, f"Failed to verify department: {str(e)}"

def update_department_locations(department_name: str, location: str) -> bool:
    """
    Add location to department if not already present.
    
    Args:
        department_name: Name of the department
        location: Location to add
        
    Returns:
        Success status
    """
    try:
        db = get_db()
        db.departments.update_one(
            {'name': department_name},
            {'$addToSet': {'locations': location}}
        )
        return True
        
    except Exception as e:
        logger.error(f"Error updating department locations: {e}")
        return False

def update_department_stats(department_name: str) -> bool:
    """
    Update department statistics (resource count, total cost).
    
    Args:
        department_name: Name of the department
        
    Returns:
        Success status
    """
    try:
        db = get_db()
        
        # Calculate statistics
        pipeline = [
            {'$match': {'department': department_name}},
            {'$group': {
                '_id': None,
                'resource_count': {'$sum': '$quantity'},
                'total_cost': {'$sum': {'$multiply': ['$cost', '$quantity']}}
            }}
        ]
        
        result = list(db.resources.aggregate(pipeline))
        
        if result:
            stats = result[0]
            db.departments.update_one(
                {'name': department_name},
                {'$set': {
                    'resource_count': stats['resource_count'],
                    'total_cost': stats['total_cost']
                }}
            )
        else:
            # No resources in department
            db.departments.update_one(
                {'name': department_name},
                {'$set': {
                    'resource_count': 0,
                    'total_cost': 0.0
                }}
            )
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating department stats: {e}")
        return False

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@resources_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return jsonify({'error': 'Bad request'}), 400

@resources_bp.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return jsonify({'error': 'Resource not found'}), 404

@resources_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error'}), 500
