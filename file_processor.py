"""
File processing module for Campus Assets system.
Handles CSV/Excel file upload, validation, and batch import of resources.
"""

import pandas as pd
import numpy as np
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone,date  
import logging
import os
from typing import Dict, List, Optional, Tuple, Any
from werkzeug.utils import secure_filename
import tempfile
from bson import ObjectId

from database import get_db
from models import ResourceModel, DepartmentModel
from auth import require_role
from resources import ensure_department_exists, update_department_locations, update_department_stats

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
file_upload_bp = Blueprint('file_upload', __name__)

# File upload configuration
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
REQUIRED_COLUMNS = ['device_name', 'quantity', 'description', 'procurement_date', 'location', 'cost']
OPTIONAL_COLUMNS = ['sl_no']

# ============================================================================
# FILE UPLOAD ENDPOINTS
# ============================================================================
@file_upload_bp.route('/upload', methods=['POST'])
@require_role('admin')
def upload_file():
    """Upload and process CSV/Excel file with enhanced debugging."""
    try:
        print(f"📧 Upload request received")
        print(f"📧 Files in request: {list(request.files.keys())}")
        print(f"📧 Form data: {dict(request.form)}")
        
        # Check if file is in request
        if 'file' not in request.files:
            print("❌ No file in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        department = request.form.get('department')
        
        print(f"📧 File name: {file.filename}")
        print(f"📧 Department: {department}")
        print(f"📧 Content length: {request.content_length}")
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not department:
            return jsonify({'error': 'Department selection is required'}), 400
        
        # Validate file
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Please use CSV or Excel files.'}), 400
        
        # Check file size
        if request.content_length and request.content_length > MAX_FILE_SIZE:
            return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 400
        
        # Check if department exists (for custom departments)
        from resources import ensure_department_exists
        dept_result, dept_message = ensure_department_exists(department)
        
        if not dept_result:
            logger.error(f"Failed to ensure department exists: {dept_message}")
            return jsonify({'error': f"Department error: {dept_message}"}), 500
            
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)
        
        print(f"📧 File saved to: {temp_path}")
        
        try:
            # Process file
            result = process_uploaded_file(temp_path, department)
            print(f"📧 Processing result: {result.get('success', False)}")
            
            if result['success']:
                # Add department creation info to response
                is_new_dept = dept_message.startswith('Created new department')
                
                return jsonify({
                    'message': 'File processed successfully',
                    'preview': result['preview'],
                    'warnings': result['warnings'],
                    'stats': result['stats'],
                    'file_id': result['file_id'],
                    'department_created': is_new_dept,
                    'department_message': dept_message if is_new_dept else None
                }), 200
            else:
                return jsonify({'error': result['error']}), 400
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        print(f"❌ Upload error: {e}")
        return jsonify({'error': 'Failed to upload file'}), 500

@file_upload_bp.route('/validate', methods=['POST'])
@require_role('admin')
def validate_file():
    """
    Validate uploaded file without importing data.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        department = request.form.get('department')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not department:
            return jsonify({'error': 'Department selection is required'}), 400
        
        # Validate file
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(tempfile.gettempdir(), filename)
        file.save(temp_path)
        
        try:
            # Validate file structure
            validation_result = validate_file_structure(temp_path, department)
            
            return jsonify({
                'valid': validation_result['valid'],
                'errors': validation_result['errors'],
                'warnings': validation_result['warnings'],
                'preview': validation_result['preview'],
                'stats': validation_result['stats']
            }), 200
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
    except Exception as e:
        logger.error(f"Error validating file: {e}")
        return jsonify({'error': 'Failed to validate file'}), 500

@file_upload_bp.route('/import', methods=['POST'])
@require_role('admin')
def import_data():
    """
    Import validated data into database.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data is required'}), 400
        
        file_id = data.get('file_id')
        department = data.get('department')
        proceed_with_warnings = data.get('proceed_with_warnings', False)
        
        if not file_id or not department:
            return jsonify({'error': 'File ID and department are required'}), 400
        
        # Get processed file data from temporary storage
        file_data = get_temp_file_data(file_id)
        if not file_data:
            return jsonify({'error': 'File data not found or expired'}), 404
        
        # Check if warnings exist and user hasn't confirmed
        if file_data['warnings'] and not proceed_with_warnings:
            return jsonify({
                'error': 'File contains warnings. Please review and confirm.',
                'warnings': file_data['warnings']
            }), 400
        
        # Ensure department exists (create if it's a new custom department)
        from resources import ensure_department_exists
        dept_result, dept_message = ensure_department_exists(department)
        
        if not dept_result:
            logger.error(f"Failed to ensure department exists: {dept_message}")
            return jsonify({'error': f"Department error: {dept_message}"}), 500
        
        # Import data
        import_result = import_resources_to_database(file_data['resources'], department, str(request.current_user['_id']))
        
        if import_result['success']:
            # Clean up temp data
            cleanup_temp_file_data(file_id)
            
            return jsonify({
                'message': 'Data imported successfully',
                'imported_count': import_result['imported_count'],
                'skipped_count': import_result['skipped_count'],
                'errors': import_result['errors'],
                'department_created': dept_message.startswith('Created new department')  # Indicate if a new department was created
            }), 200
        else:
            return jsonify({'error': import_result['error']}), 500
        
    except Exception as e:
        logger.error(f"Error importing data: {e}")
        return jsonify({'error': 'Failed to import data'}), 500

