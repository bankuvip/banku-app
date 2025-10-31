from flask import Blueprint, render_template, request, jsonify, session, current_app
from flask_login import current_user, login_required
from models import ChatbotFlow, ChatbotQuestion, ChatbotResponse, ChatbotStepBlock, ItemType, DataStorageMapping, ChatbotCompletion, Item, Profile, Bank, db, Organization
from utils.data_collection import collection_engine
from utils.permissions import require_admin_role, require_permission
from utils.geocoding import parse_location
from utils.file_utils import (
    get_media_upload_config, 
    validate_uploaded_file, 
    get_file_category,
    format_file_size,
    get_all_categories,
    validate_uploaded_file_comprehensive,
    sanitize_filename
)
from datetime import datetime
import uuid
import os
import logging
from werkzeug.utils import secure_filename

chatbot_bp = Blueprint('chatbot', __name__)

def _is_likely_file_path(value):
    """
    Check if a string value looks like a file path, not a tag or other text.
    Returns True only if it looks like an actual file path.
    Accepts both forward slashes (uploads/users/...) and backslashes (uploads\\users\\...)
    """
    if not value or not isinstance(value, str):
        return False
    
    value = value.strip()
    
    # Normalize slashes for checking (accept both \ and /)
    normalized = value.replace('\\', '/').lower()
    
    # Must start with 'uploads/' (after normalization) to be a valid file path
    if not normalized.startswith('uploads/'):
        return False
    
    # Must have a file extension (common image extensions)
    import os
    file_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', 
                      '.pdf', '.doc', '.docx', '.mp4', '.mov', '.avi', '.mp3', '.wav']
    ext = os.path.splitext(normalized)[1]
    if ext in file_extensions:
        return True
    
    # Or must contain '/' or '\' which indicates a path structure
    if ('/' in value or '\\' in value) and (len(value.split('/')) >= 2 or len(value.split('\\')) >= 2):
        return True
    
    return False

def validate_chatbot_session():
    """Validate and clean up chatbot session data"""
    try:
        # Ensure session ID exists
        if 'chatbot_session_id' not in session:
            session['chatbot_session_id'] = str(uuid.uuid4())
        
        # Validate organization context if present
        if 'organization_id' in session:
            try:
                org_id = int(session['organization_id'])
                # Validate organization exists and user has access
                org = Organization.query.get(org_id)
                if not org:
                    logging.warning(f"Invalid organization ID in session: {org_id}")
                    del session['organization_id']
                elif not current_user.is_authenticated:
                    del session['organization_id']
                else:
                    # Check if user has access to this organization
                    from models import OrganizationMember
                    membership = OrganizationMember.query.filter_by(
                        organization_id=org_id, 
                        user_id=current_user.id,
                        status='active'
                    ).first()
                    if not membership:
                        logging.warning(f"User {current_user.id} has no access to organization {org_id}")
                        del session['organization_id']
            except (ValueError, TypeError) as e:
                logging.warning(f"Invalid organization_id in session: {e}")
                del session['organization_id']
        
        return True
    except Exception as e:
        logging.error(f"Session validation error: {str(e)}")
        # Clear problematic session data
        session.pop('organization_id', None)
        return False

@chatbot_bp.route('/')
@login_required
@require_permission('chatbots', 'view')
def index():
    """List all active chatbot flows"""
    flows = ChatbotFlow.query.filter_by(is_active=True).order_by(ChatbotFlow.created_at.desc()).all()
    return render_template('chatbot/index.html', flows=flows)

@chatbot_bp.route('/<int:flow_id>')
@login_required
@require_permission('chatbots', 'view')
def start_flow(flow_id):
    """Start a chatbot flow - Admin only"""
    try:
        # Validate session first
        if not validate_chatbot_session():
            flash('Session validation failed. Please try again.', 'error')
            return redirect(url_for('chatbot.index'))
        
        flow = ChatbotFlow.query.filter_by(id=flow_id, is_active=True).first_or_404()
        
        # Store organization context if provided
        organization_id = request.args.get('organization_id')
        if organization_id:
            try:
                org_id = int(organization_id)
                # Validate organization exists and user has access
                org = Organization.query.get(org_id)
                if org:
                    from models import OrganizationMember
                    membership = OrganizationMember.query.filter_by(
                        organization_id=org_id, 
                        user_id=current_user.id,
                        status='active'
                    ).first()
                    if membership:
                        session['organization_id'] = org_id
                    else:
                        flash('You do not have access to this organization.', 'error')
                        return redirect(url_for('chatbot.index'))
                else:
                    flash('Organization not found.', 'error')
                    return redirect(url_for('chatbot.index'))
            except (ValueError, TypeError):
                flash('Invalid organization ID.', 'error')
                return redirect(url_for('chatbot.index'))
        elif 'organization_id' in session:
            # Clear organization context if not provided
            del session['organization_id']
        
        return render_template('chatbot/flow.html', flow=flow)
        
    except Exception as e:
        logging.error(f"Error starting chatbot flow {flow_id}: {str(e)}")
        flash('An error occurred while starting the chatbot. Please try again.', 'error')
        return redirect(url_for('chatbot.index'))

@chatbot_bp.route('/<int:flow_id>/questions')
@login_required
@require_permission('chatbots', 'view')
def get_questions(flow_id):
    """Get questions for a flow (organized by step blocks)"""
    flow = ChatbotFlow.query.filter_by(id=flow_id, is_active=True).first_or_404()
    
    # Get step blocks with their questions
    step_blocks = ChatbotStepBlock.query.filter_by(flow_id=flow_id, is_active=True).order_by(ChatbotStepBlock.step_order).all()
    
    steps = []
    all_questions = []
    
    for step_block in step_blocks:
        step_questions = []
        for question in step_block.questions:
            question_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_type': question.question_type,
                'options': question.options,
                'validation_rules': question.validation_rules,
                'conditional_logic': question.conditional_logic,
                'cascading_config': question.cascading_config,
                'number_unit_config': question.number_unit_config,
                'media_upload_config': question.media_upload_config,
                'branching_logic': question.branching_logic,
                'is_required': question.is_required,
                'placeholder': question.placeholder,
                'help_text': question.help_text,
                'default_view': question.default_view,
                'order_index': question.order_index,
                'step_block_id': step_block.id
            }
            step_questions.append(question_data)
            all_questions.append(question_data)
        
        steps.append({
            'id': step_block.id,
            'name': step_block.name,
            'description': step_block.description,
            'is_required': step_block.is_required,
            'completion_message': step_block.completion_message,
            'questions': step_questions
        })
    
    response = jsonify({
        'success': True,
        'flow': {
            'id': flow.id,
            'name': flow.name,
            'description': flow.description
        },
        'steps': steps,
        'questions': all_questions  # Keep for backward compatibility
    })
    
    # Add cache headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@chatbot_bp.route('/<int:flow_id>/submit', methods=['POST'])
