from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import json
from datetime import datetime
import os
from openai import OpenAI
import re
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")
client = OpenAI(api_key=api_key)

app = FastAPI(title="Enhanced Mental Health Assessment API")
origins = [
    "http://localhost:3000",  # frontend dev server
    "https://your-production-frontend.com"  # optional
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Or ["*"] for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# CORS middleware


DATABASE_URL = "enhanced_mental_health.db"

def init_db():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER,
            gender TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Questions table for structured questions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_type TEXT NOT NULL,
            question_text TEXT NOT NULL,
            options TEXT, -- JSON string for multiple choice
            scale_min INTEGER,
            scale_max INTEGER,
            is_follow_up BOOLEAN DEFAULT FALSE,
            parent_question_id INTEGER,
            trigger_condition TEXT
        )
    ''')
    
    # Responses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question_id INTEGER,
            response_value TEXT NOT NULL,
            response_text TEXT,
            day_number INTEGER,
            session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (question_id) REFERENCES questions (id)
        )
    ''')
    
    # Analysis results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT,
            conditions TEXT, -- JSON string
            clinicians TEXT, -- JSON string
            overall_score INTEGER,
            risk_level TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Real clinicians database
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clinicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            website TEXT,
            license_number TEXT,
            specializes_in TEXT, -- JSON string of condition codes
            rating REAL DEFAULT 0.0,
            years_experience INTEGER,
            accepts_insurance BOOLEAN DEFAULT TRUE,
            online_sessions BOOLEAN DEFAULT FALSE
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database and populate with structured questions
def populate_questions():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Check if questions already exist
    cursor.execute("SELECT COUNT(*) FROM questions")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    questions_data = [
        # Mood Check
        {
            "question_type": "mood_scale",
            "question_text": "On a scale of 1 to 10, how would you rate your overall mood today?",
            "scale_min": 1,
            "scale_max": 10,
            "is_follow_up": False
        },
        {
            "question_type": "mood_follow_up",
            "question_text": "What do you think contributed to this low mood today?",
            "is_follow_up": True,
            "parent_question_id": 1,
            "trigger_condition": "<5"
        },
        
        # Sleep Quality
        {
            "question_type": "sleep_quality",
            "question_text": "How well did you sleep last night?",
            "options": json.dumps(["Very well", "Okay", "Poorly", "Didn't sleep"]),
            "is_follow_up": False
        },
        
        # Energy Level
        {
            "question_type": "energy_level",
            "question_text": "How would you describe your energy level today?",
            "options": json.dumps(["High", "Moderate", "Low", "Extremely low"]),
            "is_follow_up": False
        },
        
        # Stress Level
        {
            "question_type": "stress_scale",
            "question_text": "What is your stress level right now?",
            "scale_min": 1,
            "scale_max": 10,
            "is_follow_up": False
        },
        {
            "question_type": "stress_causes",
            "question_text": "What is causing you stress today?",
            "is_follow_up": True,
            "parent_question_id": 5,
            "trigger_condition": ">5"
        },
        
        # Thought Patterns
        {
            "question_type": "negative_thoughts",
            "question_text": "Have you experienced any negative or intrusive thoughts today?",
            "options": json.dumps(["Yes", "No"]),
            "is_follow_up": False
        },
        {
            "question_type": "thought_description",
            "question_text": "Would you like to describe what came up?",
            "is_follow_up": True,
            "parent_question_id": 7,
            "trigger_condition": "Yes"
        },
        
        # Social Connection
        {
            "question_type": "social_interaction",
            "question_text": "Did you interact with someone today in a way that felt meaningful or supportive?",
            "options": json.dumps(["Yes", "No", "I avoided interactions"]),
            "is_follow_up": False
        },
        
        # Activity & Motivation
        {
            "question_type": "daily_activity",
            "question_text": "Were you able to do something you intended or enjoyed today?",
            "options": json.dumps(["Yes", "No"]),
            "is_follow_up": False
        },
        {
            "question_type": "activity_description",
            "question_text": "What was it that you accomplished or enjoyed?",
            "is_follow_up": True,
            "parent_question_id": 10,
            "trigger_condition": "Yes"
        },
        {
            "question_type": "activity_barriers",
            "question_text": "What made it difficult to do what you intended?",
            "is_follow_up": True,
            "parent_question_id": 10,
            "trigger_condition": "No"
        },
        
        # Gratitude/Positive Reflection
        {
            "question_type": "gratitude",
            "question_text": "What is one thing you felt grateful for or proud of today?",
            "is_follow_up": False
        },
        
        # Additional descriptive questions
        {
            "question_type": "physical_symptoms",
            "question_text": "Have you noticed any physical symptoms today (headaches, stomach issues, muscle tension, etc.)?",
            "is_follow_up": False
        },
        {
            "question_type": "coping_strategies",
            "question_text": "What strategies did you use today to manage difficult emotions or stress?",
            "is_follow_up": False
        },
        {
            "question_type": "support_system",
            "question_text": "How connected do you feel to your support system (family, friends, community)?",
            "options": json.dumps(["Very connected", "Somewhat connected", "Disconnected", "I don't have a support system"]),
            "is_follow_up": False
        }
    ]
    
    for q in questions_data:
        cursor.execute('''
            INSERT INTO questions (question_type, question_text, options, scale_min, scale_max, 
                                 is_follow_up, parent_question_id, trigger_condition)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            q["question_type"],
            q["question_text"],
            q.get("options"),
            q.get("scale_min"),
            q.get("scale_max"),
            q.get("is_follow_up", False),
            q.get("parent_question_id"),
            q.get("trigger_condition")
        ))
    
    conn.commit()
    conn.close()

# Populate real clinicians database
def populate_clinicians():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Check if clinicians already exist
    cursor.execute("SELECT COUNT(*) FROM clinicians")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return
    
    clinicians_data = [
        {
            "name": "Dr. Sarah Mitchell",
            "specialty": "Clinical Psychology",
            "location": "New York, NY",
            "phone": "212-555-0101",
            "email": "sarah.mitchell@nyctherapy.com",
            "website": "www.drsamitchell.com",
            "license_number": "PSY12345",
            "specializes_in": json.dumps(["F32", "F33", "F41"]),  # Depression, Anxiety
            "rating": 4.8,
            "years_experience": 12,
            "accepts_insurance": True,
            "online_sessions": True
        },
        {
            "name": "Dr. Michael Rodriguez",
            "specialty": "Anxiety Disorders & Trauma",
            "location": "Los Angeles, CA",
            "phone": "310-555-0201",
            "email": "m.rodriguez@latherapy.com",
            "website": "www.anxietyspecialistla.com",
            "license_number": "MFT67890",
            "specializes_in": json.dumps(["F41", "F43", "F40"]),  # Anxiety, PTSD, Phobias
            "rating": 4.9,
            "years_experience": 15,
            "accepts_insurance": True,
            "online_sessions": True
        },
        {
            "name": "Dr. Emily Johnson",
            "specialty": "Depression & Mood Disorders",
            "location": "Chicago, IL",
            "phone": "312-555-0301",
            "email": "emily.johnson@chicagomind.com",
            "website": "www.moodtherapychicago.com",
            "license_number": "LPC98765",
            "specializes_in": json.dumps(["F32", "F31", "F34"]),  # Depression, Bipolar
            "rating": 4.7,
            "years_experience": 10,
            "accepts_insurance": True,
            "online_sessions": False
        },
        {
            "name": "Dr. Robert Chen",
            "specialty": "Cognitive Behavioral Therapy",
            "location": "San Francisco, CA",
            "phone": "415-555-0401",
            "email": "robert.chen@sfcbt.com",
            "website": "www.sfcognitivetherapy.com",
            "license_number": "PSY54321",
            "specializes_in": json.dumps(["F32", "F41", "F42"]),  # Depression, Anxiety, OCD
            "rating": 4.6,
            "years_experience": 8,
            "accepts_insurance": False,
            "online_sessions": True
        },
        {
            "name": "Dr. Lisa Thompson",
            "specialty": "Trauma & PTSD Specialist",
            "location": "Boston, MA",
            "phone": "617-555-0501",
            "email": "lisa.thompson@bostontrauma.com",
            "website": "www.traumahealingboston.com",
            "license_number": "LCSW13579",
            "specializes_in": json.dumps(["F43", "F43.1", "F44"]),  # PTSD, Trauma
            "rating": 4.9,
            "years_experience": 18,
            "accepts_insurance": True,
            "online_sessions": True
        },
        {
            "name": "Dr. Amanda White",
            "specialty": "Eating Disorders & Body Image",
            "location": "Miami, FL",
            "phone": "305-555-0601",
            "email": "amanda.white@miamieating.com",
            "website": "www.eatingdisordermiami.com",
            "license_number": "LMHC24680",
            "specializes_in": json.dumps(["F50", "F50.0", "F50.2"]),  # Eating disorders
            "rating": 4.8,
            "years_experience": 14,
            "accepts_insurance": True,
            "online_sessions": False
        },
        {
            "name": "Dr. James Wilson",
            "specialty": "OCD & Anxiety Disorders",
            "location": "Seattle, WA",
            "phone": "206-555-0701",
            "email": "james.wilson@seattleocd.com",
            "website": "www.ocdseattle.com",
            "license_number": "PSY97531",
            "specializes_in": json.dumps(["F42", "F42.0", "F41"]),  # OCD, Anxiety
            "rating": 4.7,
            "years_experience": 11,
            "accepts_insurance": True,
            "online_sessions": True
        },
        {
            "name": "Dr. Maria Garcia",
            "specialty": "Bilingual Therapy (Spanish/English)",
            "location": "Houston, TX",
            "phone": "713-555-0801",
            "email": "maria.garcia@houstonbilingual.com",
            "website": "www.terapiabilingue.com",
            "license_number": "LPC86420",
            "specializes_in": json.dumps(["F32", "F41", "F43"]),  # Depression, Anxiety, Stress
            "rating": 4.8,
            "years_experience": 9,
            "accepts_insurance": True,
            "online_sessions": True
        }
    ]
    
    for clinician in clinicians_data:
        cursor.execute('''
            INSERT INTO clinicians (name, specialty, location, phone, email, website, 
                                  license_number, specializes_in, rating, years_experience, 
                                  accepts_insurance, online_sessions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            clinician["name"],
            clinician["specialty"],
            clinician["location"],
            clinician["phone"],
            clinician["email"],
            clinician["website"],
            clinician["license_number"],
            clinician["specializes_in"],
            clinician["rating"],
            clinician["years_experience"],
            clinician["accepts_insurance"],
            clinician["online_sessions"]
        ))
    
    conn.commit()
    conn.close()

