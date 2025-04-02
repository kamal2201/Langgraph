import os
from typing import Dict, Any, List, Literal, TypedDict, Optional, Tuple, Union, Annotated
from langchain.prompts import PromptTemplate
from langgraph.graph import END, StateGraph
from database.db_handler import DatabaseHandler
from database.connection import get_db_connection
from agents.ai_tutor import AITutorAgent
from agents.learning_guide import LearningGuideAgent
from agents.quiz_master import QuizMasterAgent
from agents.progress_tracker import ProgressTrackerAgent
from state import StateManager, UserState, LearningMode, InteractionType

# Type definitions for the state
class LearningState(TypedDict):
    student_id: str
    current_topic: Optional[str]
    current_subtopic: Optional[str]
    current_difficulty_level: int
    current_learning_mode: str
    current_quiz_id: Optional[str]
    current_session_id: Optional[str]
    conversation_history: List[Dict[str, Any]]
    user_message: str
    system_message: str
    context: Dict[str, Any]
    action: Optional[str]

class LearningWorkflow:
    """
    Orchestrates the adaptive learning workflow using LangGraph.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the learning workflow.
        
        Args:
            api_key (str): Google API key
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.db = DatabaseHandler()
        
        # Initialize agents
        self.ai_tutor = AITutorAgent(api_key=self.api_key)
        self.learning_guide = LearningGuideAgent(api_key=self.api_key)
        self.quiz_master = QuizMasterAgent(api_key=self.api_key)
        self.progress_tracker = ProgressTrackerAgent(api_key=self.api_key)
        
        # Build the workflow graph
        self.workflow = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow.
        
        Returns:
            StateGraph: The workflow graph
        """
        # Define the graph
        builder = StateGraph(LearningState)
        
        # Add nodes
        builder.add_node("classify_input", self._classify_user_input)
        builder.add_node("handle_question", self._handle_question)
        builder.add_node("handle_quiz_request", self._handle_quiz_request)
        builder.add_node("handle_quiz_answer", self._handle_quiz_answer)
        builder.add_node("handle_content_request", self._handle_content_request)
        builder.add_node("handle_progress_request", self._handle_progress_request)
        builder.add_node("handle_study_plan_request", self._handle_study_plan_request)
        builder.add_node("generate_response", self._generate_response)
        
        # Define edges
        builder.add_edge("classify_input", self._route_by_interaction_type)
        builder.add_edge("handle_question", "generate_response")
        builder.add_edge("handle_quiz_request", "generate_response")
        builder.add_edge("handle_quiz_answer", "generate_response")
        builder.add_edge("handle_content_request", "generate_response")
        builder.add_edge("handle_progress_request", "generate_response")
        builder.add_edge("handle_study_plan_request", "generate_response")
        builder.add_edge("generate_response", END)
        
        # Set the entry point
        builder.set_entry_point("classify_input")
        
        return builder.compile()
    
    def _classify_user_input(self, state: LearningState) -> LearningState:
        """
        Classify the user's input to determine the appropriate handling path.
        
        Args:
            state (LearningState): Current state
            
        Returns:
            LearningState: Updated state with classification
        """
        user_message = state["user_message"]
        current_mode = state["current_learning_mode"]
        current_quiz_id = state["current_quiz_id"]
        
        # Logic to classify the user input
        action = None
        
        # If in quiz mode and not a command, treat as quiz answer
        if current_quiz_id and current_mode == LearningMode.QUIZ.value:
            if not user_message.startswith("/"):
                action = "quiz_answer"
        # Detect quiz requests
        elif "quiz" in user_message.lower() or "test me" in user_message.lower():
            action = "quiz_request"
        # Detect progress requests
        elif "progress" in user_message.lower() or "how am I doing" in user_message.lower():
            action = "progress_request"
        # Detect study plan requests
        elif "study plan" in user_message.lower() or "learning plan" in user_message.lower():
            action = "study_plan_request"
        # Detect content requests
        elif "explain" in user_message.lower() or "teach me" in user_message.lower() or "learn about" in user_message.lower():
            action = "content_request"
        # Default to question handling
        else:
            action = "question"
        
        # Update state
        state["action"] = action
        return state
    
    def _route_by_interaction_type(self, state: LearningState) -> Literal["handle_question", "handle_quiz_request", "handle_quiz_answer", "handle_content_request", "handle_progress_request", "handle_study_plan_request"]:
        """
        Route to the appropriate handler based on interaction type.
        
        Args:
            state (LearningState): Current state
            
        Returns:
            str: Next node name
        """
        action = state["action"]
        
        if action == "quiz_answer":
            return "handle_quiz_answer"
        elif action == "quiz_request":
            return "handle_quiz_request"
        elif action == "progress_request":
            return "handle_progress_request"
        elif action == "study_plan_request":
            return "handle_study_plan_request"
        elif action == "content_request":
            return "handle_content_request"
        else:
            return "handle_question"
    
    def _handle_question(self, state: LearningState) -> LearningState:
        """
        Handle a student question using the AI Tutor.
        
        Args:
            state (LearningState): Current state
            
        Returns:
            LearningState: Updated state with the answer
        """
        student_id = state["student_id"]
        user_message = state["user_message"]
        current_topic = state["current_topic"] or "general"
        
        # Get answer from AI Tutor
        answer = self.ai_tutor.answer_question(
            student_id=student_id,
            question=user_message,
            topic=current_topic
        )
        
        # Update state
        state["system_message"] = answer
        return state
    
    def _handle_quiz_request(self, state: LearningState) -> LearningState:
        """
        Handle a quiz request using the Quiz Master.
        
        Args:
            state (LearningState): Current state
            
        Returns:
            LearningState: Updated state with the quiz
        """
        student_id = state["student_id"]
        user_message = state["user_message"]
        current_topic = state["current_topic"]
        current_subtopic = state["current_subtopic"]
        
        # Extract topic and subtopic from message if possible
        message_lower = user_message.lower()
        extracted_topic = current_topic
        extracted_subtopic = current_subtopic
        
        # Simple extraction logic - in a real system, use NLP or more sophisticated parsing
        if "on" in message_lower and not current_topic:
            parts = message_lower.split("on")[1].strip().split()
            if len(parts) >= 1:
                extracted_topic = parts[0].strip()
            if len(parts) >= 2:
                extracted_subtopic = parts[1].strip()
        
        # If topic is still not defined, use a default
        if not extracted_topic:
            extracted_topic = "general"
            extracted_subtopic = "basics"
        
        # Generate the quiz
        quiz_result = self.quiz_master.generate_quiz(
            student_id=student_id,
            topic=extracted_topic,
            subtopic=extracted_subtopic or "general"
        )
        
        # Update state
        state["current_topic"] = extracted_topic
        state["current_subtopic"] = extracted_subtopic
        state["current_quiz_id"] = quiz_result["quiz_id"]
        state["current_learning_mode"] = LearningMode.QUIZ.value
        state["system_message"] = f"Here's a quiz on {extracted_topic}"
        state["context"]["quiz_content"] = quiz_result["content"]
        
        return state
    
    def _handle_quiz_answer(self, state: LearningState) -> LearningState:
        """
        Handle a quiz answer using the Quiz Master.
        
        Args:
            state (LearningState): Current state
            
        Returns:
            LearningState: Updated state with the answer evaluation
        """
        student_id = state["student_id"]
        user_message = state["user_message"]
        quiz_id = state["current_quiz_id"]
        
        # Determine the question index from the context
        # In a real implementation, you would track this properly
        question_index = state["context"].get("current_question_index", 0)
        
        # Evaluate the answer
        evaluation = self.quiz_master.evaluate_answer(
            student_id=student_id,
            quiz_id=quiz_id,
            question_index=question_index,
            student_answer=user_message
        )
        
        # Build response
        if evaluation.get("is_correct", False):
            response = f"Correct! {evaluation.get('explanation', '')}"
        else:
            response = f"Not quite. {evaluation.get('explanation', '')}"
            if "misconception" in evaluation:
                response += f"\n\nYou might be thinking: {evaluation['misconception']}"
            if "improvement_tip" in evaluation:
                response += f"\n\nTip: {evaluation['improvement_tip']}"
        
        # Check if quiz is complete
        if question_index + 1 >= state["context"].get("total_questions", 5):
            # End of quiz - analyze results
            quiz_analysis = self.quiz_master.analyze_quiz_results(
                student_id=student_id,
                quiz_id=quiz_id
            )
            
            # Add analysis to response
            response += f"\n\n--- Quiz Completed ---\n\nYour Score: {quiz_analysis.get('score', 0):.1f}%\n\n{quiz_analysis.get('analysis', '')}"
            
            # Reset quiz state
            state["current_quiz_id"] = None
            state["current_learning_mode"] = LearningMode.REVIEW.value
            state["context"]["current_question_index"] = 0
        else:
            # Move to next question
            state["context"]["current_question_index"] = question_index + 1
        
        # Update state
        state["system_message"] = response
        return state
    
    def _handle_content_request(self, state: LearningState) -> LearningState:
        """
        Handle a content request using the Learning Guide.
        
        Args:
            state (LearningState): Current state
            
        Returns:
            LearningState: Updated state with the learning content
        """
        student_id = state["student_id"]
        user_message = state["user_message"]
        
        # Extract topic and subtopic from message
        message_lower = user_message.lower()
        topic = state["current_topic"]
        subtopic = state["current_subtopic"]
        
        # Simple extraction logic - in a real system, use NLP or more sophisticated parsing
        if "about" in message_lower:
            parts = message_lower.split("about")[1].strip().split()
            if len(parts) >= 1:
                topic = parts[0].strip()
            if len(parts) >= 2:
                subtopic = parts[1].strip()
        elif "explain" in message_lower:
            parts = message_lower.split("explain")[1].strip().split()
            if len(parts) >= 1:
                topic = parts[0].strip()
            if len(parts) >= 2:
                subtopic = parts[1].strip()
        
        # If topic is still not defined, use a default
        if not topic:
            topic = "general"
            subtopic = "basics"
        
        # Generate the learning content
        content = self.learning_guide.generate_learning_content(
            student_id=student_id,
            topic=topic,
            subtopic=subtopic or "general"
        )
        
        # Update state
        state["current_topic"] = topic
        state["current_subtopic"] = subtopic
        state["current_learning_mode"] = LearningMode.GUIDED_LEARNING.value
        state["system_message"] = content
        
        return state
    
    def _handle_progress_request(self, state: LearningState) -> LearningState:
        """
        Handle a progress request using the Progress Tracker.
        
        Args:
            state (LearningState): Current state
            
        Returns:
            LearningState: Updated state with the progress report
        """
        student_id = state["student_id"]
        current_topic = state["current_topic"]
        
        # Determine time period from message (default to 30 days)
        time_period = 30
        
        # Generate progress summary
        progress_summary = self.progress_tracker.generate_progress_summary(
            student_id=student_id,
            topic=current_topic,
            days=time_period
        )
        
        # Check if there was an error
        if "error" in progress_summary:
            response = f"Not enough learning data available yet. Keep learning and I'll be able to track your progress soon!"
        else:
            # Format the response
            response = f"Here's your learning progress for the past {time_period} days:\n\n"
            response += progress_summary.get("overall_summary", "No summary available.")
        
        # Update state
        state["system_message"] = response
        return state
    
    def _handle_study_plan_request(self, state: LearningState) -> LearningState:
        """
        Handle a study plan request using the Learning Guide.
        
        Args:
            state (LearningState): Current state
            
        Returns:
            LearningState: Updated state with the study plan
        """
        student_id = state["student_id"]
        user_message = state["user_message"]
        current_topic = state["current_topic"] or "general"
        
        # Extract goal and timeline from message
        # In a real system, use NLP for more sophisticated extraction
        goal = "master the fundamentals"
        timeline = "4 weeks"
        
        if "goal" in user_message.lower():
            goal_parts = user_message.lower().split("goal")[1].split("timeline")[0].strip()
            goal = goal_parts
        
        if "timeline" in user_message.lower():
            timeline_parts = user_message.lower().split("timeline")[1].strip()
            timeline = timeline_parts
        
        # Generate the study plan
        study_plan = self.learning_guide.create_study_plan(
            student_id=student_id,
            topic=current_topic,
            goal=goal,
            timeline=timeline
        )
        
        # Update state
        state["system_message"] = study_plan
        return state
    
    def _generate_response(self, state: LearningState) -> LearningState:
        """
        Final processing of the response before returning to the user.
        
        Args:
            state (LearningState): Current state
            
        Returns:
            LearningState: Final state with processed response
        """
        # In a real implementation, this might format the response, add UI elements, etc.
        # For now, we'll just return the system message as is
        return state
    
    def process(self, student_id: str, message: str, state_manager: Optional[StateManager] = None) -> Dict[str, Any]:
        """
        Process a user message through the workflow.
        
        Args:
            student_id (str): Student ID
            message (str): User message
            state_manager (StateManager, optional): State manager for the session
            
        Returns:
            Dict: Response including system message and updated state
        """
        # Initialize state
        if state_manager:
            # Use existing state manager
            current_state = state_manager.get_state_summary()
        else:
            # Create new state with defaults
            current_state = {
                "student_id": student_id,
                "current_topic": None,
                "current_subtopic": None,
                "current_difficulty_level": 3,
                "current_learning_mode": LearningMode.EXPLORATION.value,
                "current_quiz_id": None,
                "current_session_id": None,
                "conversation_history": [],
                "context": {}
            }
        
        # Build the state for LangGraph
        graph_state = LearningState(
            student_id=student_id,
            current_topic=current_state.get("current_topic"),
            current_subtopic=current_state.get("current_subtopic"),
            current_difficulty_level=current_state.get("difficulty_level", 3),
            current_learning_mode=current_state.get("learning_mode", LearningMode.EXPLORATION.value),
            current_quiz_id=current_state.get("current_quiz_id"),
            current_session_id=current_state.get("current_session_id"),
            conversation_history=current_state.get("conversation_history", []),
            user_message=message,
            system_message="",
            context=current_state.get("context", {}),
            action=None
        )
        
        # Run the workflow
        result = self.workflow.invoke(graph_state)
        
        # Update state manager if provided
        if state_manager:
            if result["current_topic"] != current_state.get("current_topic"):
                state_manager.change_topic(result["current_topic"], result["current_subtopic"])
            
            if result["current_learning_mode"] != current_state.get("learning_mode"):
                state_manager.change_learning_mode(result["current_learning_mode"])
            
            if result["current_difficulty_level"] != current_state.get("difficulty_level"):
                state_manager.update_difficulty(result["current_difficulty_level"])
            
            # Add message to history
            state_manager.add_message({
                "role": "user",
                "content": message
            })
            state_manager.add_message({
                "role": "system",
                "content": result["system_message"]
            })
            
            # Update context
            for key, value in result["context"].items():
                state_manager.add_context(key, value)
        
        # Return the response
        return {
            "response": result["system_message"],
            "state": {
                "topic": result["current_topic"],
                "subtopic": result["current_subtopic"],
                "difficulty_level": result["current_difficulty_level"],
                "learning_mode": result["current_learning_mode"],
                "in_quiz": result["current_quiz_id"] is not None
            }
        }


def get_learning_workflow():
    """
    Factory function to get a LearningWorkflow instance.
    
    Returns:
        LearningWorkflow: An instance of the learning workflow
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    return LearningWorkflow(api_key=api_key)