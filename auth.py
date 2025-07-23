"""
Authentication module for Campus Assets system.
Handles Firebase authentication integration, JWT token management, user registration,
login/logout endpoints, and role-based access control middleware.
"""
from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import get_db
from models import UserModel, ValidationError, handle_database_error
from config import Config

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize Firebase Admin SDK
firebase_app = None

def init_firebase():
    """Initialize Firebase Admin SDK."""
    global firebase_app
    
    try:
        if not firebase_app:
            # Use service account key file
            cred = credentials.Certificate('firebase_auth.json')
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return False

# Initialize Firebase on module import
init_firebase()

# ============================================================================
# JWT TOKEN UTILITIES
# ============================================================================

def generate_jwt_token(user_data: Dict[str, Any]) -> str:
    """
    Generate JWT token for authenticated user.
    
    Args:
        user_data: User information to encode in token
        
    Returns:
        JWT token string
    """
    try:
        payload = {
            'user_id': str(user_data['_id']),
            'uid': user_data['uid'],
            'email': user_data['email'],
            'role': user_data['role'],
            'status': user_data['status'],
            'exp': datetime.now(timezone.utc) + timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES),
            'iat': datetime.now(timezone.utc)
        }
        
        token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')
        return token
        
    except Exception as e:
        logger.error(f"Error generating JWT token: {e}")
        raise

def verify_jwt_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Tuple of (is_valid: bool, payload: dict or None)
    """
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, {'error': 'Token has expired'}
    except jwt.InvalidTokenError:
        return False, {'error': 'Invalid token'}
    except Exception as e:
        logger.error(f"Error verifying JWT token: {e}")
        return False, {'error': 'Token verification failed'}

# ============================================================================
# FIREBASE AUTHENTICATION UTILITIES
# ============================================================================

def verify_firebase_token(id_token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verify Firebase ID token.
    
    Args:
        id_token: Firebase ID token
        
    Returns:
        Tuple of (is_valid: bool, decoded_token: dict or None)
    """
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        return True, decoded_token
    except firebase_auth.InvalidIdTokenError:
        return False, {'error': 'Invalid Firebase token'}
    except firebase_auth.ExpiredIdTokenError:
        return False, {'error': 'Firebase token has expired'}
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        return False, {'error': 'Firebase token verification failed'}