# Initialize database with data
init_db()
populate_questions()
populate_clinicians()

# Pydantic models
class UserRegister(BaseModel):
    name: str
    email: str
    age: Optional[int] = None
    gender: Optional[str] = None

class ResponseSubmit(BaseModel):
    user_id: int
    question_id: int
    response_value: str
    response_text: Optional[str] = None
    session_id: str

class QuestionResponse(BaseModel):
    id: int
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    scale_min: Optional[int] = None
    scale_max: Optional[int] = None
    is_follow_up: bool = False

# Helper functions
def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def should_show_follow_up(parent_response: str, trigger_condition: str) -> bool:
    """Determine if follow-up question should be shown based on trigger condition"""
    if not trigger_condition:
        return False
    
    if trigger_condition.startswith('<'):
        threshold = int(trigger_condition[1:])
        try:
            return int(parent_response) < threshold
        except ValueError:
            return False
    elif trigger_condition.startswith('>'):
        threshold = int(trigger_condition[1:])
        try:
            return int(parent_response) > threshold
        except ValueError:
            return False
    else:
        return parent_response.strip().lower() == trigger_condition.lower()

def get_questions_for_session(user_id: int, session_id: str) -> List[dict]:
    """Get all questions for a session, including follow-ups based on responses"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all base questions (non-follow-ups)
    cursor.execute("""
        SELECT * FROM questions 
        WHERE is_follow_up = FALSE 
        ORDER BY id
    """)
    base_questions = cursor.fetchall()
    
    # Get user's responses for this session
    cursor.execute("""
        SELECT question_id, response_value 
        FROM responses 
        WHERE user_id = ? AND session_id = ?
    """, (user_id, session_id))
    user_responses = {row[0]: row[1] for row in cursor.fetchall()}
    
    questions_to_show = []
    
    for question in base_questions:
        questions_to_show.append(dict(question))
        
        # Check if this question has follow-ups and if conditions are met
        cursor.execute("""
            SELECT * FROM questions 
            WHERE parent_question_id = ? AND is_follow_up = TRUE
        """, (question['id'],))
        follow_ups = cursor.fetchall()
        
        for follow_up in follow_ups:
            if question['id'] in user_responses:
                parent_response = user_responses[question['id']]
                if should_show_follow_up(parent_response, follow_up['trigger_condition']):
                    questions_to_show.append(dict(follow_up))
    
    conn.close()
    return questions_to_show

def find_matching_clinicians(conditions: List[dict]) -> List[dict]:
    """Find clinicians who specialize in the identified conditions"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    matching_clinicians = []
    condition_codes = [c['code'] for c in conditions]
    
    cursor.execute("SELECT * FROM clinicians ORDER BY rating DESC")
    all_clinicians = cursor.fetchall()
    
    for clinician in all_clinicians:
        specializes_in = json.loads(clinician['specializes_in'])
        # Check if any of the clinician's specializations match our conditions
        if any(code in specializes_in or code.split('.')[0] in specializes_in for code in condition_codes):
            clinician_dict = dict(clinician)
            clinician_dict['specializes_in'] = specializes_in
            matching_clinicians.append(clinician_dict)
    
    conn.close()
    return matching_clinicians[:5]  # Return top 5 matches

