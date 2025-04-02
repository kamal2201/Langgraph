import os
import datetime
from typing import Dict, Any, List, Optional, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from database.db_handler import DatabaseHandler

class ProgressTrackerAgent:
    """
    Progress Tracker Agent is responsible for monitoring student progress,
    providing insights, and adjusting the difficulty level of learning materials.
    """
    
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        """
        Initialize the Progress Tracker Agent.
        
        Args:
            api_key (str): Google API key
            model (str): LLM model to use
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(temperature=0.2, model=model, google_api_key=self.api_key)
        self.db = DatabaseHandler()
        
        # Create the progress analysis prompt template
        self.progress_prompt = PromptTemplate(
            input_variables=["student_id", "topic", "learning_history", "quiz_results", "time_period"],
            template="""
            Analyze the following student progress data:
            
            Student ID: {student_id}
            Topic: {topic}
            Time period: {time_period}
            
            Learning history:
            {learning_history}
            
            Quiz results:
            {quiz_results}
            
            Provide a comprehensive analysis including:
            1. Overall progress assessment
            2. Rate of improvement
            3. Strengths identified
            4. Areas that need more attention
            5. Learning patterns observed
            6. Specific recommendations for improving weak areas
            7. Recommended difficulty level adjustments (if any)
            
            Your analysis should be data-driven, insightful, and provide actionable 
            recommendations for the student's continued learning.
            """
        )
        
        self.progress_chain = LLMChain(llm=self.llm, prompt=self.progress_prompt)
        
    def get_learning_data(self, student_id: str, topic: str, days: int = 30) -> Tuple[List[Dict], List[Dict]]:
        """
        Retrieve learning history and quiz results for a specific time period.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic
            days (int): Number of days to look back
            
        Returns:
            Tuple[List[Dict], List[Dict]]: Learning logs and quiz results
        """
        # Calculate the date for looking back
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Get learning history from database
        learning_logs = self.db.get_learning_logs(
            student_id=student_id, 
            topic=topic, 
            start_date=start_date
        )
        
        # Get quiz results from database
        quiz_results = self.db.get_quiz_results(
            student_id=student_id, 
            topic=topic, 
            start_date=start_date
        )
        
        return learning_logs, quiz_results
    
    def analyze_progress(self, student_id: str, topic: str, days: int = 30) -> Dict[str, Any]:
        """
        Analyze student's progress over a specific time period.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic
            days (int): Number of days to look back
            
        Returns:
            Dict: Progress analysis with insights and recommendations
        """
        # Get learning data
        learning_logs, quiz_results = self.get_learning_data(student_id, topic, days)
        
        if not learning_logs and not quiz_results:
            return {
                "error": "Insufficient data for analysis",
                "message": f"No learning data found for the past {days} days."
            }
        
        # Format learning history for the prompt
        learning_history = ""
        for log in learning_logs:
            date = log.get("timestamp", "Unknown date")
            subtopic = log.get("subtopic", "Unknown subtopic")
            activity = log.get("activity_type", "study session")
            learning_history += f"- {date}: {activity} on {subtopic}\n"
        
        # Format quiz results for the prompt
        quiz_results_formatted = ""
        for result in quiz_results:
            date = result.get("timestamp", "Unknown date")
            subtopic = result.get("subtopic", "Unknown subtopic")
            score = result.get("score", 0)
            quiz_results_formatted += f"- {date}: Quiz on {subtopic} - Score: {score}%\n"
        
        # Generate the progress analysis
        response = self.progress_chain.invoke({
            "student_id": student_id,
            "topic": topic,
            "time_period": f"Past {days} days",
            "learning_history": learning_history,
            "quiz_results": quiz_results_formatted
        })
        
        # Calculate average quiz score
        avg_score = 0
        if quiz_results:
            total_score = sum(result.get("score", 0) for result in quiz_results)
            avg_score = total_score / len(quiz_results)
        
        # Save progress report to database
        report_id = self.db.save_progress_report(
            student_id=student_id,
            topic=topic,
            time_period=days,
            average_score=avg_score,
            analysis=response['text']
        )
        
        return {
            "report_id": report_id,
            "average_score": avg_score,
            "analysis": response['text']
        }
    
    def recommend_difficulty_adjustment(self, student_id: str, topic: str) -> Dict[str, Any]:
        """
        Recommend adjustments to difficulty level based on student performance.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic
            
        Returns:
            Dict: Recommendation for difficulty adjustment
        """
        # Get current difficulty level
        current_level = self.db.get_student_difficulty_level(student_id, topic) or 3
        
        # Get recent quiz results (last 5 quizzes)
        recent_results = self.db.get_quiz_results(
            student_id=student_id, 
            topic=topic, 
            limit=5
        )
        
        if not recent_results:
            return {
                "current_level": current_level,
                "recommended_level": current_level,
                "explanation": "Insufficient data for difficulty adjustment."
            }
        
        # Calculate average recent score
        total_score = sum(result.get("score", 0) for result in recent_results)
        avg_score = total_score / len(recent_results)
        
        # Generate difficulty adjustment recommendation
        recommended_level = current_level
        explanation = ""
        
        if avg_score > 85 and current_level < 5:
            # Consistently high performance - increase difficulty
            recommended_level = min(current_level + 1, 5)
            explanation = f"Student has consistently performed well (avg. score: {avg_score:.1f}%). Increasing difficulty level to provide more challenge."
        elif avg_score < 60 and current_level > 1:
            # Consistently low performance - decrease difficulty
            recommended_level = max(current_level - 1, 1)
            explanation = f"Student has been struggling (avg. score: {avg_score:.1f}%). Decreasing difficulty level to build confidence and understanding."
        else:
            # Performance is appropriate for current level
            explanation = f"Student's performance (avg. score: {avg_score:.1f}%) is appropriate for the current difficulty level. No adjustment needed."
        
        # If there's a change, update the difficulty level
        if recommended_level != current_level:
            self.db.update_student_difficulty_level(
                student_id=student_id,
                topic=topic,
                difficulty_level=recommended_level
            )
        
        return {
            "current_level": current_level,
            "recommended_level": recommended_level,
            "explanation": explanation
        }
    
    def identify_learning_pattern(self, student_id: str, topic: str) -> Dict[str, Any]:
        """
        Identify patterns in the student's learning behavior and performance.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic
            
        Returns:
            Dict: Identified learning patterns and insights
        """
        # Get learning logs and quiz results
        learning_logs, quiz_results = self.get_learning_data(student_id, topic, days=60)
        
        if not learning_logs and not quiz_results:
            return {
                "error": "Insufficient data for pattern identification",
                "message": "Not enough learning data available."
            }
        
        # Create a pattern analysis prompt
        pattern_prompt = PromptTemplate(
            input_variables=["learning_logs", "quiz_results"],
            template="""
            Analyze the following student learning data to identify patterns:
            
            Learning activity logs:
            {learning_logs}
            
            Quiz performance:
            {quiz_results}
            
            Identify patterns in:
            1. Learning session frequency and timing
            2. Performance trends across different subtopics
            3. Correlation between study time and quiz performance
            4. Topics where progress is consistent vs. inconsistent
            5. Learning style indicators based on performance patterns
            
            Provide data-driven insights that could help personalize the learning experience.
            """
        )
        
        # Format learning logs for the prompt
        learning_logs_formatted = ""
        for log in learning_logs:
            date = log.get("timestamp", "Unknown date")
            subtopic = log.get("subtopic", "Unknown subtopic")
            duration = log.get("duration", "Unknown duration")
            activity = log.get("activity_type", "study session")
            learning_logs_formatted += f"- {date}: {activity} on {subtopic} for {duration} minutes\n"
        
        # Format quiz results for the prompt
        quiz_results_formatted = ""
        for result in quiz_results:
            date = result.get("timestamp", "Unknown date")
            subtopic = result.get("subtopic", "Unknown subtopic")
            score = result.get("score", 0)
            concepts = ", ".join(result.get("concepts", []))
            quiz_results_formatted += f"- {date}: Quiz on {subtopic} - Score: {score}% (Concepts: {concepts})\n"
        
        pattern_chain = LLMChain(llm=self.llm, prompt=pattern_prompt)
        
        # Generate the pattern analysis
        response = pattern_chain.invoke({
            "learning_logs": learning_logs_formatted,
            "quiz_results": quiz_results_formatted
        })
        
        # Save the pattern analysis to the database
        analysis_id = self.db.save_learning_pattern_analysis(
            student_id=student_id,
            topic=topic,
            analysis=response['text']
        )
        
        return {
            "analysis_id": analysis_id,
            "patterns": response['text']
        }
    
    def generate_progress_summary(self, student_id: str, topic: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """
        Generate a comprehensive progress summary for a student.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str, optional): The main topic, or all topics if None
            days (int): Number of days to look back
            
        Returns:
            Dict: Progress summary with visualizations and recommendations
        """
        # If topic is None, get all topics the student has studied
        topics = [topic] if topic else self.db.get_student_topics(student_id)
        
        if not topics:
            return {
                "error": "No learning data found",
                "message": f"No topics found for student {student_id}."
            }
        
        # Generate summary for each topic
        topic_summaries = {}
        overall_stats = {
            "total_study_time": 0,
            "quizzes_taken": 0,
            "average_score": 0,
            "total_score": 0,
            "concepts_mastered": set(),
            "concepts_struggling": set()
        }
        
        for topic_name in topics:
            # Get learning data for this topic
            learning_logs, quiz_results = self.get_learning_data(student_id, topic_name, days)
            
            # Skip if no data for this topic
            if not learning_logs and not quiz_results:
                continue
            
            # Analyze progress for this topic
            progress_analysis = self.analyze_progress(student_id, topic_name, days)
            
            # Get learning pattern insights
            learning_patterns = self.identify_learning_pattern(student_id, topic_name)
            
            # Calculate stats for this topic
            topic_stats = {
                "study_sessions": len(learning_logs),
                "study_time": sum(log.get("duration", 0) for log in learning_logs),
                "quizzes_taken": len(quiz_results),
                "average_score": progress_analysis.get("average_score", 0),
                "current_difficulty": self.db.get_student_difficulty_level(student_id, topic_name) or 3
            }
            
            # Update overall stats
            overall_stats["total_study_time"] += topic_stats["study_time"]
            overall_stats["quizzes_taken"] += topic_stats["quizzes_taken"]
            if quiz_results:
                overall_stats["total_score"] += sum(result.get("score", 0) for result in quiz_results)
            
            # Add to topic summaries
            topic_summaries[topic_name] = {
                "stats": topic_stats,
                "analysis": progress_analysis.get("analysis", "No analysis available"),
                "patterns": learning_patterns.get("patterns", "No pattern analysis available")
            }
        
        # Calculate overall average score
        if overall_stats["quizzes_taken"] > 0:
            overall_stats["average_score"] = overall_stats["total_score"] / overall_stats["quizzes_taken"]
        
        # Generate an overall summary prompt
        summary_prompt = PromptTemplate(
            input_variables=["student_id", "overall_stats", "topic_summaries"],
            template="""
            Generate a comprehensive progress summary for:
            
            Student ID: {student_id}
            
            Overall statistics:
            - Total study time: {overall_stats}
            
            Topic summaries:
            {topic_summaries}
            
            Provide:
            1. An executive summary of overall progress
            2. Key achievements and milestones
            3. Areas for improvement across topics
            4. Cross-topic patterns and insights
            5. Recommended next steps for continued growth
            
            Your summary should be encouraging, insightful, and actionable.
            """
        )
        
        # Format the topic_summaries for the prompt
        topic_summaries_formatted = ""
        for topic_name, summary in topic_summaries.items():
            topic_summaries_formatted += f"Topic: {topic_name}\n"
            topic_summaries_formatted += f"- Study sessions: {summary['stats']['study_sessions']}\n"
            topic_summaries_formatted += f"- Study time: {summary['stats']['study_time']} minutes\n"
            topic_summaries_formatted += f"- Quizzes taken: {summary['stats']['quizzes_taken']}\n"
            topic_summaries_formatted += f"- Average score: {summary['stats']['average_score']:.1f}%\n"
            topic_summaries_formatted += f"- Current difficulty level: {summary['stats']['current_difficulty']}\n\n"
        
        summary_chain = LLMChain(llm=self.llm, prompt=summary_prompt)
        
        # Generate the overall summary
        response = summary_chain.invoke({
            "student_id": student_id,
            "overall_stats": f"{overall_stats['total_study_time']} minutes, {overall_stats['quizzes_taken']} quizzes, {overall_stats['average_score']:.1f}% average score",
            "topic_summaries": topic_summaries_formatted
        })
        
        # Save the progress summary to the database
        summary_id = self.db.save_progress_summary(
            student_id=student_id,
            time_period=days,
            summary=response['text'],
            topic_summaries=topic_summaries
        )
        
        return {
            "summary_id": summary_id,
            "overall_stats": overall_stats,
            "topic_summaries": topic_summaries,
            "overall_summary": response['text']
        }