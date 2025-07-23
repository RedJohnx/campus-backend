"""
Database models and schemas for Campus Assets system.
Provides MongoDB collection schemas, validation functions, and utility operations.
"""
from datetime import datetime, timezone,date
from typing import Dict, List, Optional, Any, Tuple
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from database import get_db
import re
import logging



# Configure logging
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error for model validation."""
    pass

class DatabaseError(Exception):
    """Custom database error for database operations."""
    pass

# ============================================================================
# USER MODEL
# ============================================================================

class UserModel:
    """User model for authentication and role management."""
    
    VALID_ROLES = ['admin', 'viewer']
    VALID_STATUSES = ['active', 'pending', 'suspended']
    
    @staticmethod
    def validate_user_data(user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate user data and return validation errors.
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            Dictionary of field errors (empty if valid)
        """
        errors = {}
        
        # Validate email
        if not user_data.get('email'):
            errors['email'] = 'Email is required'
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', user_data['email']):
            errors['email'] = 'Invalid email format'
        
        # Validate role
        if not user_data.get('role'):
            errors['role'] = 'Role is required'
        elif user_data['role'] not in UserModel.VALID_ROLES:
            errors['role'] = f'Role must be one of: {", ".join(UserModel.VALID_ROLES)}'
        
        # Validate status if provided
        if user_data.get('status') and user_data['status'] not in UserModel.VALID_STATUSES:
            errors['status'] = f'Status must be one of: {", ".join(UserModel.VALID_STATUSES)}'
        
        # Validate Firebase UID
        if not user_data.get('uid'):
            errors['uid'] = 'Firebase UID is required'
        
        return errors
    
    @staticmethod
    def create_user_document(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a properly formatted user document for MongoDB insertion.
        
        Args:
            user_data: Raw user data
            
        Returns:
            Formatted user document
        """
        now = datetime.now(timezone.utc)
        
        return {
            'uid': user_data['uid'],
            'email': user_data['email'].lower().strip(),
            'role': user_data['role'],
            'status': user_data.get('status', 'pending' if user_data['role'] == 'admin' else 'active'),
            'created_at': now,
            'last_login': None,
            'session_id': None,
            'approved_by': user_data.get('approved_by'),
            'approval_date': user_data.get('approval_date')
        }

# ============================================================================
# RESOURCE MODEL
# ============================================================================

# class ResourceModel:
#     """Resource model for laboratory equipment management."""
    
#     REQUIRED_FIELDS = ['device_name', 'quantity', 'department', 'location']
#     OPTIONAL_FIELDS = ['description', 'procurement_date', 'cost']
    
#     @staticmethod
#     def validate_resource_data(resource_data: Dict[str, Any]) -> Dict[str, str]:
#         """
#         Validate resource data and return validation errors.
        
#         Args:
#             resource_data: Dictionary containing resource information
            
#         Returns:
#             Dictionary of field errors (empty if valid)
#         """
#         errors = {}
        
#         # Validate required fields
#         for field in ResourceModel.REQUIRED_FIELDS:
#             if not resource_data.get(field):
#                 errors[field] = f'{field.replace("_", " ").title()} is required'
        
#         # Validate device name
#         if resource_data.get('device_name'):
#             device_name = str(resource_data['device_name']).strip()
#             if len(device_name) < 2:
#                 errors['device_name'] = 'Device name must be at least 2 characters long'
#             elif len(device_name) > 200:
#                 errors['device_name'] = 'Device name must be less than 200 characters'
        
#         # Validate quantity
#         if resource_data.get('quantity') is not None:
#             try:
#                 quantity = int(resource_data['quantity'])
#                 if quantity < 0:
#                     errors['quantity'] = 'Quantity must be a non-negative number'
#             except (ValueError, TypeError):
#                 errors['quantity'] = 'Quantity must be a valid number'
        
#         # Validate cost if provided
#         if resource_data.get('cost') is not None and resource_data.get('cost') != '':
#             try:
#                 cost = float(resource_data['cost'])
#                 if cost < 0:
#                     errors['cost'] = 'Cost must be a non-negative number'
#             except (ValueError, TypeError):
#                 errors['cost'] = 'Cost must be a valid number'
        
#         # Validate department
#         if resource_data.get('department'):
#             department = str(resource_data['department']).strip()
#             if len(department) < 2:
#                 errors['department'] = 'Department name must be at least 2 characters long'
        
#         # Validate location
#         if resource_data.get('location'):
#             location = str(resource_data['location']).strip()
#             if len(location) < 2:
#                 errors['location'] = 'Location must be at least 2 characters long'
        
#         # Validate description length if provided
#         if resource_data.get('description') and len(str(resource_data['description'])) > 1000:
#             errors['description'] = 'Description must be less than 1000 characters'
        
#         return errors
    
#     @staticmethod
#     def create_resource_document(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
#         """Create resource document with enhanced date handling."""
#         print(f"🔍 Creating resource document...")
#         print(f"📅 Input procurement_date: {data.get('procurement_date')} (type: {type(data.get('procurement_date'))})")
        
#         # Get next serial number if not provided
#         db = get_db()
#         if 'sl_no' not in data:
#             last_resource = db.resources.find_one({}, sort=[('sl_no', -1)])
#             sl_no = (last_resource['sl_no'] + 1) if last_resource else 1
#         else:
#             sl_no = data['sl_no']
        
#         # Handle procurement date conversion
#         procurement_date = data.get('procurement_date')
        
#         if procurement_date:
#             if isinstance(procurement_date, str):
#                 print(f"📅 Converting string date: {procurement_date}")
#                 # Parse string date to datetime object
#                 try:
#                     # Try multiple formats
#                     date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y']
#                     parsed_date = None
                    
#                     for fmt in date_formats:
#                         try:
#                             parsed_date = datetime.strptime(procurement_date, fmt)
#                             break
#                         except ValueError:
#                             continue
                    
#                     if parsed_date:
#                         procurement_date = parsed_date
#                         print(f"📅 Successfully parsed to datetime: {procurement_date}")
#                     else:
#                         procurement_date = datetime.now()
#                         print(f"📅 Could not parse, using current date: {procurement_date}")
#                 except:
#                     procurement_date = datetime.now()
#                     print(f"📅 Parse error, using current date: {procurement_date}")
            
#             elif hasattr(procurement_date, 'date'):  # It's a date object
#                 print(f"📅 Converting date object to datetime")
#                 procurement_date = datetime.combine(procurement_date, datetime.min.time())
            
#             elif not isinstance(procurement_date, datetime):
#                 print(f"📅 Unknown date type, using current date")
#                 procurement_date = datetime.now()
#         else:
#             print(f"📅 No procurement date provided, using current date")
#             procurement_date = datetime.now()
        
#         # Ensure timezone awareness
#         if procurement_date.tzinfo is None:
#             procurement_date = procurement_date.replace(tzinfo=timezone.utc)
        
#         print(f"📅 Final procurement_date for storage: {procurement_date}")
        
#         document = {
#             'sl_no': sl_no,
#             'device_name': data['device_name'],
#             'quantity': data['quantity'],
#             'description': data['description'],
#             'procurement_date': procurement_date,  # Store as datetime
#             'location': data['location'],
#             'cost': data['cost'],
#             'department': data['department'],
#             'created_by': user_id,
#             'created_at': datetime.now(timezone.utc),
#             'updated_at': datetime.now(timezone.utc),
#             'updated_by': user_id
#         }
        
#         print(f"📋 Resource document created successfully")
#         return document

#     @staticmethod
#     def update_resource_document(resource_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
#         """
#         Create update document for resource modification.
        
#         Args:
#             resource_data: Updated resource data
#             user_id: ID of the user updating the resource
            
#         Returns:
#             Update document for MongoDB
#         """
#         now = datetime.now(timezone.utc)
#         update_doc = {'updated_at': now, 'updated_by': user_id}
        
#         # Only include fields that are being updated
#         updatable_fields = ['device_name', 'quantity', 'description', 'procurement_date', 'location', 'cost', 'department']
        
#         for field in updatable_fields:
#             if field in resource_data:
#                 if field == 'procurement_date' and resource_data[field]:
#                     if isinstance(resource_data[field], str):
#                         try:
#                             update_doc[field] = datetime.fromisoformat(resource_data[field].replace('Z', '+00:00'))
#                         except ValueError:
#                             continue
#                     elif isinstance(resource_data[field], datetime):
#                         update_doc[field] = resource_data[field]
#                 elif field == 'cost':
#                     update_doc[field] = float(resource_data[field]) if resource_data[field] not in [None, ''] else 0.0
#                 elif field == 'quantity':
#                     update_doc[field] = int(resource_data[field])
#                 else:
#                     update_doc[field] = str(resource_data[field]).strip()
        
#         return update_doc


class ResourceModel:
    """Resource data model with validation and document creation."""
    
    # @staticmethod
    # def create_resource_document(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    #     """
    #     Create a resource document for database insertion with proper date handling.
        
    #     Args:
    #         data: Resource data dictionary
    #         user_id: ID of the user creating the resource
            
    #     Returns:
    #         Complete resource document ready for database insertion
    #     """
    #     try:
    #         # Get next serial number
    #         from database import get_db
    #         db = get_db()
    #         last_resource = db.resources.find_one({}, sort=[('sl_no', -1)])
    #         next_sl_no = (last_resource['sl_no'] + 1) if last_resource else 1
            
    #         # Handle procurement date properly
    #         procurement_date = data.get('procurement_date')
            
    #         if procurement_date:
    #             # If it's already a date object, use it directly
    #             if isinstance(procurement_date, date):
    #                 final_procurement_date = procurement_date
    #             # If it's a string, try to parse it
    #             elif isinstance(procurement_date, str):
    #                 final_procurement_date = ResourceModel.parse_date_string(procurement_date)
    #             # If it's a datetime object, convert to date
    #             elif isinstance(procurement_date, datetime):
    #                 final_procurement_date = procurement_date.date()
    #             else:
    #                 # Fallback to current date
    #                 final_procurement_date = datetime.now().date()
    #                 logger.warning(f"Invalid procurement_date type: {type(procurement_date)}, using current date")
    #         else:
    #             # Use current date if no procurement date provided
    #             final_procurement_date = datetime.now().date()
            
    #         # Create the document
    #         document = {
    #             'sl_no': data.get('sl_no', next_sl_no),
    #             'device_name': data['device_name'],
    #             'quantity': int(data['quantity']),
    #             'description': data.get('description', ''),
    #             'procurement_date': final_procurement_date,  # Use the properly parsed date
    #             'location': data['location'],
    #             'cost': float(data['cost']),
    #             'department': data['department'],
    #             'created_by': user_id,
    #             'created_at': datetime.now(),  # This should be current time
    #             'updated_at': datetime.now(),  # This should be current time
    #             'updated_by': user_id
    #         }
            
    #         logger.info(f"Created resource document for {data['device_name']} with procurement_date: {final_procurement_date}")
            
    #         return document
            
    #     except Exception as e:
    #         logger.error(f"Error creating resource document: {e}")
    #         raise
    def create_resource_document(data: dict, user_id: str) -> dict:
        """Create resource document with proper datetime handling."""
        current_time = datetime.now()
        
        # Get next serial number
        db = get_db()
        last_resource = db.resources.find_one({}, sort=[('sl_no', -1)])
        next_sl_no = (last_resource['sl_no'] + 1) if last_resource else 1
        
        # Handle procurement date properly
        procurement_date = data.get('procurement_date')
        if isinstance(procurement_date, str):
            try:
                # Parse string date and convert to datetime
                procurement_date = datetime.fromisoformat(procurement_date)
            except:
                procurement_date = current_time
        elif isinstance(procurement_date, date) and not isinstance(procurement_date, datetime):
            # Convert date to datetime (add time component)
            procurement_date = datetime.combine(procurement_date, datetime.min.time())
        elif not isinstance(procurement_date, datetime):
            procurement_date = current_time
        
        resource_doc = {
            'sl_no': data.get('sl_no', next_sl_no),
            'device_name': data['device_name'],
            'quantity': int(data['quantity']),
            'description': data['description'],
            'procurement_date': procurement_date,  # Now guaranteed to be datetime
            'location': data['location'],
            'cost': float(data['cost']),
            'department': data['department'],
            'created_by': user_id,
            'created_at': current_time,
            'updated_at': current_time,
            'updated_by': user_id
        }
        
        return resource_doc

    @staticmethod
    def parse_date_string(date_string: str) -> date:
        """
        Parse various date string formats to date object.
        
        Args:
            date_string: Date string in various formats
            
        Returns:
            Parsed date object
        """
        import pandas as pd
        
        # Common date formats to try
        date_formats = [
            '%Y-%m-%d',      # 2024-01-20
            '%d-%m-%Y',      # 20-01-2024
            '%m/%d/%Y',      # 01/20/2024
            '%Y/%m/%d',      # 2024/01/20
            '%d/%m/%Y',      # 20/01/2024
            '%Y-%d-%m',      # 2024-20-01
            '%m-%d-%Y',      # 01-20-2024
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_string.strip(), fmt).date()
                logger.debug(f"Successfully parsed '{date_string}' with format '{fmt}' -> {parsed_date}")
                return parsed_date
            except ValueError:
                continue
        
        # If all formats fail, try pandas parsing as fallback
        try:
            parsed_date = pd.to_datetime(date_string).date()
            logger.debug(f"Successfully parsed '{date_string}' with pandas -> {parsed_date}")
            return parsed_date
        except Exception:
            pass
        
        # If everything fails, use current date and log warning
        logger.warning(f"Could not parse date string '{date_string}', using current date")
        return datetime.now().date()
    
    @staticmethod
    def update_resource_document(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Create update document for resource modification with proper date handling.
        
        Args:
            data: Update data dictionary
            user_id: ID of the user updating the resource
            
        Returns:
            Update document for database
        """
        update_doc = {
            'updated_at': datetime.now(),
            'updated_by': user_id
        }
        
        # Handle each field that can be updated
        for field in ['device_name', 'quantity', 'description', 'location', 'cost', 'department']:
            if field in data:
                if field == 'quantity':
                    update_doc[field] = int(data[field])
                elif field == 'cost':
                    update_doc[field] = float(data[field])
                else:
                    update_doc[field] = data[field]
        
        # Handle procurement date specially
        if 'procurement_date' in data:
            procurement_date = data['procurement_date']
            
            if isinstance(procurement_date, date):
                update_doc['procurement_date'] = procurement_date
            elif isinstance(procurement_date, str):
                update_doc['procurement_date'] = ResourceModel.parse_date_string(procurement_date)
            elif isinstance(procurement_date, datetime):
                update_doc['procurement_date'] = procurement_date.date()
            else:
                logger.warning(f"Invalid procurement_date type in update: {type(procurement_date)}")
        
        return update_doc
    
    @staticmethod
    def validate_resource_data(data: Dict[str, Any]) -> List[str]:
        """
        Validate resource data and return list of errors.
        
        Args:
            data: Resource data to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Required fields
        required_fields = ['device_name', 'quantity', 'location', 'cost', 'department']
        
        for field in required_fields:
            if field not in data or data[field] is None or str(data[field]).strip() == '':
                errors.append(f"'{field}' is required")
        
        # Validate quantity is positive integer
        if 'quantity' in data:
            try:
                quantity = int(data['quantity'])
                if quantity <= 0:
                    errors.append("'quantity' must be a positive integer")
            except (ValueError, TypeError):
                errors.append("'quantity' must be a valid integer")
        
        # Validate cost is positive number
        if 'cost' in data:
            try:
                cost = float(data['cost'])
                if cost < 0:
                    errors.append("'cost' must be a positive number")
            except (ValueError, TypeError):
                errors.append("'cost' must be a valid number")
        
        # Validate procurement date if provided
        if 'procurement_date' in data and data['procurement_date']:
            procurement_date = data['procurement_date']
            
            if isinstance(procurement_date, str):
                # Try to parse the date to validate format
                try:
                    ResourceModel.parse_date_string(procurement_date)
                except Exception:
                    errors.append("'procurement_date' has invalid date format")
            elif not isinstance(procurement_date, (date, datetime)):
                errors.append("'procurement_date' must be a valid date")
        
        return errors

# ============================================================================
# DEPARTMENT MODEL
# ============================================================================

class DepartmentModel:
    """Department model for organizational structure management."""
    
    @staticmethod
    def validate_department_data(department_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate department data and return validation errors.
        
        Args:
            department_data: Dictionary containing department information
            
        Returns:
            Dictionary of field errors (empty if valid)
        """
        errors = {}
        
        # Validate name
        if not department_data.get('name'):
            errors['name'] = 'Department name is required'
        else:
            name = str(department_data['name']).strip()
            if len(name) < 2:
                errors['name'] = 'Department name must be at least 2 characters long'
            elif len(name) > 100:
                errors['name'] = 'Department name must be less than 100 characters'
        
        # Validate locations if provided
        if department_data.get('locations'):
            if not isinstance(department_data['locations'], list):
                errors['locations'] = 'Locations must be a list'
            else:
                for i, location in enumerate(department_data['locations']):
                    if not isinstance(location, str) or len(location.strip()) < 2:
                        errors[f'locations[{i}]'] = 'Each location must be at least 2 characters long'
        
        return errors
    
    @staticmethod
    def create_department_document(department_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a properly formatted department document for MongoDB insertion.
        
        Args:
            department_data: Raw department data
            
        Returns:
            Formatted department document
        """
        now = datetime.now(timezone.utc)
        
        return {
            'name': str(department_data['name']).strip(),
            'locations': [str(loc).strip() for loc in department_data.get('locations', [])],
            'created_at': now,
            'resource_count': 0,
            'total_cost': 0.0
        }

# ============================================================================
# CHAT SESSION MODEL
# ============================================================================

class ChatSessionModel:
    """Chat session model for AI chatbot interactions."""
    
    VALID_ROLES = ['user', 'assistant']
    
    @staticmethod
    def validate_message_data(message_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate chat message data and return validation errors.
        
        Args:
            message_data: Dictionary containing message information
            
        Returns:
            Dictionary of field errors (empty if valid)
        """
        errors = {}
        
        # Validate role
        if not message_data.get('role'):
            errors['role'] = 'Message role is required'
        elif message_data['role'] not in ChatSessionModel.VALID_ROLES:
            errors['role'] = f'Role must be one of: {", ".join(ChatSessionModel.VALID_ROLES)}'
        
        # Validate content
        if not message_data.get('content'):
            errors['content'] = 'Message content is required'
        elif len(str(message_data['content'])) > 10000:
            errors['content'] = 'Message content must be less than 10000 characters'
        
        return errors
    
    @staticmethod
    def create_chat_session_document(user_id: str, session_title: str = None) -> Dict[str, Any]:
        """
        Create a properly formatted chat session document for MongoDB insertion.
        
        Args:
            user_id: ID of the user creating the session
            session_title: Optional title for the session
            
        Returns:
            Formatted chat session document
        """
        now = datetime.now(timezone.utc)
        
        return {
            'user_id': user_id,
            'session_title': session_title or f'Chat Session {now.strftime("%Y-%m-%d %H:%M")}',
            'messages': [],
            'created_at': now,
            'last_activity': now
        }
    
    @staticmethod
    def create_message_document(role: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a properly formatted message document.
        
        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional metadata
            
        Returns:
            Formatted message document
        """
        return {
            'role': role,
            'content': str(content).strip(),
            'timestamp': datetime.now(timezone.utc),
            'metadata': metadata or {}
        }

# ============================================================================
# DATABASE UTILITY FUNCTIONS
# ============================================================================

def handle_database_error(operation: str, error: Exception) -> Tuple[bool, str]:
    """
    Handle database errors and return standardized error response.
    
    Args:
        operation: Description of the operation that failed
        error: The exception that occurred
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    if isinstance(error, DuplicateKeyError):
        return False, f"Duplicate entry: {operation} failed due to existing record"
    elif isinstance(error, ValidationError):
        return False, f"Validation error: {str(error)}"
    else:
        logger.error(f"Database error during {operation}: {str(error)}")
        return False, f"Database operation failed: {operation}"

def sanitize_input(data: Any) -> Any:
    """
    Sanitize input data to prevent injection attacks.
    
    Args:
        data: Input data to sanitize
        
    Returns:
        Sanitized data
    """
    if isinstance(data, str):
        # Remove potential MongoDB operators and escape special characters
        return data.replace('$', '').replace('{', '').replace('}', '').strip()
    elif isinstance(data, dict):
        return {key: sanitize_input(value) for key, value in data.items() if not key.startswith('$')}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    else:
        return data

def validate_object_id(id_string: str) -> Tuple[bool, Optional[ObjectId]]:
    """
    Validate and convert string to ObjectId.
    
    Args:
        id_string: String representation of ObjectId
        
    Returns:
        Tuple of (is_valid: bool, object_id: ObjectId or None)
    """
    try:
        object_id = ObjectId(id_string)
        return True, object_id
    except Exception:
        return False, None

def get_collection_stats(collection_name: str) -> Dict[str, Any]:
    """
    Get statistics for a MongoDB collection.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Dictionary containing collection statistics
    """
    try:
        db = get_db()
        collection = db[collection_name]
        
        stats = {
            'count': collection.count_documents({}),
            'indexes': len(list(collection.list_indexes())),
            'size_bytes': db.command('collStats', collection_name).get('size', 0)
        }
        
        return stats
    except Exception as e:
        logger.error(f"Error getting collection stats for {collection_name}: {str(e)}")
        return {'count': 0, 'indexes': 0, 'size_bytes': 0}

def ensure_indexes():
    """
    Ensure all required indexes exist for optimal performance.
    This function can be called periodically to maintain indexes.
    """
    try:
        db = get_db()
        
        # Resources collection indexes
        db.resources.create_index([("department", 1)])
        db.resources.create_index([("location", 1)])
        db.resources.create_index([("device_name", 1)])
        db.resources.create_index([("created_at", -1)])
        db.resources.create_index([("department", 1), ("location", 1)])
        db.resources.create_index([("sl_no", 1)], unique=True)
        
        # Users collection indexes
        db.users.create_index([("email", 1)], unique=True)
        db.users.create_index([("uid", 1)], unique=True)
        db.users.create_index([("role", 1)])
        db.users.create_index([("status", 1)])
        
        # Departments collection indexes
        db.departments.create_index([("name", 1)], unique=True)
        
        # Chat sessions collection indexes
        db.chat_sessions.create_index([("user_id", 1)])
        db.chat_sessions.create_index([("created_at", -1)])
        db.chat_sessions.create_index([("last_activity", -1)])
        
        logger.info("All database indexes ensured successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error ensuring indexes: {str(e)}")
        return False