import streamlit as st
import pandas as pd
import openai
import os
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
import re
import PyPDF2

# Set page config
st.set_page_config(page_title="Candidate Search Bot", layout="wide")

# Initialize session state for storing data
if 'candidates_df' not in st.session_state:
    try:
        st.session_state.candidates_df = pd.read_csv('/Users/bradleyharrington/Documents/CS&A/Search/Candidates2000.csv')
    except Exception as e:
        st.error(f"Error loading candidates data: {str(e)}")
        st.session_state.candidates_df = pd.DataFrame()

def parse_pdf_notes(pdf_file):
    try:
        # Read the PDF file
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error parsing PDF: {str(e)}")
        return None

def process_job_description(position_description):
    # Set up OpenAI client
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Generate filters
    filters_prompt = f"""
Your task is to extract hard filters and preferences from notes about the job.
You are extracting structured filters from a job description. Use only the valid options listed below.

Return ONLY a JSON object in this exact format, with no additional text or explanation:

{{
  "required_languages": [],
  "required_position_levels": [],
  "required_citizenships": [],
  "required_ethnicities": [],
  "required_genders": [],
  "required_professional_associations": [],
  "required_religions": [],
  "min_experience_years": null,
}}

For 'required position levels' use this format: 'Senior', 'Mid', 'Entry'. Do not type out the whole name like 'senior level'. 
If citizenship in the United States is a requirement, use this format: 'USA'. 
You are not required to fill in all fields. Only fill in the fields that are absolutely essential to the job.

Here is the job description: {position_description}
"""

    filters_response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that extracts structured filters from job descriptions. Always return valid JSON."},
            {"role": "user", "content": filters_prompt}
        ]
    )

    filters = json.loads(filters_response.choices[0].message.content.strip())
    
    # Print the extracted filters
    st.write("Extracted Filters:")
    st.json(filters)
    
    # Generate job summary for cosine similarity
    summary_prompt = f"""
    Based on this job description, create a concise summary focusing on the key requirements and preferences.
    Format the summary in a way that matches how we describe candidates, using these fields:
    - Position Type
    - Position Level
    - Languages
    - Professional Association
    - Key Requirements

    Keep the summary factual and focused on requirements that would be relevant for candidate matching.
    Do not include general company information or benefits. This job description will be used in comparison with candidate information to calculate cosine similarity scores, and filter those candidates to find the best matches. 

    Job Description:
    {position_description}
    """

    summary_response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates concise, structured summaries of job requirements."},
            {"role": "user", "content": summary_prompt}
        ]
    )

    return filters, summary_response.choices[0].message.content.strip()

def filter_candidates(df, filters):
    # Convert Experience column to numeric
    if df['Experience'].dtype == 'object':
        df['Experience'] = df['Experience'].astype(str).str.extract('(\d+)').astype(float)

    # Apply filters
    for lang in filters["required_languages"]:
        df = df[df["Languages"].str.contains(lang, case=False, na=False)]

    for position_level in filters["required_position_levels"]:
        df = df[df["Position Level"].str.contains(position_level, case=False, na=False)]

    for citizenship in filters["required_citizenships"]:
        df = df[df["Citizenship"].str.contains(citizenship, case=False, na=False)]

    for ethnicity in filters["required_ethnicities"]:
        df = df[df["Ethnicity"].str.contains(ethnicity, case=False, na=False)]

    for gender in filters["required_genders"]:
        df = df[df["Gender"].str.contains(gender, case=False, na=False)]

    for professional_association in filters["required_professional_associations"]:
        df = df[df["Professional Association"].str.contains(professional_association, case=False, na=False)]

    for religion in filters["required_religions"]:
        df = df[df["Religion"].str.contains(religion, case=False, na=False)]

    if filters["min_experience_years"] is not None:
        df = df[df['Experience'] >= filters["min_experience_years"]]

    return df

def calculate_similarities(df, job_summary):
    # Create formatted info for candidates
    df['Formatted Info'] = df.apply(lambda row: f"""Name: {row['Candidate Name']}
    Citizenship: {row['Citizenship']}
    Ethnicity: {row['Ethnicity']}
    Gender: {row['Gender']}
    Languages: {row['Languages']}
    Position Type: {row['Position Type']}
    Position Level: {row['Position Level']}
    Professional Association: {row['Professional Association']}""", axis=1)

    # Initialize the sentence transformer model
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Create embeddings
    job_embedding = model.encode([job_summary])
    candidate_embeddings = model.encode(df['Formatted Info'].tolist())

    # Calculate similarities
    similarities = cosine_similarity(job_embedding, candidate_embeddings)[0]
    df['Similarity Score'] = similarities

    # Sort and keep top 300
    df = df.sort_values('Similarity Score', ascending=False)
    if len(df) > 300:
        df = df.head(300)

    return df

def get_top_matches(df, position_description):
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    prompt = f"""
    Given the following job description:
    {position_description}

    Please analyze the following candidates and return the top 5 BEST fits for the job:
    {df.to_dict('records')}

    For each of the top 5 candidates, provide:
    1. Their full name
    2. A fit score out of 10 (where 10 is perfect fit) - use one decimal place (e.g., 8.5)
    3. A brief 2-sentence explanation of why they would be a good fit for this position

    All candidates should be a great fit for the job. Do not include any candidates that are not a great fit. Always output 5 candidates.

    Format your response as:
    Name1|Score1|explanation1
    Name2|Score2|explanation2
    Name3|Score3|explanation3
    Name4|Score4|explanation4
    Name5|Score5|explanation5
    """

    response = client.chat.completions.create(
        model="gpt-4.1-nano",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that matches candidates to job descriptions based on compatibility."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

# Streamlit UI
st.title("Candidate Search Bot")

# File uploader for job description PDF
uploaded_file = st.file_uploader("Upload Job Description PDF", type=['pdf'])

if uploaded_file is not None:
    # Parse PDF
    position_description = parse_pdf_notes(uploaded_file)
    
    if position_description:
        # Process job description
        with st.spinner("Processing job description..."):
            filters, job_summary = process_job_description(position_description)
            
            # Filter candidates
            filtered_df = filter_candidates(st.session_state.candidates_df.copy(), filters)
            
            # Calculate similarities
            final_df = calculate_similarities(filtered_df, job_summary)
            
            # Get top matches
            top_matches = get_top_matches(final_df, position_description)
            
            # Display results
            st.subheader("Top 5 Candidate Matches")
            
            # Parse and display matches
            for line in top_matches.strip().split('\n'):
                if '|' in line:
                    name, score, explanation = line.split('|', 2)
                    name = re.sub(r'^\d+\.\s*', '', name.strip())
                    
                    with st.expander(f"{name} - Score: {score}"):
                        st.write(explanation.strip())
            
            # Display statistics
            st.subheader("Search Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Initial Candidates", len(st.session_state.candidates_df))
            with col2:
                st.metric("After Filtering", len(filtered_df))
            with col3:
                st.metric("Final Candidates", len(final_df))
            
            # Display raw data
            if st.checkbox("Show Raw Data"):
                st.dataframe(final_df) 