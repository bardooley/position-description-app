import streamlit as st
import searchBot
import pandas as pd

# Set page config
st.set_page_config(
    page_title="School Candidate Matcher",
    page_icon="🎓",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    /* Main background and text colors */
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Header styling */
    h1 {
        color: #ffffff;
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
    }
    
    /* Subheader styling */
    h3 {
        color: #ffffff;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
    }
    
    /* Button styling */
    .stButton>button {
        background-color: #4a90e2;
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        background-color: #357abd;
        box-shadow: 0 2px 5px rgba(255,255,255,0.2);
    }
    
    /* Input field styling */
    .stTextInput>div>div>input {
        background-color: #1a1a1a;
        border: 2px solid #333333;
        color: #ffffff;
        border-radius: 5px;
        padding: 0.5rem;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #4a90e2;
        box-shadow: 0 0 0 1px #4a90e2;
    }
    
    /* Card styling */
    .candidate-card {
        background-color: #1a1a1a;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(255,255,255,0.1);
        border-left: 5px solid #4a90e2;
        color: #ffffff;
    }
    
    /* Score badge styling */
    .score-badge {
        background-color: #4a90e2;
        color: #ffffff;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-weight: 600;
        display: inline-block;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        color: #888888;
        font-size: 0.9rem;
        margin-top: 2rem;
        padding: 1rem;
        border-top: 1px solid #333333;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #1a1a1a;
        border-radius: 5px;
        font-weight: 600;
        color: #ffffff;
    }
    
    /* Error message styling */
    .stAlert {
        background-color: #2d1a1a;
        border-left: 5px solid #e53e3e;
        color: #ffffff;
    }
    
    /* Markdown text color */
    .stMarkdown {
        color: #ffffff;
    }
    
    /* Spinner color */
    .stSpinner > div {
        border-color: #4a90e2;
    }
    </style>
    """, unsafe_allow_html=True)

# Title and description
st.title("School Candidate Matcher")
st.markdown("Find the best candidates for your school's open positions using AI-powered matching.")

# Input fields in two columns
col1, col2 = st.columns(2)
with col1:
    school_name = st.text_input("School Name", placeholder="Enter the name of your school")
with col2:
    position = st.text_input("Position", placeholder="Enter the position you're hiring for")

# Search button
if st.button("Find Best Candidates", use_container_width=True):
    if not school_name or not position:
        st.error("Please enter both school name and position")
    else:
        with st.spinner("Finding the best candidates..."):
            try:
                # Get school info
                school_info = searchBot.find_school_info(school_name)
                if not school_info:
                    st.error(f"School '{school_name}' not found in database. Please try another spelling or wording.")
                else:
                    # Get best candidates
                    best_candidates = searchBot.find_best_candidates(school_info, position)
                    
                    # Sort candidates by score
                    best_candidates.sort(key=lambda x: float(x['score']), reverse=True)
                    
                    # Display results
                    st.markdown("### Top 3 Candidates")
                    
                    for candidate in best_candidates:
                        with st.container():
                            st.markdown(f"""
                                <div class="candidate-card">
                                    <h3>{candidate['Candidate Name']}</h3>
                                    <div class="score-badge">Fit Score: {float(candidate['score']):.1f}/10</div>
                                    <p style="margin-top: 1rem;">{candidate['explanation']}</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            with st.expander("View Full Profile"):
                                st.markdown(f"""
                                    **Position Type:** {candidate['Position Type']}  
                                    **Experience:** {candidate['Experience']}  
                                    **Degree(s):** {candidate['Degree(s) Attained']}  
                                    **Languages:** {candidate['Languages']}  
                                    **Professional Association:** {candidate['Professional Association']}  
                                    **Position Level:** {candidate['Position Level']}
                                """)
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

# Footer
st.markdown("""
    <div class="footer">
        Powered by AI • Built with Streamlit
    </div>
""", unsafe_allow_html=True) 