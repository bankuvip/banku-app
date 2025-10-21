from flask import Blueprint, render_template

simulations_bp = Blueprint('simulations', __name__, url_prefix='/simulations')

@simulations_bp.route('/question-based')
def question_based():
    """Question-based form simulation"""
    return render_template('simulations/question_based_form.html')

@simulations_bp.route('/ai-driven')
def ai_driven():
    """AI-driven chat simulation"""
    return render_template('simulations/ai_driven_chat.html')

@simulations_bp.route('/')
def index():
    """Simulations index page"""
    return render_template('simulations/index.html')





