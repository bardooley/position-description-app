import streamlit as st
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import inch
import requests
import os
from PIL import Image as PILImage
from io import BytesIO
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import openai
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable, Image, Table, TableStyle, PageBreak, FrameBreak
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen import canvas
import matplotlib.pyplot as plt
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

st.set_page_config(page_title="Position Description Generator", layout="wide")

st.title("Position Description Generator")

# Sidebar for inputs
with st.sidebar:
    st.header("Input Information")
    school_name = st.text_input("School Name")
    position_name = st.text_input("Position Name")
    location = st.text_input("Location")
    date = st.text_input("Start Date (e.g., July 2026)")
    consultant_name = st.text_input("Consultant Name")
    consultant_email = st.text_input("Consultant Email")
    
    # File uploader for notes
    notes_file = st.file_uploader("Upload Notes File (PDF or TXT)", type=['pdf', 'txt'])
    
    # API Keys
    openai_api_key = os.getenv('OPENAI_API_KEY')
    google_api_key = os.getenv('GOOGLE_API_KEY')
    google_search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')

def process_notes_file(notes_file):
    if notes_file is None:
        return ""
    
    try:
        if notes_file.name.lower().endswith('.pdf'):
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(notes_file)
            notes_content = ""
            for page in pdf_reader.pages:
                notes_content += page.extract_text()
        else:
            notes_content = notes_file.getvalue().decode()
        
        return notes_content
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return ""

