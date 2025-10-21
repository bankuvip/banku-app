from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import User, Role, Tag, db
from utils.data_collection import collection_engine
from utils.email_service import email_service
from datetime import datetime, timedelta
import os
import uuid
import secrets
from PIL import Image

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        login_field = data.get('login_field') or data.get('email')  # Support both field names
        password = data.get('password')
        remember = data.get('remember', False)
        
        # Try to find user by email or username
        user = User.query.filter(
            (User.email == login_field) | (User.username == login_field)
        ).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.is_active:
                login_user(user, remember=remember)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                # Check if email is verified
                if not user.email_verified:
                    if request.is_json:
                        return jsonify({
                            'success': True,
                            'message': 'Login successful, but please verify your email',
                            'redirect': url_for('auth.verification')
                        })
                    flash('Please verify your email address to access all features.', 'warning')
                    return redirect(url_for('auth.verification'))
                
                # Handle redirect after successful login
                next_page = request.form.get('next') or request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('dashboard.index')
                
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'Login successful',
                        'redirect': next_page
                    })
                return redirect(next_page)
            else:
                message = 'Account is deactivated. Please contact support.'
        else:
            message = 'Invalid email/username or password.'
        
        if request.is_json:
            return jsonify({'success': False, 'message': message})
        flash(message, 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            phone = data.get('phone')
            location = data.get('location')
            
            # Validate required fields
            if not username or not email or not password or not first_name or not last_name:
                message = 'All required fields must be filled'
                if request.is_json:
                    return jsonify({'success': False, 'message': message})
                flash(message, 'error')
                return render_template('auth/register.html')
        
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                message = 'Email already registered'
                if request.is_json:
                    return jsonify({'success': False, 'message': message, 'field': 'email'})
                flash(message, 'error')
                return render_template('auth/register.html')
            
            if User.query.filter_by(username=username).first():
                message = 'Username already taken'
                if request.is_json:
                    return jsonify({'success': False, 'message': message, 'field': 'username'})
                flash(message, 'error')
                return render_template('auth/register.html')
            
            # Create new user (unverified initially)
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                location=location,
                email_verified=False,
                is_active=True  # Allow login but with limited features
            )
            
            db.session.add(user)
            db.session.flush()  # Get user ID
        
            # Create default personal profile
            from models import Profile, ProfileType
            
            # Get the 'person' profile type, or create it if it doesn't exist
            person_profile_type = ProfileType.query.filter_by(name='person').first()
            if not person_profile_type:
                # Create default 'person' profile type if it doesn't exist
                person_profile_type = ProfileType(
                    name='person',
                    display_name='Person',
                    description='Basic personal profile for individuals',
                    icon_class='fas fa-user',
                    color_class='primary',
                    max_profiles_per_user=3,
                    requires_verification=False,
                    is_active=True,
                    order_index=1
                )
                db.session.add(person_profile_type)
                db.session.flush()  # Get the ID
            
            personal_profile = Profile(
                user_id=user.id,
                name=f"{first_name} {last_name}",
                profile_type='person',  # Keep for backward compatibility
                profile_type_id=person_profile_type.id,  # New foreign key system
                description=f"Personal profile of {first_name} {last_name}",
                is_public=False,  # Private by default
                is_default=True  # Mark as default profile
            )
            db.session.add(personal_profile)
        
            # Assign default "User" role to new user
            from models import Role, UserRole
            user_role = Role.query.filter_by(name='User').first()
            if user_role:
                user_role_assignment = UserRole(
                    user_id=user.id,
                    role_id=user_role.id,
                    assigned_by=1,  # System assignment
                    is_active=True
                )
                db.session.add(user_role_assignment)
            else:
                print(f"Warning: 'User' role not found in database. New user {username} will not have any roles assigned.")
            
            db.session.commit()
        
            # Send email verification
            try:
                email_sent = email_service.send_verification_email(user)
                if email_sent:
                    message = 'Registration successful! Please check your email to verify your account.'
                else:
                    message = 'Registration successful! However, email verification is not configured. Your account is active but please contact support to verify your email.'
            except Exception as e:
                print(f"Error sending verification email: {e}")
                message = 'Registration successful! However, email verification is not configured. Your account is active but please contact support to verify your email.'
            
            # Trigger data collection for the new user
            try:
                collection_engine.on_data_created('users', user.id)
            except Exception as e:
                print(f"Error triggering data collection: {e}")
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': message,
                    'redirect': url_for('auth.login')
                })
            
            flash(message, 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            print(f"Registration error: {e}")
            import traceback
            traceback.print_exc()
            
            message = 'An unexpected error occurred during registration. Please try again.'
            if request.is_json:
                return jsonify({'success': False, 'message': message})
            flash(message, 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/validate-field', methods=['POST'])
def validate_field():
    """Validate if username or email is available"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'available': False, 'message': 'Invalid request data'})
        
        field = data.get('field')
        value = data.get('value')
        
        if not field or not value:
            return jsonify({'available': False, 'message': 'Field and value are required'})
        
        # Validate field type
        if field not in ['username', 'email']:
            return jsonify({'available': False, 'message': 'Invalid field type'})
        
        # Check database connection
        try:
            if field == 'username':
                user = User.query.filter_by(username=value).first()
                if user:
                    return jsonify({'available': False, 'message': 'Username already taken'})
                else:
                    return jsonify({'available': True, 'message': 'Username available'})
            
            elif field == 'email':
                user = User.query.filter_by(email=value).first()
                if user:
                    return jsonify({'available': False, 'message': 'Email already registered'})
                else:
                    return jsonify({'available': True, 'message': 'Email available'})
        except Exception as db_error:
            print(f"Database error in validate_field: {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'available': False, 'message': 'Database connection error'})
        
        return jsonify({'available': True, 'message': 'Valid'})
    
    except Exception as e:
        print(f"Error in validate_field: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'available': False, 'message': 'An unexpected error occurred'})

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify user email with token"""
    user = User.query.filter_by(email_verification_token=token).first()
    
    if not user:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('auth.login'))
    
    # Check if token is expired (24 hours)
    if user.email_verification_sent_at and \
       datetime.utcnow() > user.email_verification_sent_at + timedelta(hours=24):
        flash('Verification link has expired. Please request a new one.', 'error')
        return redirect(url_for('auth.login'))
    
    # Verify the user
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_sent_at = None
    db.session.commit()
    
    # Send welcome email
    try:
        email_service.send_welcome_email(user)
    except Exception as e:
        print(f"Error sending welcome email: {e}")
    
    flash('Email verified successfully! Welcome to BankU!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/resend-verification', methods=['POST'])
@login_required
def resend_verification():
    """Resend email verification with 3-attempt limit per user"""
    if current_user.email_verified:
        return jsonify({'success': False, 'message': 'Email already verified'})
    
    # Check if user is in cooldown period
    if current_user.email_resend_cooldown_until and \
       datetime.utcnow() < current_user.email_resend_cooldown_until:
        remaining_time = int((current_user.email_resend_cooldown_until - datetime.utcnow()).total_seconds())
        return jsonify({
            'success': False, 
            'message': f'Too many attempts. Please wait {remaining_time} seconds before trying again.',
            'cooldown': remaining_time,
            'max_attempts': True
        })
    
    # Check if user has reached the limit (3 attempts)
    if current_user.email_resend_count >= 3:
        # Set cooldown period (5 minutes from now)
        current_user.email_resend_cooldown_until = datetime.utcnow() + timedelta(minutes=5)
        current_user.email_resend_count = 0  # Reset counter for next cooldown cycle
        db.session.commit()
        
        remaining_time = 300  # 5 minutes
        return jsonify({
            'success': False, 
            'message': f'Too many attempts. Please wait {remaining_time} seconds before trying again.',
            'cooldown': remaining_time,
            'max_attempts': True
        })
    
    try:
        email_sent = email_service.send_verification_email(current_user)
        if email_sent:
            # Check if email verification was auto-verified (local testing mode)
            if current_user.email_verified and os.environ.get('DISABLE_EMAIL_VERIFICATION') == 'true':
                return jsonify({
                    'success': True, 
                    'message': 'Email verification disabled for local testing. Your account is automatically verified!',
                    'auto_verified': True
                })
            
            # Increment resend count for this user
            current_user.email_resend_count += 1
            db.session.commit()
            
            remaining_attempts = 3 - current_user.email_resend_count
            if remaining_attempts > 0:
                message = f'Verification email sent! Please check your inbox. ({remaining_attempts} attempts remaining)'
            else:
                message = 'Verification email sent! Please check your inbox. (No more attempts remaining - wait 5 minutes for next try)'
            
            return jsonify({
                'success': True, 
                'message': message,
                'attempts_remaining': remaining_attempts,
                'max_attempts': remaining_attempts == 0
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Email verification is not configured. Please contact support to verify your email address.',
                'needs_config': True
            })
    except Exception as e:
        print(f"Error resending verification email: {e}")
        return jsonify({
            'success': False, 
            'message': 'Email verification is not configured. Please contact support to verify your email address.',
            'needs_config': True
        })

@auth_bp.route('/verify-phone', methods=['POST'])
@login_required
def verify_phone():
    """Verify phone number with SMS code"""
    data = request.get_json()
    phone = data.get('phone')
    code = data.get('code')
    
    if not phone or not code:
        return jsonify({'success': False, 'message': 'Phone number and verification code are required'})
    
    # Check if user has a pending verification
    if not current_user.phone_verification_code or \
       not current_user.phone_verification_sent_at or \
       datetime.utcnow() > current_user.phone_verification_sent_at + timedelta(minutes=10):
        return jsonify({'success': False, 'message': 'No valid verification code found. Please request a new one.'})
    
    # Verify the code
    if current_user.phone_verification_code == code:
        current_user.phone_verified = True
        current_user.phone_verification_code = None
        current_user.phone_verification_sent_at = None
        current_user.phone = phone
        db.session.commit()
        return jsonify({'success': True, 'message': 'Phone number verified successfully!'})
    else:
        return jsonify({'success': False, 'message': 'Invalid verification code'})

@auth_bp.route('/send-phone-verification', methods=['POST'])
@login_required
def send_phone_verification():
    """Send SMS verification code to phone"""
    data = request.get_json()
    phone = data.get('phone')
    
    if not phone:
        return jsonify({'success': False, 'message': 'Phone number is required'})
    
    # Check if we can send (not too frequent)
    if current_user.phone_verification_sent_at and \
       datetime.utcnow() < current_user.phone_verification_sent_at + timedelta(minutes=1):
        return jsonify({'success': False, 'message': 'Please wait 1 minute before requesting another verification code'})
    
    # Generate verification code
    verification_code = secrets.randbelow(900000) + 100000  # 6-digit code
    current_user.phone_verification_code = str(verification_code)
    current_user.phone_verification_sent_at = datetime.utcnow()
    db.session.commit()
    
    try:
        # Send SMS (placeholder - requires SMS service integration)
        sms_sent = email_service.send_phone_verification_sms(phone, verification_code)
        if sms_sent:
            return jsonify({'success': True, 'message': f'Verification code sent to {phone}'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send verification code. Please try again later.'})
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return jsonify({'success': False, 'message': 'An error occurred. Please try again later.'})

@auth_bp.route('/verification')
@login_required
def verification():
    """Account verification status page"""
    return render_template('auth/verification.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    from models import Item, Information, Profile
    
    # Get user's profiles
    user_profiles = Profile.query.filter_by(user_id=current_user.id).all()
    default_profile = Profile.query.filter_by(user_id=current_user.id, is_default=True).first()
    
    # Get user's items from ALL profiles organized by type
    user_items = {}
    all_items = Item.query.join(Profile).filter(Profile.user_id == current_user.id).order_by(Item.created_at.desc()).all()
    for item in all_items:
        category = item.category
        if category not in user_items:
            user_items[category] = []
        user_items[category].append(item)
    
    # Get user's information entries
    user_information = Information.query.filter_by(created_by=current_user.id).order_by(Information.created_at.desc()).all()
    
    # Calculate counts for each item type (user's own items only)
    item_counts = {
        'products': len(user_items.get('product', [])),
        'services': len(user_items.get('service', [])),
        'experiences': len(user_items.get('experiences', [])),
        'opportunities': len(user_items.get('opportunities', [])),
        'events': len(user_items.get('events', [])),
        'observations': len(user_items.get('observations', [])),
        'hidden_gems': len(user_items.get('hidden_gems', [])),
        'funders': len(user_items.get('funders', [])),
        'knowledge': len(user_items.get('knowledge', [])),
        'ideas': len(user_items.get('idea', [])),
        'funding': len(user_items.get('funding', [])),
        'information': len(user_information)  # Information comes from Information table, not Item table
    }
    
    # Calculate personality classification based on item distribution
    total_items = sum(item_counts.values())
    personality_percentages = {}
    
    if total_items > 0:
        personality_percentages = {
            'producer': round((item_counts['products'] / total_items) * 100, 1),
            'skiller': round((item_counts['services'] / total_items) * 100, 1),
            'experiencer': round((item_counts['experiences'] / total_items) * 100, 1),
            'opportunist': round((item_counts['opportunities'] / total_items) * 100, 1),
            'organizer': round((item_counts['events'] / total_items) * 100, 1),
            'observer': round((item_counts['observations'] / total_items) * 100, 1),
            'explorer': round((item_counts['hidden_gems'] / total_items) * 100, 1),
            'investor': round(((item_counts['funders'] + item_counts['funding']) / total_items) * 100, 1),
            'consultant': round((item_counts['information'] / total_items) * 100, 1),
            'thinker': round((item_counts['ideas'] / total_items) * 100, 1),
            'learner': round((item_counts['knowledge'] / total_items) * 100, 1)
        }
    else:
        personality_percentages = {
            'producer': 0,
            'skiller': 0,
            'experiencer': 0,
            'opportunist': 0,
            'organizer': 0,
            'observer': 0,
            'explorer': 0,
            'investor': 0,
            'consultant': 0,
            'thinker': 0,
            'learner': 0
        }
    
    return render_template('auth/profile.html', 
                         user=current_user, 
                         user_profiles=user_profiles,
                         default_profile=default_profile,
                         user_items=user_items, 
                         user_information=user_information,
                         item_counts=item_counts,
                         personality_percentages=personality_percentages)

@auth_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """User settings page for editing profile"""
    if request.method == 'POST':
        try:
            # Update basic profile information
            current_user.first_name = request.form.get('first_name', current_user.first_name)
            current_user.last_name = request.form.get('last_name', current_user.last_name)
            current_user.username = request.form.get('username', current_user.username)
            current_user.email = request.form.get('email', current_user.email)
            current_user.phone = request.form.get('phone', current_user.phone)
            current_user.location = request.form.get('location', current_user.location)
            current_user.bio = request.form.get('bio', current_user.bio)
            
            # Handle avatar upload
            if 'avatar' in request.files:
                avatar_file = request.files['avatar']
                if avatar_file and avatar_file.filename != '':
                    # Validate file size (5MB max)
                    avatar_file.seek(0, 2)  # Seek to end
                    file_size = avatar_file.tell()
                    avatar_file.seek(0)  # Reset to beginning
                    
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        flash('File too large. Please upload an image smaller than 5MB.', 'error')
                        return render_template('auth/settings.html', user=current_user)
                    
                    # Validate file type
                    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
                    if '.' in avatar_file.filename and \
                       avatar_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                        
                        # Generate unique filename
                        filename = secure_filename(avatar_file.filename)
                        file_extension = filename.rsplit('.', 1)[1].lower()
                        unique_filename = f"{current_user.id}_{uuid.uuid4().hex}.{file_extension}"
                        
                        # Create uploads directory if it doesn't exist
                        upload_dir = os.path.join('static', 'uploads')
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        # Save file
                        file_path = os.path.join(upload_dir, unique_filename)
                        avatar_file.save(file_path)
                        
                        # Resize image to 200x200 for consistency
                        try:
                            with Image.open(file_path) as img:
                                img = img.convert('RGB')
                                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                                img.save(file_path, 'JPEG', quality=85)
                        except ImportError:
                            print("PIL not available, skipping image resize")
                        except Exception as e:
                            print(f"Error resizing image: {e}")
                        
                        # Delete old avatar if exists
                        if current_user.avatar:
                            old_avatar_path = os.path.join(upload_dir, current_user.avatar)
                            if os.path.exists(old_avatar_path):
                                os.remove(old_avatar_path)
                        
                        # Update user avatar
                        current_user.avatar = unique_filename
                    else:
                        flash('Invalid file type. Please upload a PNG, JPG, JPEG, or GIF image.', 'error')
                        return render_template('auth/settings.html', user=current_user)
            
            # Handle password change if provided
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if current_password and new_password and confirm_password:
                # Verify current password
                if not check_password_hash(current_user.password_hash, current_password):
                    flash('Current password is incorrect', 'error')
                    return render_template('auth/settings.html', user=current_user)
                
                # Verify new password confirmation
                if new_password != confirm_password:
                    flash('New passwords do not match', 'error')
                    return render_template('auth/settings.html', user=current_user)
                
                # Update password
                current_user.password_hash = generate_password_hash(new_password)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your profile', 'error')
            print(f"Error updating profile: {e}")
    
    return render_template('auth/settings.html', user=current_user)

@auth_bp.route('/remove-avatar', methods=['POST'])
@login_required
def remove_avatar():
    """Remove user's avatar"""
    try:
        if current_user.avatar:
            # Delete avatar file
            upload_dir = os.path.join('static', 'uploads')
            avatar_path = os.path.join(upload_dir, current_user.avatar)
            if os.path.exists(avatar_path):
                os.remove(avatar_path)
            
            # Clear avatar from database
            current_user.avatar = None
            db.session.commit()
            
            flash('Avatar removed successfully!', 'success')
        else:
            flash('No avatar to remove.', 'info')
            
    except Exception as e:
        db.session.rollback()
        flash('Error removing avatar.', 'error')
        print(f"Error removing avatar: {e}")
    
    return redirect(url_for('auth.settings'))