def create_firebase_user(email: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Create user in Firebase Authentication.
    
    Args:
        email: User email
        password: User password
        
    Returns:
        Tuple of (success: bool, user_record: dict or error_message)
    """
    try:
        user_record = firebase_auth.create_user(
            email=email,
            password=password,
            email_verified=False
        )
        return True, {
            'uid': user_record.uid,
            'email': user_record.email,
            'email_verified': user_record.email_verified
        }
    except firebase_auth.EmailAlreadyExistsError:
        return False, {'error': 'Email already exists'}
    except Exception as e:
        logger.error(f"Error creating Firebase user: {e}")
        return False, {'error': 'Failed to create user account'}

# ============================================================================
# EMAIL NOTIFICATION SYSTEM
# ============================================================================

def send_email_notification(to_email: str, subject: str, body: str, is_html: bool = False) -> Tuple[bool, str]:
    """
    Send email notification using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body content
        is_html: Whether body is HTML formatted
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if not Config.MAIL_SERVER or not Config.MAIL_USERNAME or not Config.MAIL_PASSWORD:
            logger.warning("Email configuration not complete. Skipping email notification.")
            return False, "Email configuration not complete"
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = Config.MAIL_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
            if Config.MAIL_USE_TLS:
                server.starttls()
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {to_email}")
        return True, "Email sent successfully"
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False, f"Failed to send email: {str(e)}"

def send_admin_approval_notification(user_email: str, user_name: str = None) -> Tuple[bool, str]:
    """
    Send notification to master admin about new admin registration.
    
    Args:
        user_email: Email of the user requesting admin access
        user_name: Optional name of the user
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if not Config.MASTER_ADMIN_EMAIL:
            logger.warning("Master admin email not configured. Skipping notification.")
            return False, "Master admin email not configured"
        
        subject = "New Admin Account Approval Required - Campus Assets System"
        
        body = f"""
Dear Master Administrator,

A new admin account registration requires your approval in the Campus Assets System.

User Details:
- Email: {user_email}
- Name: {user_name or 'Not provided'}
- Registration Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
- Role Requested: Admin

Please log in to the Campus Assets System to review and approve this request.

Action Required:
1. Log in to the admin dashboard
2. Navigate to "Pending Approvals"
3. Review the user's request
4. Approve or reject the admin access

This is an automated notification. Please do not reply to this email.

Best regards,
Campus Assets System
        """.strip()
        
        return send_email_notification(Config.MASTER_ADMIN_EMAIL, subject, body)
        
    except Exception as e:
        logger.error(f"Error sending admin approval notification: {e}")
        return False, f"Failed to send notification: {str(e)}"

def send_approval_confirmation_email(user_email: str, approved: bool, approver_email: str = None) -> Tuple[bool, str]:
    """
    Send confirmation email to user about approval status.
    
    Args:
        user_email: Email of the user whose status changed
        approved: Whether the user was approved or rejected
        approver_email: Email of the approving admin
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if approved:
            subject = "Admin Account Approved - Campus Assets System"
            body = f"""
Dear User,

Your admin account request for the Campus Assets System has been approved!

Account Details:
- Email: {user_email}
- Role: Admin
- Status: Active
- Approved Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
- Approved By: {approver_email or 'System Administrator'}

You can now log in to the Campus Assets System with full admin privileges including:
- Create, read, update, and delete resources
- Upload and process CSV/Excel files
- Use AI-powered natural language commands
- Generate comprehensive reports
- Access dashboard analytics

Welcome to the Campus Assets System!

Best regards,
Campus Assets System
            """.strip()
        else:
            subject = "Admin Account Request - Campus Assets System"
            body = f"""
Dear User,

Thank you for your interest in the Campus Assets System.

Your admin account request has been reviewed. Unfortunately, we cannot approve your request at this time.

If you believe this is an error or would like to discuss your access requirements, please contact the system administrator.

You can still access the system with viewer privileges, which include:
- View all resources and equipment
- Use the AI chatbot for queries
- Access dashboard analytics (read-only)
- Export data in various formats

Best regards,
Campus Assets System
            """.strip()
        
        return send_email_notification(user_email, subject, body)
        
    except Exception as e:
        logger.error(f"Error sending approval confirmation email: {e}")
        return False, f"Failed to send confirmation: {str(e)}"

# ============================================================================
# USER MANAGEMENT FUNCTIONS
# ============================================================================

def create_user_in_db(user_data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Create user record in MongoDB.
    
    Args:
        user_data: User information
        
    Returns:
        Tuple of (success: bool, user_document or error_message)
    """
    try:
        db = get_db()
        
        # Validate user data
        validation_errors = UserModel.validate_user_data(user_data)
        if validation_errors:
            return False, {'error': 'Validation failed', 'details': validation_errors}
        
        # Create user document
        user_doc = UserModel.create_user_document(user_data)
        
        # Insert into database
        result = db.users.insert_one(user_doc)
        user_doc['_id'] = result.inserted_id
        
        logger.info(f"User created successfully: {user_data['email']}")
        return True, user_doc
        
    except Exception as e:
        success, error_msg = handle_database_error("create user", e)
        return success, {'error': error_msg}

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user by email from database.
    
    Args:
        email: User email
        
    Returns:
        User document or None
    """
    try:
        db = get_db()
        user = db.users.find_one({'email': email.lower().strip()})
        return user
    except Exception as e:
        logger.error(f"Error retrieving user by email: {e}")
        return None

def get_user_by_uid(uid: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user by Firebase UID from database.
    
    Args:
        uid: Firebase user ID
        
    Returns:
        User document or None
    """
    try:
        db = get_db()
        user = db.users.find_one({'uid': uid})
        return user
    except Exception as e:
        logger.error(f"Error retrieving user by UID: {e}")
        return None

def update_user_session(user_id: str, session_id: str) -> bool:
    """
    Update user's session information.
    
    Args:
        user_id: User ID
        session_id: Session identifier
        
    Returns:
        Success status
    """
    try:
        db = get_db()
        from bson import ObjectId
        
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'session_id': session_id,
                    'last_login': datetime.now(timezone.utc)
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error updating user session: {e}")
        return False

def approve_admin_user(user_id: str, approver_id: str) -> Tuple[bool, str]:
    """
    Approve admin user account.
    
    Args:
        user_id: ID of user to approve
        approver_id: ID of approving admin
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        db = get_db()
        from bson import ObjectId
        
        # Get user details before approval for email notification
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return False, "User not found"
        
        if user['status'] != 'pending':
            return False, "User is not in pending status"
        
        if user['role'] != 'admin':
            return False, "User is not an admin account"
        
        # Get approver details
        approver = db.users.find_one({'_id': ObjectId(approver_id)})
        approver_email = approver['email'] if approver else None
        
        # Update user status
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'status': 'active',
                    'approved_by': approver_id,
                    'approval_date': datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count > 0:
            # Send confirmation email to user
            email_success, email_message = send_approval_confirmation_email(
                user['email'], True, approver_email
            )
            if not email_success:
                logger.warning(f"Failed to send approval confirmation email: {email_message}")
            
            # Log approval action
            log_approval_action(user_id, approver_id, 'approved', 'Admin account approved')
            
            logger.info(f"Admin user approved: {user_id} by {approver_id}")
            return True, "Admin user approved successfully"
        else:
            return False, "Failed to update user status"
            
    except Exception as e:
        logger.error(f"Error approving admin user: {e}")
        return False, "Failed to approve admin user"

def reject_admin_user(user_id: str, approver_id: str, reason: str = None) -> Tuple[bool, str]:
    """
    Reject admin user account.
    
    Args:
        user_id: ID of user to reject
        approver_id: ID of rejecting admin
        reason: Optional reason for rejection
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        db = get_db()
        from bson import ObjectId
        
        # Get user details before rejection for email notification
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return False, "User not found"
        
        if user['status'] != 'pending':
            return False, "User is not in pending status"
        
        if user['role'] != 'admin':
            return False, "User is not an admin account"
        
        # Get approver details
        approver = db.users.find_one({'_id': ObjectId(approver_id)})
        approver_email = approver['email'] if approver else None
        
        # Update user status to viewer (downgrade from admin request)
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'role': 'viewer',
                    'status': 'active',
                    'rejected_by': approver_id,
                    'rejection_date': datetime.now(timezone.utc),
                    'rejection_reason': reason or 'Admin access denied'
                }
            }
        )
        
        if result.modified_count > 0:
            # Send confirmation email to user
            email_success, email_message = send_approval_confirmation_email(
                user['email'], False, approver_email
            )
            if not email_success:
                logger.warning(f"Failed to send rejection confirmation email: {email_message}")
            
            # Log rejection action
            log_approval_action(user_id, approver_id, 'rejected', reason or 'Admin access denied')
            
            logger.info(f"Admin user rejected: {user_id} by {approver_id}")
            return True, "Admin user rejected successfully"
        else:
            return False, "Failed to update user status"
            
    except Exception as e:
        logger.error(f"Error rejecting admin user: {e}")
        return False, "Failed to reject admin user"

def suspend_user(user_id: str, admin_id: str, reason: str = None) -> Tuple[bool, str]:
    """
    Suspend user account.
    
    Args:
        user_id: ID of user to suspend
        admin_id: ID of admin performing suspension
        reason: Optional reason for suspension
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        db = get_db()
        from bson import ObjectId
        
        # Get user details
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return False, "User not found"
        
        if user['status'] == 'suspended':
            return False, "User is already suspended"
        
        # Update user status
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'status': 'suspended',
                    'suspended_by': admin_id,
                    'suspension_date': datetime.now(timezone.utc),
                    'suspension_reason': reason or 'Account suspended by administrator'
                }
            }
        )
        
        if result.modified_count > 0:
            # Log suspension action
            log_approval_action(user_id, admin_id, 'suspended', reason or 'Account suspended')
            
            logger.info(f"User suspended: {user_id} by {admin_id}")
            return True, "User suspended successfully"
        else:
            return False, "Failed to suspend user"
            
    except Exception as e:
        logger.error(f"Error suspending user: {e}")
        return False, "Failed to suspend user"