def generate_position_description():
    if not all([school_name, position_name, location, date, consultant_name, consultant_email, openai_api_key]):
        st.error("Please fill in all required fields")
        return
    
    notes_content = process_notes_file(notes_file)
    
    # Set up OpenAI client
    client = openai.OpenAI(api_key=openai_api_key)
    
    # Generate overview
    with st.spinner("Generating overview..."):
        overview_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"You are an experienced HR professional. You are creating a 'Position Description.' This document will be displayed to people that apply for the position '{position_name}' at '{school_name}'. Please pull from the internet to create this overview. Additionally, here are some notes on the school, taken directly from a phone call or personal visit with school administrators: {notes_content} "},
                {"role": "user", "content": f"Please create the 'overview' section of a Position Description for the {position_name} position at {school_name} in {location}. This overview section should be about 100 words in length."}
            ],
            max_tokens=1500
        )
        overview = overview_response.choices[0].message.content
    
    # Generate responsibilities
    with st.spinner("Generating responsibilities..."):
        responsibilities_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"You are an experienced HR professional. You are creating a 'Position Description.' This document will be displayed to people that apply for the position '{position_name}' at '{school_name}'. Please pull from the internet to create this overview. Additionally, here are some notes on the school, taken directly from a phone call or personal visit with school administrators: {notes_content} "},
                {"role": "user", "content": f"Please create the 'responsibilities' section of a Position Description for the {position_name} position at {school_name}. This responsibilities section should be about 200 words in length. Make sure to break your response up into bullet points. Each bullet point should be about 50 words. 55 maximum."}
            ],
            max_tokens=1500
        )
        responsibilities = responsibilities_response.choices[0].message.content
    
    # Generate qualifications
    with st.spinner("Generating qualifications..."):
        qualifications_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"You are an experienced HR professional. You are creating a 'Position Description.' This document will be displayed to people that apply for the position '{position_name}' at '{school_name}'. Please pull from the internet to create this. Additionally, here are some notes on the school, taken directly from a phone call or personal visit with school administrators: {notes_content} "},
                {"role": "user", "content": f"Please create the 'qualifications' section of a Position Description for the {position_name} position at {school_name}. This qualifications section should be between 75-110 words in length. Make sure to break your response up into bullet points. Each bullet point should be about 30 words long. No longer than 40 maximum."}
            ],
            max_tokens=1500
        )
        qualifications = qualifications_response.choices[0].message.content
    
    # Generate salary
    with st.spinner("Generating salary information..."):
        salary_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"You are an experienced HR professional. You are creating a 'Position Description.' This document will be displayed to people that apply for the position '{position_name}' at '{school_name}'. Here are some notes on the school, taken directly from a phone call or personal visit with school administrators. If there is an exact salary specified, that's most important. If there is conflicting salary expectations online, ignore that information and use the salary specified in the notes. Here are the notes: {notes_content} "},
                {"role": "user", "content": f"Please create the 'salary' section of a Position Description for the {position_name} position at {school_name}. This salary section should be about 50 words in length."}
            ],
            max_tokens=1500
        )
        salary = salary_response.choices[0].message.content
    
    # Display the generated content
    st.header("Generated Position Description")
    
    st.subheader("Overview")
    st.write(overview)
    
    st.subheader("Major Functions and Responsibilities")
    st.write(responsibilities)
    
    st.subheader("Experience and Skills")
    st.write(qualifications)
    
    st.subheader("Salary Range")
    st.write(salary)
    
    # Generate PDF button
    if st.button("Generate PDF"):
        with st.spinner("Generating PDF..."):
            # Create the document with a custom page template
            doc = BaseDocTemplate("position_description.pdf", pagesize=letter)
            frame = Frame(
                doc.leftMargin,
                doc.bottomMargin + .9 * inch,
                doc.width,
                doc.height - .7 * inch,
                id='normal'
            )

            # Register fonts
            pdfmetrics.registerFont(TTFont('MinionPro', 'MinionPro-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('MinionPro-Bold', 'MinionPro-Bold.ttf'))
            pdfmetrics.registerFont(TTFont('MinionPro-Italic', 'MinionPro-It.ttf'))

            # Add page templates
            doc.addPageTemplates([
                PageTemplate(
                    id='WithHeaderAndFooter',
                    frames=[frame],
                    onPage=lambda canvas, doc: (draw_header(canvas, doc), draw_footer(canvas, doc))
                )
            ])

            # Define styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(name="Title", fontSize=14, leading=12, alignment=TA_CENTER, spaceAfter=12, fontName="MinionPro-Bold")
            subtitle_style = ParagraphStyle(name="Subtitle", fontSize=12, leading=15, alignment=TA_CENTER, spaceAfter=24, fontName="MinionPro")
            header_style = ParagraphStyle(name="SectionHeader", fontSize=13, leading=16, spaceBefore=12, spaceAfter=6, fontName="MinionPro-Bold")
            body_style = ParagraphStyle(name="Body", fontSize=11, leading=15.5, fontName="MinionPro")

            # Build story content
            story = []
            story.append(Spacer(1, 1 * inch))
            story.append(Paragraph(f"{school_name} - {location}", title_style))
            story.append(Paragraph(position_name, title_style))
            story.append(Paragraph(date, title_style))
            story.append(HRFlowable(width="100%", thickness=1, color="black", spaceBefore=6, spaceAfter=12))
            story.append(Paragraph(overview, body_style))

            # Add responsibilities section
            story.append(Paragraph("Major Functions and Responsibilities", header_style))
            responsibilities_list = [item.strip("● ").strip() for item in responsibilities.strip().split("\n") if item.strip()]
            bullets = [ListItem(Paragraph(item, body_style)) for item in responsibilities_list]
            story.append(ListFlowable(bullets, bulletType='bullet', leftIndent=20))

            # Add qualifications section
            story.append(Paragraph("Experience and Skills", header_style))
            qualifications_list = qualifications.strip().split("-")
            bullets = [ListItem(Paragraph(item.strip(), body_style)) for item in qualifications_list if item.strip()]
            story.append(ListFlowable(bullets, bulletType='bullet', leftIndent=20))

            # Add salary section
            story.append(Paragraph("Salary Range", header_style))
            story.append(Paragraph(salary, body_style))

            # Add application instructions
            story.append(Paragraph("To Apply", header_style))
            story.append(Paragraph("Interested and qualified candidates should submit, as separate PDF documents, the following materials:", body_style))
            apply_list = [
                "A cover letter expressing interest in this particular position;",
                "A current resume with all dates included; and",
                "A list of five professional references with the name, relationship, phone number, and email address of each (references will not be contacted without the candidate's permission and not before a mutual interest has clearly been established)"
            ]
            bullets = [ListItem(Paragraph(item, body_style)) for item in apply_list]
            story.append(ListFlowable(bullets, bulletType='bullet', leftIndent=20))
            contact_info = f"to {consultant_name} at {consultant_email}. Please do not contact the school directly."
            story.append(Paragraph(contact_info, body_style))

            # Build the PDF
            doc.build(story)
            st.success("PDF generated successfully!")
            
            # Provide download link
            with open("position_description.pdf", "rb") as f:
                st.download_button(
                    label="Download PDF",
                    data=f,
                    file_name="position_description.pdf",
                    mime="application/pdf"
                )

# Main app
if __name__ == "__main__":
    if st.button("Generate Position Description"):
        generate_position_description() 