# ============================================================================
# FILE PROCESSING FUNCTIONS
# ============================================================================

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_uploaded_file(file_path: str, department: str) -> Dict[str, Any]:
    """Process uploaded file with enhanced debugging."""
    try:
        print(f"🔍 Starting file processing for: {file_path}")
        print(f"🔍 Department: {department}")
        
        # Read file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            print(f"✅ CSV file read successfully")
        else:
            df = pd.read_excel(file_path)
            print(f"✅ Excel file read successfully")
        
        print(f"📊 File shape: {df.shape}")
        print(f"📋 Original columns: {list(df.columns)}")
        print(f"📋 First few rows:")
        print(df.head(2).to_string())
        
        # Normalize column names FIRST
        df = normalize_columns(df)
        print(f"📋 Normalized columns: {list(df.columns)}")
        
        # Handle comma-separated numbers in cost column
        if 'cost' in df.columns:
            print(f"💰 Processing cost column...")
            original_cost_sample = df['cost'].head(3).tolist()
            print(f"💰 Original cost sample: {original_cost_sample}")
            
            df['cost'] = df['cost'].astype(str).str.replace(',', '').str.replace('₹', '').str.replace('Rs.', '').astype(float)
            
            processed_cost_sample = df['cost'].head(3).tolist()
            print(f"💰 Processed cost sample: {processed_cost_sample}")
        
        # Validate structure AFTER normalization
        print(f"🔍 Starting validation...")
        validation_result = validate_dataframe(df, department)
        print(f"🔍 Validation result: {validation_result}")
        
        if not validation_result['valid']:
            print(f"❌ Validation failed: {validation_result['errors']}")
            return {
                'success': False,
                'error': 'File validation failed',
                'errors': validation_result['errors']
            }
        
        print(f"✅ Validation passed, processing data...")
        
        # Process data
        processed_data = process_dataframe(df, department)
        print(f"📊 Processed {len(processed_data['resources'])} resources")
        
        # Store temporarily
        file_id = store_temp_file_data(processed_data)
        print(f"💾 Stored with file_id: {file_id}")
        
        return {
            'success': True,
            'preview': processed_data['preview'],
            'warnings': processed_data['warnings'],
            'stats': processed_data['stats'],
            'file_id': file_id
        }
        
    except Exception as e:
        print(f"❌ Processing error: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        logger.error(f"Error processing file: {e}")
        return {
            'success': False,
            'error': f'Failed to process file: {str(e)}'
        }


def validate_file_structure(file_path: str, department: str) -> Dict[str, Any]:
    """
    Validate file structure without processing data.
    """
    try:
        # Read file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Validate structure
        validation_result = validate_dataframe(df, department)
        
        # Get preview
        preview = df.head(10).to_dict('records') if not df.empty else []
        
        # Calculate stats
        stats = {
            'total_rows': len(df),
            'columns': list(df.columns),
            'required_columns_present': all(col in df.columns for col in REQUIRED_COLUMNS),
            'optional_columns_present': [col for col in OPTIONAL_COLUMNS if col in df.columns]
        }
        
        return {
            'valid': validation_result['valid'],
            'errors': validation_result['errors'],
            'warnings': validation_result.get('warnings', []),
            'preview': preview,
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Error validating file structure: {e}")
        return {
            'valid': False,
            'errors': [f'Failed to read file: {str(e)}'],
            'warnings': [],
            'preview': [],
            'stats': {}
        }

def validate_dataframe(df: pd.DataFrame, department: str) -> Dict[str, Any]:
    """
    Validate DataFrame structure and content.
    """
    errors = []
    warnings = []
    
    # Check if DataFrame is empty
    if df.empty:
        errors.append("File is empty")
        return {'valid': False, 'errors': errors, 'warnings': warnings}
    
    # Check required columns
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Check data types and values
    if 'quantity' in df.columns:
        non_numeric_quantity = df[~pd.to_numeric(df['quantity'], errors='coerce').notna()]
        if not non_numeric_quantity.empty:
            errors.append(f"Non-numeric values found in quantity column at rows: {non_numeric_quantity.index.tolist()}")
    
    if 'cost' in df.columns:
        non_numeric_cost = df[~pd.to_numeric(df['cost'], errors='coerce').notna()]
        if not non_numeric_cost.empty:
            errors.append(f"Non-numeric values found in cost column at rows: {non_numeric_cost.index.tolist()}")
    
    # Check for empty fields (warnings)
    for col in REQUIRED_COLUMNS:
        if col in df.columns:
            empty_count = df[col].isna().sum() + (df[col] == '').sum()
            if empty_count > 0:
                warnings.append(f"{empty_count} empty values found in '{col}' column")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }
def normalize_columns(df):
    """Enhanced column normalization with date column debugging."""
    print(f"🔄 Normalizing columns...")
    print(f"📋 Original columns: {list(df.columns)}")
    
    column_mapping = {
        'sl no': 'sl_no',
        'device name': 'device_name',
        'quantity': 'quantity',
        'description': 'description',
        'procurement date': 'procurement_date',  # Make sure this mapping exists
        'location': 'location',
        'cost': 'cost',
        'department': 'department'
    }
    
    new_columns = []
    for col in df.columns:
        normalized = col.lower().strip()
        if normalized in column_mapping:
            new_columns.append(column_mapping[normalized])
            print(f"   ✅ Mapped '{col}' -> '{column_mapping[normalized]}'")
        else:
            new_col = normalized.replace(' ', '_')
            new_columns.append(new_col)
            print(f"   🔄 Transformed '{col}' -> '{new_col}'")
    
    df.columns = new_columns
    print(f"📋 Final columns: {list(df.columns)}")
    return df

def process_dataframe(df: pd.DataFrame, department: str) -> Dict[str, Any]:
    """Process DataFrame with enhanced date handling."""
    warnings = []
    processed_resources = []
    
    # Normalize column names
    df = normalize_columns(df)
    
    # Handle cost formatting
    if 'cost' in df.columns:
        df['cost'] = df['cost'].astype(str).str.replace(',', '').str.replace('₹', '').astype(float)
    
    # Get next serial number
    db = get_db()
    last_resource = db.resources.find_one({}, sort=[('sl_no', -1)])
    next_sl_no = (last_resource['sl_no'] + 1) if last_resource else 1
    
    print(f"🔢 Next SL No: {next_sl_no}")
    
    for index, row in df.iterrows():
        print(f"\n🔄 Processing Row {index + 1}/{len(df)}")
        
        # Handle empty values with defaults
        processed_row = {}
        
        # Serial number
        if 'sl_no' in df.columns and pd.notna(row['sl_no']):
            processed_row['sl_no'] = int(row['sl_no'])
        else:
            processed_row['sl_no'] = next_sl_no
            next_sl_no += 1
        
        print(f"   SL No: {processed_row['sl_no']} (auto-generated)")
        
        # Required fields with defaults
        processed_row['device_name'] = str(row['device_name']) if pd.notna(row['device_name']) else f"Unknown Device {processed_row['sl_no']}"
        processed_row['quantity'] = int(row['quantity']) if pd.notna(row['quantity']) else 1
        processed_row['description'] = str(row['description']) if pd.notna(row['description']) else "No description provided"
        processed_row['location'] = str(row['location']) if pd.notna(row['location']) else "Location TBD"
        processed_row['cost'] = float(row['cost']) if pd.notna(row['cost']) else 0.0
        processed_row['department'] = department
        
        print(f"   Device: {processed_row['device_name']}")
        print(f"   Quantity: {processed_row['quantity']}")
        print(f"   Cost: ₹{processed_row['cost']:,.2f}")
        
        # Handle procurement date with enhanced logging
        print(f"   📅 Processing procurement date...")
        
        # if 'procurement_date' in df.columns and pd.notna(row['procurement_date']):
        #     date_value = row['procurement_date']
        #     print(f"   📅 Raw value: {date_value} (type: {type(date_value)})")
            
        #     try:
        #         # If it's already a datetime, convert to date
        #         if isinstance(date_value, pd.Timestamp):
        #             processed_row['procurement_date'] = date_value.date()
        #             print(f"   📅 Converted pandas Timestamp to date: {processed_row['procurement_date']}")
        #         elif isinstance(date_value, datetime):
        #             processed_row['procurement_date'] = date_value.date()
        #             print(f"   📅 Converted datetime to date: {processed_row['procurement_date']}")
        #         elif isinstance(date_value, date):
        #             processed_row['procurement_date'] = date_value
        #             print(f"   📅 Using existing date object: {processed_row['procurement_date']}")
        #         else:
        #             # Try to parse string date
        #             date_str = str(date_value).strip()
        #             print(f"   📅 Date is string: '{date_str}'")
                    
        #             # Try common formats
        #             date_formats = [
        #                 '%Y-%m-%d',      # 2024-01-20
        #                 '%d-%m-%Y',      # 20-01-2024
        #                 '%m/%d/%Y',      # 01/20/2024
        #                 '%Y/%m/%d',      # 2024/01/20
        #                 '%d/%m/%Y',      # 20/01/2024
        #             ]
                    
        #             parsed_date = None
        #             for fmt in date_formats:
        #                 try:
        #                     parsed_date = datetime.strptime(date_str, fmt).date()
        #                     print(f"   📅 Successfully parsed with format '{fmt}': {parsed_date}")
        #                     break
        #                 except ValueError:
        #                     continue
                    
        #             if parsed_date:
        #                 processed_row['procurement_date'] = parsed_date
        #             else:
        #                 # Fallback to pandas
        #                 try:
        #                     parsed_date = pd.to_datetime(date_str).date()
        #                     processed_row['procurement_date'] = parsed_date
        #                     print(f"   📅 Successfully parsed with pandas: {parsed_date}")
        #                 except:
        #                     processed_row['procurement_date'] = datetime.now().date()
        #                     warnings.append(f"Row {index + 1}: Invalid date format '{date_str}', using current date")
        #                     print(f"   📅 Failed to parse, using current date: {processed_row['procurement_date']}")
                
        #         print(f"   📅 Final procurement date: {processed_row['procurement_date']}")
                
        #     except Exception as e:
        #         processed_row['procurement_date'] = datetime.now().date()
        #         warnings.append(f"Row {index + 1}: Date parsing error - {str(e)}")
        #         print(f"   📅 Error parsing date: {e}")
        # else:
        #     processed_row['procurement_date'] = datetime.now().date()
        #     print(f"   📅 No procurement date provided, using current date: {processed_row['procurement_date']}")
        if 'procurement_date' in df.columns and pd.notna(row['procurement_date']):
            try:
                # Convert to datetime.datetime, not datetime.date
                parsed_date = pd.to_datetime(row['procurement_date'])
                # Convert to Python datetime.datetime object (MongoDB compatible)
                processed_row['procurement_date'] = parsed_date.to_pydatetime()
            except:
                # Fallback to current datetime
                processed_row['procurement_date'] = datetime.now()
                warnings.append(f"Invalid date format in row {index + 1}, using current date")
        else:
            # Use current datetime, not date
            processed_row['procurement_date'] = datetime.now()
        
        # Track warnings for empty fields
        empty_fields = []
        for col in ['device_name', 'quantity', 'description', 'location', 'cost']:
            if col in df.columns and (pd.isna(row[col]) or row[col] == ''):
                empty_fields.append(col)
        
        if empty_fields:
            warnings.append(f"Row {index + 1}: Empty fields [{', '.join(empty_fields)}] filled with defaults")
        
        print(f"   ✅ Row {index + 1} processed successfully")
        processed_resources.append(processed_row)
    
    # Generate preview
    preview = processed_resources[:10] if processed_resources else []
    
    # Calculate stats
    stats = {
        'total_rows': len(processed_resources),
        'warnings_count': len(warnings),
        'department': department,
        'unique_locations': len(set(r['location'] for r in processed_resources)),
        'unique_devices': len(set(r['device_name'] for r in processed_resources)),
        'total_cost': sum(r['cost'] * r['quantity'] for r in processed_resources)
    }
    
    print(f"\n📊 Processing Summary:")
    print(f"   Total rows processed: {stats['total_rows']}")
    print(f"   Warnings generated: {stats['warnings_count']}")
    print(f"   Unique locations: {stats['unique_locations']}")
    print(f"   Total cost: ₹{stats['total_cost']:,.2f}")
    
    return {
        'resources': processed_resources,
        'warnings': warnings,
        'preview': preview,
        'stats': stats
    }


def import_resources_to_database(resources: List[Dict], department: str, user_id: str) -> Dict[str, Any]:
    """
    Import processed resources into database.
    """
    try:
        db = get_db()
        imported_count = 0
        skipped_count = 0
        errors = []
        
        for resource in resources:
            try:
                # Create resource document
                resource_doc = ResourceModel.create_resource_document(resource, user_id)
                
                # Insert into database
                db.resources.insert_one(resource_doc)
                
                # Update department locations
                update_department_locations(department, resource['location'])
                
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Error importing resource {resource.get('device_name', 'Unknown')}: {e}")
                errors.append(f"Failed to import {resource.get('device_name', 'Unknown')}: {str(e)}")
                skipped_count += 1
        
        # Update department statistics
        update_department_stats(department)
        
        logger.info(f"Imported {imported_count} resources for department {department}")
        
        return {
            'success': True,
            'imported_count': imported_count,
            'skipped_count': skipped_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Error importing resources to database: {e}")
        return {
            'success': False,
            'error': f'Database import failed: {str(e)}'
        }

# ============================================================================
# TEMPORARY FILE STORAGE
# ============================================================================

# In-memory storage for temporary file data (replace with Redis in production)
temp_file_storage = {}

def store_temp_file_data(data: Dict[str, Any]) -> str:
    """Store file data temporarily and return file ID."""
    file_id = str(ObjectId())
    temp_file_storage[file_id] = {
        'data': data,
        'timestamp': datetime.now(),
        'expires_at': datetime.now().timestamp() + 3600  # 1 hour expiry
    }
    return file_id

def get_temp_file_data(file_id: str) -> Optional[Dict[str, Any]]:
    """Get temporary file data by ID."""
    if file_id in temp_file_storage:
        file_data = temp_file_storage[file_id]
        if datetime.now().timestamp() < file_data['expires_at']:
            return file_data['data']
        else:
            # Remove expired data
            del temp_file_storage[file_id]
    return None

def cleanup_temp_file_data(file_id: str) -> None:
    """Clean up temporary file data."""
    if file_id in temp_file_storage:
        del temp_file_storage[file_id]

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@file_upload_bp.route('/template', methods=['GET'])
@require_role('admin')
def download_template():
    """
    Download CSV template for resource import.
    """
    try:
        template_data = {
            'device_name': ['Desktop Computer', 'Projector', 'Oscilloscope'],
            'quantity': [10, 2, 1],
            'description': ['High-performance desktop for lab use', 'Digital projector for presentations', 'Digital oscilloscope for signal analysis'],
            'procurement_date': ['2023-01-15', '2023-02-20', '2023-03-10'],
            'location': ['Lab A-101', 'Lecture Hall B-201', 'EEE Lab C-301'],
            'cost': [45000.00, 75000.00, 125000.00]
        }
        
        df = pd.DataFrame(template_data)
        
        # Create CSV response
        output = df.to_csv(index=False)
        
        return output, 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=resource_import_template.csv'
        }
        
    except Exception as e:
        logger.error(f"Error generating template: {e}")
        return jsonify({'error': 'Failed to generate template'}), 500

@file_upload_bp.route('/supported-formats', methods=['GET'])
def get_supported_formats():
    """
    Get supported file formats and requirements.
    """
    return jsonify({
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'max_file_size': f"{MAX_FILE_SIZE // (1024*1024)}MB",
        'required_columns': REQUIRED_COLUMNS,
        'optional_columns': OPTIONAL_COLUMNS,
        'sample_data': {
            'device_name': 'Desktop Computer',
            'quantity': 10,
            'description': 'High-performance desktop for lab use',
            'procurement_date': '2023-01-15',
            'location': 'Lab A-101',
            'cost': 45000.00
        }
    }), 200

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@file_upload_bp.errorhandler(413)
def too_large(e):
    """Handle file too large errors."""
    return jsonify({'error': 'File too large'}), 413

@file_upload_bp.errorhandler(400)
def bad_request(error):
    """Handle bad request errors."""
    return jsonify({'error': 'Bad request'}), 400

@file_upload_bp.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error'}), 500