@login_required
@require_permission('chatbots', 'view')
def submit_response(flow_id):
    """Submit a response to a flow"""
    flow = ChatbotFlow.query.filter_by(id=flow_id, is_active=True).first_or_404()
    
    try:
        data = request.get_json()
        responses = data.get('responses', {})
        is_completed = data.get('completed', False)
        
        # Get or create session ID
        session_id = session.get('chatbot_session_id', str(uuid.uuid4()))
        if 'chatbot_session_id' not in session:
            session['chatbot_session_id'] = session_id
        
        # Validate responses if completing
        if is_completed:
            validation_errors = validate_responses(flow_id, responses)
            if validation_errors:
                return jsonify({
                    'success': False,
                    'errors': validation_errors,
                    'message': 'Please complete all required fields'
                }), 400
        
        # Check if response already exists
        existing_response = ChatbotResponse.query.filter_by(
            flow_id=flow_id, 
            session_id=session_id
        ).first()
        
        if existing_response:
            # Update existing response
            existing_response.responses = responses
            existing_response.completed = is_completed
            if is_completed:
                existing_response.completed_at = datetime.utcnow()
        else:
            # Create new response
            response = ChatbotResponse(
                flow_id=flow_id,
                session_id=session_id,
                user_id=current_user.id if current_user.is_authenticated else None,
                responses=responses,
                completed=is_completed,
                completed_at=datetime.utcnow() if is_completed else None
            )
            db.session.add(response)
        
        db.session.commit()
        
        # If completed, trigger the completion logic
        if is_completed:
            print(f"DEBUG: Form completed, triggering completion logic for flow {flow_id}")
            try:
                # Call the completion logic directly
                completion_result = complete_flow_with_storage_logic(flow_id, responses)
                if completion_result.get('success'):
                    return jsonify({
                        'success': True,
                        'message': 'Response saved and item created successfully',
                        'storage_status': completion_result.get('storage_status', 'stored'),
                        'completion': completion_result
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Response saved but item creation failed',
                        'storage_status': completion_result.get('storage_status', 'failed'),
                        'error': completion_result.get('error', 'Unknown error')
                    }), 500
            except Exception as e:
                print(f"DEBUG: Error in completion logic: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Response saved but item creation failed',
                    'storage_status': 'failed',
                    'error': str(e)
                }), 500
        
        return jsonify({
            'success': True,
            'message': 'Response saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def validate_responses(flow_id, responses):
    """Validate question responses"""
    errors = []
    
    # Get all questions for this flow
    questions = ChatbotQuestion.query.filter_by(flow_id=flow_id).order_by(ChatbotQuestion.order_index).all()
    
    for question in questions:
        question_id = str(question.id)
        response_value = responses.get(question_id)
        
        # Check if required question is answered
        is_empty = False
        if question.question_type == 'number_unit':
            # For number_unit, check if it's None or has empty values
            is_empty = (not response_value or 
                       not isinstance(response_value, dict) or 
                       not response_value.get('number') or 
                       not response_value.get('unit'))
        elif question.question_type in ['cascading_dropdown', 'tags', 'images', 'videos', 'audio', 'files_documents', 'location']:
            # For complex types, check if it's None or empty
            is_empty = (not response_value or 
                       (isinstance(response_value, (list, dict)) and len(response_value) == 0))
        else:
            # For simple types, check string emptiness
            is_empty = (not response_value or response_value == '')
        
        if question.is_required and is_empty:
            errors.append({
                'question_id': question_id,
                'question_text': question.question_text,
                'error': 'This field is required'
            })
            continue
        
        # Skip validation if not required and empty
        if is_empty:
            continue
            
        # Type-specific validation
        if question.question_type == 'email':
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, response_value):
                errors.append({
                    'question_id': question_id,
                    'question_text': question.question_text,
                    'error': 'Please enter a valid email address'
                })
        
        elif question.question_type == 'phone':
            import re
            phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
            if not re.match(phone_pattern, response_value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                errors.append({
                    'question_id': question_id,
                    'question_text': question.question_text,
                    'error': 'Please enter a valid phone number'
                })
        
        elif question.question_type == 'url':
            import re
            url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
            if not re.match(url_pattern, response_value):
                errors.append({
                    'question_id': question_id,
                    'question_text': question.question_text,
                    'error': 'Please enter a valid URL'
                })
        
        elif question.question_type == 'number_unit':
            # Validate number_unit response structure
            if not isinstance(response_value, dict):
                errors.append({
                    'question_id': question_id,
                    'question_text': question.question_text,
                    'error': 'Invalid number format'
                })
            else:
                number = response_value.get('number')
                unit = response_value.get('unit')
                
                if not isinstance(number, (int, float)) or number <= 0:
                    errors.append({
                        'question_id': question_id,
                        'question_text': question.question_text,
                        'error': 'Please enter a valid positive number'
                    })
                
                if not unit or not isinstance(unit, str) or not unit.strip():
                    errors.append({
                        'question_id': question_id,
                        'question_text': question.question_text,
                        'error': 'Please select a unit'
                    })

        elif question.question_type == 'location':
            # Validate location structure: object with optional link, lat, lng
            if not isinstance(response_value, dict):
                errors.append({
                    'question_id': question_id,
                    'question_text': question.question_text,
                    'error': 'Invalid location format'
                })
            else:
                lat = response_value.get('lat')
                lng = response_value.get('lng')
                link = response_value.get('link')
                # If required, allow either link or lat/lng to satisfy requirement
                # Type-specific validation: if lat/lng provided, they must be numbers
                if lat is not None and not isinstance(lat, (int, float)):
                    errors.append({
                        'question_id': question_id,
                        'question_text': question.question_text,
                        'error': 'Latitude must be a number'
                    })
                if lng is not None and not isinstance(lng, (int, float)):
                    errors.append({
                        'question_id': question_id,
                        'question_text': question.question_text,
                        'error': 'Longitude must be a number'
                    })
                if link is not None and not isinstance(link, str):
                    errors.append({
                        'question_id': question_id,
                        'question_text': question.question_text,
                        'error': 'Link must be a string URL'
                    })
        
        elif question.question_type == 'number':
            try:
                float(response_value)
            except ValueError:
                errors.append({
                    'question_id': question_id,
                    'question_text': question.question_text,
                    'error': 'Please enter a valid number'
                })
        
        # Check validation rules if they exist
        if question.validation_rules:
            rules = question.validation_rules
            
            if 'min_length' in rules and len(str(response_value)) < rules['min_length']:
                errors.append({
                    'question_id': question_id,
                    'question_text': question.question_text,
                    'error': f'Minimum length is {rules["min_length"]} characters'
                })
            
            if 'max_length' in rules and len(str(response_value)) > rules['max_length']:
                errors.append({
                    'question_id': question_id,
                    'question_text': question.question_text,
                    'error': f'Maximum length is {rules["max_length"]} characters'
                })
    
    return errors

@chatbot_bp.route('/<int:flow_id>/resume')
@login_required
@require_permission('chatbots', 'view')
def resume_flow(flow_id):
    """Resume an incomplete flow"""
    flow = ChatbotFlow.query.filter_by(id=flow_id, is_active=True).first_or_404()
    session_id = session.get('chatbot_session_id')
    
    if not session_id:
        return redirect(url_for('chatbot.start_flow', flow_id=flow_id))
    
    # Get existing response
    existing_response = ChatbotResponse.query.filter_by(
        flow_id=flow_id,
        session_id=session_id,
        completed=False
    ).first()
    
    if not existing_response:
        return redirect(url_for('chatbot.start_flow', flow_id=flow_id))
    
    return render_template('chatbot/flow.html', flow=flow, existing_responses=existing_response.responses)

@chatbot_bp.route('/<int:flow_id>/complete')
@login_required
@require_permission('chatbots', 'view')
def complete_flow(flow_id):
    """Show completion page"""
    flow = ChatbotFlow.query.filter_by(id=flow_id, is_active=True).first_or_404()
    session_id = session.get('chatbot_session_id')
    
    if not session_id:
        return redirect(url_for('chatbot.start_flow', flow_id=flow_id))
    
    # Get completed response
    response = ChatbotResponse.query.filter_by(
        flow_id=flow_id,
        session_id=session_id,
        completed=True
    ).first()
    
    if not response:
        return redirect(url_for('chatbot.start_flow', flow_id=flow_id))
    
    return render_template('chatbot/complete.html', flow=flow, response=response)

@chatbot_bp.route('/<int:flow_id>/upload', methods=['POST'])
# @login_required  # REMOVED: Allow mobile uploads without authentication
# @require_permission('chatbots', 'view')  # REMOVED: Allow mobile uploads without permission
def handle_file_upload(flow_id):
    """Handle file uploads for media upload questions with mobile support and organized structure"""
    print(f"DEBUG: File upload endpoint called for flow {flow_id}")
    flow = ChatbotFlow.query.filter_by(id=flow_id, is_active=True).first_or_404()
    
    try:
        # Import the new file structure utilities
        from utils.file_structure import save_file_organized, validate_file_for_mobile, get_mobile_file_limits
        
        # Get the question ID and category from the request
        question_id = request.form.get('question_id')
        category = request.form.get('category', 'documents')  # Default to documents
        
        if not question_id:
            return jsonify({
                'success': False,
                'error': 'Question ID is required'
            }), 400
        
        # Get the question to validate upload config
        question = ChatbotQuestion.query.filter_by(id=question_id, flow_id=flow_id).first()
        if not question or question.question_type not in ['images', 'videos', 'audio', 'files_documents']:
            return jsonify({
                'success': False,
                'error': 'Invalid question or question type'
            }), 400
        
        # Get media upload config
        media_config = question.media_upload_config or {}
        file_type = media_config.get('file_type', question.question_type)
        
        # Validate file type matches question type
        if file_type != question.question_type:
            return jsonify({
                'success': False,
                'error': f'File type mismatch for question type {question.question_type}'
            }), 400
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file uploaded'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Get allowed extensions from config
        allowed_extensions = media_config.get('extensions', [])
        
        # Validate file with mobile support
        validation = validate_file_for_mobile(file, allowed_extensions)
        if not validation['valid']:
            return jsonify({
                'success': False,
                'error': validation['error']
            }), 400
        
        # Determine file type for organization
        file_type_for_storage = 'item'  # Default for chatbot uploads
        
        # Save file with organized structure
        result = save_file_organized(
            file=file,
            user_id=current_user.id,
            item_id=question_id,  # Use question_id as item_id for now
            file_type=file_type_for_storage,
            context_name=None
        )
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
        
        # Store file information in session for later use
        if 'uploaded_files' not in session:
            session['uploaded_files'] = []
        
        file_info = {
            'question_id': question_id,
            'original_name': secure_filename(file.filename),
            'saved_name': result['file_info']['filename'],
            'relative_path': result['file_info']['relative_path'],
            'file_type': file_type,
            'size': result['file_info']['size'],
            'size_formatted': result['file_info']['size_formatted'],
            'mime_type': file.content_type,
            'is_mobile': result['file_info']['is_mobile'],
            'device_type': result['file_info']['device_type'],
            'path': result['file_info']['relative_path']
        }
        
        session['uploaded_files'].append(file_info)
        session.modified = True
        
        print(f"DEBUG: File stored in session: {file_info}")
        
        # Return success response with file info
        return jsonify({
            'success': True,
            'file_info': {
                'original_name': secure_filename(file.filename),
                'saved_name': result['file_info']['filename'],
                'relative_path': result['file_info']['relative_path'],
                'file_type': file_type,
                'size': result['file_info']['size'],
                'size_formatted': result['file_info']['size_formatted'],
                'mime_type': file.content_type,
                'is_mobile': result['file_info']['is_mobile'],
                'device_type': result['file_info']['device_type'],
                'path': result['file_info']['relative_path']  # Use relative path for database
            }
        })
        
    except Exception as e:
        print(f"DEBUG: Upload error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        }), 500

@chatbot_bp.route('/media-config')
@login_required
@require_permission('chatbots', 'view')
def get_media_config():
    """Get media upload configuration for all categories"""
    try:
        config = get_media_upload_config()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chatbot_bp.route('/categories')
@login_required
@require_permission('chatbots', 'view')
def get_categories():
    """Get all available file categories"""
    try:
        categories = get_all_categories()
        return jsonify({
            'success': True,
            'categories': categories
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def complete_flow_with_storage_logic(flow_id, collected_data):
    """Handle chatbot completion and data storage logic (without Flask route)"""
    try:
        print(f"DEBUG: Chatbot completion logic called for flow {flow_id}")
        # Safely print collected data without Unicode issues
        try:
            print(f"DEBUG: Collected data: {collected_data}")
        except UnicodeEncodeError:
            print("DEBUG: Collected data contains Unicode characters that can't be displayed")
        
        if not current_user.is_authenticated:
            return {'success': False, 'message': 'Authentication required'}
        
        # Get the chatbot flow
        flow = ChatbotFlow.query.get_or_404(flow_id)
        
        # Create completion record
        completion = ChatbotCompletion(
            chatbot_id=flow_id,
            user_id=current_user.id,
            collected_data=collected_data,
            completion_status='completed',
            completed_at=datetime.utcnow()
        )
        
        # Find data storage mapping for this chatbot flow
        mapping = DataStorageMapping.query.filter_by(
            chatbot_id=flow_id,
            is_active=True
        ).first()
        
        if mapping:
            completion.item_type_id = mapping.item_type_id
            
            # Use mapping configuration
            bank_id = mapping.bank_id
            data_mapping = mapping.data_mapping
            
            # Get item type for additional processing
            item_type = ItemType.query.get(mapping.item_type_id)
            
            if bank_id:
                # Process and store the data
                processed_data = process_chatbot_data(collected_data, data_mapping, flow.id)
                
                # Create item in the specified bank
                item = None
                try:
                    item = create_item_from_chatbot_data(
                        processed_data, 
                        item_type, 
                        bank_id,
                        flow.id
                    )
                    
                    if item:
                        completion.processed_data = processed_data
                        completion.storage_status = 'stored'
                        completion.storage_location = f"Item ID: {item.id}"
                        completion.stored_at = datetime.utcnow()
                    else:
                        completion.storage_status = 'failed'
                        completion.error_message = 'Failed to create item (item creation returned None)'
                except Exception as item_error:
                    # Catch specific item creation errors
                    item = None
                    error_msg = str(item_error)
                    completion.storage_status = 'failed'
                    completion.error_message = error_msg if 'Item creation failed' in error_msg else f'Item creation failed: {error_msg}'
                    print(f"DEBUG: Item creation exception caught: {error_msg}")
            else:
                completion.storage_status = 'failed'
                completion.error_message = 'No storage bank configured'
        else:
            completion.storage_status = 'failed'
            completion.error_message = 'No data storage mapping found for this chatbot'
        
        db.session.add(completion)
        db.session.commit()
        
        # Prepare response based on item type configuration
        # Return success: False if storage failed
        success = completion.storage_status == 'stored'
        response_data = {
            'success': success,
            'completion_id': completion.id,
            'storage_status': completion.storage_status
        }
        
        # Add error message if storage failed
        if not success:
            response_data['error'] = completion.error_message or 'Failed to create item'
            response_data['message'] = f'Item creation failed: {response_data["error"]}'
        
        if item_type:
            if item_type.completion_action in ['message', 'both']:
                response_data['message'] = item_type.completion_message
            
            if item_type.completion_action in ['redirect', 'both'] and item_type.redirect_url:
                response_data['redirect_url'] = item_type.redirect_url
        
        return response_data
        
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG: Error in completion logic: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@chatbot_bp.route('/complete/<int:flow_id>', methods=['POST'])
@login_required
@require_permission('chatbots', 'view')
def complete_flow_with_storage(flow_id):
    """Handle chatbot completion and data storage (Flask route)"""
    try:
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        
        # Get the collected data from the request
        collected_data = request.get_json().get('data', {})
        
        # Merge session data with collected data
        if 'uploaded_files' in session and session['uploaded_files']:
            print(f"DEBUG: Found {len(session['uploaded_files'])} uploaded files in session")
            # Add uploaded files to collected data
            collected_data['uploaded_files'] = session['uploaded_files']
            print(f"DEBUG: Merged session data with collected data")
        
        # Call the completion logic
        result = complete_flow_with_storage_logic(flow_id, collected_data)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def process_chatbot_data(collected_data, data_mapping, chatbot_id=None):
    """Process collected data according to mapping rules"""
    processed_data = {}
    
    # First, convert question IDs to field names if chatbot_id is provided
    if chatbot_id:
        question_mapping = get_question_field_mapping(chatbot_id)
        for question_id, field_name in question_mapping.items():
            if str(question_id) in collected_data:
                value = collected_data[str(question_id)]
                
                # Handle special cascading dropdown mapping
                if field_name == 'category_subcategory' and isinstance(value, dict):
                    # Extract category and subcategory from cascading dropdown data
                    processed_data['category'] = value.get('category', '')
                    processed_data['subcategory'] = value.get('subcategory', '')
                else:
                    processed_data[field_name] = value
        
        # Handle questions without field mappings (store with question ID as key)
        for question_id, value in collected_data.items():
            if question_id not in question_mapping and value and str(value).strip():
                # Store unmapped questions with descriptive names
                question_id_int = int(question_id)
                if question_id_int == 436:  # Category question
                    if isinstance(value, dict):
                        processed_data['category'] = value.get('category', '')
                        processed_data['subcategory'] = value.get('subcategory', '')
                elif question_id_int == 439:  # Images question
                    processed_data['images'] = value
                elif question_id_int == 440:  # Price question
                    processed_data['pricing_type'] = value
                else:
                    # Store other questions with question ID
                    processed_data[f'question_{question_id}'] = value
    
    # Then apply any additional data mapping
    if data_mapping:
        for chatbot_field, item_field in data_mapping.items():
            if chatbot_field in collected_data:
                processed_data[item_field] = collected_data[chatbot_field]
    
        # Handle file uploads - extract file information from collected data
        if chatbot_id:
            # Get all questions for this chatbot to find file upload questions
            from models import ChatbotQuestion
            file_questions = ChatbotQuestion.query.filter(
                ChatbotQuestion.flow_id == chatbot_id,
                ChatbotQuestion.question_type.in_(['images', 'videos', 'audio', 'files_documents'])
            ).all()
            
            for question in file_questions:
                question_id_str = str(question.id)
                if question_id_str in collected_data:
                    value = collected_data[question_id_str]
                    if isinstance(value, dict) and 'files' in value:
                        files = value.get('files', [])
                        if files:
                            # Convert file names to paths that match the uploaded files
                            file_paths = []
                            for file_info in files:
                                if isinstance(file_info, dict) and 'relative_path' in file_info:
                                    file_paths.append(file_info['relative_path'])
                                elif isinstance(file_info, dict) and 'saved_name' in file_info:
                                    file_paths.append(file_info['saved_name'])
                            
                            if file_paths:
                                # Store file paths in processed_data
                                if question.question_type == 'images':
                                    processed_data['images'] = file_paths
                                else:
                                    processed_data['files'] = file_paths
    
    # If no mappings were applied, return original data
    if not processed_data and not data_mapping:
        return collected_data
    
    return processed_data

def get_question_field_mapping(chatbot_id):
    """Map question IDs to field names for each chatbot based on database field_mapping"""
    from models import ChatbotQuestion
    
    # Get all questions for this chatbot that have field mappings (both essential and essential_custom)
    questions = ChatbotQuestion.query.filter(
        ChatbotQuestion.flow_id == chatbot_id,
        ChatbotQuestion.question_classification.in_(['essential', 'essential_custom'])
    ).filter(ChatbotQuestion.field_mapping != '').all()
    
    mappings = {}
    for question in questions:
        if question.field_mapping:
            mappings[str(question.id)] = question.field_mapping
    
    return mappings

def get_custom_field_mapping(chatbot_id):
    """Map custom field names to database column names for essential_custom questions"""
    from models import ChatbotQuestion
    
    # Get the question field mapping first to convert question IDs to field names
    question_mapping = get_question_field_mapping(chatbot_id)
    
    # Get all essential_custom questions for this chatbot
    questions = ChatbotQuestion.query.filter_by(
        flow_id=chatbot_id,
        question_classification='essential_custom'
    ).filter(ChatbotQuestion.field_mapping != '').all()
    
    mappings = {}
    for question in questions:
        if question.field_mapping:
            # Get the field name from question_mapping (which converts question ID to field name)
            question_id_str = str(question.id)
            field_name = question_mapping.get(question_id_str, question.field_mapping)
            # For custom fields, the field_mapping contains the column name directly
            # Map field name to column name
            mappings[field_name] = question.field_mapping
    
    return mappings

def create_item_from_chatbot_data(processed_data, item_type, bank_id, chatbot_id=None):
    """Create an item from processed chatbot data using hybrid field mapping"""
    try:
        print(f"DEBUG: Creating item from chatbot data - ItemType: {item_type.name}, Bank: {bank_id}")
        # Safely print processed data without Unicode issues
        try:
            print(f"DEBUG: Processed data: {processed_data}")
        except UnicodeEncodeError:
            print("DEBUG: Processed data contains Unicode characters that can't be displayed")
        
        # Get user's first profile
        if not current_user.is_authenticated:
            print("DEBUG: User not authenticated!")
            return None
            
        user_profile = Profile.query.filter_by(user_id=current_user.id).first()
        if not user_profile:
            print("DEBUG: No user profile found!")
            return None
        
        # Handle subcategory data (might be nested object)
        subcategory = processed_data.get('subcategory', '')
        if isinstance(subcategory, dict):
            subcategory = subcategory.get('subcategory', subcategory.get('category', ''))
        
        # CORRECT: Use ItemType.id for core classification and descriptive category for search enhancement
        # item_type_id = item_type.id  # This will be set when creating the Item
        category = processed_data.get('category', '')  # Descriptive category (Science & Research, Music, etc.)
        
        # If no descriptive category from chatbot, use a default based on item type
        if not category:
            category_defaults = {
                'idea': 'Innovation',
                'product': 'General Product',
                'service': 'Professional Service',
                'need': 'General Need',
                'project': 'Project',
                'event': 'Event',
                'fund': 'Funding'
            }
            category = category_defaults.get(item_type.name, 'General')
        
        # Normalize location value (support object with lat/lng/link)
        location_raw = processed_data.get('location', '')
        if isinstance(location_raw, dict):
            lat = location_raw.get('lat')
            lng = location_raw.get('lng')
            link = location_raw.get('link')
            # Prefer link (URL) if available, as it contains coordinates we can extract
            # If link exists, use it; otherwise use coordinates
            if link:
                location_raw = link  # URL will be parsed to extract coordinates
            elif lat is not None and lng is not None:
                try:
                    location_raw = f"{float(lat)},{float(lng)}"
                except Exception:
                    location_raw = ''
            else:
                location_raw = ''
        
        # Process location: convert raw input (coordinates/URL) to formatted (city, country)
        location_formatted = ''
        if location_raw:
            try:
                # Use geocoding utility to parse and format location
                # This handles URLs (Google Maps, Apple Maps, etc.) and coordinates
                location_data = parse_location(location_raw)
                location_formatted = location_data.get('formatted', location_raw)
                
                # If it's a URL and parsing found coordinates, use the formatted result
                # If parsing didn't work (no coordinates found), keep original URL as formatted
                if location_raw.startswith('http'):
                    # If we got coordinates from URL, use formatted location
                    if location_data.get('coordinates'):
                        location_formatted = location_data.get('formatted', location_raw)
                    else:
                        # URL parsing failed, keep URL but try to extract a readable name
                        # For now, keep URL as formatted (user will see the URL)
                        location_formatted = location_raw
                elif location_formatted == location_raw:
                    # If no change, might be coordinates or plain text - keep as is
                    location_formatted = location_data.get('formatted', location_raw)
            except Exception as e:
                # If geocoding fails, use raw value
                print(f"DEBUG: Location geocoding failed: {e}")
                location_formatted = location_raw if not location_raw.startswith('http') else location_raw
        else:
            location_formatted = ''

        # Handle price conversion safely
        price_value = processed_data.get('price')
        if price_value == '' or price_value is None:
            price_value = None
        else:
            try:
                price_value = float(price_value)
            except (ValueError, TypeError):
                price_value = None

        # Collect uploaded file paths for images_media field with early deduplication
        images_media = []
        # Use a set to track added files (normalized paths) to prevent duplicates immediately
        seen_image_paths = set()
        
        def add_image_safely(image_path):
            """Add image path only if not already seen (normalized for comparison)"""
            if not image_path or not image_path.strip():
                return False
            
            # Normalize path for comparison (handle backslashes and forward slashes)
            normalized = image_path.strip().replace('\\', '/').lower()
            
            # Check if already seen (using normalized path)
            if normalized in seen_image_paths:
                return False
            
            # Check if it's a valid file path (pass original path, function handles normalization)
            if not _is_likely_file_path(image_path.strip()):
                return False
            
            # Add the original path but normalize slashes to forward slashes for consistency
            normalized_path = image_path.strip().replace('\\', '/')
            images_media.append(normalized_path)
            seen_image_paths.add(normalized)
            return True
        
        # First, check processed data for uploaded files (NEW METHOD)
        if 'uploaded_files' in processed_data and processed_data['uploaded_files']:
            for file_info in processed_data['uploaded_files']:
                if isinstance(file_info, dict) and 'relative_path' in file_info:
                    add_image_safely(file_info['relative_path'])
        
        # 1. First, collect from session (most reliable source)
        try:
            from flask import session
            if 'uploaded_files' in session and session['uploaded_files']:
                for file_info in session['uploaded_files']:
                    if isinstance(file_info, dict) and 'relative_path' in file_info:
                        add_image_safely(file_info['relative_path'])
        except Exception as e:
            pass  # Session access may fail in some contexts
        
        # 2. Then, collect from processed_data (fallback)
        # Exclude known non-image fields to prevent tags and other data from being treated as images
        excluded_keys = ['uploaded_files', 'tags', 'title', 'short_description', 'detailed_description', 
                        'category', 'subcategory', 'pricing_type', 'price', 'currency', 'location', 
                        'images']  # Exclude 'images' since we collect from question_26.files directly
        
        for key, value in processed_data.items():
            # Skip excluded keys (tags, text fields, etc.)
            if key in excluded_keys:
                continue
            
            # Skip question_26 if it's already been processed (it contains the same files as 'images')
            # We'll collect from question_26.files which has the full file info
            if key.startswith('question_') and isinstance(value, dict) and 'files' in value:
                for file_info in value['files']:
                    if isinstance(file_info, dict) and 'relative_path' in file_info:
                        add_image_safely(file_info['relative_path'])
            elif isinstance(value, list):
                # Handle list of files - but be more strict
                # Only process if the key suggests it might contain files (not tags!)
                # BUT skip 'images' since we already got them from question_26
                if key in ['photos', 'image', 'photo', 'media', 'files'] and key != 'images':
                    for file_info in value:
                        if isinstance(file_info, dict):
                            filename = file_info.get('relative_path') or file_info.get('saved_name') or file_info.get('path')
                            if filename:
                                add_image_safely(filename)
                        elif isinstance(file_info, str):
                            add_image_safely(file_info)
            elif isinstance(value, str):
                # Skip string values unless they clearly look like file paths
                if value.strip().startswith('uploads'):
                    add_image_safely(value)
        
        # Note: We don't need step 3 anymore since we already processed 'images' key above
        
        # Final cleanup: Normalize paths to forward slashes for consistency
        # (we already deduplicated, just normalize format now)
        final_images = []
        for image_path in images_media:
            if image_path and image_path.strip():
                # Normalize to forward slashes (but keep original format in DB)
                normalized = image_path.strip().replace('\\', '/')
                final_images.append(normalized)
        
        images_media = final_images

        # Create item with core fields
        item = Item(
            profile_id=user_profile.id,
            item_type_id=item_type.id,  # Core classification - THE BIG THING
            title=processed_data.get('title', 'Untitled Item'),
            short_description=processed_data.get('short_description', processed_data.get('title', '')[:100]),
            detailed_description=processed_data.get('detailed_description', processed_data.get('title', '')),
            category=category,  # Search/filter enhancement
            subcategory=subcategory,  # Further classification
            tags=processed_data.get('tags', []),
            images_media=images_media if images_media else None,
            owner_type='me',
            pricing_type=processed_data.get('pricing_type', 'free'),
            price=price_value,
            currency=processed_data.get('currency', 'USD'),
            location_raw=location_raw,  # Store raw input (coordinates/URL)
            location=location_formatted,  # Store formatted location (city, country)
            is_available=True,
            is_verified=False
        )
        
        # HYBRID FIELD MAPPING: Map chatbot data to category-specific fields
        category_field_mapping = get_category_field_mapping(item_type.name)
        
        # Map core chatbot data to category-specific fields
        for chatbot_field, item_field in category_field_mapping.items():
            if chatbot_field in processed_data:
                value = processed_data[chatbot_field]
                if hasattr(item, item_field):
                    setattr(item, item_field, value)
        
        # CUSTOM FIELD MAPPING: Map custom fields to database columns
        if chatbot_id:
            custom_field_mapping = get_custom_field_mapping(chatbot_id)
            
            # Map custom fields directly from processed_data (field names, not question IDs)
            for field_name, item_field in custom_field_mapping.items():
                if field_name in processed_data:
                    value = processed_data[field_name]
                    if hasattr(item, item_field):
                        setattr(item, item_field, value)
        
        # Store any unmapped data in flexible JSON storage
        # These are fields that are NOT displayed on the main item page
        unmapped_data = {}
        # Standard Item fields displayed on item detail page - EXCLUDE these from Additional Information
        standard_displayed_fields = set([
            'title',           # Shown in main title
            'short_description',  # Shown in Short Description section
            'detailed_description',  # Shown in Detailed Description section
            'category',        # Shown in badges
            'subcategory',    # Shown in badges
            'tags',           # Shown in badges
            'pricing_type',   # Implied from price section
            'price',          # Shown in Price section
            'currency',       # Shown in Price section
            'location',       # Shown in Location section
            'location_raw',   # Not displayed but stored
            'images',         # Shown in Images section
            'images_media',   # Shown in Images section
            'photos',         # Same as images
            'image',          # Same as images
            'photo',          # Same as images
            'media',          # Same as images
            'files'           # Same as images
        ])
        
        # Add any fields mapped to Item columns (these are already displayed)
        used_fields = standard_displayed_fields.copy()
        used_fields.update(category_field_mapping.keys())
        if chatbot_id:
            used_fields.update(custom_field_mapping.keys())
        
        # Only store fields that are NOT displayed on the main item page
        for key, value in processed_data.items():
            if key not in used_fields and value is not None:
                unmapped_data[key] = value

        # NOTE: Location object is preserved in original_processed_data for reference,
        # but NOT added to unmapped_data since it's already displayed on the item page
        
        # Always store processed_data in type_data for rich display
        if processed_data:
            import json
            # Create a rich data structure for display
            rich_data = {
                'original_processed_data': processed_data,
                'unmapped_additional_data': unmapped_data,
                'display_fields': {}
            }
            
            # Create display-friendly fields ONLY from unmapped data
            # Exclude location and other standard fields that are already displayed elsewhere
            excluded_from_display = set(['location', 'location_raw'])  # Already shown on item page
            
            # Fetch question texts and types from database if chatbot_id is available
            question_texts = {}
            image_question_ids = set()  # Track image upload questions to exclude them
            if chatbot_id:
                try:
                    questions = ChatbotQuestion.query.filter_by(flow_id=chatbot_id).all()
                    for q in questions:
                        question_texts[f'question_{q.id}'] = q.question_text
                        # Exclude image upload questions (they're only for uploading, not for displaying info)
                        if q.question_type in ['images', 'videos', 'audio', 'files_documents']:
                            image_question_ids.add(f'question_{q.id}')
                except Exception as e:
                    pass  # Could not fetch question texts
            
            for key, value in unmapped_data.items():
                if key not in excluded_from_display:
                    # Skip image/media upload questions - they're only for uploading, not displaying
                    if key in image_question_ids:
                        continue
                    
                    # Additional check: Skip if value is an object with 'files' property (file upload indicator)
                    # This handles cases where chatbot_id might be missing or question type wasn't found
                    if isinstance(value, dict):
                        if 'files' in value and isinstance(value.get('files'), (list, str)):
                            # This is a file upload response, skip it
                            continue
                        # Also check if it looks like a file upload object (has file-related keys)
                        if any(file_key in value for file_key in ['files', 'file_paths', 'uploaded_files', 'media_files']):
                            continue
                    
                    # Check if value has actual content (not None, not empty string, not empty list/dict)
                    has_content = False
                    if value is None:
                        has_content = False
                    elif isinstance(value, str):
                        has_content = bool(value.strip())
                    elif isinstance(value, (list, dict)):
                        has_content = bool(value)  # Non-empty list or dict
                    elif isinstance(value, (int, float, bool)):
                        has_content = True  # Numbers and booleans are valid
                    else:
                        has_content = bool(value)  # Other types
                    
                    if has_content:
                        # Use question text if available, otherwise create human-readable label
                        if key in question_texts:
                            display_key = question_texts[key]
                        else:
                            display_key = key.replace('_', ' ').title()
                        
                        rich_data['display_fields'][display_key] = value
            
            item.type_data = json.dumps(rich_data, ensure_ascii=False, indent=2)
        
        db.session.add(item)
        db.session.commit()
        
        # Safely print item creation success without Unicode issues
        try:
            print(f"DEBUG: Item created successfully - ID: {item.id}, Title: {item.title}, Category: {item.category}")
        except UnicodeEncodeError:
            print(f"DEBUG: Item created successfully - ID: {item.id}, Category: {item.category}")
        
        # Trigger data collection for the new item
        collection_engine.on_data_created('items', item.id)
        
        # Handle organization context if item was created within an organization
        from flask import session
        from models import OrganizationContent, OrganizationMember
        
        if 'organization_id' in session:
            organization_id = session['organization_id']
            
            # Verify user is a member of the organization
            membership = OrganizationMember.query.filter_by(
                organization_id=organization_id,
                user_id=current_user.id,
                status='active'
            ).first()
            
            if membership and membership.role in ['owner', 'admin', 'member']:
                # Create organization content association
                org_content = OrganizationContent(
                    organization_id=organization_id,
                    item_id=item.id,
                    content_type='item',
                    added_by=current_user.id
                )
                db.session.add(org_content)
                
                # Update organization content count
                from models import Organization
                organization = Organization.query.get(organization_id)
                if organization:
                    organization.content_count += 1
                
                db.session.commit()
                
                # Clear organization context from session
                del session['organization_id']
        
        # Clear uploaded files from session after successful item creation
        try:
            from flask import session
            if 'uploaded_files' in session:
                del session['uploaded_files']
                session.modified = True
                print(f"DEBUG: Cleared uploaded files from session")
        except Exception as e:
            print(f"DEBUG: Session cleanup error: {e}")
        
        # Track field usage for analytics
        track_field_usage(item_type.name, category_field_mapping, processed_data)
        
        return item
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error creating item: {error_msg}")
        # Check for common data type mismatch errors
        if 'invalid input syntax' in error_msg.lower() or 'type mismatch' in error_msg.lower():
            print(f"DEBUG: Data type mismatch detected - likely invalid data type for a column")
        db.session.rollback()
        # Re-raise with more context for completion logic
        raise Exception(f"Item creation failed: {error_msg}")

def get_category_field_mapping(item_type_name):
    """Get field mapping for specific item type"""
    field_mappings = {
        'product': {
            'condition': 'condition',
            'quantity': 'quantity',
            'brand': 'brand',
            'model': 'model',
            'creator': 'creator',
            'specifications': 'specifications',
            'warranty': 'warranty',
            'accessories': 'accessories',
            'shipping': 'shipping'
        },
        'service': {
            'duration': 'duration',
            'experience_level': 'experience_level',
            'service_type': 'service_type',
            'availability': 'availability',
            'availability_schedule': 'availability_schedule',
            'service_area': 'service_area',
            'certifications': 'certifications',
            'portfolio': 'portfolio'
        },
        'event': {
            'event_date': 'event_date',
            'venue': 'venue',
            'event_location': 'event_location',
            'capacity': 'capacity',
            'max_participants': 'max_participants',
            'event_type': 'event_type',
            'event_type_category': 'event_type_category',
            'registration_required': 'registration_required',
            'registration_fee': 'registration_fee'
        },
        'project': {
            'timeline': 'timeline',
            'budget': 'price',  # Map to price field
            'project_status': 'project_status',
            'team_size': 'team_size',
            'project_type': 'project_type',
            'technologies_used': 'technologies_used',
            'deadline': 'deadline'
        },
        'fund': {
            'amount': 'price',  # Map to price field
            'funding_goal': 'funding_goal',
            'funding_type': 'funding_type',
            'funding_type_category': 'funding_type_category',
            'investment_terms': 'investment_terms',
            'roi_expectation': 'roi_expectation',
            'funding_amount_min': 'funding_amount_min',
            'funding_amount_max': 'funding_amount_max'
        },
        'experience': {
            'experience_type': 'experience_type',
            'duration': 'duration',
            'group_size': 'group_size',
            'location_type': 'location_type',
            'difficulty_level': 'difficulty_level',
            'equipment_needed': 'equipment_needed',
            'lessons_learned': 'lessons_learned',
            'mistakes_avoided': 'mistakes_avoided',
            'success_factors': 'success_factors'
        },
        'opportunity': {
            'opportunity_type': 'opportunity_type',
            'urgency_level': 'urgency_level',
            'deadline': 'deadline',
            'requirements': 'requirements',
            'compensation_type': 'compensation_type',
            'compensation_amount': 'compensation_amount',
            'remote_work': 'remote_work',
            'part_time': 'part_time'
        },
        'information': {
            'information_type': 'information_type',
            'source': 'source',
            'reliability_score': 'reliability_score',
            'format': 'format',
            'language': 'language',
            'accessibility': 'accessibility',
            'update_frequency': 'update_frequency',
            'last_updated': 'last_updated'
        },
        'observation': {
            'observation_type': 'observation_type',
            'context': 'context',
            'significance': 'significance',
            'potential_impact': 'potential_impact',
            'observation_date': 'observation_date',
            'data_source': 'data_source',
            'confidence_level': 'confidence_level',
            'actionable_insights': 'actionable_insights'
        },
        'hidden_gem': {
            'gem_type': 'gem_type',
            'recognition_level': 'recognition_level',
            'unique_value': 'unique_value',
            'promotion_potential': 'promotion_potential',
            'discovery_context': 'discovery_context',
            'rarity_level': 'rarity_level',
            'value_type': 'value_type',
            'promotion_strategy': 'promotion_strategy'
        },
        'auction': {
            'start_price': 'start_price',
            'price': 'price',  # Current price
            'end_date': 'end_date',
            'bid_increment': 'bid_increment',
            'reserve_price': 'reserve_price'
        },
        'need': {
            'need_type': 'need_type',
            'urgency_level': 'urgency_level',
            'budget_range': 'budget_range',
            'timeline': 'timeline',
            'requirements': 'requirements'
        },
        'idea': {
            'idea_type': 'idea_type',
            'innovation_level': 'innovation_level',
            'market_potential': 'market_potential',
            'development_stage': 'development_stage',
            'target_audience': 'target_audience',
            'implementation_timeline': 'implementation_timeline',
            'resources_needed': 'resources_needed',
            'challenges': 'challenges',
            'benefits': 'benefits'
        }
    }
    
    return field_mappings.get(item_type_name, {})

def track_field_usage(item_type_name, field_mapping, processed_data):
    """Track which fields are being used for analytics"""
    try:
        from models import SearchAnalytics
        
        # Track field usage
        for chatbot_field, item_field in field_mapping.items():
            if chatbot_field in processed_data and processed_data[chatbot_field] is not None:
                # Check if this field usage already exists
                existing = SearchAnalytics.query.filter_by(
                    item_type=item_type_name,
                    filter_field=item_field,
                    filter_value=str(processed_data[chatbot_field])
                ).first()
                
                if existing:
                    existing.search_count += 1
                    existing.last_searched = datetime.utcnow()
                else:
                    analytics = SearchAnalytics(
                        item_type=item_type_name,
                        filter_field=item_field,
                        filter_value=str(processed_data[chatbot_field]),
                        search_count=1,
                        user_id=current_user.id if current_user.is_authenticated else None
                    )
                    db.session.add(analytics)
        
        db.session.commit()
        
    except Exception as e:
        print(f"Error tracking field usage: {str(e)}")
        db.session.rollback()
