import os
import json
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from datetime import datetime, timedelta

from database.db_handler import DatabaseHandler
from database.connection import get_db_connection
from state import StateManager, LearningMode, DifficultyLevel
from langgraph_workflow import get_learning_workflow
from agents.ai_tutor import AITutorAgent
from agents.learning_guide import LearningGuideAgent
from agents.quiz_master import QuizMasterAgent
from agents.progress_tracker import ProgressTrackerAgent

# Initialize Flask app
app = Flask(__name__, 
            static_folder="../frontend/static", 
            template_folder="../frontend/templates")
CORS(app)

# Set up session configuration
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# Initialize database connection
db = DatabaseHandler()

# Initialize the learning workflow
learning_workflow = get_learning_workflow()

# Dictionary to store active state managers
# In a production environment, you would use a database or Redis for this
active_sessions = {}

@app.route('/')
def index():
    """Render the main chatbot interface"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Render the progress dashboard"""
    return render_template('dashboard.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/session', methods=['POST'])
def create_session():
    """Create a new learning session for a student"""
    data = request.json
    student_id = data.get('student_id')
    
    if not student_id:
        return jsonify({"error": "Student ID is required"}), 400
    
    # Check if student exists, create if not
    student = db.get_student_profile(student_id)
    if not student:
        # Create a basic profile for new students
        db.create_student_profile(student_id, {
            "name": data.get('name', f"Student {student_id}"),
            "learning_style": "balanced",
            "difficulty_preferences": {},
            "interests": []
        })
    
    # Create a new state manager for this session
    session_id = f"session_{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    active_sessions[session_id] = StateManager(student_id)
    
    # Store session ID in Flask session
    session['session_id'] = session_id
    session['student_id'] = student_id
    
    # Log this session start
    topic = data.get('topic')
    subtopic = data.get('subtopic')
    if topic:
        # Create a learning session in the database
        log_id = db.log_learning_session(
            student_id=student_id,
            topic=topic,
            subtopic=subtopic or "general",
            difficulty_level=data.get('difficulty_level', 3),
            content_summary="Session started"
        )
        
        # Update state manager with the topic and session ID
        state_manager = active_sessions[session_id]
        state_manager.start_learning_session(
            topic=topic,
            subtopic=subtopic or "general",
            difficulty_level=DifficultyLevel(data.get('difficulty_level', 3)),
            learning_mode=LearningMode(data.get('learning_mode', 'exploration')),
            session_id=log_id
        )
    
    return jsonify({
        "session_id": session_id,
        "student_id": student_id,
        "message": "Session created successfully"
    })

@app.route('/api/message', methods=['POST'])
def process_message():
    """Process a user message and return the AI response"""
    data = request.json
    message = data.get('message')
    session_id = data.get('session_id') or session.get('session_id')
    student_id = data.get('student_id') or session.get('student_id')
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    if not student_id:
        return jsonify({"error": "Student ID is required"}), 400
    
    # Get state manager for this session
    state_manager = active_sessions.get(session_id)
    if not state_manager:
        # Create a new state manager if none exists
        state_manager = StateManager(student_id)
        active_sessions[session_id] = state_manager
    
    # Process the message through the workflow
    result = learning_workflow.process(
        student_id=student_id,
        message=message,
        state_manager=state_manager
    )
    
    # Format the response
    return jsonify({
        "response": result["response"],
        "state": result["state"]
    })

@app.route('/api/quiz/generate', methods=['POST'])
def generate_quiz():
    """Generate a quiz for a student"""
    data = request.json
    student_id = data.get('student_id') or session.get('student_id')
    topic = data.get('topic')
    subtopic = data.get('subtopic')
    question_count = data.get('question_count', 5)
    
    if not student_id:
        return jsonify({"error": "Student ID is required"}), 400
    
    if not topic:
        return jsonify({"error": "Topic is required"}), 400
    
    # Initialize the Quiz Master agent
    quiz_master = QuizMasterAgent()
    
    # Generate quiz
    quiz_result = quiz_master.generate_quiz(
        student_id=student_id,
        topic=topic,
        subtopic=subtopic or "general",
        question_count=question_count
    )
    
    # Update state manager if session exists
    session_id = data.get('session_id') or session.get('session_id')
    if session_id and session_id in active_sessions:
        state_manager = active_sessions[session_id]
        state_manager.start_quiz(quiz_result["quiz_id"])
    
    return jsonify({
        "quiz_id": quiz_result["quiz_id"],
        "content": quiz_result["content"]
    })

