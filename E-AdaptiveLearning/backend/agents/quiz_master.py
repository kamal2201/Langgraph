import os
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from database.db_handler import DatabaseHandler

class QuizMasterAgent:
    """
    Quiz Master Agent is responsible for generating adaptive quizzes
    based on student's learning progress and analyzing their responses.
    """
    
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        """
        Initialize the Quiz Master Agent.
        
        Args:
            api_key (str): Google API key
            model (str): LLM model to use
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(temperature=0.3, model=model, google_api_key=self.api_key)
        self.db = DatabaseHandler()
        
        # Create the quiz generation prompt template
        self.quiz_prompt = PromptTemplate(
            input_variables=["student_id", "topic", "subtopic", "difficulty_level", "question_count", "concepts"],
            template="""
            You are a Quiz Master specializing in creating personalized educational assessments.
            
            Create a quiz for:
            Student ID: {student_id}
            Topic: {topic}
            Subtopic: {subtopic}
            Difficulty level: {difficulty_level} (1-5 scale)
            Number of questions: {question_count}
            Key concepts to test: {concepts}
            
            For each question:
            1. Create a clear, concise question that tests understanding, not just memorization
            2. Provide 4 multiple-choice options (A, B, C, D)
            3. Mark the correct answer
            4. Include a brief explanation of why the answer is correct
            5. Assign relevant concept tags to the question
            
            The questions should gradually increase in difficulty, starting with basic understanding
            and moving toward application and analysis.
            
            Format your response as a structured list of questions with answer choices and explanations.
            Each question should be labeled with "Question #" and include options A-D, the correct answer,
            explanation, and concept tags.
            """
        )
        
        self.quiz_chain = LLMChain(llm=self.llm, prompt=self.quiz_prompt)
        
    def get_testable_concepts(self, student_id: str, topic: str, subtopic: str) -> List[str]:
        """
        Determine which concepts should be tested based on student's learning history.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic
            subtopic (str): The specific subtopic
            
        Returns:
            List[str]: List of concepts to test
        """
        # Get learning history
        learning_logs = self.db.get_learning_logs(student_id, topic, limit=10)
        
        # Check if the subtopic has been studied
        subtopic_studied = any(log["subtopic"] == subtopic for log in learning_logs)
        
        if not subtopic_studied:
            # If subtopic not studied, get default concepts from the curriculum
            return self.db.get_default_concepts(topic, subtopic)
        
        # Get recent quiz results to identify areas for improvement
        quiz_results = self.db.get_quiz_results(student_id, topic, limit=10)
        
        # Identify concepts that need reinforcement (score below 70%)
        weak_concepts = []
        strong_concepts = []
        
        for result in quiz_results:
            for concept, score in result.get("concept_scores", {}).items():
                if score < 70:
                    weak_concepts.append(concept)
                else:
                    strong_concepts.append(concept)
        
        # Get all concepts for the subtopic
        all_concepts = self.db.get_default_concepts(topic, subtopic)
        
        # Prioritize weak concepts but include some strong ones for reinforcement
        # and some new ones for advancement
        test_concepts = []
        
        # Add weak concepts first (they need more reinforcement)
        for concept in all_concepts:
            if concept in weak_concepts:
                test_concepts.append(concept)
        
        # Then add some strong concepts (for reinforcement)
        for concept in all_concepts:
            if concept in strong_concepts and concept not in test_concepts:
                test_concepts.append(concept)
                if len(test_concepts) >= len(all_concepts) * 0.7:  # Cap at 70% of all concepts
                    break
        
        # Finally, add some new concepts (for advancement)
        for concept in all_concepts:
            if concept not in weak_concepts and concept not in strong_concepts:
                test_concepts.append(concept)
        
        return test_concepts
    
    def generate_quiz(self, student_id: str, topic: str, subtopic: str, question_count: int = 5) -> Dict[str, Any]:
        """
        Generate an adaptive quiz based on student's learning profile.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic
            subtopic (str): The specific subtopic
            question_count (int): Number of questions to generate
            
        Returns:
            Dict: Quiz content and metadata
        """
        # Get student's current difficulty level
        difficulty_level = self.db.get_student_difficulty_level(student_id, topic) or 3
        
        # Get concepts to test
        concepts = self.get_testable_concepts(student_id, topic, subtopic)
        concepts_str = ", ".join(concepts[:min(len(concepts), 10)])  # Limit to 10 concepts
        
        # Generate the quiz
        response = self.quiz_chain.invoke({
            "student_id": student_id,
            "topic": topic,
            "subtopic": subtopic,
            "difficulty_level": difficulty_level,
            "question_count": question_count,
            "concepts": concepts_str
        })
        
        # Process the raw response to extract structured questions
        # In a real implementation, you would parse the LLM output more robustly
        # For demo purposes, we'll simulate a parsed result
        
        # Create a parser prompt to extract structured data from the quiz response
        parser_prompt = PromptTemplate(
            input_variables=["quiz_text"],
            template="""
            Parse the following quiz into a structured JSON format:
            
            {quiz_text}
            
            Format each question as a JSON object with the following fields:
            - question_text: The question text
            - options: An array of 4 options, each with letter and text
            - correct_answer: The letter of the correct option
            - explanation: The explanation for the correct answer
            - concepts: Array of concept tags associated with the question
            
            Return the result as an array of question objects in proper JSON format.
            """
        )
        
        parser_chain = LLMChain(llm=self.llm, prompt=parser_prompt)
        parsed_response = parser_chain.invoke({"quiz_text": response['text']})
        
        # In a real implementation, you would parse the JSON from the response
        # For now, we'll simulate a parsed result
        quiz_id = self.db.save_quiz(
            student_id=student_id,
            topic=topic,
            subtopic=subtopic,
            difficulty_level=difficulty_level,
            raw_content=response['text'],
            question_count=question_count
        )
        
        return {
            "quiz_id": quiz_id,
            "content": response['text']
        }
    
    def evaluate_answer(self, student_id: str, quiz_id: str, question_index: int, student_answer: str) -> Dict[str, Any]:
        """
        Evaluate a student's answer to a quiz question.
        
        Args:
            student_id (str): Unique identifier for the student
            quiz_id (str): The quiz identifier
            question_index (int): The index of the question
            student_answer (str): The student's answer
            
        Returns:
            Dict: Evaluation result with correctness, explanation, and next steps
        """
        # Get the quiz and question details
        quiz = self.db.get_quiz(quiz_id)
        
        if not quiz:
            return {"error": "Quiz not found"}
        
        # In a real implementation, you would parse the quiz content to get the question
        # and the correct answer. For now, we'll simulate this.
        
        # Create an evaluation prompt
        evaluation_prompt = PromptTemplate(
            input_variables=["question", "correct_answer", "student_answer"],
            template="""
            Evaluate the following student response:
            
            Question: {question}
            Correct answer: {correct_answer}
            Student's answer: {student_answer}
            
            Provide:
            1. Is the answer correct? (yes/no)
            2. A brief explanation of why the answer is correct or incorrect
            3. If incorrect, what misconception might the student have?
            4. A helpful tip for improving understanding
            
            Format your response as a JSON object with fields:
            - is_correct: boolean
            - explanation: string
            - misconception: string (if applicable)
            - improvement_tip: string
            """
        )
        
        # For demo purposes, we'll simulate question and correct answer
        # In a real implementation, you would extract these from the quiz
        question = f"Simulated question {question_index} from quiz {quiz_id}"
        correct_answer = "A"  # Simulated correct answer
        
        evaluation_chain = LLMChain(llm=self.llm, prompt=evaluation_prompt)
        
        # Generate the evaluation
        evaluation_response = evaluation_chain.invoke({
            "question": question,
            "correct_answer": correct_answer,
            "student_answer": student_answer
        })
        
        # Process the evaluation response
        # In a real implementation, you would parse the JSON response
        # For demo purposes, we'll simulate a parsed result
        is_correct = student_answer.upper() == correct_answer.upper()
        
        evaluation_result = {
            "is_correct": is_correct,
            "explanation": "Simulated explanation for question " + str(question_index),
            "misconception": "Simulated misconception" if not is_correct else None,
            "improvement_tip": "Simulated improvement tip"
        }
        
        # Log the student's answer
        self.db.log_quiz_answer(
            student_id=student_id,
            quiz_id=quiz_id,
            question_index=question_index,
            student_answer=student_answer,
            is_correct=is_correct
        )
        
        return evaluation_result
    
    def analyze_quiz_results(self, student_id: str, quiz_id: str) -> Dict[str, Any]:
        """
        Analyze the results of a completed quiz.
        
        Args:
            student_id (str): Unique identifier for the student
            quiz_id (str): The quiz identifier
            
        Returns:
            Dict: Analysis of quiz results with strengths, weaknesses, and recommendations
        """
        # Get quiz answers and details
        answers = self.db.get_quiz_answers(student_id, quiz_id)
        quiz = self.db.get_quiz(quiz_id)
        
        if not quiz or not answers:
            return {"error": "Quiz or answers not found"}
        
        # Calculate overall score
        total_questions = len(answers)
        correct_answers = sum(1 for answer in answers if answer["is_correct"])
        score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # Create an analysis prompt
        analysis_prompt = PromptTemplate(
            input_variables=["topic", "subtopic", "score", "question_results"],
            template="""
            Analyze the following quiz results:
            
            Topic: {topic}
            Subtopic: {subtopic}
            Overall score: {score}%
            
            Question results:
            {question_results}
            
            Provide:
            1. A summary of the student's performance
            2. Identified strengths (concepts they understood well)
            3. Identified weaknesses (concepts they struggled with)
            4. Specific recommendations for further study
            5. Suggested next subtopics to explore
            
            Your analysis should be constructive, encouraging, and provide clear guidance
            for improvement.
            """
        )
        
        # Format question results for the prompt
        question_results = ""
        for i, answer in enumerate(answers):
            question_results += f"Question {i+1}: {'Correct' if answer['is_correct'] else 'Incorrect'}\n"
        
        analysis_chain = LLMChain(llm=self.llm, prompt=analysis_prompt)
        
        # Generate the analysis
        analysis_response = analysis_chain.invoke({
            "topic": quiz["topic"],
            "subtopic": quiz["subtopic"],
            "score": round(score, 1),
            "question_results": question_results
        })
        
        # Save quiz results to database
        result_id = self.db.save_quiz_result(
            student_id=student_id,
            quiz_id=quiz_id,
            score=score,
            analysis=analysis_response['text']
        )
        
        # Return the analysis
        return {
            "quiz_id": quiz_id,
            "score": score,
            "analysis": analysis_response['text'],
            "result_id": result_id
        }
    
    def generate_follow_up_quiz(self, student_id: str, previous_quiz_id: str) -> Dict[str, Any]:
        """
        Generate a follow-up quiz based on the results of a previous quiz.
        
        Args:
            student_id (str): Unique identifier for the student
            previous_quiz_id (str): The previous quiz identifier
            
        Returns:
            Dict: New quiz focused on areas that need improvement
        """
        # Get previous quiz details and results
        previous_quiz = self.db.get_quiz(previous_quiz_id)
        previous_results = self.db.get_quiz_result(student_id, previous_quiz_id)
        
        if not previous_quiz or not previous_results:
            return {"error": "Previous quiz or results not found"}
        
        # Get answers to identify weak areas
        answers = self.db.get_quiz_answers(student_id, previous_quiz_id)
        
        # Identify concepts from incorrect answers
        weak_concepts = []
        for answer in answers:
            if not answer["is_correct"] and "concepts" in answer:
                weak_concepts.extend(answer["concepts"])
        
        # Remove duplicates
        weak_concepts = list(set(weak_concepts))
        
        # Create a follow-up quiz focused on weak areas
        follow_up_quiz = self.generate_quiz(
            student_id=student_id,
            topic=previous_quiz["topic"],
            subtopic=previous_quiz["subtopic"],
            question_count=5  # Shorter follow-up quiz
        )
        
        # Mark this as a follow-up quiz
        self.db.update_quiz_metadata(
            quiz_id=follow_up_quiz["quiz_id"],
            metadata={
                "is_follow_up": True,
                "previous_quiz_id": previous_quiz_id,
                "focus_concepts": weak_concepts
            }
        )
        
        return follow_up_quiz