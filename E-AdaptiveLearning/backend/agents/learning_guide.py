import os
from typing import Dict, Any, List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from database.db_handler import DatabaseHandler

class LearningGuideAgent:
    """
    Learning Guide Agent is responsible for generating personalized learning content
    and study materials based on the student's progress and learning goals.
    """
    
    def __init__(self, api_key: str = None, model: str = "gemini-1.5-flash"):
        """
        Initialize the Learning Guide Agent.
        
        Args:
            api_key (str): Google API key
            model (str): LLM model to use
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(temperature=0.5, model=model, google_api_key=self.api_key)
        self.db = DatabaseHandler()
        
        # Create the learning content prompt template
        self.content_prompt = PromptTemplate(
            input_variables=["student_id", "topic", "subtopic", "difficulty_level", "learning_style", "previous_knowledge"],
            template="""
            You are an expert Learning Guide specializing in creating personalized educational content.
            
            Student ID: {student_id}
            Topic: {topic}
            Subtopic: {subtopic}
            Current difficulty level: {difficulty_level} (1-5 scale)
            Learning style preference: {learning_style}
            Previous knowledge: {previous_knowledge}
            
            Create a comprehensive learning module for this student that:
            
            1. Starts with a brief introduction to the subtopic
            2. Explains key concepts with clear definitions
            3. Provides illustrative examples that match their learning style
            4. Includes analogies that connect to their previous knowledge
            5. Contains step-by-step explanations where appropriate
            6. Highlights important points and common misconceptions
            7. Concludes with a summary of key takeaways
            
            The content should be engaging, educational, and tailored to the student's 
            difficulty level and learning style.
            """
        )
        
        self.content_chain = LLMChain(llm=self.llm, prompt=self.content_prompt)
        
    def get_student_profile(self, student_id: str) -> Dict[str, Any]:
        """
        Retrieve the student's learning profile.
        
        Args:
            student_id (str): Unique identifier for the student
            
        Returns:
            Dict: Student's learning profile including preferences and history
        """
        # Get student profile from database
        profile = self.db.get_student_profile(student_id)
        
        if not profile:
            # Create a default profile if none exists
            profile = {
                "learning_style": "balanced",
                "difficulty_preferences": {},
                "interests": []
            }
            self.db.create_student_profile(student_id, profile)
        
        return profile
    
    def analyze_previous_knowledge(self, student_id: str, topic: str) -> Dict[str, Any]:
        """
        Analyze student's previous knowledge on the topic.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The topic to analyze
            
        Returns:
            Dict: Analysis of previous knowledge
        """
        # Get learning logs and quiz results
        learning_logs = self.db.get_learning_logs(student_id, topic, limit=20)
        quiz_results = self.db.get_quiz_results(student_id, topic, limit=20)
        
        # Analyze mastered concepts, gaps, and strengths
        subtopics_covered = set()
        mastered_concepts = []
        knowledge_gaps = []
        
        for log in learning_logs:
            subtopics_covered.add(log["subtopic"])
        
        for result in quiz_results:
            if result["score"] >= 80:
                mastered_concepts.extend(result["concepts"])
            elif result["score"] < 60:
                knowledge_gaps.extend(result["concepts"])
        
        # Remove duplicates
        mastered_concepts = list(set(mastered_concepts))
        knowledge_gaps = list(set(knowledge_gaps))
        
        return {
            "subtopics_covered": list(subtopics_covered),
            "mastered_concepts": mastered_concepts,
            "knowledge_gaps": knowledge_gaps
        }
    
    def generate_learning_content(self, student_id: str, topic: str, subtopic: str) -> str:
        """
        Generate personalized learning content for a specific subtopic.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic (e.g., "Mathematics")
            subtopic (str): The specific subtopic (e.g., "Quadratic Equations")
            
        Returns:
            str: Personalized learning content
        """
        # Get student profile
        profile = self.get_student_profile(student_id)
        learning_style = profile.get("learning_style", "balanced")
        
        # Get student's current difficulty level for this topic
        difficulty_level = self.db.get_student_difficulty_level(student_id, topic) or 3
        
        # Analyze previous knowledge
        previous_knowledge = self.analyze_previous_knowledge(student_id, topic)
        
        # Format previous knowledge for the prompt
        previous_knowledge_formatted = f"""
        Subtopics already covered: {', '.join(previous_knowledge['subtopics_covered']) if previous_knowledge['subtopics_covered'] else 'None yet'}
        Mastered concepts: {', '.join(previous_knowledge['mastered_concepts']) if previous_knowledge['mastered_concepts'] else 'None yet'}
        Knowledge gaps: {', '.join(previous_knowledge['knowledge_gaps']) if previous_knowledge['knowledge_gaps'] else 'None identified yet'}
        """
        
        # Generate the learning content
        response = self.content_chain.invoke({
            "student_id": student_id,
            "topic": topic,
            "subtopic": subtopic,
            "difficulty_level": difficulty_level,
            "learning_style": learning_style,
            "previous_knowledge": previous_knowledge_formatted
        })
        
        # Log this learning session
        self.db.log_learning_session(
            student_id=student_id,
            topic=topic,
            subtopic=subtopic,
            difficulty_level=difficulty_level,
            content_summary="Generated learning content"
        )
        
        return response['text']
    
    def create_study_plan(self, student_id: str, topic: str, goal: str, timeline: str) -> str:
        """
        Create a personalized study plan based on learning goals and timeline.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic for the study plan
            goal (str): The student's learning goal
            timeline (str): The timeline for completing the goal
            
        Returns:
            str: Personalized study plan
        """
        # Get student profile
        profile = self.get_student_profile(student_id)
        
        # Analyze previous knowledge
        previous_knowledge = self.analyze_previous_knowledge(student_id, topic)
        
        # Create study plan prompt
        study_plan_prompt = PromptTemplate(
            input_variables=["topic", "goal", "timeline", "previous_knowledge", "learning_style"],
            template="""
            Create a comprehensive study plan for a student with the following:
            
            Topic: {topic}
            Learning goal: {goal}
            Timeline: {timeline}
            Learning style: {learning_style}
            
            Previous knowledge:
            {previous_knowledge}
            
            The study plan should:
            1. Break down the goal into achievable milestones
            2. Provide a week-by-week schedule of subtopics to cover
            3. Include recommended learning activities for each subtopic
            4. Suggest practice exercises or projects
            5. Include checkpoints for self-assessment
            6. Address any identified knowledge gaps as priorities
            
            The plan should be realistic, motivating, and tailored to the student's 
            learning style and previous knowledge.
            """
        )
        
        study_plan_chain = LLMChain(llm=self.llm, prompt=study_plan_prompt)
        
        # Format previous knowledge for the prompt
        previous_knowledge_formatted = f"""
        Subtopics already covered: {', '.join(previous_knowledge['subtopics_covered']) if previous_knowledge['subtopics_covered'] else 'None yet'}
        Mastered concepts: {', '.join(previous_knowledge['mastered_concepts']) if previous_knowledge['mastered_concepts'] else 'None yet'}
        Knowledge gaps: {', '.join(previous_knowledge['knowledge_gaps']) if previous_knowledge['knowledge_gaps'] else 'None identified yet'}
        """
        
        # Generate the study plan
        response = study_plan_chain.invoke({
            "topic": topic,
            "goal": goal,
            "timeline": timeline,
            "previous_knowledge": previous_knowledge_formatted,
            "learning_style": profile.get("learning_style", "balanced")
        })
        
        # Save the study plan to the database
        self.db.save_study_plan(
            student_id=student_id,
            topic=topic,
            goal=goal,
            timeline=timeline,
            plan_content=response['text']
        )
        
        return response['text']
    
    def recommend_resources(self, student_id: str, topic: str, subtopic: str) -> List[Dict[str, str]]:
        """
        Recommend additional learning resources based on student's profile.
        
        Args:
            student_id (str): Unique identifier for the student
            topic (str): The main topic
            subtopic (str): The specific subtopic
            
        Returns:
            List[Dict]: List of recommended resources
        """
        # Get student profile
        profile = self.get_student_profile(student_id)
        learning_style = profile.get("learning_style", "balanced")
        
        # Get student's current difficulty level
        difficulty_level = self.db.get_student_difficulty_level(student_id, topic) or 3
        
        # Create resources prompt
        resources_prompt = PromptTemplate(
            input_variables=["topic", "subtopic", "learning_style", "difficulty_level"],
            template="""
            Recommend learning resources for a student studying:
            
            Topic: {topic}
            Subtopic: {subtopic}
            Learning style preference: {learning_style}
            Difficulty level: {difficulty_level} (1-5 scale)
            
            Provide 5 diverse resources including:
            - Online articles or tutorials
            - Video content
            - Interactive exercises
            - Books or textbook sections
            - Practice problems
            
            For each resource, include:
            1. Title
            2. Type (article, video, etc.)
            3. Brief description (1-2 sentences)
            4. Why it's appropriate for this student's learning style and level
            
            Format your response as a structured list with clear headings.
            """
        )
        
        resources_chain = LLMChain(llm=self.llm, prompt=resources_prompt)
        
        # Generate resource recommendations
        response = resources_chain.invoke({
            "topic": topic,
            "subtopic": subtopic,
            "learning_style": learning_style,
            "difficulty_level": difficulty_level
        })
        
        # Process the response to extract structured resource recommendations
        # In a real implementation, you might want to parse the response more robustly
        # For now, we'll just return the formatted text
        
        # Log the recommendations
        self.db.log_resource_recommendations(
            student_id=student_id,
            topic=topic,
            subtopic=subtopic,
            recommendations=response['text']
        )
        
        return response['text']