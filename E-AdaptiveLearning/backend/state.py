from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class InteractionType(str, Enum):
    """Enum for different types of user interactions"""
    QUESTION = "question"
    QUIZ_ANSWER = "quiz_answer"
    CONTENT_REQUEST = "content_request"
    STUDY_PLAN_REQUEST = "study_plan_request"
    PROGRESS_REQUEST = "progress_request"
    HINT_REQUEST = "hint_request"
    FEEDBACK = "feedback"

class LearningMode(str, Enum):
    """Enum for different learning modes"""
    EXPLORATION = "exploration"
    GUIDED_LEARNING = "guided_learning"
    QUIZ = "quiz"
    REVIEW = "review"
    CHALLENGE = "challenge"

class DifficultyLevel(int, Enum):
    """Enum for difficulty levels"""
    BEGINNER = 1
    EASY = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5

class LearningStyle(str, Enum):
    """Enum for learning styles"""
    VISUAL = "visual"
    AUDITORY = "auditory"
    READING_WRITING = "reading_writing"
    KINESTHETIC = "kinesthetic"
    BALANCED = "balanced"

class UserMessage(BaseModel):
    """Model for user messages"""
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SystemMessage(BaseModel):
    """Model for system messages"""
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    message_type: str = "text"  # text, quiz, learning_content, progress_report, etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)

class QuizQuestion(BaseModel):
    """Model for quiz questions"""
    question_text: str
    options: List[Dict[str, str]]  # List of {letter: A, text: "Option text"}
    correct_answer: str  # The letter of the correct option
    explanation: str
    concepts: List[str] = Field(default_factory=list)
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE

class Quiz(BaseModel):
    """Model for quizzes"""
    quiz_id: str
    topic: str
    subtopic: str
    questions: List[QuizQuestion]
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class QuizResult(BaseModel):
    """Model for quiz results"""
    quiz_id: str
    student_id: str
    score: float
    answers: List[Dict[str, Any]]  # List of answers with correctness
    analysis: str
    timestamp: datetime = Field(default_factory=datetime.now)

class LearningSession(BaseModel):
    """Model for learning sessions"""
    session_id: str
    student_id: str
    topic: str
    subtopic: str
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    learning_mode: LearningMode = LearningMode.GUIDED_LEARNING
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: int = 0  # Duration in minutes
    content_summary: str = ""

class UserState(BaseModel):
    """Model for tracking user state during a session"""
    student_id: str
    current_topic: Optional[str] = None
    current_subtopic: Optional[str] = None
    current_difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE
    current_learning_mode: LearningMode = LearningMode.EXPLORATION
    current_quiz_id: Optional[str] = None
    current_session_id: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)  # Additional context for agents

class StudentProfile(BaseModel):
    """Model for student profiles"""
    student_id: str
    name: str
    email: Optional[str] = None
    learning_style: LearningStyle = LearningStyle.BALANCED
    difficulty_preferences: Dict[str, DifficultyLevel] = Field(default_factory=dict)
    interests: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ProgressReport(BaseModel):
    """Model for progress reports"""
    report_id: str
    student_id: str
    topic: str
    time_period: int  # in days
    average_score: float
    analysis: str
    created_at: datetime = Field(default_factory=datetime.now)

class StudyPlan(BaseModel):
    """Model for study plans"""
    plan_id: str
    student_id: str
    topic: str
    goal: str
    timeline: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)

class LearningResource(BaseModel):
    """Model for learning resources"""
    title: str
    resource_type: str  # article, video, interactive, book, practice
    description: str
    url: Optional[str] = None
    relevance_score: float = 1.0
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE

class StateManager:
    """
    Manages the application state during a session.
    """
    
    def __init__(self, student_id: str):
        """
        Initialize the state manager.
        
        Args:
            student_id (str): The ID of the current student
        """
        self.user_state = UserState(student_id=student_id)
        
    def start_learning_session(self, topic: str, subtopic: str, 
                             difficulty_level: DifficultyLevel, 
                             learning_mode: LearningMode,
                             session_id: str) -> None:
        """
        Start a new learning session.
        
        Args:
            topic (str): The topic of the session
            subtopic (str): The subtopic of the session
            difficulty_level (DifficultyLevel): The difficulty level
            learning_mode (LearningMode): The learning mode
            session_id (str): The ID of the new session
        """
        self.user_state.current_topic = topic
        self.user_state.current_subtopic = subtopic
        self.user_state.current_difficulty_level = difficulty_level
        self.user_state.current_learning_mode = learning_mode
        self.user_state.current_session_id = session_id
        
    def start_quiz(self, quiz_id: str) -> None:
        """
        Start a quiz.
        
        Args:
            quiz_id (str): The ID of the quiz
        """
        self.user_state.current_quiz_id = quiz_id
        self.user_state.current_learning_mode = LearningMode.QUIZ
        
    def end_quiz(self) -> None:
        """End the current quiz."""
        self.user_state.current_quiz_id = None
        self.user_state.current_learning_mode = LearningMode.REVIEW
        
    def add_message(self, message: Dict[str, Any]) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            message (Dict): The message to add
        """
        self.user_state.conversation_history.append(message)
        
    def add_context(self, key: str, value: Any) -> None:
        """
        Add context information for agents.
        
        Args:
            key (str): The context key
            value (Any): The context value
        """
        self.user_state.context[key] = value
        
    def update_difficulty(self, difficulty_level: DifficultyLevel) -> None:
        """
        Update the current difficulty level.
        
        Args:
            difficulty_level (DifficultyLevel): The new difficulty level
        """
        self.user_state.current_difficulty_level = difficulty_level
        
    def change_learning_mode(self, mode: LearningMode) -> None:
        """
        Change the current learning mode.
        
        Args:
            mode (LearningMode): The new learning mode
        """
        self.user_state.current_learning_mode = mode
        
    def change_topic(self, topic: str, subtopic: Optional[str] = None) -> None:
        """
        Change the current topic and optionally subtopic.
        
        Args:
            topic (str): The new topic
            subtopic (str, optional): The new subtopic
        """
        self.user_state.current_topic = topic
        if subtopic:
            self.user_state.current_subtopic = subtopic
        
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current state.
        
        Returns:
            Dict: Summary of the current state
        """
        return {
            "student_id": self.user_state.student_id,
            "current_topic": self.user_state.current_topic,
            "current_subtopic": self.user_state.current_subtopic,
            "difficulty_level": self.user_state.current_difficulty_level.value,
            "learning_mode": self.user_state.current_learning_mode.value,
            "in_quiz": self.user_state.current_quiz_id is not None,
            "conversation_length": len(self.user_state.conversation_history)
        }
        
    def clear_session(self) -> None:
        """Clear the current session data but keep student ID."""
        student_id = self.user_state.student_id
        self.user_state = UserState(student_id=student_id)