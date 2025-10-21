"""
Email service for sending verification emails and notifications
"""
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import current_app, url_for
from models import db, User

class EmailService:
    def __init__(self):
        self.smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('MAIL_PORT', 587))
        self.smtp_username = os.environ.get('MAIL_USERNAME')
        self.smtp_password = os.environ.get('MAIL_PASSWORD')
        self.use_tls = os.environ.get('MAIL_USE_TLS', 'false').lower() == 'true'
        self.use_ssl = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
        self.from_email = os.environ.get('MAIL_USERNAME', 'noreply@banku.com')
        self.from_name = os.environ.get('MAIL_FROM_NAME', 'BankU')
    
    def send_email(self, to_email, subject, html_content, text_content=None):
        """Send email using SMTP"""
        try:
            # Check if email configuration is available
            if not self.smtp_username or not self.smtp_password:
                print("Email configuration missing. Please set MAIL_USERNAME and MAIL_PASSWORD environment variables.")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            if self.use_ssl:
                # Use SSL connection (port 465)
                import ssl
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context) as server:
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            else:
                # Use TLS connection (port 587)
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)
            
            print(f"Email sent successfully to {to_email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            print(f"SMTP Authentication Error: {e}")
            print("Please check your email credentials (MAIL_USERNAME and MAIL_PASSWORD)")
            return False
        except smtplib.SMTPException as e:
            print(f"SMTP Error: {e}")
            return False
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def send_verification_email(self, user):
        """Send email verification to user"""
        # Check if email verification is disabled for local testing
        if os.environ.get('DISABLE_EMAIL_VERIFICATION') == 'true':
            print("Email verification disabled for local testing")
            # Auto-verify the user for local testing
            user.email_verified = True
            user.email_verification_token = None
            user.email_verification_sent_at = None
            db.session.commit()
            return True
        
        # Check if webmail simulation is enabled
        if os.environ.get('WEBMAIL_SIMULATION') == 'true':
            print("Webmail simulation mode - showing verification link in console")
            # Generate verification token
            token = secrets.token_urlsafe(32)
            user.email_verification_token = token
            user.email_verification_sent_at = datetime.utcnow()
            db.session.commit()
            
            # Create verification URL
            verification_url = url_for('auth.verify_email', token=token, _external=True)
            
            # Display verification info in console
            print("\n" + "="*80)
            print("📧 WEBMAIL SIMULATION - EMAIL VERIFICATION")
            print("="*80)
            print(f"FROM: noreply@allnd.me (your webmail)")
            print(f"TO: {user.email}")
            print(f"SUBJECT: Verify Your BankU Account")
            print(f"VERIFICATION URL: {verification_url}")
            print("="*80)
            print("📋 INSTRUCTIONS:")
            print("1. Copy the verification URL above")
            print("2. Open it in your browser to verify the account")
            print("3. Or register a new user to test the full workflow")
            print("="*80 + "\n")
            
            return True
        
        # Generate verification token
        token = secrets.token_urlsafe(32)
        user.email_verification_token = token
        user.email_verification_sent_at = datetime.utcnow()
        db.session.commit()
        
        # Create verification URL
        verification_url = url_for('auth.verify_email', token=token, _external=True)
        
        # Email content
        subject = "Verify Your BankU Account"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Account</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #007bff; color: white !important; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to BankU!</h1>
                    <p>Please verify your email address to complete your registration</p>
                </div>
                <div class="content">
                    <h2>Hello {user.first_name}!</h2>
                    <p>Thank you for creating an account with BankU. To complete your registration and start using all features, please verify your email address by clicking the button below:</p>
                    
                    <div style="text-align: center;">
                        <a href="{verification_url}" class="button">Verify Email Address</a>
                    </div>
                    
                    <p>If the button doesn't work, you can also copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; background: #e9ecef; padding: 10px; border-radius: 5px; font-family: monospace;">{verification_url}</p>
                    
                    <p><strong>Important:</strong> This verification link will expire in 24 hours for security reasons.</p>
                    
                    <p>If you didn't create an account with BankU, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>© 2025 BankU. All rights reserved.</p>
                    <p>This is an automated message, please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to BankU!
        
        Hello {user.first_name},
        
        Thank you for creating an account with BankU. To complete your registration and start using all features, please verify your email address by visiting this link:
        
        {verification_url}
        
        This verification link will expire in 24 hours for security reasons.
        
        If you didn't create an account with BankU, please ignore this email.
        
        Best regards,
        The BankU Team
        """
        
        return self.send_email(user.email, subject, html_content, text_content)
    
    def send_phone_verification_sms(self, phone_number, verification_code):
        """Send SMS verification code (DISABLED - requires SMS service integration)"""
        # PHONE VERIFICATION IS CURRENTLY DISABLED
        # This is a placeholder. In production, you would integrate with an SMS service like:
        # - Twilio
        # - AWS SNS
        # - SendGrid
        # - Vonage (formerly Nexmo)
        
        print(f"[DISABLED] SMS to {phone_number}: Your BankU verification code is: {verification_code}")
        return True
    
    def send_welcome_email(self, user):
        """Send welcome email after successful verification"""
        subject = "Welcome to BankU - Your Account is Verified!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to BankU</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .feature {{ margin: 20px 0; padding: 15px; background: white; border-radius: 5px; border-left: 4px solid #007bff; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to BankU!</h1>
                    <p>Your account has been successfully verified</p>
                </div>
                <div class="content">
                    <h2>Hello {user.first_name}!</h2>
                    <p>Congratulations! Your BankU account is now fully activated and ready to use. You can now access all features of our platform.</p>
                    
                    <div class="feature">
                        <h3>🏦 Centralized Banks</h3>
                        <p>Explore our organized banks of products, services, ideas, and opportunities.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>🤖 AI-Powered Matching</h3>
                        <p>Let our AI help you find the perfect matches for your needs and offerings.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>🏢 Organizations</h3>
                        <p>Create or join organizations to collaborate with teams and manage content together.</p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="{url_for('dashboard.index', _external=True)}" class="button">Go to Dashboard</a>
                    </div>
                    
                    <p>If you have any questions or need help getting started, don't hesitate to reach out to our support team.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return self.send_email(user.email, subject, html_content)

# Global email service instance
email_service = EmailService()
