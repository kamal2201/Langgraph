import os
from typing import Dict, Any, List, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from database.db_handler import DatabaseHandler

class AITutorAgent:
    """
    AI Tutor Agent is responsible for answering specific student questions
    and providing personalized explanations based on the student's learning history.
    """
    
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        """
        Initialize the AI Tutor Agent.
        
        Args:
            api_key (str): Google API key
            model (str): LLM model to use
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(temperature=0.7, model=model, google_api_key=self.api_key)
        self.db = DatabaseHandler()
        
        # Create the tutor prompt template
        self.tutor_prompt = PromptTemplate(
            input_variables=["student_id", "question", "topic", "learning_history", "difficulty_level"],
            template="""
            You are an AI Tutor specializing in {topic}. 
            
            Student ID: {student_id}
            Current difficulty level: {difficulty_level} (1-5 scale)
            
            The student has asked: {question}
            
            Their learning history shows: {learning_history}
            
            Provide a personalized explanation that:
            1. Directly addresses their question
            2. Is adjusted to their current difficulty level
            3. Connects to concepts they've already mastered
            4. Uses examples that build on their previous knowledge
            5. Avoids concepts they've consistently struggled with unless necessary
            
            Your explanation should be clear, concise, and educational.
            If relevant, include 1-2 small practice questions to reinforce the explanation.
            """
        )
        
        self.tutor_chain = LLMChain(llm=self.llm, prompt=self.tutor_prompt)
        
    def get_learning_history(self, student_id: str, topic: str) -> Dict[str, Any]:
        """
        Retrieve student's learning history for contextual tutoring.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The current topic of study
            
        Returns:
            Dict: Learning history with mastered concepts and struggle areas
        """
        # Get learning history from database
        learning_logs = self.db.get_learning_logs(student_id, topic, limit=10)
        quiz_results = self.db.get_quiz_results(student_id, topic, limit=10)
        
        # Process learning history to identify mastered concepts and struggle areas
        mastered_concepts = []
        struggle_areas = []
        
        for result in quiz_results:
            if result["score"] > 80:
                mastered_concepts.extend(result["concepts"])
            elif result["score"] < 60:
                struggle_areas.extend(result["concepts"])
        
        # Remove duplicates
        mastered_concepts = list(set(mastered_concepts))
        struggle_areas = list(set(struggle_areas))
        
        return {
            "mastered_concepts": mastered_concepts,
            "struggle_areas": struggle_areas,
            "recent_topics": [log["subtopic"] for log in learning_logs],
            "quiz_performance": quiz_results
        }
    
    def answer_question(self, student_id: str, question: str, topic: str) -> str:
        """
        Answer a specific question from a student with personalized context.
        
        Args:
            student_id (str): Unique identifier for the student
            question (str): The student's question
            topic (str): The topic related to the question
            
        Returns:
            str: Personalized answer to the student's question
        """
        # Get student's current difficulty level
        difficulty_level = self.db.get_student_difficulty_level(student_id, topic) or 3
        
        # Get learning history
        learning_history = self.get_learning_history(student_id, topic)
        
        # Format the learning history for the prompt
        history_formatted = f"""
        Mastered concepts: {', '.join(learning_history['mastered_concepts']) if learning_history['mastered_concepts'] else 'None yet'}
        Struggle areas: {', '.join(learning_history['struggle_areas']) if learning_history['struggle_areas'] else 'None identified yet'}
        Recent topics studied: {', '.join(learning_history['recent_topics']) if learning_history['recent_topics'] else 'Just starting'}
        """
        
        # Generate the response
        response = self.tutor_chain.invoke({
            "student_id": student_id,
            "question": question,
            "topic": topic,
            "learning_history": history_formatted,
            "difficulty_level": difficulty_level
        })
        
        # Log this interaction
        self.db.log_learning_interaction(
            student_id=student_id,
            interaction_type="question",
            topic=topic,
            content=question,
            response=response['text']
        )
        
        return response['text']
    
    def provide_hint(self, student_id: str, question_id: str, topic: str) -> str:
        """
        Provide a hint for a quiz question without giving away the answer.
        
        Args:
            student_id (str): Unique identifier for the student
            question_id (str): ID of the question
            topic (str): The topic of the question
            
        Returns:
            str: A helpful hint
        """
        # Get the question details
        question_details = self.db.get_quiz_question(question_id)
        
        if not question_details:
            return "Sorry, I couldn't find that question."
        
        # Get student's current difficulty level
        difficulty_level = self.db.get_student_difficulty_level(student_id, topic) or 3
        
        # Create a hint prompt
        hint_prompt = PromptTemplate(
            input_variables=["question", "difficulty_level"],
            template="""
            For the following question: 
            
            {question}
            
            Provide a helpful hint that guides the student toward the answer without giving it away.
            Tailor your hint to difficulty level: {difficulty_level} (1-5 scale).
            """
        )
        
        hint_chain = LLMChain(llm=self.llm, prompt=hint_prompt)
        
        # Generate the hint
        response = hint_chain.invoke({
            "question": question_details["question"],
            "difficulty_level": difficulty_level
        })
        
        # Log this interaction
        self.db.log_learning_interaction(
            student_id=student_id,
            interaction_type="hint",
            topic=topic,
            content=question_details["question"],
            response=response['text']
        )
        
        return response['text']
    
    def explain_misconception(self, student_id: str, topic: str, wrong_answer: str, correct_answer: str) -> str:
        """
        Explain why a student's answer was incorrect and clarify the misconception.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The topic being studied
            wrong_answer (str): The student's incorrect answer
            correct_answer (str): The correct answer
            
        Returns:
            str: An explanation of the misconception
        """
        # Get student's current difficulty level
        difficulty_level = self.db.get_student_difficulty_level(student_id, topic) or 3
        
        # Get learning history
        learning_history = self.get_learning_history(student_id, topic)
        
        # Create a misconception prompt
        misconception_prompt = PromptTemplate(
            input_variables=["wrong_answer", "correct_answer", "difficulty_level", "struggle_areas"],
            template="""
            The student provided this answer: {wrong_answer}
            
            The correct answer is: {correct_answer}
            
            The student has struggled with these concepts: {struggle_areas}
            
            Explain the misconception in a way that:
            1. Is respectful and encourages further learning
            2. Clearly identifies the specific error in their thinking
            3. Connects the correct answer to concepts they are familiar with
            4. Is tailored to difficulty level: {difficulty_level} (1-5 scale)
            
            Your explanation should help the student understand why their answer was incorrect
            and strengthen their understanding of the concept.
            """
        )
        
        misconception_chain = LLMChain(llm=self.llm, prompt=misconception_prompt)
        
        # Generate the explanation
        struggle_areas_str = ", ".join(learning_history["struggle_areas"]) if learning_history["struggle_areas"] else "None identified yet"
        
        response = misconception_chain.invoke({
            "wrong_answer": wrong_answer,
            "correct_answer": correct_answer,
            "difficulty_level": difficulty_level,
            "struggle_areas": struggle_areas_str
        })
        
        # Log this interaction
        self.db.log_learning_interaction(
            student_id=student_id,
            interaction_type="misconception",
            topic=topic,
            content=f"Wrong: {wrong_answer}, Correct: {correct_answer}",
            response=response['text']
        )
        
        return response['text']