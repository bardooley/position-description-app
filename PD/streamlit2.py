import streamlit as st
import os
from PIL import Image
import requests
from io import BytesIO
import openai
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import inch
import PyPDF2

# Set page config
st.set_page_config(page_title="Position Description Generator", layout="wide")

# Title
st.title("Position Description Generator")

# Input fields
col1, col2 = st.columns(2)
with col1:
    school_name = st.text_input("School name")
    position_name = st.text_input("Position name") 
    location = st.text_input("Location of the school")
    date = st.text_input("Start date (e.g. July 2026)", value="July 2026")

with col2:
    consultant_name = st.text_input("Consultant name", value="Jim Shwartz")
    consultant_email = st.text_input("Consultant email", value="jim.shwartz@carneysandoe.com")
    notes_file = st.file_uploader("Upload school notes (TXT or PDF)", type=["txt", "pdf"])

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=api_key)

# Process uploaded file
notes_content = ""
if notes_file is not None:
    if notes_file.name.lower().endswith('.pdf'):
        try:
            pdf_reader = PyPDF2.PdfReader(notes_file)
            notes_content = ""
            for page in pdf_reader.pages:
                notes_content += page.extract_text()
            st.success("Successfully read PDF notes")
        except Exception as e:
            st.error(f"Error reading PDF: {str(e)}")
    else:
        try:
            notes_content = notes_file.getvalue().decode()
            st.success("Successfully read text notes")
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

# Generate content button
if st.button("Generate Position Description"):
    if not all([school_name, position_name, location, date, consultant_name, consultant_email]):
        st.error("Please fill in all required fields")
    else:
        with st.spinner("Generating content..."):
            # Generate overview
            overview_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are an experienced HR professional creating a Position Description for {position_name} at {school_name}. Notes: {notes_content}"},
                    {"role": "user", "content": "Create a 100-word overview section for the position description."}
                ]
            )
            overview = overview_response.choices[0].message.content

            # Generate responsibilities
            responsibilities_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are an experienced HR professional creating a Position Description for {position_name} at {school_name}. Notes: {notes_content}"},
                    {"role": "user", "content": "Create a 200-word responsibilities section with bullet points (35-40 words each)."}
                ]
            )
            responsibilities = responsibilities_response.choices[0].message.content

            # Generate qualifications
            qualifications_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are an experienced HR professional creating a Position Description for {position_name} at {school_name}. Notes: {notes_content}"},
                    {"role": "user", "content": "Create a 75-110 word qualifications section with bullet points (30-40 words each)."}
                ]
            )
            qualifications = qualifications_response.choices[0].message.content

            # Generate salary
            salary_response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are an experienced HR professional creating a Position Description for {position_name} at {school_name}. Notes: {notes_content}"},
                    {"role": "user", "content": "Create a 50-word salary section."}
                ]
            )
            salary = salary_response.choices[0].message.content

            # Display generated content
            st.subheader("Generated Content")
            st.write("### Overview")
            st.write(overview)
            st.write("### Responsibilities")
            st.write(responsibilities)
            st.write("### Qualifications")
            st.write(qualifications)
            st.write("### Salary")
            st.write(salary)

            # Download button for PDF
            if st.button("Download PDF"):
                # PDF generation code would go here
                st.info("PDF generation functionality to be implemented")