def analyze_responses_with_openai(responses: List[dict]) -> dict:
    """Analyze responses using OpenAI for more accurate assessment"""
    try:
        # Prepare response text for analysis
        response_text = ""
        mood_scores = []
        stress_scores = []
        
        for resp in responses:
            response_text += f"Question: {resp.get('question_text', 'Unknown')}\n"
            response_text += f"Answer: {resp.get('response_value', '')} {resp.get('response_text', '')}\n\n"
            
            # Extract numerical scores for trend analysis
            if resp.get('question_type') == 'mood_scale':
                try:
                    mood_scores.append(int(resp.get('response_value', '5')))
                except ValueError:
                    pass
            elif resp.get('question_type') == 'stress_scale':
                try:
                    stress_scores.append(int(resp.get('response_value', '5')))
                except ValueError:
                    pass
        
        # Calculate average scores
        avg_mood = sum(mood_scores) / len(mood_scores) if mood_scores else 5
        avg_stress = sum(stress_scores) / len(stress_scores) if stress_scores else 5
        
        prompt = f"""Analyze the following mental health assessment responses and provide a structured analysis:

{response_text}

Average mood score: {avg_mood}/10
Average stress level: {avg_stress}/10

Please provide your analysis in this exact JSON format:
{{
    "conditions": [
        {{
            "code": "F32.1",
            "name": "Major Depressive Episode, Moderate",
            "probability": 75,
            "reasoning": "Based on low mood scores and sleep disturbances"
        }}
    ],
    "overall_assessment": "Brief summary of mental health status",
    "risk_level": "Low/Moderate/High",
    "recommendations": ["Specific recommendation 1", "Recommendation 2"],
    "overall_score": 65
}}

Consider these ICD-10 codes:
- F32.x (Depressive Episodes)
- F41.x (Anxiety Disorders)
- F43.x (Stress-related Disorders)
- F40.x (Phobic Disorders)
- F42.x (OCD)
- F50.x (Eating Disorders)

Be conservative with probability scores and focus on actionable insights."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3
        )
        
        # Parse JSON response
        result_text = response.choices[0].message.content.strip()
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        
        if json_match:
            return json.loads(json_match.group())
        else:
            raise ValueError("Could not parse JSON from OpenAI response")
            
    except Exception as e:
        print(f"OpenAI analysis error: {e}")
        return fallback_analysis(responses)

def fallback_analysis(responses: List[dict]) -> dict:
    """Fallback analysis when OpenAI is unavailable"""
    conditions = []
    
    # Simple rule-based analysis
    low_mood_count = 0
    high_stress_count = 0
    negative_thoughts = False
    sleep_issues = False
    
    for resp in responses:
        if resp.get('question_type') == 'mood_scale':
            try:
                if int(resp.get('response_value', '5')) <= 4:
                    low_mood_count += 1
            except ValueError:
                pass
        elif resp.get('question_type') == 'stress_scale':
            try:
                if int(resp.get('response_value', '5')) >= 7:
                    high_stress_count += 1
            except ValueError:
                pass
        elif resp.get('question_type') == 'negative_thoughts':
            if resp.get('response_value', '').lower() == 'yes':
                negative_thoughts = True
        elif resp.get('question_type') == 'sleep_quality':
            if resp.get('response_value', '') in ['Poorly', "Didn't sleep"]:
                sleep_issues = True
    
    if low_mood_count > 0 or sleep_issues:
        conditions.append({
            "code": "F32.1",
            "name": "Major Depressive Episode, Moderate",
            "probability": min(30 + (low_mood_count * 20), 80),
            "reasoning": "Indicators of low mood and potential sleep disturbances"
        })
    
    if high_stress_count > 0 or negative_thoughts:
        conditions.append({
            "code": "F41.1",
            "name": "Generalized Anxiety Disorder",
            "probability": min(25 + (high_stress_count * 15), 70),
            "reasoning": "High stress levels and negative thought patterns detected"
        })
    
    overall_score = max(10, 100 - (low_mood_count * 15) - (high_stress_count * 10) - (20 if negative_thoughts else 0))
    
    return {
        "conditions": conditions,
        "overall_assessment": "Assessment based on response patterns. Professional evaluation recommended.",
        "risk_level": "Low" if overall_score > 70 else "Moderate" if overall_score > 40 else "High",
        "recommendations": [
            "Consider speaking with a mental health professional",
            "Practice daily self-care activities",
            "Maintain regular sleep schedule"
        ],
        "overall_score": overall_score
    }

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Enhanced Mental Health Assessment API is running"}

@app.post("/register_user")
async def register_user(user: UserRegister):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Insert into users table
        cursor.execute(
            "INSERT INTO users (name, email, age, gender) VALUES (?, ?, ?, ?)",
            (user.name, user.email, user.age, user.gender)
        )
        user_id = cursor.lastrowid

        # Generate session_id
        session_id = str(user_id.uuid4())

        # Insert into sessions table
        cursor.execute(
            "INSERT INTO sessions (session_id, user_id) VALUES (?, ?)",
            (session_id, user_id)
        )

        conn.commit()
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "message": "User registered and session started successfully"
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email already exists")
    finally:
        conn.close()

@app.get("/get_questions/{user_id}/{session_id}")
async def get_questions(user_id: int, session_id: str):
    """Get all questions for a user session, including dynamic follow-ups"""
    questions = get_questions_for_session(user_id, session_id)
    
    # Convert to response format
    formatted_questions = []
    for q in questions:
        question_data = {
            "id": q["id"],
            "question_type": q["question_type"],
            "question_text": q["question_text"],
            "is_follow_up": q["is_follow_up"]
        }
        
        if q["options"]:
            question_data["options"] = json.loads(q["options"])
        if q["scale_min"] and q["scale_max"]:
            question_data["scale_min"] = q["scale_min"]
            question_data["scale_max"] = q["scale_max"]
            
        formatted_questions.append(question_data)
    
    return {"questions": formatted_questions}

@app.post("/submit_response")
async def submit_response(response_data: ResponseSubmit):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO responses (user_id, question_id, response_value, response_text, session_id)
            VALUES (?, ?, ?, ?, ?)
        """, (
            response_data.user_id,
            response_data.question_id,
            response_data.response_value,
            response_data.response_text,
            response_data.session_id
        ))
        conn.commit()
        return {"message": "Response submitted successfully"}
    finally:
        conn.close()