@app.route('/api/quiz/evaluate', methods=['POST'])
def evaluate_quiz_answer():
    """Evaluate a student's quiz answer"""
    data = request.json
    student_id = data.get('student_id') or session.get('student_id')
    quiz_id = data.get('quiz_id')
    question_index = data.get('question_index')
    answer = data.get('answer')
    
    if not all([student_id, quiz_id, question_index is not None, answer]):
        return jsonify({"error": "student_id, quiz_id, question_index, and answer are required"}), 400
    
    # Initialize the Quiz Master agent
    quiz_master = QuizMasterAgent()
    
    # Evaluate answer
    evaluation = quiz_master.evaluate_answer(
        student_id=student_id,
        quiz_id=quiz_id,
        question_index=question_index,
        student_answer=answer
    )
    
    return jsonify(evaluation)

@app.route('/api/quiz/result', methods=['GET'])
def get_quiz_result():
    """Get results for a completed quiz"""
    student_id = request.args.get('student_id') or session.get('student_id')
    quiz_id = request.args.get('quiz_id')
    
    if not all([student_id, quiz_id]):
        return jsonify({"error": "student_id and quiz_id are required"}), 400
    
    # Initialize the Quiz Master agent
    quiz_master = QuizMasterAgent()
    
    # Get quiz results
    results = quiz_master.analyze_quiz_results(
        student_id=student_id,
        quiz_id=quiz_id
    )
    
    return jsonify(results)

@app.route('/api/progress', methods=['GET'])
def get_progress():
    """Get a student's learning progress"""
    student_id = request.args.get('student_id') or session.get('student_id')
    topic = request.args.get('topic')
    days = int(request.args.get('days', 30))
    
    if not student_id:
        return jsonify({"error": "Student ID is required"}), 400
    
    # Initialize the Progress Tracker agent
    progress_tracker = ProgressTrackerAgent()
    
    # Get progress summary
    progress_summary = progress_tracker.generate_progress_summary(
        student_id=student_id,
        topic=topic,
        days=days
    )
    
    return jsonify(progress_summary)

@app.route('/api/content', methods=['GET'])
def get_learning_content():
    """Get learning content for a topic"""
    student_id = request.args.get('student_id') or session.get('student_id')
    topic = request.args.get('topic')
    subtopic = request.args.get('subtopic')
    
    if not all([student_id, topic]):
        return jsonify({"error": "Student ID and topic are required"}), 400
    
    # Initialize the Learning Guide agent
    learning_guide = LearningGuideAgent()
    
    # Generate learning content
    content = learning_guide.generate_learning_content(
        student_id=student_id,
        topic=topic,
        subtopic=subtopic or "general"
    )
    
    return jsonify({
        "content": content,
        "topic": topic,
        "subtopic": subtopic or "general"
    })

@app.route('/api/study-plan', methods=['POST'])
def create_study_plan():
    """Create a study plan for a student"""
    data = request.json
    student_id = data.get('student_id') or session.get('student_id')
    topic = data.get('topic')
    goal = data.get('goal')
    timeline = data.get('timeline')
    
    if not all([student_id, topic, goal, timeline]):
        return jsonify({"error": "Student ID, topic, goal, and timeline are required"}), 400
    
    # Initialize the Learning Guide agent
    learning_guide = LearningGuideAgent()
    
    # Create study plan
    study_plan = learning_guide.create_study_plan(
        student_id=student_id,
        topic=topic,
        goal=goal,
        timeline=timeline
    )
    
    return jsonify({
        "study_plan": study_plan,
        "topic": topic
    })

