# E-AdaptiveLearning Platform

E-AdaptiveLearning is an intelligent, adaptive learning platform that personalizes educational content and assessments based on individual student progress and learning patterns. The system leverages AI to create a tailored learning experience for each student.

## 🚀 Features

- **Personalized Learning Content**: Dynamically generates educational materials tailored to each student's learning style, difficulty level, and previous knowledge
- **Adaptive Quiz System**: Creates assessments that adjust difficulty based on student performance
- **Progress Tracking**: Monitors student progress and provides detailed analytics and insights
- **AI Tutoring**: Offers personalized explanations and assistance for student questions
- **Study Planning**: Creates customized study plans with achievable milestones
- **Resource Recommendations**: Suggests additional learning materials based on student needs

## 🏗️ System Architecture

The system is built using a modular agent-based architecture with the following components:

### Core Agents

1. **AI Tutor Agent**: Answers student questions with personalized explanations
2. **Learning Guide Agent**: Generates tailored learning content and study plans
3. **Quiz Master Agent**: Creates and evaluates adaptive quizzes
4. **Progress Tracker Agent**: Analyzes student performance and provides insights

### Technical Components

- **Flask API**: RESTful backend for handling requests
- **MongoDB**: Database for storing student profiles, learning history, and content
- **LangGraph**: Orchestrates workflows between different AI agents
- **Gemini AI**: Powers the intelligent capabilities of the agents

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.9+
- MongoDB
- Google API key for Gemini AI

### Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/e-adaptivelearning.git
   cd e-adaptivelearning
   ```

2. Create and activate a virtual environment
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with the following variables:
   ```
   FLASK_SECRET_KEY=your_secret_key
   GOOGLE_API_KEY=your_google_api_key
   MONGODB_URI=mongodb://localhost:27017/
   MONGODB_DB=e_adaptive_learning
   FLASK_DEBUG=False
   ```

5. Initialize the database
   ```bash
   python scripts/init_db.py
   ```

### Running the Application

1. Start the server
   ```bash
   python flask_api.py
   ```

2. Access the application at http://localhost:5000

## 📋 API Endpoints

The platform provides the following API endpoints:

| Endpoint | Method | Description |
|---------|--------|-------------|
| `/api/session` | POST | Create a new learning session |
| `/api/message` | POST | Process a user message |
| `/api/quiz/generate` | POST | Generate a quiz |
| `/api/quiz/evaluate` | POST | Evaluate a quiz answer |
| `/api/quiz/result` | GET | Get quiz results |
| `/api/progress` | GET | Get student progress |
| `/api/content` | GET | Get learning content |
| `/api/study-plan` | POST | Create a study plan |
| `/api/resources` | GET | Get recommended resources |
| `/api/learning-patterns` | GET | Get learning pattern analysis |
| `/api/difficulty-recommendation` | GET | Get difficulty adjustment recommendation |
| `/api/hint` | GET | Get a hint for a quiz question |
| `/api/misconception` | POST | Explain a misconception |
| `/api/session/end` | POST | End a learning session |

## 🗂️ Project Structure

```
e-adaptivelearning/
├── agents/                     # AI agent modules
│   ├── ai_tutor.py             # Handles student questions
│   ├── learning_guide.py       # Generates learning content
│   ├── quiz_master.py          # Creates and evaluates quizzes
│   └── progress_tracker.py     # Analyzes student progress
├── database/                   # Database handling
│   ├── connection.py           # MongoDB connection
│   └── db_handler.py           # Database operations
├── frontend/                   # Frontend files
│   ├── static/                 # Static assets (CSS, JS)
│   └── templates/              # HTML templates
├── logs/                       # Application logs
├── scripts/                    # Utility scripts
├── config.py                   # Configuration settings
├── flask_api.py                # Flask application
├── langgraph_workflow.py       # AI workflow orchestration
├── requirements.txt            # Project dependencies
├── state.py                    # State management
└── README.md                   # Project documentation
```

## 🧠 Agent Details

### AI Tutor Agent
Answers student questions with explanations tailored to their learning history, difficulty level, and previously mastered concepts.

### Learning Guide Agent
Generates personalized learning content, study plans, and resource recommendations based on student profiles and learning styles.

### Quiz Master Agent
Creates adaptive quizzes that focus on areas needing improvement, evaluates answers, and provides constructive feedback.

### Progress Tracker Agent
Analyzes learning patterns, monitors progress over time, and recommends difficulty adjustments based on performance.

## 🔄 Workflow

1. Students interact with the platform through text-based messages
2. The system classifies the input to determine the appropriate agent
3. The selected agent processes the request using the student's history and profile
4. Personalized responses are generated and delivered to the student
5. All interactions are tracked to continuously improve the learning experience

## ⚙️ Configuration Options

The system can be configured through environment variables or the `config.py` file. Key configurations include:

- Model settings (temperature, API keys)
- Default difficulty levels
- Database connection parameters
- Feature flags for enabling/disabling specific components
- Rate limiting and timeout settings

## 🔐 Security Considerations

- All student data is stored securely in MongoDB
- API keys should be kept confidential and never committed to the repository
- Session management ensures data isolation between students
- Production deployments should use HTTPS and proper authentication

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions or support, please contact [kamalguddanti@example.com]