@app.get("/analyze_session/{user_id}/{session_id}")
async def analyze_session(user_id: int, session_id: str):
    """Analyze all responses for a session and provide recommendations"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get all responses with question details
        cursor.execute("""
            SELECT r.*, q.question_type, q.question_text
            FROM responses r
            JOIN questions q ON r.question_id = q.id
            WHERE r.user_id = ? AND r.session_id = ?
        """, (user_id, session_id))
        
        responses = [dict(row) for row in cursor.fetchall()]
        
        if not responses:
            raise HTTPException(status_code=404, detail="No responses found for this session")
        
        # Perform analysis
        analysis = analyze_responses_with_openai(responses)
        
        # Find matching clinicians
        conditions = analysis.get('conditions', [])
        clinicians = find_matching_clinicians(conditions)
        
        # Save analysis results
        cursor.execute("""
            INSERT INTO analysis_results (user_id, session_id, conditions, clinicians, 
                                        overall_score, risk_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            session_id,
            json.dumps(analysis),
            json.dumps(clinicians),
            analysis.get('overall_score', 50),
            analysis.get('risk_level', 'Moderate')
        ))
        conn.commit()
        
        return {
            "analysis": analysis,
            "clinicians": clinicians,
            "session_id": session_id,
            "total_responses": len(responses)
        }
        
    finally:
        conn.close()

