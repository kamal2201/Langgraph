"""
E-AdaptiveLearning Agents

This package contains the AI agents that power the E-AdaptiveLearning system:
- AITutorAgent: Answers student questions and provides explanations
- LearningGuideAgent: Generates personalized learning content and study plans
- QuizMasterAgent: Creates adaptive quizzes and evaluates student responses
- ProgressTrackerAgent: Monitors student progress and provides insights
"""

from .ai_tutor import AITutorAgent
from .learning_guide import LearningGuideAgent
from .quiz_master import QuizMasterAgent
from .progress_tracker import ProgressTrackerAgent

__all__ = [
    'AITutorAgent',
    'LearningGuideAgent',
    'QuizMasterAgent',
    'ProgressTrackerAgent'
]