@app.route('/api/resources', methods=['GET'])
def get_resources():
    """Get recommended learning resources"""
    student_id = request.args.get('student_id') or session.get('student_id')
    topic = request.args.get('topic')
    subtopic = request.args.get('subtopic')
    
    if not all([student_id, topic]):
        return jsonify({"error": "Student ID and topic are required"}), 400
    
    # Initialize the Learning Guide agent
    learning_guide = LearningGuideAgent()
    
    # Get resource recommendations
    resources = learning_guide.recommend_resources(
        student_id=student_id,
        topic=topic,
        subtopic=subtopic or "general"
    )
    
    return jsonify({
        "resources": resources,
        "topic": topic,
        "subtopic": subtopic or "general"
    })

@app.route('/api/learning-patterns', methods=['GET'])
def get_learning_patterns():
    """Get learning pattern analysis for a student"""
    student_id = request.args.get('student_id') or session.get('student_id')
    topic = request.args.get('topic')
    
    if not student_id:
        return jsonify({"error": "Student ID is required"}), 400
    
    # Initialize the Progress Tracker agent
    progress_tracker = ProgressTrackerAgent()
    
    # Get learning pattern analysis
    patterns = progress_tracker.identify_learning_pattern(
        student_id=student_id,
        topic=topic
    )
    
    return jsonify(patterns)

@app.route('/api/difficulty-recommendation', methods=['GET'])
def get_difficulty_recommendation():
    """Get a recommendation for difficulty level adjustment"""
    student_id = request.args.get('student_id') or session.get('student_id')
    topic = request.args.get('topic')
    
    if not all([student_id, topic]):
        return jsonify({"error": "Student ID and topic are required"}), 400
    
    # Initialize the Progress Tracker agent
    progress_tracker = ProgressTrackerAgent()
    
    # Get difficulty adjustment recommendation
    recommendation = progress_tracker.recommend_difficulty_adjustment(
        student_id=student_id,
        topic=topic
    )
    
    return jsonify(recommendation)

@app.route('/api/hint', methods=['GET'])
def get_hint():
    """Get a hint for a quiz question"""
    student_id = request.args.get('student_id') or session.get('student_id')
    question_id = request.args.get('question_id')
    topic = request.args.get('topic')
    
    if not all([student_id, question_id, topic]):
        return jsonify({"error": "Student ID, question ID, and topic are required"}), 400
    
    # Initialize the AI Tutor agent
    ai_tutor = AITutorAgent()
    
    # Get hint
    hint = ai_tutor.provide_hint(
        student_id=student_id,
        question_id=question_id,
        topic=topic
    )
    
    return jsonify({"hint": hint})

@app.route('/api/misconception', methods=['POST'])
def explain_misconception():
    """Explain a misconception in a student's answer"""
    data = request.json
    student_id = data.get('student_id') or session.get('student_id')
    topic = data.get('topic')
    wrong_answer = data.get('wrong_answer')
    correct_answer = data.get('correct_answer')
    
    if not all([student_id, topic, wrong_answer, correct_answer]):
        return jsonify({"error": "Student ID, topic, wrong answer, and correct answer are required"}), 400
    
    # Initialize the AI Tutor agent
    ai_tutor = AITutorAgent()
    
    # Get explanation of misconception
    explanation = ai_tutor.explain_misconception(
        student_id=student_id,
        topic=topic,
        wrong_answer=wrong_answer,
        correct_answer=correct_answer
    )
    
    return jsonify({"explanation": explanation})

@app.route('/api/session/end', methods=['POST'])
def end_session():
    """End the current learning session"""
    data = request.json
    session_id = data.get('session_id') or session.get('session_id')
    student_id = data.get('student_id') or session.get('student_id')
    
    if not session_id:
        return jsonify({"error": "Session ID is required"}), 400
    
    # Clean up state manager
    if session_id in active_sessions:
        # Get duration from request or calculate it
        duration = data.get('duration', 0)
        
        # Get the learning session ID from state manager
        state_manager = active_sessions[session_id]
        learning_session_id = state_manager.user_state.current_session_id
        
        # Update the session in the database if it exists
        if learning_session_id:
            db.update_learning_session(
                log_id=learning_session_id,
                duration=duration
            )
        
        # Remove the state manager
        del active_sessions[session_id]
    
    # Clear the Flask session
    session.pop('session_id', None)
    
    return jsonify({"message": "Session ended successfully"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get("FLASK_DEBUG", "False") == "True")