@app.get("/get_session_responses/{user_id}/{session_id}")
async def get_session_responses(user_id: int, session_id: str):
    """Get all responses for a specific session"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, q.question_text, q.question_type
            FROM responses r
            JOIN questions q ON r.question_id = q.id
            WHERE r.user_id = ? AND r.session_id = ?
            ORDER BY r.created_at
        """, (user_id, session_id))
        
        responses = [dict(row) for row in cursor.fetchall()]
        return {"responses": responses}
    finally:
        conn.close()

@app.get("/get_clinicians")
async def get_all_clinicians():
    """Get all clinicians in the database"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clinicians ORDER BY rating DESC")
        clinicians = [dict(row) for row in cursor.fetchall()]
        
        # Parse specializes_in JSON for each clinician
        for clinician in clinicians:
            clinician['specializes_in'] = json.loads(clinician['specializes_in'])
        
        return {"clinicians": clinicians}
    finally:
        conn.close()
@app.get("/get_disease_code")
async def get_disease_code():
    """Return a list of ICD-10 mental health condition codes and their descriptions"""
    disease_codes = [
        {"code": "F32", "name": "Depressive Episode"},
        {"code": "F32.1", "name": "Major Depressive Episode, Moderate"},
        {"code": "F33", "name": "Recurrent Depressive Disorder"},
        {"code": "F34", "name": "Persistent Mood Disorders"},
        {"code": "F41", "name": "Anxiety Disorders"},
        {"code": "F41.1", "name": "Generalized Anxiety Disorder"},
        {"code": "F40", "name": "Phobic Anxiety Disorders"},
        {"code": "F42", "name": "Obsessive-Compulsive Disorder"},
        {"code": "F42.0", "name": "Predominantly Obsessional Thoughts or Ruminations"},
        {"code": "F43", "name": "Reaction to Severe Stress and Adjustment Disorders"},
        {"code": "F43.1", "name": "Post-Traumatic Stress Disorder (PTSD)"},
        {"code": "F44", "name": "Dissociative [Conversion] Disorders"},
        {"code": "F50", "name": "Eating Disorders"},
        {"code": "F50.0", "name": "Anorexia Nervosa"},
        {"code": "F50.2", "name": "Bulimia Nervosa"},
    ]
    return {"disease_codes": disease_codes}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
