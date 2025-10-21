from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, URL

class ProfileForm(FlaskForm):
    name = StringField('Profile Name', validators=[DataRequired(), Length(min=2, max=100)])
    profile_type = SelectField('Profile Type', 
                              choices=[],  # Will be populated dynamically
                              validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=50)])
    location = StringField('Location', validators=[Optional(), Length(max=100)])
    website = StringField('Website', validators=[Optional(), URL(), Length(max=200)])
    photo = FileField('Profile Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Only image files are allowed!')])
    is_public = BooleanField('Make Profile Public', default=True, description='Public profiles appear in searches and can be discovered by others')
    submit = SubmitField('Create Profile')
    
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        # Populate profile type choices from database
        self.populate_profile_types()
    
    def populate_profile_types(self):
        """Populate profile type choices from ProfileType model"""
        try:
            from models import ProfileType
            profile_types = ProfileType.query.filter_by(is_active=True).order_by(ProfileType.order_index, ProfileType.display_name).all()
            self.profile_type.choices = [(str(pt.id), pt.display_name) for pt in profile_types]
            
            # Fallback to static choices if no profile types in database
            if not self.profile_type.choices:
                self.profile_type.choices = [
                    ('person', 'Person'), 
                    ('professional', 'Professional/Expert'), 
                    ('freelancer', 'Freelancer'), 
                    ('entrepreneur', 'Entrepreneur/Founder'), 
                    ('investor', 'Investor'), 
                    ('volunteer', 'Volunteer/Activist')
                ]
        except Exception as e:
            # Fallback to static choices if database error
            print(f"Warning: Could not load profile types from database: {e}")
            self.profile_type.choices = [
                ('person', 'Person'), 
                ('professional', 'Professional/Expert'), 
                ('freelancer', 'Freelancer'), 
                ('entrepreneur', 'Entrepreneur/Founder'), 
                ('investor', 'Investor'), 
                ('volunteer', 'Volunteer/Activist')
            ]
