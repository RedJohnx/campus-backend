"""
Email templates for Campus Assets system.
"""

def generate_admin_approval_email(user_data, approval_url):
    """
    Generate HTML email template for admin approval.
    
    Args:
        user_data: Dictionary with user information
        approval_url: URL for approval endpoint
    """
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Campus Assets - Admin Approval Request</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e0e0e0;
            }}
            .header h1 {{
                color: #2c3e50;
                margin: 0;
                font-size: 24px;
            }}
            .header p {{
                color: #7f8c8d;
                margin: 5px 0 0 0;
            }}
            .request-info {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #3498db;
            }}
            .request-info h3 {{
                color: #2c3e50;
                margin-top: 0;
            }}
            .info-row {{
                margin: 10px 0;
                padding: 8px 0;
                border-bottom: 1px solid #eee;
            }}
            .info-row:last-child {{
                border-bottom: none;
            }}
            .info-label {{
                font-weight: bold;
                color: #34495e;
                display: inline-block;
                width: 120px;
            }}
            .info-value {{
                color: #555;
            }}
            .button-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .approve-btn {{
                background-color: #27ae60;
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                display: inline-block;
                transition: background-color 0.3s;
            }}
            .approve-btn:hover {{
                background-color: #219a52;
            }}
            .reject-btn {{
                background-color: #e74c3c;
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
                display: inline-block;
                margin-left: 10px;
                transition: background-color 0.3s;
            }}
            .reject-btn:hover {{
                background-color: #c0392b;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #7f8c8d;
                font-size: 12px;
            }}
            .warning {{
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                color: #856404;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .timestamp {{
                color: #95a5a6;
                font-size: 12px;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏫 Campus Assets Management</h1>
                <p>Admin Account Approval Request</p>
            </div>
            
            <div class="request-info">
                <h3>📋 New Admin Registration Details</h3>
                
                <div class="info-row">
                    <span class="info-label">Name:</span>
                    <span class="info-value">{user_data.get('name', 'N/A')}</span>
                </div>
                
                <div class="info-row">
                    <span class="info-label">Email:</span>
                    <span class="info-value">{user_data.get('email', 'N/A')}</span>
                </div>
                
                <div class="info-row">
                    <span class="info-label">Role:</span>
                    <span class="info-value">{user_data.get('role', 'N/A').title()}</span>
                </div>
                
                <div class="info-row">
                    <span class="info-label">User ID:</span>
                    <span class="info-value">{user_data.get('user_id', 'N/A')}</span>
                </div>
                
                <div class="info-row">
                    <span class="info-label">Registration Time:</span>
                    <span class="info-value">{user_data.get('created_at', 'N/A')}</span>
                </div>
            </div>
            
            <div class="warning">
                <strong>⚠️ Security Notice:</strong> This user is requesting admin privileges for the Campus Assets Management System. Admin users can create, modify, and delete resource records. Please verify the identity of this user before approval.
            </div>
            
            <div class="button-container">
                <a href="{approval_url}&action=approve" class="approve-btn">
                    ✅ Approve Admin Account
                </a>
                <a href="{approval_url}&action=reject" class="reject-btn">
                    ❌ Reject Request
                </a>
            </div>
            
            <div class="footer">
                <p>Campus Assets Management System</p>
                <p>This is an automated email. Please do not reply.</p>
                <p class="timestamp">Generated on: {user_data.get('timestamp', 'N/A')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template

def generate_approval_success_email(user_data):
    """Generate email template for successful approval."""
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Campus Assets - Account Approved</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #e0e0e0;
            }}
            .success-message {{
                background: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
                text-align: center;
            }}
            .login-info {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Account Approved!</h1>
                <p>Your admin account has been activated</p>
            </div>
            
            <div class="success-message">
                <h3>✅ Congratulations!</h3>
                <p>Your admin account for Campus Assets Management System has been approved and activated.</p>
            </div>
            
            <div class="login-info">
                <h3>🔐 Login Information</h3>
                <p><strong>Email:</strong> {user_data.get('email', 'N/A')}</p>
                <p><strong>Role:</strong> Administrator</p>
                <p><strong>Login URL:</strong> <a href="http://localhost:3000/login">Campus Assets Portal</a></p>
            </div>
            
            <div class="footer">
                <p>Campus Assets Management System</p>
                <p>Welcome to the team!</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_template