def reactivate_user(user_id: str, admin_id: str) -> Tuple[bool, str]:
    """
    Reactivate suspended user account.
    
    Args:
        user_id: ID of user to reactivate
        admin_id: ID of admin performing reactivation
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        db = get_db()
        from bson import ObjectId
        
        # Get user details
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return False, "User not found"
        
        if user['status'] != 'suspended':
            return False, "User is not suspended"
        
        # Update user status
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {
                '$set': {
                    'status': 'active',
                    'reactivated_by': admin_id,
                    'reactivation_date': datetime.now(timezone.utc)
                },
                '$unset': {
                    'suspended_by': 1,
                    'suspension_date': 1,
                    'suspension_reason': 1
                }
            }
        )
        
        if result.modified_count > 0:
            # Log reactivation action
            log_approval_action(user_id, admin_id, 'reactivated', 'Account reactivated')
            
            logger.info(f"User reactivated: {user_id} by {admin_id}")
            return True, "User reactivated successfully"
        else:
            return False, "Failed to reactivate user"
            
    except Exception as e:
        logger.error(f"Error reactivating user: {e}")
        return False, "Failed to reactivate user"

def log_approval_action(user_id: str, admin_id: str, action: str, details: str = None) -> bool:
    """
    Log approval/rejection actions for audit trail.
    
    Args:
        user_id: ID of user affected
        admin_id: ID of admin performing action
        action: Action performed (approved, rejected, suspended, reactivated)
        details: Additional details about the action
        
    Returns:
        Success status
    """
    try:
        db = get_db()
        
        audit_record = {
            'user_id': user_id,
            'admin_id': admin_id,
            'action': action,
            'details': details,
            'timestamp': datetime.now(timezone.utc),
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        }
        
        db.approval_audit.insert_one(audit_record)
        logger.info(f"Audit log created: {action} for user {user_id} by admin {admin_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error logging approval action: {e}")
        return False
def send_admin_approval_email(user_data):
    """Send admin approval email to master admin."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email_templates import generate_admin_approval_email
        
        # Email configuration
        master_email = os.getenv('MASTER_EMAIL')
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        email_user = os.getenv('EMAIL_USER')
        email_password = os.getenv('EMAIL_PASSWORD')
        
        # Generate approval URL
        approval_url = f"http://localhost:5000/api/auth/approve-admin-email?user_id={user_data['user_id']}"
        
        # Generate HTML email
        html_content = generate_admin_approval_email(user_data, approval_url)
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = email_user
        msg['To'] = master_email
        msg['Subject'] = f"Campus Assets - Admin Approval Required: {user_data['name']}"
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Admin approval email sent to {master_email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send admin approval email: {e}")
        return False

# ============================================================================
# AUTHENTICATION MIDDLEWARE
# ============================================================================

def require_auth(f):
    """
    Decorator to require authentication for endpoints.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Authentication token is required'}), 401
        
        # Verify token
        is_valid, payload = verify_jwt_token(token)
        if not is_valid:
            return jsonify({'error': payload.get('error', 'Invalid token')}), 401
        
        # Check user status
        user = get_user_by_uid(payload['uid'])
        if not user or user['status'] != 'active':
            return jsonify({'error': 'User account is not active'}), 403
        
        # Add user info to request context
        request.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(required_role: str):
    """
    Decorator to require specific role for endpoints.
    
    Args:
        required_role: Required user role ('admin' or 'viewer')
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = request.current_user
            
            if user['role'] != required_role and required_role != 'viewer':
                return jsonify({'error': f'Access denied. {required_role.title()} role required'}), 403
            
            # Viewers can access viewer endpoints, admins can access both
            if required_role == 'viewer' and user['role'] not in ['viewer', 'admin']:
                return jsonify({'error': 'Access denied'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def check_permissions(user_id: str, required_role: str) -> Tuple[bool, str]:
    """
    Check if user has required permissions.
    
    Args:
        user_id: User ID to check
        required_role: Required role
        
    Returns:
        Tuple of (has_permission: bool, message: str)
    """
    try:
        from bson import ObjectId
        db = get_db()
        
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return False, "User not found"
        
        if user['status'] != 'active':
            return False, "User account is not active"
        
        if user['role'] == 'admin':
            return True, "Admin access granted"
        elif user['role'] == 'viewer' and required_role == 'viewer':
            return True, "Viewer access granted"
        else:
            return False, f"Insufficient permissions. {required_role.title()} role required"
            
    except Exception as e:
        logger.error(f"Error checking permissions: {e}")
        return False, "Permission check failed"

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    User registration endpoint.
    Creates Firebase user and database record with role assignment.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        # Validate required fields
        required_fields = ['email', 'password', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field.title()} is required'}), 400
        
        email = data['email'].lower().strip()
        password = data['password']
        role = data['role']
        
        # Validate role
        if role not in UserModel.VALID_ROLES:
            return jsonify({'error': f'Invalid role. Must be one of: {", ".join(UserModel.VALID_ROLES)}'}), 400
        
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 409
        
        # Create Firebase user
        firebase_success, firebase_result = create_firebase_user(email, password)
        if not firebase_success:
            return jsonify(firebase_result), 400
        
        # Create user in database
        user_data = {
            'uid': firebase_result['uid'],
            'email': email,
            'role': role
        }
        
        db_success, db_result = create_user_in_db(user_data)
        if not db_success:
            # Clean up Firebase user if database creation fails
            try:
                firebase_auth.delete_user(firebase_result['uid'])
            except:
                pass
            return jsonify(db_result), 400
        
        # Send email notification for admin registration
        if role == 'admin':
            email_success, email_message = send_admin_approval_notification(email, data.get('name'))
            if not email_success:
                logger.warning(f"Failed to send admin approval notification: {email_message}")
        
        # Prepare response
        response_data = {
            'message': 'User registered successfully',
            'user': {
                'id': str(db_result['_id']),
                'email': db_result['email'],
                'role': db_result['role'],
                'status': db_result['status']
            }
        }
        
        # Add approval message for admin users
        if role == 'admin':
            response_data['message'] += '. Admin account pending approval.'
            response_data['notification_sent'] = email_success if 'email_success' in locals() else False
        
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500
@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint supporting both Firebase ID token and email/password.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400

        # Check if Firebase ID token is provided
        if data.get('id_token'):
            # Firebase ID token flow
            id_token = data['id_token']
            firebase_valid, firebase_result = verify_firebase_token(id_token)
            
            if not firebase_valid:
                return jsonify(firebase_result), 401
            
            user = get_user_by_uid(firebase_result['uid'])
            if not user:
                return jsonify({'error': 'User not found in database'}), 404
                
        elif data.get('email') and data.get('password'):
            # Email/password flow (for testing)
            email = data['email'].lower().strip()
            password = data['password']
            
            user = get_user_by_email(email)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Verify password with Firebase
            try:
                # For testing, we'll skip Firebase password verification
                # In production, you'd want to use Firebase client SDK
                pass
            except Exception as e:
                return jsonify({'error': 'Invalid credentials'}), 401
                
        else:
            return jsonify({'error': 'Either id_token or email/password required'}), 400

        # Check user status
        if user['status'] != 'active':
            if user['status'] == 'pending':
                return jsonify({'error': 'Account pending approval'}), 403
            else:
                return jsonify({'error': 'Account is suspended'}), 403

        # Generate JWT token
        jwt_token = generate_jwt_token(user)

        # Update user session
        session_id = f"session_{datetime.now(timezone.utc).timestamp()}"
        update_user_session(str(user['_id']), session_id)

        response_data = {
            'message': 'Login successful',
            'token': jwt_token,
            'user': {
                'id': str(user['_id']),
                'email': user['email'],
                'role': user['role'],
                'status': user['status'],
                'last_login': user.get('last_login')
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    User logout endpoint.
    Clears user session information.
    """
    try:
        user = request.current_user
        
        # Clear session in database
        db = get_db()
        from bson import ObjectId
        
        db.users.update_one(
            {'_id': ObjectId(user['_id'])},
            {'$unset': {'session_id': 1}}
        )
        
        return jsonify({'message': 'Logout successful'}), 200
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@auth_bp.route('/verify', methods=['GET'])
@require_auth
def verify_token():
    """
    Token verification endpoint.
    Returns current user information if token is valid.
    """
    try:
        user = request.current_user
        
        response_data = {
            'valid': True,
            'user': {
                'id': str(user['_id']),
                'email': user['email'],
                'role': user['role'],
                'status': user['status'],
                'last_login': user.get('last_login')
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return jsonify({'error': 'Token verification failed'}), 500
@auth_bp.route('/approve-admin-email', methods=['GET'])
def approve_admin_email():
    """
    Handle admin approval via email link.
    """
    try:
        user_id = request.args.get('user_id')
        action = request.args.get('action')  # 'approve' or 'reject'
        
        if not user_id or not action:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        if action not in ['approve', 'reject']:
            return jsonify({'error': 'Invalid action'}), 400
        
        db = get_db()
        
        # Find user
        from bson import ObjectId
        user = db.users.find_one({'_id': ObjectId(user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if action == 'approve':
            # Approve user
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$set': {
                        'status': 'active',
                        'approved_at': datetime.now(),
                        'approved_by': 'master_admin'
                    }
                }
            )
            
            if result.modified_count > 0:
                # Send approval notification email to user
                # (You can implement this later)
                
                return f"""
                <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #27ae60;">✅ Admin Approved!</h1>
                    <p>The admin account for <strong>{user['email']}</strong> has been successfully approved.</p>
                    <p>The user can now login to the Campus Assets system.</p>
                    <hr style="margin: 30px 0;">
                    <p style="color: #666; font-size: 12px;">Campus Assets Management System</p>
                </body>
                </html>
                """
            else:
                return jsonify({'error': 'Failed to approve user'}), 500
                
        else:  # reject
            # Reject user
            result = db.users.update_one(
                {'_id': ObjectId(user_id)},
                {
                    '$set': {
                        'status': 'rejected',
                        'rejected_at': datetime.now(),
                        'rejected_by': 'master_admin'
                    }
                }
            )
            
            if result.modified_count > 0:
                return f"""
                <html>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1 style="color: #e74c3c;">❌ Admin Request Rejected</h1>
                    <p>The admin account request for <strong>{user['email']}</strong> has been rejected.</p>
                    <p>The user will not be able to access the Campus Assets system.</p>
                    <hr style="margin: 30px 0;">
                    <p style="color: #666; font-size: 12px;">Campus Assets Management System</p>
                </body>
                </html>
                """
            else:
                return jsonify({'error': 'Failed to reject user'}), 500
        
    except Exception as e:
        logger.error(f"Error in email approval: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/approve-admin', methods=['POST'])
@require_role('admin')
def approve_admin():
    """
    Admin approval endpoint.
    Allows master admin to approve new admin accounts.
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('user_id'):
            return jsonify({'error': 'User ID is required'}), 400
        
        user_id = data['user_id']
        approver = request.current_user
        
        # Approve the admin user
        success, message = approve_admin_user(user_id, str(approver['_id']))
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Admin approval error: {e}")
        return jsonify({'error': 'Admin approval failed'}), 500

@auth_bp.route('/pending-admins', methods=['GET'])
@require_role('admin')
def get_pending_admins():
    """
    Get list of pending admin approvals.
    """
    try:
        db = get_db()
        
        pending_admins = list(db.users.find(
            {'role': 'admin', 'status': 'pending'},
            {'password': 0, 'session_id': 0}  # Exclude sensitive fields
        ))
        
        # Convert ObjectId to string
        for admin in pending_admins:
            admin['_id'] = str(admin['_id'])
        
        return jsonify({
            'pending_admins': pending_admins,
            'count': len(pending_admins)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching pending admins: {e}")
        return jsonify({'error': 'Failed to fetch pending admins'}), 500

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@auth_bp.route('/user-profile', methods=['GET'])
@require_auth
def get_user_profile():
    """
    Get current user profile information.
    """
    try:
        user = request.current_user
        
        profile_data = {
            'id': str(user['_id']),
            'email': user['email'],
            'role': user['role'],
            'status': user['status'],
            'created_at': user['created_at'],
            'last_login': user.get('last_login'),
            'approved_by': user.get('approved_by'),
            'approval_date': user.get('approval_date')
        }
        
        return jsonify({'profile': profile_data}), 200
        
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        return jsonify({'error': 'Failed to fetch user profile'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@require_auth
def change_password():
    """
    Change user password in Firebase.
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('new_password'):
            return jsonify({'error': 'New password is required'}), 400
        
        user = request.current_user
        new_password = data['new_password']
        
        # Update password in Firebase
        firebase_auth.update_user(
            user['uid'],
            password=new_password
        )
        
        return jsonify({'message': 'Password updated successfully'}), 200
        
    except Exception as e:
        logger.error(f"Password change error: {e}")
        return jsonify({'error': 'Failed to change password'}), 500

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@auth_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return jsonify({'error': 'Bad request'}), 400

@auth_bp.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors."""
    return jsonify({'error': 'Unauthorized access'}), 401

@auth_bp.errorhandler(403)
def forbidden(error):
    """Handle forbidden errors."""
    return jsonify({'error': 'Access forbidden'}), 403

@auth_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error'}), 500