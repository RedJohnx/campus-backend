"""
Interactive CLI for Campus Assets Backend Testing.
Manual control with menus - makes HTTP requests to localhost:5000 endpoints.
"""

import requests
import json
import os
from datetime import datetime,time

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

class CampusAssetsCLI:
    """Interactive CLI for manual backend endpoint testing."""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.auth_token = None
        self.current_user = None
        self.user_role = None
        
    def print_header(self, title):
        print(f"\n{'='*60}")
        print(f"🏫 {title}")
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
    
    def print_warning(self, message):
        print(f"⚠️  {message}")
    
    def make_request(self, method, endpoint, **kwargs):
        """Make HTTP request to backend endpoint."""
        try:
            url = f"{self.base_url}{endpoint}"
            
            # Add auth token if available
            if self.auth_token:
                if 'headers' not in kwargs:
                    kwargs['headers'] = {}
                kwargs['headers']['Authorization'] = f"Bearer {self.auth_token}"
            
            response = getattr(self.session, method.lower())(url, timeout=TIMEOUT, **kwargs)
            return response
            
        except requests.exceptions.RequestException as e:
            self.print_error(f"Request failed: {e}")
            return None
    
    def check_server_status(self):
        """Check if Flask server is running."""
        print("🔍 Checking server status...")
        
        response = self.make_request("GET", "/health")
        if response and response.status_code == 200:
            data = response.json()
            self.print_success("Flask server is running and healthy")
            self.print_info(f"Message: {data.get('message')}")
            return True
        else:
            self.print_error("Flask server is not responding")
            self.print_info("Please ensure 'python app.py' is running on localhost:5000")
            return False
    
    def authentication_menu(self):
        """Authentication system menu."""
        self.print_section("Authentication System")
        
        while True:
            print("\n🔐 Authentication Options:")
            print("1. 📝 Register New User")
            print("2. 🔑 Login User")
            print("3. 🔍 Check Current User Status")
            print("4. 🚪 Logout")
            print("5. 📋 List Pending Admin Approvals")
            print("6. ✅ Approve Admin User")
            print("7. ⬅️  Back to Main Menu")
            
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == '1':
                self.register_user()
            elif choice == '2':
                self.login_user()
            elif choice == '3':
                self.check_current_user()
            elif choice == '4':
                self.logout_user()
            elif choice == '5':
                self.list_pending_admins()
            elif choice == '6':
                self.approve_admin_user()
            elif choice == '7':
                break
            else:
                self.print_error("Invalid choice. Please try again.")
    
    def register_user(self):
        """Register new user via API."""
        print("\n📝 Register New User")
        
        name = input("Enter full name: ").strip()
        email = input("Enter email: ").strip()
        password = input("Enter password: ").strip()
        
        print("\nSelect user role:")
        print("1. Admin (requires approval)")
        print("2. Viewer (immediate access)")
        role_choice = input("Enter choice (1-2): ").strip()
        
        role = "admin" if role_choice == "1" else "viewer"
        
        user_data = {
            "name": name,
            "email": email,
            "password": password,
            "role": role
        }
        
        print(f"\n🔄 Making POST request to /api/auth/register...")
        response = self.make_request("POST", "/api/auth/register", json=user_data)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                self.print_success("User registered successfully!")
                self.print_info(f"User ID: {data.get('user', {}).get('id')}")
                
                if role == "admin":
                    self.print_warning("Admin account requires approval before login")
                    self.print_info("Use 'List Pending Admin Approvals' and 'Approve Admin User' options")
                else:
                    self.print_info("Viewer account is ready for immediate login")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Registration failed: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Registration failed: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def login_user(self):
        """Login user via API."""
        print("\n🔑 Login User")
        
        email = input("Enter email: ").strip()
        password = input("Enter password: ").strip()
        
        login_data = {
            "email": email,
            "password": password
        }
        
        print(f"\n🔄 Making POST request to /api/auth/login...")
        response = self.make_request("POST", "/api/auth/login", json=login_data)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get('token')
                self.current_user = data.get('user')
                self.user_role = self.current_user.get('role')
                
                self.print_success("Login successful!")
                self.print_info(f"Welcome, {self.current_user.get('name', 'User')}")
                self.print_info(f"Role: {self.user_role.title()}")
                self.print_info(f"Token: {self.auth_token[:20]}...")
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', 'Unknown error')
                    self.print_error(f"Login failed: {error_msg}")
                    
                    if response.status_code == 403 and "pending approval" in error_msg.lower():
                        self.print_info("Admin account needs approval. Use admin approval options.")
                except:
                    self.print_error(f"Login failed: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def check_current_user(self):
        """Check current user status."""
        if self.current_user:
            print(f"\n👤 Current User: {self.current_user.get('name', 'Unknown')}")
            print(f"📧 Email: {self.current_user.get('email')}")
            print(f"🔰 Role: {self.user_role.title()}")
            print(f"🆔 User ID: {self.current_user.get('id')}")
            print(f"🔑 Token: {self.auth_token[:20]}... (length: {len(self.auth_token)})")
        else:
            self.print_warning("No user currently logged in")
    
    def logout_user(self):
        """Logout current user."""
        if self.current_user:
            self.print_info(f"Logging out {self.current_user.get('name', 'User')}")
            self.current_user = None
            self.auth_token = None
            self.user_role = None
            self.print_success("Logged out successfully")
        else:
            self.print_warning("No user currently logged in")
    
    def list_pending_admins(self):
        """List pending admin approvals (direct database access for this specific function)."""
        print("\n📋 List Pending Admin Approvals")
        
        try:
            # This is one case where we need direct database access for approval workflow
            from database import init_db, get_db
            
            if not init_db():
                self.print_error("Database connection failed")
                return
            
            db = get_db()
            pending_admins = list(db.users.find({'role': 'admin', 'status': 'pending'}))
            
            if pending_admins:
                print(f"\n📋 Pending Admin Approvals ({len(pending_admins)}):")
                for i, admin in enumerate(pending_admins, 1):
                    print(f"{i}. {admin.get('name', 'N/A')} ({admin['email']})")
                    print(f"   Registered: {admin.get('created_at', 'N/A')}")
                    print(f"   User ID: {admin['_id']}")
                    print()
            else:
                self.print_info("No pending admin approvals")
                
        except Exception as e:
            self.print_error(f"Error listing pending admins: {e}")
    
    def approve_admin_user(self):
        """Approve a pending admin user."""
        print("\n✅ Approve Admin User")
        
        try:
            from database import get_db
            from datetime import datetime
            
            email = input("Enter admin email to approve: ").strip()
            
            db = get_db()
            user = db.users.find_one({'email': email, 'role': 'admin', 'status': 'pending'})
            
            if not user:
                self.print_error("No pending admin found with that email")
                return
            
            # Update user status
            result = db.users.update_one(
                {'_id': user['_id']},
                {
                    '$set': {
                        'status': 'active',
                        'approved_at': datetime.now(),
                        'approved_by': 'cli_admin'
                    }
                }
            )
            
            if result.modified_count > 0:
                self.print_success(f"Admin approved: {email}")
                self.print_info("User can now login successfully")
            else:
                self.print_error("Failed to approve admin")
                
        except Exception as e:
            self.print_error(f"Error approving admin: {e}")
    
    def resource_management_menu(self):
        """Resource management menu with complete CRUD operations."""
        self.print_section("Resource Management")
        
        if not self.auth_token:
            self.print_error("Please login first")
            return
        
        while True:
            print("\n📦 Resource Management Options:")
            print("1. 📋 List All Resources")
            print("2. 🔍 Search Resources")
            print("3. 📦 View Resource Details")
            print("4. ➕ Add New Resource (Admin Only)")
            print("5. ✏️  Update Resource (Admin Only)")
            print("6. 🗑️  Delete Resource (Admin Only)")
            print("7. 🏢 List Departments")
            print("8. 📍 Department Locations")
            print("9. 🔽 Export Resources")
            print("10. ⬅️  Back to Main Menu")
            
            choice = input("\nEnter your choice (1-10): ").strip()
            
            if choice == '1':
                self.list_resources()
            elif choice == '2':
                self.search_resources()
            elif choice == '3':
                self.view_resource_details()
            elif choice == '4':
                self.add_resource()
            elif choice == '5':
                self.update_resource()
            elif choice == '6':
                self.delete_resource()
            elif choice == '7':
                self.list_departments()
            elif choice == '8':
                self.department_locations()
            elif choice == '9':
                self.export_resources()
            elif choice == '10':
                break
            else:
                self.print_error("Invalid choice. Please try again.")

    def view_resource_details(self):
        """View details of a specific resource."""
        print("\n📦 View Resource Details")
        
        resource_id = input("Enter resource ID: ").strip()
        
        print(f"\n🔄 Making GET request to /api/resources/{resource_id}...")
        response = self.make_request("GET", f"/api/resources/{resource_id}")
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                resource = data.get('resource', {})
                
                print(f"\n📦 Resource Details:")
                print(f"   ID: {resource.get('_id', 'N/A')}")
                print(f"   SL No: {resource.get('sl_no', 'N/A')}")
                print(f"   Device Name: {resource.get('device_name', 'N/A')}")
                print(f"   Quantity: {resource.get('quantity', 0)}")
                print(f"   Description: {resource.get('description', 'N/A')}")
                print(f"   Location: {resource.get('location', 'N/A')}")
                print(f"   Cost: ₹{resource.get('cost', 0):,.2f}")
                print(f"   Department: {resource.get('department', 'N/A')}")
                print(f"   Procurement Date: {resource.get('procurement_date', 'N/A')}")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")

    def update_resource(self):
        """Update an existing resource (admin only)."""
        if self.user_role != 'admin':
            self.print_error("Only admin users can update resources")
            return
        
        print("\n✏️  Update Resource")
        
        resource_id = input("Enter resource ID to update: ").strip()
        
        # Get current resource details first
        print(f"\n🔄 Making GET request to /api/resources/{resource_id}...")
        response = self.make_request("GET", f"/api/resources/{resource_id}")
        
        if not response or response.status_code != 200:
            self.print_error("Resource not found")
            return
        
        current_resource = response.json().get('resource', {})
        
        print(f"\n📦 Current Resource: {current_resource.get('device_name', 'Unknown')}")
        print("Enter new values (press Enter to keep current value):")
        
        # Collect update data
        update_data = {}
        
        fields = [
            ('device_name', 'Device name'),
            ('quantity', 'Quantity'),
            ('description', 'Description'),
            ('location', 'Location'),
            ('cost', 'Cost'),
            ('department', 'Department')
        ]
        
        for field, label in fields:
            current_value = current_resource.get(field, '')
            new_value = input(f"{label} (current: {current_value}): ").strip()
            
            if new_value:
                if field in ['quantity']:
                    update_data[field] = int(new_value)
                elif field in ['cost']:
                    update_data[field] = float(new_value)
                else:
                    update_data[field] = new_value
        
        if not update_data:
            self.print_info("No changes made")
            return
        
        # Update resource
        print(f"\n🔄 Making PUT request to /api/resources/{resource_id}...")
        response = self.make_request("PUT", f"/api/resources/{resource_id}", json=update_data)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                self.print_success("Resource updated successfully!")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")

    def delete_resource(self):
        """Delete a resource using hierarchical selection (admin only)."""
        if self.user_role != 'admin':
            self.print_error("Only admin users can delete resources")
            return
        
        print("\n🗑️  Delete Resource (Hierarchical Selection)")
        print("Follow the steps to select the resource to delete:")
        
        # Step 1: Select Department
        print("\n🏢 Step 1: Select Department")
        department = self.select_department_for_deletion()
        if not department:
            return
        
        # Step 2: Select Location within Department
        print(f"\n📍 Step 2: Select Location in {department}")
        location = self.select_location_for_deletion(department)
        if not location:
            return
        
        # Step 3: Select Device in Location
        print(f"\n🎯 Step 3: Select Device in {location}")
        device_name = self.select_device_for_deletion(department, location)
        if not device_name:
            return
        
        # Step 4: Preview and execute deletion
        print(f"\n📦 Step 4: Preview and Delete Resource")
        success = self.execute_hierarchical_deletion(department, location, device_name)
        
        if success:
            self.print_success("Resource deletion completed!")
        else:
            self.print_error("Resource deletion failed or cancelled")

    def select_department_for_deletion(self):
        """Select department using the deletion-specific endpoint."""
        print(f"\n🔄 Getting departments for deletion...")
        response = self.make_request("GET", "/api/resources/deletion/departments")
        
        if not response or response.status_code != 200:
            self.print_error("Failed to get departments")
            return None
        
        data = response.json()
        departments = data.get('departments', [])
        
        if not departments:
            self.print_error("No departments found")
            return None
        
        print(f"\n📋 Available Departments ({data.get('total_departments', 0)}):")
        for i, dept in enumerate(departments, 1):
            print(f"{i}. {dept.get('name', 'N/A')}")
            print(f"   Resources: {dept.get('resource_count', 0)} units")
            print(f"   Total Value: ₹{dept.get('total_cost', 0):,.2f}")
            print(f"   Locations: {dept.get('unique_locations_count', 0)}")
            print()
        
        try:
            choice = int(input(f"Select department (1-{len(departments)}): ").strip())
            if 1 <= choice <= len(departments):
                selected_dept = departments[choice - 1]['name']
                self.print_info(f"Selected: {selected_dept}")
                return selected_dept
            else:
                self.print_error("Invalid selection")
                return None
        except ValueError:
            self.print_error("Please enter a valid number")
            return None

    def select_location_for_deletion(self, department):
        """Select location using the deletion-specific endpoint."""
        print(f"\n🔄 Getting locations for {department}...")
        response = self.make_request("GET", f"/api/resources/deletion/locations/{department}")
        
        if not response or response.status_code != 200:
            self.print_error("Failed to get locations")
            return None
        
        data = response.json()
        locations = data.get('locations', [])
        
        if not locations:
            self.print_error(f"No locations found in {department}")
            return None
        
        print(f"\n📋 Available Locations in {department} ({data.get('total_locations', 0)}):")
        for i, loc in enumerate(locations, 1):
            print(f"{i}. {loc.get('name', 'N/A')}")
            print(f"   Resources: {loc.get('resource_count', 0)} units")
            print(f"   Total Value: ₹{loc.get('total_cost', 0):,.2f}")
            print(f"   Device Types: {loc.get('device_types_count', 0)}")
            print()
        
        try:
            choice = int(input(f"Select location (1-{len(locations)}): ").strip())
            if 1 <= choice <= len(locations):
                selected_location = locations[choice - 1]['name']
                self.print_info(f"Selected: {selected_location}")
                return selected_location
            else:
                self.print_error("Invalid selection")
                return None
        except ValueError:
            self.print_error("Please enter a valid number")
            return None

    def select_device_for_deletion(self, department, location):
        """Select device using the deletion-specific endpoint."""
        print(f"\n🔄 Getting devices for {location} in {department}...")
        response = self.make_request("GET", f"/api/resources/deletion/devices/{department}/{location}")
        
        if not response or response.status_code != 200:
            self.print_error("Failed to get devices")
            return None
        
        data = response.json()
        devices = data.get('devices', [])
        
        if not devices:
            self.print_error(f"No devices found in {location}")
            return None
        
        print(f"\n📋 Available Devices in {location} ({data.get('total_device_types', 0)}):")
        for i, device in enumerate(devices, 1):
            print(f"{i}. {device.get('device_name', 'N/A')}")
            print(f"   Total Quantity: {device.get('total_quantity', 0)} units")
            print(f"   Total Value: ₹{device.get('total_cost', 0):,.2f}")
            print(f"   Resource Entries: {device.get('resource_entries', 0)}")
            print()
        
        try:
            choice = int(input(f"Select device (1-{len(devices)}): ").strip())
            if 1 <= choice <= len(devices):
                selected_device = devices[choice - 1]['device_name']
                self.print_info(f"Selected: {selected_device}")
                return selected_device
            else:
                self.print_error("Invalid selection")
                return None
        except ValueError:
            self.print_error("Please enter a valid number")
            return None

    def execute_hierarchical_deletion(self, department, location, device_name):
        """Execute the hierarchical deletion process."""
        # Step 1: Preview what will be deleted
        preview_data = {
            "department": department,
            "location": location,
            "device_name": device_name
        }
        
        print(f"\n🔄 Previewing resources to delete...")
        response = self.make_request("POST", "/api/resources/deletion/preview", json=preview_data)
        
        if not response or response.status_code != 200:
            self.print_error("Failed to preview deletion")
            return False
        
        data = response.json()
        
        if not data.get('found', False):
            self.print_error("No resources found matching the criteria")
            return False
        
        matches = data.get('matches', [])
        summary = data.get('summary', {})
        
        print(f"\n📋 Preview: Found {summary.get('total_resources', 0)} resource(s) to delete:")
        print(f"   Total Quantity: {summary.get('total_quantity', 0)} units")
        print(f"   Total Value: ₹{summary.get('total_value', 0):,.2f}")
        
        # Show individual resources
        for i, resource in enumerate(matches, 1):
            print(f"\n{i}. {resource.get('device_name', 'N/A')}")
            print(f"   Quantity: {resource.get('quantity', 0)}")
            print(f"   Description: {resource.get('description', 'N/A')}")
            print(f"   Cost: ₹{resource.get('cost', 0):,.2f}")
            print(f"   Total Value: ₹{resource.get('total_value', 0):,.2f}")
            print(f"   SL No: {resource.get('sl_no', 'N/A')}")
        
        # Check if quantity selection is needed
        if summary.get('requires_quantity_selection', False):
            print(f"\n⚠️  Multiple resources found. Please specify quantity:")
            try:
                quantity = int(input("Enter quantity of the specific resource to delete: ").strip())
                preview_data['quantity'] = quantity
                
                # Re-preview with quantity
                response = self.make_request("POST", "/api/resources/deletion/preview", json=preview_data)
                if not response or response.status_code != 200:
                    self.print_error("Failed to preview with quantity")
                    return False
                
                data = response.json()
                matches = data.get('matches', [])
                
                if not matches:
                    self.print_error("No resource found with that quantity")
                    return False
                
            except ValueError:
                self.print_error("Invalid quantity entered")
                return False
        
        # Final confirmation
        print(f"\n⚠️  FINAL CONFIRMATION")
        print(f"You are about to permanently delete:")
        print(f"   Department: {department}")
        print(f"   Location: {location}")
        print(f"   Device: {device_name}")
        if 'quantity' in preview_data:
            print(f"   Quantity: {preview_data['quantity']}")
        
        if matches:
            target = matches[0]
            print(f"   Description: {target.get('description', 'N/A')}")
            print(f"   Total Value: ₹{target.get('total_value', 0):,.2f}")
        
        confirm = input(f"\nType 'DELETE' to confirm permanent deletion: ").strip()
        
        if confirm != 'DELETE':
            self.print_info("Deletion cancelled")
            return False
        
        # Execute deletion
        print(f"\n🔄 Executing deletion...")
        response = self.make_request("DELETE", "/api/resources/deletion/execute", json=preview_data)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success', False):
                    deleted_resource = result.get('deleted_resource', {})
                    
                    self.print_success("Resource deleted successfully!")
                    print(f"\n📋 Deleted Resource Details:")
                    print(f"   Device: {deleted_resource.get('device_name', 'N/A')}")
                    print(f"   Quantity: {deleted_resource.get('quantity', 0)}")
                    print(f"   Location: {deleted_resource.get('location', 'N/A')}")
                    print(f"   Department: {deleted_resource.get('department', 'N/A')}")
                    print(f"   Total Value: ₹{deleted_resource.get('total_value', 0):,.2f}")
                    print(f"   Deleted by: {result.get('deleted_by', 'N/A')}")
                    
                    return True
                else:
                    self.print_error(f"Deletion failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Deletion failed: {error_data.get('error', 'Unknown error')}")
                    
                    # Show matching resources if available
                    if 'matching_resources' in error_data:
                        print(f"\n📋 Available options:")
                        for resource in error_data['matching_resources']:
                            print(f"   - Quantity: {resource.get('quantity', 0)}, Value: ₹{resource.get('total_value', 0):,.2f}")
                except:
                    self.print_error(f"Deletion failed: HTTP {response.status_code}")
                
                return False
        else:
            self.print_error("No response from server")
            return False

    def export_resources(self):
        """Export resources to CSV/Excel."""
        print("\n🔽 Export Resources")
        
        print("Export options:")
        print("1. Export all resources")
        print("2. Export by department")
        print("3. Export by location")
        
        choice = input("Enter choice (1-3): ").strip()
        
        if choice == '1':
            endpoint = "/api/export/csv"
        elif choice == '2':
            department = input("Enter department: ").strip()
            endpoint = f"/api/export/csv?department={department}"
        elif choice == '3':
            location = input("Enter location: ").strip()
            endpoint = f"/api/export/csv?location={location}"
        else:
            self.print_error("Invalid choice")
            return
        
        print(f"\n🔄 Making GET request to {endpoint}...")
        response = self.make_request("GET", endpoint)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                filename = f"resources_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                with open(filename, 'w') as f:
                    f.write(response.text)
                
                self.print_success(f"Resources exported to: {filename}")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")

    def list_resources(self):
        """List all resources via API."""
        print("\n📋 List All Resources")
        
        page = input("Enter page number (default: 1): ").strip() or "1"
        per_page = input("Enter items per page (default: 10): ").strip() or "10"
        
        params = {'page': page, 'per_page': per_page}
        
        print(f"\n🔄 Making GET request to /api/resources...")
        response = self.make_request("GET", "/api/resources", params=params)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                resources = data.get('resources', [])
                pagination = data.get('pagination', {})
                
                if resources:
                    print(f"\n📦 Resources (Page {pagination.get('page', 1)} of {pagination.get('total_pages', 1)}):")
                    for i, resource in enumerate(resources, 1):
                        print(f"{i}. {resource.get('device_name', 'N/A')}")
                        print(f"   Department: {resource.get('department', 'N/A')}")
                        print(f"   Location: {resource.get('location', 'N/A')}")
                        print(f"   Quantity: {resource.get('quantity', 0)}")
                        print(f"   Cost: ₹{resource.get('cost', 0):,.2f}")
                        print()
                    
                    print(f"📊 Total: {pagination.get('total_count', 0)} resources")
                else:
                    self.print_info("No resources found")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def search_resources(self):
        """Search resources via API."""
        print("\n🔍 Search Resources")
        
        query = input("Enter search query: ").strip()
        
        params = {'query': query}
        
        print(f"\n🔄 Making GET request to /api/resources/search...")
        response = self.make_request("GET", "/api/resources/search", params=params)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                resources = data.get('resources', [])
                
                if resources:
                    print(f"\n🔍 Search Results for '{query}' ({len(resources)} found):")
                    for i, resource in enumerate(resources, 1):
                        print(f"{i}. {resource.get('device_name', 'N/A')}")
                        print(f"   Department: {resource.get('department', 'N/A')}")
                        print(f"   Location: {resource.get('location', 'N/A')}")
                        print()
                else:
                    self.print_info(f"No resources found matching '{query}'")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def add_resource(self):
        """Add new resource via API."""
        if self.user_role != 'admin':
            self.print_error("Only admin users can add resources")
            return
        
        print("\n➕ Add New Resource")
        
        device_name = input("Device name: ").strip()
        quantity = input("Quantity: ").strip()
        description = input("Description: ").strip()
        location = input("Location: ").strip()
        cost = input("Cost (₹): ").strip()
        department = input("Department: ").strip()
        
        resource_data = {
            "device_name": device_name,
            "quantity": int(quantity),
            "description": description,
            "location": location,
            "cost": float(cost),
            "department": department
        }
        
        print(f"\n🔄 Making POST request to /api/resources...")
        response = self.make_request("POST", "/api/resources", json=resource_data)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                self.print_success("Resource added successfully!")
                self.print_info(f"Resource ID: {data.get('resource', {}).get('_id')}")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def list_departments(self):
        """List all departments via API."""
        print("\n🏢 List All Departments")
        
        print(f"\n🔄 Making GET request to /api/resources/departments...")
        response = self.make_request("GET", "/api/resources/departments")
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                departments = data.get('departments', [])
                
                if departments:
                    print(f"\n🏢 Departments ({len(departments)}):")
                    for i, dept in enumerate(departments, 1):
                        print(f"{i}. {dept.get('name', 'N/A')}")
                        locations = dept.get('locations', [])
                        if locations:
                            print(f"   Locations: {len(locations)} locations")
                else:
                    self.print_info("No departments found")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def department_locations(self):
        """View locations for a specific department."""
        print("\n📍 Department Locations")
        
        department = input("Enter department name: ").strip()
        
        print(f"\n🔄 Making GET request to /api/resources/departments/{department}/locations...")
        response = self.make_request("GET", f"/api/resources/departments/{department}/locations")
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                locations = data.get('locations', [])
                
                if locations:
                    print(f"\n📍 Locations in {department} ({len(locations)}):")
                    for i, location in enumerate(locations, 1):
                        print(f"{i}. {location}")
                else:
                    self.print_info(f"No locations found for {department}")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def file_upload_menu(self):
        """File upload menu."""
        self.print_section("File Upload Testing")
        
        if not self.auth_token:
            self.print_error("Please login first")
            return
        
        if self.user_role != 'admin':
            self.print_error("Only admin users can upload files")
            return
        
        while True:
            print("\n📁 File Upload Options:")
            print("1. 📋 Download Template")
            print("2. 📄 View Supported Formats")
            print("3. 📊 Upload Excel Dataset")
            print("4. ⬅️  Back to Main Menu")
            
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == '1':
                self.download_template()
            elif choice == '2':
                self.view_supported_formats()
            elif choice == '3':
                self.upload_excel_dataset()
            elif choice == '4':
                break
            else:
                self.print_error("Invalid choice. Please try again.")
    
    def download_template(self):
        """Download CSV template."""
        print("\n📋 Download Template")
        
        print(f"\n🔄 Making GET request to /api/upload/template...")
        response = self.make_request("GET", "/api/upload/template")
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                template_filename = "resource_import_template.csv"
                with open(template_filename, 'w') as f:
                    f.write(response.text)
                
                self.print_success(f"Template downloaded: {template_filename}")
            else:
                self.print_error(f"Download failed: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def view_supported_formats(self):
        """View supported file formats."""
        print("\n📄 View Supported Formats")
        
        print(f"\n🔄 Making GET request to /api/upload/supported-formats...")
        response = self.make_request("GET", "/api/upload/supported-formats")
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n✅ Supported formats: {', '.join(data.get('supported_formats', []))}")
                print(f"📏 Max file size: {data.get('max_file_size', 'Unknown')}")
                print(f"\n📋 Required columns:")
                for col in data.get('required_columns', []):
                    print(f"   - {col}")
                
                print(f"\n📝 Sample data format:")
                sample = data.get('sample_data', {})
                for key, value in sample.items():
                    print(f"   {key}: {value}")
            else:
                self.print_error(f"Error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def upload_excel_dataset(self):
        """Upload Excel dataset."""
        print("\n📊 Upload Excel Dataset")
        
        file_path = input("Enter path to Excel file: ").strip()
        
        if not os.path.exists(file_path):
            self.print_error("File not found")
            return
        
        department = input("Enter department for this data: ").strip()
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                data = {'department': department}
                
                print(f"\n🔄 Making POST request to /api/upload/upload...")
                response = self.make_request("POST", "/api/upload/upload", files=files, data=data)
                
                if response:
                    print(f"📥 Response Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        file_id = result.get('file_id')
                        warnings = result.get('warnings', [])
                        stats = result.get('stats', {})
                        
                        self.print_success("File uploaded and processed successfully!")
                        self.print_info(f"File ID: {file_id}")
                        self.print_info(f"Total rows: {stats.get('total_rows', 0)}")
                        self.print_info(f"Warnings: {len(warnings)}")
                        
                        if warnings:
                            print("\n⚠️  Warnings:")
                            for warning in warnings[:5]:
                                print(f"   - {warning}")
                        
                        # Ask if user wants to proceed with import
                        proceed = input("\nProceed with import? (y/n): ").strip().lower()
                        
                        if proceed in ['y', 'yes']:
                            self.import_file_data(file_id, department)
                        else:
                            self.print_info("Import cancelled")
                    else:
                        try:
                            error_data = response.json()
                            self.print_error(f"Upload error: {error_data.get('error', 'Unknown error')}")
                        except:
                            self.print_error(f"Upload error: HTTP {response.status_code}")
                else:
                    self.print_error("No response from server")
                    
        except Exception as e:
            self.print_error(f"Error uploading file: {e}")
    
    def import_file_data(self, file_id, department):
        """Import file data via API."""
        import_data = {
            'file_id': file_id,
            'department': department,
            'proceed_with_warnings': True
        }
        
        print(f"\n🔄 Making POST request to /api/upload/import...")
        response = self.make_request("POST", "/api/upload/import", json=import_data)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                imported_count = result.get('imported_count', 0)
                skipped_count = result.get('skipped_count', 0)
                
                self.print_success(f"Data imported successfully!")
                self.print_info(f"Imported: {imported_count} resources")
                self.print_info(f"Skipped: {skipped_count} resources")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Import error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Import error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def ai_integration_menu(self):
        """AI integration menu."""
        self.print_section("AI Integration Testing")
        
        if not self.auth_token:
            self.print_error("Please login first")
            return
        
        while True:
            print("\n🤖 AI Integration Options:")
            print("1. 🔍 Check AI Status")
            print("2. 🤖 AI Chat Query")
            print("3. 🔮 Natural Language CRUD (Admin Only)")
            print("4. 🧪 Test AI with Sample Queries")
            print("5. ⬅️  Back to Main Menu")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                self.check_ai_status()
            elif choice == '2':
                self.ai_chat_query()
            elif choice == '3':
                self.ai_natural_language_crud()
            elif choice == '4':
                self.test_ai_samples()
            elif choice == '5':
                break
            else:
                self.print_error("Invalid choice. Please try again.")
    
    def ai_chat_query(self):
        """AI chat query via API."""
        print("\n🤖 AI Chat Query")
        
        query = input("Enter your question about resources: ").strip()
        
        chat_data = {
            "query": query,
            "session_id": None
        }
        
        print(f"\n🔄 Making POST request to /api/ai/chat...")
        response = self.make_request("POST", "/api/ai/chat", json=chat_data)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get('response', '')
                resources = data.get('resources', [])
                
                print(f"\n🤖 AI Response:")
                print(f"   {ai_response}")
                
                if resources:
                    print(f"\n📋 Relevant Resources ({len(resources)}):")
                    for i, resource in enumerate(resources, 1):
                        print(f"{i}. {resource.get('device_name', 'N/A')} - {resource.get('department', 'N/A')}")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"AI chat error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"AI chat error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def ai_natural_language_crud(self):
        """AI natural language CRUD via API."""
        if self.user_role != 'admin':
            self.print_error("Only admin users can perform CRUD operations")
            return
        
        print("\n🔮 Natural Language CRUD")
        print("Examples:")
        print("- 'Add 5 laptops to Computer Science department in Lab A-101, cost 50000 each'")
        print("- 'Add 10 projectors to Electronics Lab B-205, cost 25000 each, description high-resolution projectors'")
        print("- 'Create 3 microscopes in Biology Lab, location Lab-301, cost 75000 each'")
        
        instruction = input("\nEnter your instruction: ").strip()
        if not instruction:
            self.print_error("Instruction cannot be empty")
            return
            
        department = input("Enter department: ").strip()
        if not department:
            self.print_error("Department cannot be empty")
            return
        
        crud_data = {
            "instruction": instruction,
            "department": department
        }
        
        print(f"\n🔄 Making POST request to /api/ai/crud...")
        response = self.make_request("POST", "/api/ai/crud", json=crud_data)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                operation = data.get('operation', 'unknown')
                details = data.get('details', '')
                resource_data = data.get('data', {})
                
                self.print_success(f"AI CRUD operation completed!")
                self.print_info(f"Operation: {operation}")
                self.print_info(f"Details: {details}")
                
                if resource_data:
                    print(f"\n📋 Created Resource:")
                    print(f"   Device: {resource_data.get('device_name', 'N/A')}")
                    print(f"   Quantity: {resource_data.get('quantity', 'N/A')}")
                    print(f"   Location: {resource_data.get('location', 'N/A')}")
                    print(f"   Cost: ₹{resource_data.get('cost', 0):,.2f}")
                    
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', 'Unknown error')
                    missing_fields = error_data.get('missing_fields', [])
                    suggestions = error_data.get('suggestions', [])
                    
                    self.print_error(f"AI CRUD error: {error_msg}")
                    
                    if missing_fields:
                        print(f"   Missing fields: {', '.join(missing_fields)}")
                    
                    if suggestions:
                        print(f"   Suggestions:")
                        for suggestion in suggestions:
                            print(f"   - {suggestion}")
                            
                except:
                    self.print_error(f"AI CRUD error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def check_ai_status(self):
        """Check AI integration status."""
        print("\n🔍 Checking AI Integration Status...")
        
        response = self.make_request("GET", "/api/ai/status")
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n📊 AI Status Report:")
                print(f"   GROQ API Configured: {'✅' if data.get('groq_api_configured') else '❌'}")
                print(f"   GROQ Model: {data.get('groq_model', 'N/A')}")
                print(f"   API Base URL: {data.get('api_base_url', 'N/A')}")
                
                api_test = data.get('api_test', {})
                if api_test.get('success'):
                    self.print_success("API Connection Test: PASSED")
                    print(f"   Test Response: {api_test.get('response', 'N/A')}")
                else:
                    self.print_error("API Connection Test: FAILED")
                    if api_test.get('error'):
                        print(f"   Error: {api_test['error']}")
                        
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Status check error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Status check error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")
    
    def test_ai_samples(self):
        """Test AI with sample queries."""
        print("\n🧪 Testing AI with Sample Queries")
        
        sample_queries = [
            {
                'type': 'chat',
                'query': 'How many laptops do we have in Computer Science department?',
                'description': 'Resource count query'
            },
            {
                'type': 'chat', 
                'query': 'What equipment is available in Electronics Lab?',
                'description': 'Location-based query'
            },
            {
                'type': 'crud',
                'instruction': 'Add 2 whiteboards to Mathematics department in Room M-101, cost 5000 each',
                'department': 'Mathematics',
                'description': 'Simple create operation'
            }
        ]
        
        for i, sample in enumerate(sample_queries, 1):
            print(f"\n--- Sample Test {i}: {sample['description']} ---")
            
            if sample['type'] == 'chat':
                print(f"Query: {sample['query']}")
                
                chat_data = {
                    "query": sample['query'],
                    "session_id": None
                }
                
                response = self.make_request("POST", "/api/ai/chat", json=chat_data)
                
                if response and response.status_code == 200:
                    data = response.json()
                    ai_response = data.get('response', '')
                    self.print_success("Chat test passed")
                    print(f"AI Response: {ai_response[:200]}...")
                else:
                    self.print_error("Chat test failed")
                    
            elif sample['type'] == 'crud' and self.user_role == 'admin':
                print(f"Instruction: {sample['instruction']}")
                print(f"Department: {sample['department']}")
                
                crud_data = {
                    "instruction": sample['instruction'],
                    "department": sample['department']
                }
                
                response = self.make_request("POST", "/api/ai/crud", json=crud_data)
                
                if response and response.status_code == 200:
                    data = response.json()
                    self.print_success("CRUD test passed")
                    print(f"Operation: {data.get('operation', 'N/A')}")
                    print(f"Details: {data.get('details', 'N/A')}")
                else:
                    self.print_error("CRUD test failed")
                    
            elif sample['type'] == 'crud':
                self.print_warning("CRUD test skipped - Admin role required")
            
            input("\nPress Enter to continue to next test...")
        
        print(f"\n✅ Sample testing completed!")
    def test_advanced_filtering(self):
        """Test advanced filtering system."""
        self.print_section("Advanced Filtering System Testing")
        
        if not self.auth_token:
            self.print_error("Please login first")
            return
        
        while True:
            print("\n🔍 Advanced Filtering Options:")
            print("1. 📊 Get Filter Options (Three-tier Structure)")
            print("2. 🔎 Advanced Search with Multiple Filters")
            print("3. 📍 Get Locations for Department")
            print("4. 🎯 Get Devices for Location")
            print("5. ⚡ Quick Filters (Top Items)")
            print("6. ⬅️  Back to Main Menu")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                self.test_filter_options()
            elif choice == '2':
                self.test_advanced_search()
            elif choice == '3':
                self.test_department_locations()
            elif choice == '4':
                self.test_location_devices()
            elif choice == '5':
                self.test_quick_filters()
            elif choice == '6':
                break
            else:
                self.print_error("Invalid choice. Please try again.")

    def test_filter_options(self):
        """Test three-tier filter options."""
        print("\n📊 Three-tier Filter Options")
        
        print(f"\n🔄 Making GET request to /api/resources/filter-options...")
        response = self.make_request("GET", "/api/resources/filter-options")
        
        if response and response.status_code == 200:
            data = response.json()
            departments = data.get('departments', [])
            summary = data.get('summary', {})
            
            print(f"\n✅ Filter Structure Retrieved:")
            print(f"   Total Departments: {summary.get('total_departments', 0)}")
            print(f"   Total Locations: {summary.get('total_locations', 0)}")
            print(f"   Total Device Types: {summary.get('total_device_types', 0)}")
            
            print(f"\n📋 Department Structure (First 3):")
            for i, dept in enumerate(departments[:3], 1):
                print(f"{i}. {dept['name']}")
                print(f"   Locations: {len(dept['locations'])} ({', '.join(dept['locations'][:3])}...)")
                print(f"   Device Types: {len(dept['device_types'])}")
                print(f"   Resources: {dept['stats']['total_resources']}")
                print(f"   Total Cost: ₹{dept['stats']['total_cost']:,.2f}")
                print()
        else:
            self.print_error(f"Failed to get filter options: HTTP {response.status_code if response else 'No response'}")

    def test_advanced_search(self):
        """Test advanced search with multiple filters."""
        print("\n🔎 Advanced Search Testing")
        
        print("Enter search criteria (press Enter to skip):")
        search_query = input("Search query: ").strip()
        department = input("Department: ").strip()
        location = input("Location: ").strip()
        device_type = input("Device type: ").strip()
        min_cost = input("Minimum cost: ").strip()
        max_cost = input("Maximum cost: ").strip()
        
        search_data = {}
        
        if search_query:
            search_data['query'] = search_query
        if department:
            search_data['department'] = department
        if location:
            search_data['location'] = location
        if device_type:
            search_data['device_type'] = device_type
        
        cost_range = {}
        if min_cost:
            cost_range['min'] = float(min_cost)
        if max_cost:
            cost_range['max'] = float(max_cost)
        if cost_range:
            search_data['cost_range'] = cost_range
        
        search_data['page'] = 1
        search_data['per_page'] = 5
        search_data['sort_by'] = 'cost'
        search_data['sort_order'] = 'desc'
        
        print(f"\n🔄 Making POST request to /api/resources/advanced-search...")
        response = self.make_request("POST", "/api/resources/advanced-search", json=search_data)
        
        if response and response.status_code == 200:
            data = response.json()
            resources = data.get('resources', [])
            summary = data.get('search_summary', {})
            pagination = data.get('pagination', {})
            
            print(f"\n✅ Advanced Search Results:")
            print(f"   Total Found: {pagination.get('total_count', 0)}")
            print(f"   Total Cost: ₹{summary.get('total_cost', 0):,.2f}")
            print(f"   Total Quantity: {summary.get('total_quantity', 0)}")
            print(f"   Average Cost: ₹{summary.get('average_cost', 0):,.2f}")
            
            if resources:
                print(f"\n📋 Results (Page 1):")
                for i, resource in enumerate(resources, 1):
                    print(f"{i}. {resource.get('device_name', 'N/A')}")
                    print(f"   Department: {resource.get('department', 'N/A')}")
                    print(f"   Location: {resource.get('location', 'N/A')}")
                    print(f"   Cost: ₹{resource.get('cost', 0):,.2f}")
                    print()
        else:
            self.print_error(f"Advanced search failed: HTTP {response.status_code if response else 'No response'}")

    def test_department_locations(self):
        """Test dynamic location population for department."""
        print("\n📍 Department Locations Testing")
        
        department = input("Enter department name: ").strip()
        
        print(f"\n🔄 Making GET request to /api/resources/filter/locations/{department}...")
        response = self.make_request("GET", f"/api/resources/filter/locations/{department}")
        
        if response and response.status_code == 200:
            data = response.json()
            locations = data.get('locations', [])
            summary = data.get('summary', {})
            
            print(f"\n✅ Locations for {department}:")
            print(f"   Total Locations: {summary.get('total_locations', 0)}")
            print(f"   Total Resources: {summary.get('total_resources', 0)}")
            print(f"   Total Cost: ₹{summary.get('total_cost', 0):,.2f}")
            
            for i, location in enumerate(locations, 1):
                print(f"{i}. {location['name']}")
                print(f"   Resources: {location['resource_count']}")
                print(f"   Device Types: {location['device_types_count']}")
                print(f"   Cost: ₹{location['total_cost']:,.2f}")
                print()
        else:
            self.print_error(f"Failed to get locations: HTTP {response.status_code if response else 'No response'}")

    def test_location_devices(self):
        """Test device types for specific location."""
        print("\n🎯 Location Devices Testing")
        
        department = input("Enter department name: ").strip()
        location = input("Enter location name: ").strip()
        
        print(f"\n🔄 Making GET request to /api/resources/filter/devices/{department}/{location}...")
        response = self.make_request("GET", f"/api/resources/filter/devices/{department}/{location}")
        
        if response and response.status_code == 200:
            data = response.json()
            devices = data.get('devices', [])
            summary = data.get('summary', {})
            
            print(f"\n✅ Devices in {location} ({department}):")
            print(f"   Device Types: {summary.get('total_device_types', 0)}")
            print(f"   Total Quantity: {summary.get('total_quantity', 0)}")
            print(f"   Total Cost: ₹{summary.get('total_cost', 0):,.2f}")
            
            for i, device in enumerate(devices, 1):
                print(f"{i}. {device['device_name']}")
                print(f"   Quantity: {device['total_quantity']}")
                print(f"   Average Cost: ₹{device['average_cost']:,.2f}")
                print(f"   Total Cost: ₹{device['total_cost']:,.2f}")
                print()
        else:
            self.print_error(f"Failed to get devices: HTTP {response.status_code if response else 'No response'}")

    def test_quick_filters(self):
        """Test quick filters for common options."""
        print("\n⚡ Quick Filters Testing")
        
        print(f"\n🔄 Making GET request to /api/resources/quick-filters...")
        response = self.make_request("GET", "/api/resources/quick-filters")
        
        if response and response.status_code == 200:
            data = response.json()
            
            print(f"\n✅ Quick Filter Options:")
            
            top_departments = data.get('top_departments', [])
            print(f"\n🏢 Top 5 Departments by Resources:")
            for i, dept in enumerate(top_departments, 1):
                print(f"{i}. {dept['name']} - {dept['resource_count']} resources")
            
            top_locations = data.get('top_locations', [])
            print(f"\n📍 Top 10 Locations by Resources:")
            for i, loc in enumerate(top_locations[:5], 1):  # Show first 5
                print(f"{i}. {loc['name']} ({loc['department']}) - {loc['resource_count']} resources")
            
            top_devices = data.get('top_devices', [])
            print(f"\n🎯 Top 10 Device Types:")
            for i, device in enumerate(top_devices[:5], 1):  # Show first 5
                print(f"{i}. {device['name']} - {device['resource_count']} units")
            
            print(f"\n📅 Recent Additions (30 days): {data.get('recent_additions', 0)}")
        else:
            self.print_error(f"Failed to get quick filters: HTTP {response.status_code if response else 'No response'}")
    def test_dashboard_system(self):
        """Test dashboard and analytics system."""
        self.print_section("Dashboard & Analytics System Testing")
        
        if not self.auth_token:
            self.print_error("Please login first")
            return
        
        while True:
            print("\n📊 Dashboard Testing Options:")
            print("1. 🏠 Dashboard Overview")
            print("2. 🏢 Department Analytics")
            print("3. 💰 Cost Analysis")
            print("4. 📈 Utilization Metrics")
            print("5. 📊 Chart Data Generation")
            print("6. 🎯 Performance Summary")
            print("7. ⬅️  Back to Main Menu")
            
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == '1':
                self.test_dashboard_overview()
            elif choice == '2':
                self.test_department_analytics()
            elif choice == '3':
                self.test_cost_analysis()
            elif choice == '4':
                self.test_utilization_metrics()
            elif choice == '5':
                self.test_chart_data()
            elif choice == '6':
                self.test_performance_summary()
            elif choice == '7':
                break
            else:
                self.print_error("Invalid choice. Please try again.")

    def test_dashboard_overview(self):
        """Test dashboard overview endpoint."""
        print("\n🏠 Dashboard Overview Testing")
        
        print(f"\n🔄 Making GET request to /api/dashboard/overview...")
        response = self.make_request("GET", "/api/dashboard/overview")
        
        if response and response.status_code == 200:
            data = response.json()
            overview = data.get('overview', {})
            financial = data.get('financial_metrics', {})
            top_performers = data.get('top_performers', {})
            
            print(f"\n✅ Dashboard Overview Retrieved:")
            print(f"   📦 Total Resources: {overview.get('total_resources', 0):,}")
            print(f"   🏢 Total Departments: {overview.get('total_departments', 0)}")
            print(f"   👥 Total Users: {overview.get('total_users', 0)}")
            print(f"   💰 Total Asset Value: ₹{overview.get('total_value', 0):,.2f}")
            print(f"   📊 Total Quantity: {overview.get('total_quantity', 0):,}")
            print(f"   🎯 Unique Devices: {overview.get('unique_devices', 0)}")
            print(f"   📍 Unique Locations: {overview.get('unique_locations', 0)}")
            print(f"   📅 Recent Additions (30d): {overview.get('recent_additions_30d', 0)}")
            
            print(f"\n💰 Financial Metrics:")
            print(f"   Average Cost/Item: ₹{financial.get('average_cost_per_item', 0):,.2f}")
            print(f"   Most Expensive: ₹{financial.get('most_expensive_item', 0):,.2f}")
            print(f"   Least Expensive: ₹{financial.get('least_expensive_item', 0):,.2f}")
            
            print(f"\n🏆 Top Performers:")
            leading_dept = top_performers.get('leading_department', {})
            most_expensive = top_performers.get('most_expensive_item', {})
            print(f"   Leading Department: {leading_dept.get('name', 'N/A')} ({leading_dept.get('resource_count', 0)} resources)")
            print(f"   Most Expensive Item: {most_expensive.get('device_name', 'N/A')} (₹{most_expensive.get('cost', 0):,.2f})")
        else:
            self.print_error(f"Dashboard overview failed: HTTP {response.status_code if response else 'No response'}")

    def test_department_analytics(self):
        """Test department analytics endpoint."""
        print("\n🏢 Department Analytics Testing")
        
        print(f"\n🔄 Making GET request to /api/dashboard/department-analytics...")
        response = self.make_request("GET", "/api/dashboard/department-analytics")
        
        if response and response.status_code == 200:
            data = response.json()
            departments = data.get('department_analytics', [])
            summary = data.get('summary', {})
            
            print(f"\n✅ Department Analytics Retrieved:")
            print(f"   Total Departments: {summary.get('total_departments', 0)}")
            print(f"   Total System Value: ₹{summary.get('total_system_value', 0):,.2f}")
            print(f"   Avg Resources/Dept: {summary.get('average_resources_per_dept', 0):.1f}")
            
            comparison = summary.get('comparison_metrics', {})
            print(f"\n🏆 Department Leaders:")
            print(f"   Highest Value: {comparison.get('highest_value_department', 'N/A')}")
            print(f"   Most Diverse: {comparison.get('most_diverse_department', 'N/A')}")
            print(f"   Most Distributed: {comparison.get('most_distributed_department', 'N/A')}")
            
            print(f"\n📋 Top 5 Departments by Value:")
            for i, dept in enumerate(departments[:5], 1):
                metrics = dept.get('metrics', {})
                efficiency = dept.get('efficiency', {})
                print(f"{i}. {dept.get('department_name', 'N/A')}")
                print(f"   Value: ₹{metrics.get('total_cost', 0):,.2f}")
                print(f"   Resources: {metrics.get('total_resources', 0)}")
                print(f"   Efficiency Score: {efficiency.get('efficiency_score', 0):.1f}%")
                print()
        else:
            self.print_error(f"Department analytics failed: HTTP {response.status_code if response else 'No response'}")

    def test_cost_analysis(self):
        """Test cost analysis endpoint."""
        print("\n💰 Cost Analysis Testing")
        
        time_range = input("Enter time range (1_month/3_months/6_months/12_months, default: 12_months): ").strip() or "12_months"
        
        print(f"\n🔄 Making GET request to /api/dashboard/cost-analysis?time_range={time_range}...")
        response = self.make_request("GET", f"/api/dashboard/cost-analysis?time_range={time_range}")
        
        if response and response.status_code == 200:
            data = response.json()
            cost_analysis = data.get('cost_analysis', {})
            financial_summary = data.get('financial_summary', {})
            
            print(f"\n✅ Cost Analysis Retrieved:")
            print(f"   Total Invested: ₹{financial_summary.get('total_invested', 0):,.2f}")
            print(f"   Avg Cost/Device Type: ₹{financial_summary.get('average_cost_per_device_type', 0):,.2f}")
            print(f"   Cost Efficiency Score: {financial_summary.get('cost_efficiency_score', 0):.1f}%")
            print(f"   Budget Utilization: {financial_summary.get('budget_utilization_rate', 0):.1f}%")
            
            # Show top cost categories
            device_costs = cost_analysis.get('device_type_costs', [])
            print(f"\n💸 Top 5 Device Types by Cost:")
            for i, device in enumerate(device_costs[:5], 1):
                print(f"{i}. {device.get('_id', 'N/A')}: ₹{device.get('total_cost', 0):,.2f} ({device.get('total_quantity', 0)} units)")
            
            location_costs = cost_analysis.get('location_costs', [])
            print(f"\n🏢 Top 5 Locations by Cost:")
            for i, location in enumerate(location_costs[:5], 1):
                print(f"{i}. {location.get('_id', 'N/A')}: ₹{location.get('total_cost', 0):,.2f}")
        else:
            self.print_error(f"Cost analysis failed: HTTP {response.status_code if response else 'No response'}")

    def test_utilization_metrics(self):
        """Test utilization metrics endpoint."""
        print("\n📈 Utilization Metrics Testing")
        
        print(f"\n🔄 Making GET request to /api/dashboard/utilization-metrics...")
        response = self.make_request("GET", "/api/dashboard/utilization-metrics")
        
        if response and response.status_code == 200:
            data = response.json()
            utilization = data.get('utilization_metrics', {})
            efficiency_scores = data.get('efficiency_scores', {})
            recommendations = data.get('recommendations', [])
            
            print(f"\n✅ Utilization Metrics Retrieved:")
            print(f"\n📊 Efficiency Scores:")
            print(f"   Overall Efficiency: {efficiency_scores.get('overall_efficiency', 0):.1f}%")
            print(f"   Resource Distribution: {efficiency_scores.get('resource_distribution_score', 0):.1f}%")
            print(f"   Cost Optimization: {efficiency_scores.get('cost_optimization_score', 0):.1f}%")
            print(f"   Maintenance Readiness: {efficiency_scores.get('maintenance_readiness_score', 0):.1f}%")
            
            # Show location density insights
            location_density = utilization.get('location_density', [])
            print(f"\n🏢 Top 5 Most Dense Locations:")
            for i, location in enumerate(location_density[:5], 1):
                print(f"{i}. {location.get('_id', 'N/A')}: {location.get('resource_count', 0)} resources ({location.get('device_diversity', 0)} device types)")
            
            # Show recommendations
            print(f"\n💡 Top Recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"{i}. [{rec.get('priority', 'Medium')}] {rec.get('category', 'General')}")
                print(f"   {rec.get('recommendation', 'N/A')}")
                print()
        else:
            self.print_error(f"Utilization metrics failed: HTTP {response.status_code if response else 'No response'}")

    def test_chart_data(self):
        """Test chart data generation."""
        print("\n📊 Chart Data Generation Testing")
        
        chart_type = input("Enter chart type (all/pie/bar/line/donut/heatmap, default: all): ").strip() or "all"
        
        print(f"\n🔄 Making GET request to /api/dashboard/charts?type={chart_type}...")
        response = self.make_request("GET", f"/api/dashboard/charts?type={chart_type}")
        
        if response and response.status_code == 200:
            data = response.json()
            charts = data.get('charts', {})
            metadata = data.get('metadata', {})
            
            print(f"\n✅ Chart Data Generated:")
            print(f"   Available Chart Types: {len(charts)}")
            print(f"   Total Data Points: {metadata.get('data_points', 0)}")
            
            for chart_name, chart_data in charts.items():
                chart_info = f"   📊 {chart_name.replace('_', ' ').title()}: "
                if 'labels' in chart_data:
                    chart_info += f"{len(chart_data['labels'])} categories"
                elif 'categories' in chart_data:
                    chart_info += f"{len(chart_data['categories'])} data points"
                elif 'data' in chart_data:
                    chart_info += f"{len(chart_data['data'])} items"
                print(chart_info)
        else:
            self.print_error(f"Chart data generation failed: HTTP {response.status_code if response else 'No response'}")

    def test_performance_summary(self):
        """Test dashboard performance summary."""
        print("\n🎯 Performance Summary Testing")
        
        try:
            # Test individual dashboard endpoints
            endpoints = [
                ("/api/dashboard/overview", "Dashboard Overview"),
                ("/api/dashboard/department-analytics", "Department Analytics"), 
                ("/api/dashboard/cost-analysis", "Cost Analysis"),
                ("/api/dashboard/utilization-metrics", "Utilization Metrics")
            ]
            
            for endpoint, name in endpoints:
                print(f"\n🔄 Testing {name}...")
                
                response = self.make_request("GET", endpoint)
                
                if response and response.status_code == 200:
                    data = response.json()
                    self.print_success(f"{name} working")
                    
                    # Show key metrics if available
                    if 'overview' in data:
                        overview = data['overview']
                        self.print_info(f"Resources: {overview.get('total_resources', 0)}")
                        self.print_info(f"Total Value: ₹{overview.get('total_value', 0):,.2f}")
                    elif 'department_analytics' in data:
                        analytics = data['department_analytics']
                        self.print_info(f"Departments analyzed: {len(analytics)}")
                    elif 'cost_analysis' in data:
                        cost = data['cost_analysis']
                        self.print_info(f"Cost categories: {len(cost.get('categories', []))}")
                        
                else:
                    error_msg = response.json().get('error', 'Unknown error') if response else 'No response'
                    self.print_error(f"{name} failed: {error_msg}")
        
        except Exception as e:
            self.print_error(f"Performance summary error: {e}")
    def test_export_functionality(self):
        """Test export functionality."""
        self.print_section("Export System Testing")
        
        if not self.auth_token:
            self.print_error("Please login first")
            return
        
        while True:
            print("\n📊 Export Options:")
            print("1. 📄 Export All Resources (CSV)")
            print("2. 📗 Export All Resources (Excel)")
            print("3. 🏢 Export by Department")
            print("4. 📍 Export by Location")
            print("5. 🔍 Export with Filters")
            print("6. 📋 Download CSV Template")
            print("7. 📊 View Export Formats")
            print("8. ⬅️  Back to Main Menu")
            
            choice = input("\nEnter your choice (1-8): ").strip()
            
            if choice == '1':
                self.export_all_csv()
            elif choice == '2':
                self.export_all_excel()
            elif choice == '3':
                self.export_by_department()
            elif choice == '4':
                self.export_by_location()
            elif choice == '5':
                self.export_with_filters()
            elif choice == '6':
                self.download_csv_template()
            elif choice == '7':
                self.view_export_formats()
            elif choice == '8':
                break
            else:
                self.print_error("Invalid choice. Please try again.")

    def export_all_csv(self):
        """Export all resources to CSV."""
        print("\n📄 Export All Resources (CSV)")
        
        print(f"\n🔄 Making GET request to /api/export/csv...")
        response = self.make_request("GET", "/api/export/csv")
        
        if response and response.status_code == 200:
            filename = f"all_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            self.print_success(f"All resources exported to: {filename}")
        else:
            self.print_error(f"Export failed: HTTP {response.status_code if response else 'No response'}")

    def export_by_department(self):
        """Export resources by department."""
        print("\n🏢 Export by Department")
        
        department = input("Enter department name: ").strip()
        format_type = input("Enter format (csv/excel): ").strip().lower() or 'csv'
        
        print(f"\n🔄 Making GET request to /api/export/department/{department}?format={format_type}...")
        response = self.make_request("GET", f"/api/export/department/{department}?format={format_type}")
        
        if response and response.status_code == 200:
            ext = 'xlsx' if format_type == 'excel' else 'csv'
            filename = f"{department.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            
            mode = 'wb' if format_type == 'excel' else 'w'
            content = response.content if format_type == 'excel' else response.text
            
            with open(filename, mode, encoding='utf-8' if mode == 'w' else None) as f:
                f.write(content)
            
            self.print_success(f"Department resources exported to: {filename}")
        else:
            self.print_error(f"Export failed: HTTP {response.status_code if response else 'No response'}")

    # def export_with_filters(self):
    #     """Export with custom filters."""
    #     print("\n🔍 Export with Filters")
        
    #     department = input("Department (optional): ").strip() or None
    #     location = input("Location (optional): ").strip() or None
    #     device_type = input("Device type (optional): ").strip() or None
    #     search_query = input("Search query (optional): ").strip() or None
        
    #     # Build query parameters
    #     params = {}
    #     if department:
    #         params['department'] = department
    #     if location:
    #         params['location'] = location
    #     if device_type:
    #         params['device_type'] = device_type
    #     if search_query:
    #         params['query'] = search_query
        
    #     print(f"\n🔄 Making GET request to /api/export/csv with filters...")
    #     response = self.make_request("GET", "/api/export/csv", params=params)
        
    #     if response and response.status_code == 200:
    #         filename = f"filtered_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    #         with open(filename, 'w', encoding='utf-8') as f:
    #             f.write(response.text)
            
    #         self.print_success(f"Filtered resources exported to: {filename}")
    #     else:
    #         self.print_error(f"Export failed: HTTP {response.status_code if response else 'No response'}")

    def view_export_formats(self):
        """View available export formats."""
        print("\n📊 Export Formats")
        
        print(f"\n🔄 Making GET request to /api/export/formats...")
        response = self.make_request("GET", "/api/export/formats")
        
        if response and response.status_code == 200:
            data = response.json()
            formats = data.get('supported_formats', {})
            
            print("\n✅ Available Export Formats:")
            for format_key, format_info in formats.items():
                print(f"\n📋 {format_info['name']}:")
                print(f"   Extension: {format_info['file_extension']}")
                print(f"   Description: {format_info['description']}")
                print(f"   Features: {', '.join(format_info['features'])}")
            
            print(f"\n📈 Performance:")
            est_times = data.get('estimated_generation_time', {})
            for fmt, time in est_times.items():
                print(f"   {fmt.upper()}: {time}")
        else:
            self.print_error(f"Failed to get formats: HTTP {response.status_code if response else 'No response'}")
    def export_all_excel(self):
        """Export all resources to Excel format."""
        print("\n📗 Export All Resources (Excel)")
        
        print(f"\n🔄 Making GET request to /api/export/excel...")
        response = self.make_request("GET", "/api/export/excel")
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                filename = f"all_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                self.print_success(f"All resources exported to: {filename}")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Export error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Export error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")

    def export_by_location(self):
        """Export resources by specific location."""
        print("\n📍 Export by Location")
        
        location = input("Enter location name: ").strip()
        format_choice = input("Enter format (csv/excel): ").strip().lower() or "excel"
        
        print(f"\n🔄 Making GET request to /api/export/location/{location}?format={format_choice}...")
        response = self.make_request("GET", f"/api/export/location/{location}?format={format_choice}")
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                safe_location = location.replace(' ', '_').replace('/', '_')
                
                if format_choice == 'excel':
                    filename = f"{safe_location}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                else:
                    filename = f"{safe_location}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    with open(filename, 'w') as f:
                        f.write(response.text)
                
                self.print_success(f"Location resources exported to: {filename}")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Export error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Export error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")

    def download_csv_template(self):
        """Download CSV template for resource import."""
        print("\n📋 Download CSV Template")
        
        print(f"\n🔄 Making GET request to /api/upload/template...")
        response = self.make_request("GET", "/api/upload/template")
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                filename = f"resource_import_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                with open(filename, 'w') as f:
                    f.write(response.text)
                
                self.print_success(f"CSV template downloaded: {filename}")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Download error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Download error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")

    def export_with_filters(self):
        """Export resources with filters - Excel as primary format."""
        print("\n🔍 Export with Filters")
        
        department = input("Department (optional): ").strip()
        location = input("Location (optional): ").strip()
        device_type = input("Device type (optional): ").strip()
        search_query = input("Search query (optional): ").strip()
        format_choice = input("Format (excel/csv, default: excel): ").strip().lower() or "excel"
        
        # Build query parameters
        params = []
        if department:
            params.append(f"department={department}")
        if location:
            params.append(f"location={location}")
        if device_type:
            params.append(f"device_type={device_type}")
        if search_query:
            params.append(f"search={search_query}")
        
        params.append(f"format={format_choice}")
        
        query_string = "&".join(params)
        endpoint = f"/api/export/filtered?{query_string}" if query_string else f"/api/export/filtered?format={format_choice}"
        
        print(f"\n🔄 Making GET request to {endpoint}...")
        response = self.make_request("GET", endpoint)
        
        if response:
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                if format_choice == 'excel':
                    filename = f"filtered_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                else:
                    filename = f"filtered_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    with open(filename, 'w') as f:
                        f.write(response.text)
                
                self.print_success(f"Filtered resources exported to: {filename}")
            else:
                try:
                    error_data = response.json()
                    self.print_error(f"Export error: {error_data.get('error', 'Unknown error')}")
                except:
                    self.print_error(f"Export error: HTTP {response.status_code}")
        else:
            self.print_error("No response from server")

    def export_system_menu(self):
        """Export system menu with all options."""
        self.print_section("Export System Testing")
        
        if not self.auth_token:
            self.print_error("Please login first")
            return
        
        while True:
            print("\n📊 Export Options:")
            print("1. 📄 Export All Resources (CSV)")
            print("2. 📗 Export All Resources (Excel)")
            print("3. 🏢 Export by Department")
            print("4. 📍 Export by Location")
            print("5. 🔍 Export with Filters")
            print("6. 📋 Download CSV Template")
            print("7. 📊 View Export Formats")
            print("8. ⬅️  Back to Main Menu")
            
            choice = input("\nEnter your choice (1-8): ").strip()
            
            if choice == '1':
                self.export_all_csv()
            elif choice == '2':
                self.export_all_excel()
            elif choice == '3':
                self.export_by_department()
            elif choice == '4':
                self.export_by_location()
            elif choice == '5':
                self.export_with_filters()
            elif choice == '6':
                self.download_csv_template()
            elif choice == '7':
                self.view_export_formats()
            elif choice == '8':
                break
            else:
                self.print_error("Invalid choice. Please try again.")

    # Update main menu to include export testing
    def main_menu(self):
        """Main menu interface with export functionality."""
        self.print_header("Campus Assets Management System - Interactive CLI")
        
        if not self.check_server_status():
            return
        
        while True:
            print("\n🏠 Main Menu:")
            print("1. 🔐 Authentication System")
            print("2. 📦 Resource Management")
            print("3. 🔍 Advanced Filtering & Search")
            print("4. 📁 File Upload & Processing")
            print("5. 📤 Export & Download System")  # NEW OPTION
            print("6. 🤖 AI Integration")
            print("7. 🚪 Exit")
            
            choice = input("\nEnter your choice (1-7): ").strip()
            
            if choice == '1':
                self.authentication_menu()
            elif choice == '2':
                self.resource_management_menu()
            elif choice == '3':
                self.test_advanced_filtering()
            elif choice == '4':
                self.file_upload_menu()
            elif choice == '5':
                self.export_system_menu()  # NEW METHOD
            elif choice == '6':
                self.ai_integration_menu()
            elif choice == '7':
                print("\n👋 Thank you for using Campus Assets Management System!")
                break
            else:
                self.print_error("Invalid choice. Please try again.")

def main():
    """Main CLI execution."""
    try:
        cli = CampusAssetsCLI()
        cli.main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
