import streamlit as st
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

# Configure the page
st.set_page_config(
    page_title="Enhanced Mental Health Assessment",
    page_icon="🧠",
    layout="wide"
)

# FastAPI backend URL
API_BASE_URL = "https://healthcare-demo-q5ce.onrender.com"

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'current_session_id' not in st.session_state:
    st.session_state.current_session_id = None
if 'current_questions' not in st.session_state:
    st.session_state.current_questions = []
if 'current_question_index' not in st.session_state:
    st.session_state.current_question_index = 0
if 'session_responses' not in st.session_state:
    st.session_state.session_responses = {}
if 'assessment_complete' not in st.session_state:
    st.session_state.assessment_complete = False

def register_user(name, email, age, gender):
    """Register a new user"""
    try:
        response = requests.post(f"{API_BASE_URL}/register_user", json={
            "name": name,
            "email": email,
            "age": age,
            "gender": gender
        })
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Registration failed: {response.json().get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        st.error(f"Error registering user: {str(e)}")
        return None

def get_questions_for_session(user_id, session_id):
    """Get questions for the current session"""
    try:
        response = requests.get(f"{API_BASE_URL}/get_questions/{user_id}/{session_id}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error getting questions: {response.json().get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        st.error(f"Error getting questions: {str(e)}")
        return None

def submit_response(user_id, question_id, response_value, response_text, session_id):
    """Submit a response"""
    try:
        response = requests.post(f"{API_BASE_URL}/submit_response", json={
            "user_id": user_id,
            "question_id": question_id,
            "response_value": response_value,
            "response_text": response_text,
            "session_id": session_id
        })
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error submitting response: {response.json().get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        st.error(f"Error submitting response: {str(e)}")
        return None

def analyze_session(user_id, session_id):
    """Analyze session responses"""
    try:
        response = requests.get(f"{API_BASE_URL}/analyze_session/{user_id}/{session_id}")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error analyzing session: {response.json().get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        st.error(f"Error analyzing session: {str(e)}")
        return None

def get_session_responses(user_id, session_id):
    """Get session responses"""
    try:
        response = requests.get(f"{API_BASE_URL}/get_session_responses/{user_id}/{session_id}")
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Error getting responses: {str(e)}")
        return None

def start_new_session():
    """Start a new assessment session"""
    session_id = str(uuid.uuid4())
    st.session_state.current_session_id = session_id
    st.session_state.current_question_index = 0
    st.session_state.session_responses = {}
    st.session_state.assessment_complete = False
    
    # Get questions for this session
    questions_data = get_questions_for_session(st.session_state.user_id, session_id)
    if questions_data:
        st.session_state.current_questions = questions_data['questions']
        st.success("New assessment session started!")
        st.rerun()

def render_question(question):
    """Render a single question based on its type"""
    question_id = question['id']
    question_text = question['question_text']
    question_type = question['question_type']
    
    st.write(f"**{question_text}**")
    
    response_value = None
    response_text = None
    
    # Handle different question types
    if 'scale_min' in question and 'scale_max' in question:
        # Scale questions (1-10)
        response_value = st.slider(
            "Your rating:",
            min_value=question['scale_min'],
            max_value=question['scale_max'],
            value=5,
            key=f"question_{question_id}"
        )
        response_value = str(response_value)
        
    elif 'options' in question and question['options']:
        # Multiple choice questions
        options = question['options']
        response_value = st.radio(
            "Select your answer:",
            options,
            key=f"question_{question_id}"
        )
        
    else:
        # Text input questions
        response_text = st.text_area(
            "Your answer:",
            placeholder="Please share your thoughts...",
            height=100,
            key=f"question_{question_id}"
        )
        response_value = "text_response"
    
    return response_value, response_text

def display_assessment_progress():
    """Display progress bar for assessment"""
    if st.session_state.current_questions:
        progress = (st.session_state.current_question_index) / len(st.session_state.current_questions)
        st.progress(progress)
        st.write(f"Question {st.session_state.current_question_index + 1} of {len(st.session_state.current_questions)}")

def main():
    st.title("🧠 Enhanced Mental Health Assessment")
    st.write("A comprehensive mental health assessment with personalized clinician recommendations")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    if st.session_state.user_id:
        page = st.sidebar.selectbox("Choose a page", 
                                   ["Daily Assessment", "My Sessions", "Assessment Results", "Find Clinicians", "Logout"])
    else:
        page = "Register/Login"
    
    # Register/Login Page
    if page == "Register/Login" or not st.session_state.user_id:
        st.header("User Registration")
        st.write("Please register to start your mental health assessment journey.")
        
        with st.form("register_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Full Name *", placeholder="Enter your full name")
                email = st.text_input("Email *", placeholder="Enter your email")
            
            with col2:
                age = st.number_input("Age", min_value=13, max_value=100, value=25)
                gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
            
            submitted = st.form_submit_button("Register & Start Assessment", type="primary")
            
            if submitted:
                if name and email:
                    result = register_user(name, email, age, gender)
                    if result and 'user_id' in result:
                        st.session_state.user_id = result['user_id']
                        st.success(f"Welcome {name}! Registration successful.")
                        st.rerun()
                    else:
                        st.error("Registration failed. Email might already exist.")
                else:
                    st.error("Please fill in all required fields.")
    
    # Daily Assessment Page
    elif page == "Daily Assessment":
        st.header("Daily Mental Health Assessment")
        
        # Check if there's an active session
        if not st.session_state.current_session_id or st.session_state.assessment_complete:
            st.write("Ready to start a new mental health check-in?")
            st.info("This assessment includes questions about your mood, sleep, stress levels, and overall wellbeing. It takes about 5-10 minutes to complete.")
            
            if st.button("🚀 Start New Assessment", type="primary", use_container_width=True):
                start_new_session()
        
        else:
            # Continue current session
            if st.session_state.current_questions:
                display_assessment_progress()
                st.write("---")
                
                # Get current question
                if st.session_state.current_question_index < len(st.session_state.current_questions):
                    current_question = st.session_state.current_questions[st.session_state.current_question_index]
                    
                    # Display question type info
                    if current_question.get('is_follow_up'):
                        st.info("📋 Follow-up Question")
                    else:
                        question_types = {
                            'mood_scale': '😊 Mood Check',
                            'sleep_quality': '😴 Sleep Quality',
                            'energy_level': '⚡ Energy Level',
                            'stress_scale': '😰 Stress Level',
                            'negative_thoughts': '💭 Thought Patterns',
                            'social_interaction': '👥 Social Connection',
                            'daily_activity': '🎯 Activity & Motivation',
                            'gratitude': '🙏 Gratitude & Reflection'
                        }
                        question_category = question_types.get(current_question['question_type'], '📝 Assessment')
                        st.info(f"{question_category}")
                    
                    with st.form(f"question_form_{current_question['id']}"):
                        response_value, response_text = render_question(current_question)
                        
                        col1, col2, col3 = st.columns([1, 1, 1])
                        
                        with col1:
                            if st.session_state.current_question_index > 0:
                                prev_clicked = st.form_submit_button("⬅️ Previous")
                            else:
                                prev_clicked = False
                        
                        with col2:
                            skip_clicked = st.form_submit_button("⏭️ Skip (Optional)")
                        
                        with col3:
                            next_clicked = st.form_submit_button("Next ➡️", type="primary")
                        
                        # Handle form submissions
                        if prev_clicked and st.session_state.current_question_index > 0:
                            st.session_state.current_question_index -= 1
                            st.rerun()
                        
                        elif skip_clicked:
                            # Mark as skipped and move to next question
                            st.session_state.current_question_index += 1
                            # Refresh questions to check for new follow-ups
                            questions_data = get_questions_for_session(st.session_state.user_id, st.session_state.current_session_id)
                            if questions_data:
                                st.session_state.current_questions = questions_data['questions']
                            st.rerun()
                        
                        elif next_clicked:
                            # Validate response
                            valid_response = False
                            if response_value and response_value != "text_response":
                                valid_response = True
                            elif response_text and response_text.strip():
                                valid_response = True
                            
                            if valid_response:
                                # Submit response
                                result = submit_response(
                                    st.session_state.user_id,
                                    current_question['id'],
                                    response_value or "",
                                    response_text or "",
                                    st.session_state.current_session_id
                                )
                                
                                if result:
                                    st.session_state.current_question_index += 1
                                    # Refresh questions to check for new follow-ups
                                    questions_data = get_questions_for_session(st.session_state.user_id, st.session_state.current_session_id)
                                    if questions_data:
                                        st.session_state.current_questions = questions_data['questions']
                                    st.rerun()
                            else:
                                st.error("Please provide an answer before proceeding.")
                
                else:
                    # Assessment complete
                    st.success("🎉 Assessment Complete!")
                    st.write("Thank you for completing your mental health check-in.")
                    st.session_state.assessment_complete = True
                    
                    if st.button("📊 View Analysis Results", type="primary", use_container_width=True):
                        st.session_state.page = "Assessment Results"
                        st.rerun()
    
    # My Sessions Page
    elif page == "My Sessions":
        st.header("My Assessment Sessions")
        
        if st.session_state.current_session_id:
            responses_data = get_session_responses(st.session_state.user_id, st.session_state.current_session_id)
            
            if responses_data and responses_data['responses']:
                st.subheader("Current Session Responses")
                
                for response in responses_data['responses']:
                    with st.expander(f"{response['question_type'].replace('_', ' ').title()} - {response['created_at'][:16]}"):
                        st.write(f"**Question:** {response['question_text']}")
                        if response['response_value'] and response['response_value'] != 'text_response':
                            st.write(f"**Answer:** {response['response_value']}")
                        if response['response_text']:
                            st.write(f"**Details:** {response['response_text']}")
            else:
                st.info("No responses found for the current session.")
        else:
            st.info("No active assessment session. Please start a new assessment.")
    
    # Assessment Results Page
    elif page == "Assessment Results":
        st.header("Assessment Results & Analysis")
        
        if not st.session_state.current_session_id:
            st.warning("No active session found. Please complete an assessment first.")
            return
        
        if st.button("🔍 Analyze My Responses", type="primary", use_container_width=True):
            with st.spinner("Analyzing your responses with AI..."):
                analysis_result = analyze_session(st.session_state.user_id, st.session_state.current_session_id)
                
                if analysis_result:
                    st.success("Analysis completed!")
                    
                    analysis = analysis_result.get('analysis', {})
                    
                    # Overall Assessment
                    col1, col2 = st.columns(2)
                    with col1:
                        overall_score = analysis.get('overall_score', 50)
                        st.metric("Overall Wellbeing Score", f"{overall_score}/100")
                        
                        # Score interpretation
                        if overall_score >= 80:
                            st.success("Excellent mental health indicators")
                        elif overall_score >= 60:
                            st.info("Good overall mental health")
                        elif overall_score >= 40:
                            st.warning("Some areas may need attention")
                        else:
                            st.error("Consider seeking professional support")
                    
                    with col2:
                        risk_level = analysis.get('risk_level', 'Moderate')
                        st.metric("Risk Level", risk_level)
                        
                        risk_colors = {
                            'Low': 'success',
                            'Moderate': 'warning',
                            'High': 'error'
                        }
                        if risk_level in risk_colors:
                            getattr(st, risk_colors[risk_level])(f"Current risk level: {risk_level}")
                    
                    st.write("---")
                    
                    # Overall Assessment Text
                    if analysis.get('overall_assessment'):
                        st.subheader("Professional Assessment Summary")
                        st.info(analysis['overall_assessment'])
                    
                    # Conditions Identified
                    conditions = analysis.get('conditions', [])
                    if conditions:
                        st.subheader("Areas of Focus Identified")
                        
                        for condition in conditions:
                            with st.container():
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"**{condition['name']}** ({condition['code']})")
                                    if condition.get('reasoning'):
                                        st.caption(condition['reasoning'])
                                with col2:
                                    probability = condition.get('probability', 0)
                                    st.write(f"Confidence: {probability}%")
                                    st.progress(probability / 100)
                                st.write("---")
                    
                    # Recommendations
                    recommendations = analysis.get('recommendations', [])
                    if recommendations:
                        st.subheader("Personalized Recommendations")
                        for i, rec in enumerate(recommendations, 1):
                            st.write(f"{i}. {rec}")
                        st.write("---")
                    
                    # Recommended Clinicians
                    clinicians = analysis_result.get('clinicians', [])
                    if clinicians:
                        st.subheader("Recommended Mental Health Professionals")
                        st.write("Based on your assessment, here are qualified professionals who specialize in your areas of need:")
                        
                        for clinician in clinicians[:5]:  # Show top 5
                            with st.expander(f" {clinician['name']} - {clinician['specialty']}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write(f"**Specialty:** {clinician['specialty']}")
                                    st.write(f"**Location:** {clinician['location']}")
                                    st.write(f"**Experience:** {clinician['years_experience']} years")
                                    if clinician.get('rating'):
                                        st.write(f"**Rating:** {clinician['rating']}/5.0 ⭐")
                                
                                with col2:
                                    st.write(f"**Phone:** {clinician['phone']}")
                                    if clinician.get('email'):
                                        st.write(f"**Email:** {clinician['email']}")
                                    if clinician.get('website'):
                                        st.write(f"**Website:** {clinician['website']}")
                                    
                                    # Features
                                    features = []
                                    if clinician.get('accepts_insurance'):
                                        features.append("✅ Insurance Accepted")
                                    if clinician.get('online_sessions'):
                                        features.append("💻 Online Sessions")
                                    if features:
                                        st.write("**Features:** " + " | ".join(features))
                    
                    # Disclaimer
                    st.write("---")
                    st.warning("**Important Disclaimer:** This assessment is for informational purposes only and should not replace professional medical advice. Please consult with qualified healthcare professionals for proper diagnosis and treatment.")
                    
                    # Analysis metadata
                    st.caption(f"Analysis completed: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Session ID: {st.session_state.current_session_id[:8]}...")
    
    # Find Clinicians Page
    elif page == "Find Clinicians":
        st.header("Find Mental Health Professionals")
        
        try:
            response = requests.get(f"{API_BASE_URL}/get_clinicians")
            if response.status_code == 200:
                all_clinicians = response.json()['clinicians']
                
                # Filters
                st.subheader("Filter Clinicians")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    specialty_filter = st.selectbox(
                        "Specialty",
                        ["All"] + list(set([c['specialty'] for c in all_clinicians]))
                    )
                
                with col2:
                    location_filter = st.selectbox(
                        "Location",
                        ["All"] + list(set([c['location'] for c in all_clinicians]))
                    )
                
                with col3:
                    online_only = st.checkbox("Online Sessions Only")
                
                # Filter clinicians
                filtered_clinicians = all_clinicians
                if specialty_filter != "All":
                    filtered_clinicians = [c for c in filtered_clinicians if c['specialty'] == specialty_filter]
                if location_filter != "All":
                    filtered_clinicians = [c for c in filtered_clinicians if c['location'] == location_filter]
                if online_only:
                    filtered_clinicians = [c for c in filtered_clinicians if c['online_sessions']]
                
                st.write(f"Found {len(filtered_clinicians)} clinicians")
                
                # Display clinicians
                for clinician in filtered_clinicians:
                    with st.container():
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**{clinician['name']}**")
                            st.write(f"*{clinician['specialty']}*")
                            st.write(f"📍 {clinician['location']}")
                            st.write(f"⭐ {clinician['rating']}/5.0 | {clinician['years_experience']} years experience")
                        
                        with col2:
                            st.write(f"📞 {clinician['phone']}")
                            if clinician.get('email'):
                                st.write(f"✉️ {clinician['email']}")
                            if clinician.get('website'):
                                st.write(f"🌐 {clinician['website']}")
                            
                            features = []
                            if clinician['accepts_insurance']:
                                features.append("💳 Insurance")
                            if clinician['online_sessions']:
                                features.append("💻 Online")
                            if features:
                                st.write(" | ".join(features))
                        
                        st.write("---")
            
        except Exception as e:
            st.error(f"Error loading clinicians: {str(e)}")
    
    # Logout
    elif page == "Logout":
        st.session_state.user_id = None
        st.session_state.current_session_id = None
        st.session_state.current_questions = []
        st.session_state.current_question_index = 0
        st.session_state.session_responses = {}
        st.session_state.assessment_complete = False
        st.success("Logged out successfully!")
        st.rerun()

if __name__ == "__main__":
    main()
