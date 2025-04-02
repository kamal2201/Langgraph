from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from .connection import get_db_connection

class DatabaseHandler:
    """
    Handles all database operations for the E-AdaptiveLearning system.
    """
    
    def __init__(self):
        """
        Initialize the DatabaseHandler.
        """
        self.db_conn = get_db_connection()
        
    def _get_collection(self, collection_name: str):
        """
        Get a specific collection from the database.
        
        Args:
            collection_name (str): Name of the collection
            
        Returns:
            Collection: pymongo collection object
        """
        return self.db_conn.get_collection(collection_name)
    
    # ==================== Student Profiles ====================
    
    def get_student_profile(self, student_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a student's profile.
        
        Args:
            student_id (str): Unique identifier for the student
            
        Returns:
            Dict: Student profile data or None if not found
        """
        students_coll = self._get_collection("students")
        return students_coll.find_one({"_id": student_id})
    
    def create_student_profile(self, student_id: str, profile_data: Dict[str, Any]) -> bool:
        """
        Create a new student profile.
        
        Args:
            student_id (str): Unique identifier for the student
            profile_data (Dict): Student profile data
            
        Returns:
            bool: True if successful, False otherwise
        """
        students_coll = self._get_collection("students")
        profile_data["_id"] = student_id
        profile_data["created_at"] = datetime.now()
        profile_data["updated_at"] = datetime.now()
        
        try:
            students_coll.insert_one(profile_data)
            return True
        except Exception as e:
            print(f"Error creating student profile: {e}")
            return False
    
    def update_student_profile(self, student_id: str, profile_data: Dict[str, Any]) -> bool:
        """
        Update an existing student profile.
        
        Args:
            student_id (str): Unique identifier for the student
            profile_data (Dict): Updated student profile data
            
        Returns:
            bool: True if successful, False otherwise
        """
        students_coll = self._get_collection("students")
        profile_data["updated_at"] = datetime.now()
        
        try:
            result = students_coll.update_one(
                {"_id": student_id},
                {"$set": profile_data}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating student profile: {e}")
            return False
    
    def get_student_topics(self, student_id: str) -> List[str]:
        """
        Get all topics a student has studied.
        
        Args:
            student_id (str): Unique identifier for the student
            
        Returns:
            List[str]: List of topics
        """
        learning_logs_coll = self._get_collection("learning_logs")
        
        # Find distinct topics in learning logs
        topics = learning_logs_coll.distinct("topic", {"student_id": student_id})
        return list(topics)
    
    def get_student_difficulty_level(self, student_id: str, topic: str) -> Optional[int]:
        """
        Get the current difficulty level for a student on a specific topic.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The topic
            
        Returns:
            int: Difficulty level (1-5) or None if not set
        """
        student_levels_coll = self._get_collection("student_levels")
        result = student_levels_coll.find_one({"student_id": student_id, "topic": topic})
        
        if result:
            return result.get("difficulty_level", 3)  # Default to level 3 if not specified
        return None
    
    def update_student_difficulty_level(self, student_id: str, topic: str, difficulty_level: int) -> bool:
        """
        Update the difficulty level for a student on a specific topic.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The topic
            difficulty_level (int): New difficulty level (1-5)
            
        Returns:
            bool: True if successful, False otherwise
        """
        student_levels_coll = self._get_collection("student_levels")
        
        try:
            result = student_levels_coll.update_one(
                {"student_id": student_id, "topic": topic},
                {"$set": {
                    "difficulty_level": difficulty_level,
                    "updated_at": datetime.now()
                }},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating student difficulty level: {e}")
            return False
    
    # ==================== Learning Logs ====================
    
    def log_learning_session(self, student_id: str, topic: str, subtopic: str, difficulty_level: int, content_summary: str) -> str:
        """
        Log a learning session.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic
            subtopic (str): The specific subtopic
            difficulty_level (int): Difficulty level of the content
            content_summary (str): Summary of the content covered
            
        Returns:
            str: ID of the log entry
        """
        learning_logs_coll = self._get_collection("learning_logs")
        
        log_id = str(uuid.uuid4())
        log_entry = {
            "_id": log_id,
            "student_id": student_id,
            "topic": topic,
            "subtopic": subtopic,
            "difficulty_level": difficulty_level,
            "content_summary": content_summary,
            "activity_type": "study_session",
            "timestamp": datetime.now(),
            "duration": 0  # To be updated when session ends
        }
        
        learning_logs_coll.insert_one(log_entry)
        return log_id
    
    def update_learning_session(self, log_id: str, duration: int) -> bool:
        """
        Update a learning session with duration.
        
        Args:
            log_id (str): ID of the log entry
            duration (int): Duration in minutes
            
        Returns:
            bool: True if successful, False otherwise
        """
        learning_logs_coll = self._get_collection("learning_logs")
        
        try:
            result = learning_logs_coll.update_one(
                {"_id": log_id},
                {"$set": {"duration": duration}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating learning session: {e}")
            return False
    
    def get_learning_logs(self, student_id: str, topic: Optional[str] = None, subtopic: Optional[str] = None, 
                         start_date: Optional[datetime] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get learning logs for a student.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str, optional): Filter by topic
            subtopic (str, optional): Filter by subtopic
            start_date (datetime, optional): Filter by start date
            limit (int): Maximum number of logs to return
            
        Returns:
            List[Dict]: List of learning logs
        """
        learning_logs_coll = self._get_collection("learning_logs")
        
        # Build query
        query = {"student_id": student_id}
        if topic:
            query["topic"] = topic
        if subtopic:
            query["subtopic"] = subtopic
        if start_date:
            query["timestamp"] = {"$gte": start_date}
        
        # Execute query
        logs = list(learning_logs_coll.find(query).sort("timestamp", -1).limit(limit))
        return logs
    
    def log_learning_interaction(self, student_id: str, interaction_type: str, topic: str, 
                               content: str, response: str) -> str:
        """
        Log an interaction between the student and the AI.
        
        Args:
            student_id (str): Unique identifier for the student
            interaction_type (str): Type of interaction (question, hint, etc.)
            topic (str): The topic related to the interaction
            content (str): Content of the interaction (e.g., student's question)
            response (str): AI's response
            
        Returns:
            str: ID of the interaction log
        """
        interactions_coll = self._get_collection("interactions")
        
        interaction_id = str(uuid.uuid4())
        interaction = {
            "_id": interaction_id,
            "student_id": student_id,
            "type": interaction_type,
            "topic": topic,
            "content": content,
            "response": response,
            "timestamp": datetime.now()
        }
        
        interactions_coll.insert_one(interaction)
        return interaction_id
    
    # ==================== Quizzes ====================
    
    def save_quiz(self, student_id: str, topic: str, subtopic: str, difficulty_level: int, 
                 raw_content: str, question_count: int) -> str:
        """
        Save a generated quiz.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic
            subtopic (str): The specific subtopic
            difficulty_level (int): Difficulty level of the quiz
            raw_content (str): Raw quiz content
            question_count (int): Number of questions in the quiz
            
        Returns:
            str: ID of the quiz
        """
        quizzes_coll = self._get_collection("quizzes")
        
        quiz_id = str(uuid.uuid4())
        quiz = {
            "_id": quiz_id,
            "student_id": student_id,
            "topic": topic,
            "subtopic": subtopic,
            "difficulty_level": difficulty_level,
            "content": raw_content,
            "question_count": question_count,
            "created_at": datetime.now(),
            "metadata": {}
        }
        
        quizzes_coll.insert_one(quiz)
        return quiz_id
    
    def get_quiz(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a quiz by ID.
        
        Args:
            quiz_id (str): ID of the quiz
            
        Returns:
            Dict: Quiz data or None if not found
        """
        quizzes_coll = self._get_collection("quizzes")
        return quizzes_coll.find_one({"_id": quiz_id})
    
    def update_quiz_metadata(self, quiz_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update quiz metadata.
        
        Args:
            quiz_id (str): ID of the quiz
            metadata (Dict): Metadata to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        quizzes_coll = self._get_collection("quizzes")
        
        try:
            result = quizzes_coll.update_one(
                {"_id": quiz_id},
                {"$set": {"metadata": metadata}}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating quiz metadata: {e}")
            return False
    
    def get_quiz_question(self, question_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific quiz question.
        
        Args:
            question_id (str): ID of the question
            
        Returns:
            Dict: Question data or None if not found
        """
        questions_coll = self._get_collection("quiz_questions")
        return questions_coll.find_one({"_id": question_id})
    
    def log_quiz_answer(self, student_id: str, quiz_id: str, question_index: int, 
                       student_answer: str, is_correct: bool) -> str:
        """
        Log a student's answer to a quiz question.
        
        Args:
            student_id (str): Unique identifier for the student
            quiz_id (str): ID of the quiz
            question_index (int): Index of the question
            student_answer (str): Student's answer
            is_correct (bool): Whether the answer is correct
            
        Returns:
            str: ID of the answer log
        """
        answers_coll = self._get_collection("quiz_answers")
        
        answer_id = str(uuid.uuid4())
        answer = {
            "_id": answer_id,
            "student_id": student_id,
            "quiz_id": quiz_id,
            "question_index": question_index,
            "student_answer": student_answer,
            "is_correct": is_correct,
            "timestamp": datetime.now()
        }
        
        answers_coll.insert_one(answer)
        return answer_id
    
    def get_quiz_answers(self, student_id: str, quiz_id: str) -> List[Dict[str, Any]]:
        """
        Get all answers for a specific quiz.
        
        Args:
            student_id (str): Unique identifier for the student
            quiz_id (str): ID of the quiz
            
        Returns:
            List[Dict]: List of answers
        """
        answers_coll = self._get_collection("quiz_answers")
        
        answers = list(answers_coll.find({
            "student_id": student_id,
            "quiz_id": quiz_id
        }).sort("question_index", 1))
        
        return answers
    
    def save_quiz_result(self, student_id: str, quiz_id: str, score: float, analysis: str) -> str:
        """
        Save quiz result with analysis.
        
        Args:
            student_id (str): Unique identifier for the student
            quiz_id (str): ID of the quiz
            score (float): Score as a percentage
            analysis (str): Analysis of the quiz result
            
        Returns:
            str: ID of the result
        """
        results_coll = self._get_collection("quiz_results")
        
        # Get the quiz to include topic and subtopic
        quiz = self.get_quiz(quiz_id)
        if not quiz:
            return ""
        
        result_id = str(uuid.uuid4())
        result = {
            "_id": result_id,
            "student_id": student_id,
            "quiz_id": quiz_id,
            "topic": quiz.get("topic", ""),
            "subtopic": quiz.get("subtopic", ""),
            "score": score,
            "analysis": analysis,
            "timestamp": datetime.now()
        }
        
        results_coll.insert_one(result)
        return result_id
    
    def get_quiz_result(self, student_id: str, quiz_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific quiz result.
        
        Args:
            student_id (str): Unique identifier for the student
            quiz_id (str): ID of the quiz
            
        Returns:
            Dict: Quiz result or None if not found
        """
        results_coll = self._get_collection("quiz_results")
        return results_coll.find_one({"student_id": student_id, "quiz_id": quiz_id})
    
    def get_quiz_results(self, student_id: str, topic: Optional[str] = None, subtopic: Optional[str] = None,
                        start_date: Optional[datetime] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get quiz results for a student.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str, optional): Filter by topic
            subtopic (str, optional): Filter by subtopic
            start_date (datetime, optional): Filter by start date
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of quiz results
        """
        results_coll = self._get_collection("quiz_results")
        
        # Build query
        query = {"student_id": student_id}
        if topic:
            query["topic"] = topic
        if subtopic:
            query["subtopic"] = subtopic
        if start_date:
            query["timestamp"] = {"$gte": start_date}
        
        # Execute query
        results = list(results_coll.find(query).sort("timestamp", -1).limit(limit))
        return results
    
    # ==================== Progress Tracking ====================
    
    def save_progress_report(self, student_id: str, topic: str, time_period: int, 
                           average_score: float, analysis: str) -> str:
        """
        Save a progress report.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The topic
            time_period (int): Time period in days
            average_score (float): Average quiz score
            analysis (str): Analysis of the progress
            
        Returns:
            str: ID of the report
        """
        reports_coll = self._get_collection("progress_reports")
        
        report_id = str(uuid.uuid4())
        report = {
            "_id": report_id,
            "student_id": student_id,
            "topic": topic,
            "time_period": time_period,
            "average_score": average_score,
            "analysis": analysis,
            "created_at": datetime.now()
        }
        
        reports_coll.insert_one(report)
        return report_id
    
    def save_learning_pattern_analysis(self, student_id: str, topic: str, analysis: str) -> str:
        """
        Save a learning pattern analysis.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The topic
            analysis (str): Analysis of learning patterns
            
        Returns:
            str: ID of the analysis
        """
        patterns_coll = self._get_collection("learning_patterns")
        
        analysis_id = str(uuid.uuid4())
        pattern_analysis = {
            "_id": analysis_id,
            "student_id": student_id,
            "topic": topic,
            "analysis": analysis,
            "created_at": datetime.now()
        }
        
        patterns_coll.insert_one(pattern_analysis)
        return analysis_id
    
    def save_progress_summary(self, student_id: str, time_period: int, summary: str, 
                             topic_summaries: Dict[str, Any]) -> str:
        """
        Save a comprehensive progress summary.
        
        Args:
            student_id (str): Unique identifier for the student
            time_period (int): Time period in days
            summary (str): Overall progress summary
            topic_summaries (Dict): Summaries for individual topics
            
        Returns:
            str: ID of the summary
        """
        summaries_coll = self._get_collection("progress_summaries")
        
        summary_id = str(uuid.uuid4())
        summary_doc = {
            "_id": summary_id,
            "student_id": student_id,
            "time_period": time_period,
            "summary": summary,
            "topic_summaries": topic_summaries,
            "created_at": datetime.now()
        }
        
        summaries_coll.insert_one(summary_doc)
        return summary_id
    
    # ==================== Study Plans ====================
    
    def save_study_plan(self, student_id: str, topic: str, goal: str, timeline: str, 
                       plan_content: str) -> str:
        """
        Save a study plan.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The topic
            goal (str): Learning goal
            timeline (str): Timeline for completion
            plan_content (str): Study plan content
            
        Returns:
            str: ID of the study plan
        """
        plans_coll = self._get_collection("study_plans")
        
        plan_id = str(uuid.uuid4())
        plan = {
            "_id": plan_id,
            "student_id": student_id,
            "topic": topic,
            "goal": goal,
            "timeline": timeline,
            "content": plan_content,
            "created_at": datetime.now()
        }
        
        plans_coll.insert_one(plan)
        return plan_id
    
    # ==================== Resources ====================
    
    def log_resource_recommendations(self, student_id: str, topic: str, subtopic: str, 
                                    recommendations: str) -> str:
        """
        Log resource recommendations.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The topic
            subtopic (str): The subtopic
            recommendations (str): Resource recommendations
            
        Returns:
            str: ID of the recommendations log
        """
        resources_coll = self._get_collection("resource_recommendations")
        
        rec_id = str(uuid.uuid4())
        rec = {
            "_id": rec_id,
            "student_id": student_id,
            "topic": topic,
            "subtopic": subtopic,
            "recommendations": recommendations,
            "created_at": datetime.now()
        }
        
        resources_coll.insert_one(rec)
        return rec_id
    
    def get_default_concepts(self, topic: str, subtopic: str) -> List[str]:
        """
        Get default concepts for a subtopic.
        
        Args:
            topic (str): The main topic
            subtopic (str): The specific subtopic
            
        Returns:
            List[str]: List of default concepts
        """
        curriculum_coll = self._get_collection("curriculum")
        
        result = curriculum_coll.find_one({"topic": topic, "subtopic": subtopic})
        if result and "concepts" in result:
            return result["concepts"]
        
        # Return some dummy concepts if not found
        return ["Concept 1", "Concept 2", "Concept 3"]