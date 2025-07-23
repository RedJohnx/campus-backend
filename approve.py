"""
Admin approval script for Campus Assets system.
"""

from database import init_db, get_db
from datetime import datetime
import json

def list_pending_admins():
    """List all pending admin accounts."""
    print("📋 Pending Admin Accounts")
    print("=" * 40)
    
    if not init_db():
        print("❌ Database connection failed")
        return []
    
    db = get_db()
    
    # Find pending admin accounts
    pending_admins = list(db.users.find({
        'role': 'admin',
        'status': 'pending'
    }))
    
    if not pending_admins:
        print("ℹ️  No pending admin accounts found")
        return []
    
    print(f"Found {len(pending_admins)} pending admin account(s):")
    print()
    
    for i, admin in enumerate(pending_admins, 1):
        print(f"{i}. Name: {admin.get('name', 'N/A')}")
        print(f"   Email: {admin['email']}")
        print(f"   Registered: {admin.get('created_at', 'N/A')}")
        print(f"   User ID: {admin['_id']}")
        print()
    
    return pending_admins

def approve_admin(admin_id):
    """Approve a specific admin account."""
    try:
        db = get_db()
        
        # Update user status to active
        result = db.users.update_one(
            {'_id': admin_id},
            {
                '$set': {
                    'status': 'active',
                    'approved_at': datetime.now(),
                    'approved_by': 'master_admin'
                }
            }
        )
        
        if result.modified_count > 0:
            print("✅ Admin account approved successfully!")
            return True
        else:
            print("❌ Failed to approve admin account")
            return False
            
    except Exception as e:
        print(f"❌ Error approving admin: {e}")
        return False

def approve_admin_by_email(email):
    """Approve admin account by email."""
    try:
        db = get_db()
        
        # Find user by email
        user = db.users.find_one({'email': email, 'role': 'admin', 'status': 'pending'})
        
        if not user:
            print(f"❌ No pending admin account found with email: {email}")
            return False
        
        # Update user status
        result = db.users.update_one(
            {'_id': user['_id']},
            {
                '$set': {
                    'status': 'active',
                    'approved_at': datetime.now(),
                    'approved_by': 'master_admin'
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ Admin account approved: {email}")
            return True
        else:
            print(f"❌ Failed to approve admin account: {email}")
            return False
            
    except Exception as e:
        print(f"❌ Error approving admin: {e}")
        return False

def interactive_approval():
    """Interactive admin approval process."""
    print("Campus Assets - Admin Approval Tool")
    print("=" * 40)
    
    # List pending admins
    pending_admins = list_pending_admins()
    
    if not pending_admins:
        return
    
    print("Options:")
    print("1. Approve specific admin by number")
    print("2. Approve all pending admins")
    print("3. Approve by email")
    print("4. Exit")
    
    try:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            admin_num = int(input("Enter admin number to approve: "))
            if 1 <= admin_num <= len(pending_admins):
                admin = pending_admins[admin_num - 1]
                if approve_admin(admin['_id']):
                    print(f"✅ Approved: {admin['name']} ({admin['email']})")
            else:
                print("❌ Invalid admin number")
                
        elif choice == '2':
            approved_count = 0
            for admin in pending_admins:
                if approve_admin(admin['_id']):
                    approved_count += 1
                    print(f"✅ Approved: {admin['name']} ({admin['email']})")
            
            print(f"\n✅ Approved {approved_count} out of {len(pending_admins)} admin accounts")
            
        elif choice == '3':
            email = input("Enter admin email to approve: ").strip()
            approve_admin_by_email(email)
            
        elif choice == '4':
            print("👋 Goodbye!")
            return
            
        else:
            print("❌ Invalid choice")
            
    except ValueError:
        print("❌ Invalid input")
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def main():
    """Main approval function."""
    if not init_db():
        print("❌ Database initialization failed")
        return
    
    interactive_approval()

if __name__ == "__main__":
    main()
