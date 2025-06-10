import re
import pandas
from sentence_transformers import SentenceTransformer
import pandas as pd

df = pandas.read_csv('/Users/bradleyharrington/Documents/CS&A/Search/Candidates2000.csv')
#on Tuesday, this will connect to SMS and upload all candidates as a dataframe. 

import PyPDF2

def parse_pdf_notes(pdf_path):
    try:
        # Open the PDF file
        with open(pdf_path, 'rb') as file:
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Initialize an empty string to store the text
            text = ""
            
            # Iterate through all pages
            for page in pdf_reader.pages:
                # Extract text from each page
                text += page.extract_text()
            
            return text
    except FileNotFoundError:
        print(f"Error: Could not find the file {pdf_path}")
        return None
    except Exception as e:
        print(f"Error parsing PDF: {str(e)}")
        return None

# Parse the notes file
position_description = parse_pdf_notes('/Users/bradleyharrington/Documents/CS&A/Search/GoodHopePD.pdf')

if position_description:
    print("Successfully parsed PDF notes")
    # You can process the notes_text further as needed
else:
    print("Failed to parse PDF notes")




import openai
import os

# Set up OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Create prompt for OpenAI
prompt = f"""
Your task is to extract hard filters and preferences from notes about the job.
You are extracting structured filters from a job description. Use only the valid options listed below.

Return ONLY a JSON object in this exact format, with no additional text or explanation:

{{
  "required_languages": [],
  "required_position_types": [],
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

# Get response from OpenAI
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that extracts structured filters from job descriptions. Always return valid JSON."},
        {"role": "user", "content": prompt}
    ]
)

# Extract and print the job description
job_filters = response.choices[0].message.content.strip()


# Parse the JSON string into a Python dictionary
import json
try:
    filters = json.loads(job_filters)
    # Ensure all filter keys exist with default empty lists
    required_keys = [
        "required_languages", "required_position_types",
        "required_position_levels", "required_citizenships", "required_ethnicities",
        "required_genders", "required_professional_associations", "required_religions",
        "min_experience_years"
    ]
    for key in required_keys:
        if key not in filters:
            filters[key] = [] if key != "min_experience_years" else None
    #print("\nParsed Filters:")
    #print(filters)
except json.JSONDecodeError as e:
    print("\nError parsing JSON response:")
    print(f"Error details: {str(e)}")
    print("Raw response was not valid JSON. Please check the GPT response format.")
    exit(1)

# Generate a structured job summary for similarity matching
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
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that creates concise, structured summaries of job requirements."},
        {"role": "user", "content": summary_prompt}
    ]
)

job_cosine_summary = summary_response.choices[0].message.content.strip()

# Convert Experience column to numeric by extracting numbers from strings
if df['Experience'].dtype == 'object':  # If it's a string/object type
    df['Experience'] = df['Experience'].astype(str).str.extract('(\d+)').astype(float)
else:
    print("Experience column is already numeric")

print("\nInitial number of candidates:", len(df))

for lang in filters["required_languages"]:
    df = df[df["Languages"].str.contains(lang, case=False, na=False)]

for position_type in filters["required_position_types"]:
    df = df[df["Position Type"].str.contains(position_type, case=False, na=False)]

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
    # Filter for experience greater than or equal to the minimum
    df = df[df['Experience'] >= filters["min_experience_years"]]

print(f"\nNumber of remaining candidates after filtering: {len(df)}")


# Create a copy of the dataframe to store the formatted strings
df['Formatted Info'] = df.apply(lambda row: f"""Name: {row['Candidate Name']}
Citizenship: {row['Citizenship']}
Ethnicity: {row['Ethnicity']}
Gender: {row['Gender']}
Languages: {row['Languages']}
Position Type: {row['Position Type']}
Position Level: {row['Position Level']}
Professional Association: {row['Professional Association']}""", axis=1)


import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Initialize the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Create embeddings for the job summary instead of full description
job_embedding = model.encode([job_cosine_summary])

# Create embeddings for all candidates using the formatted info
candidate_embeddings = model.encode(df['Formatted Info'].tolist())

# Calculate cosine similarity between job summary and each candidate
similarities = cosine_similarity(job_embedding, candidate_embeddings)[0]

# Add similarity scores to the dataframe
df['Similarity Score'] = similarities

# Sort the dataframe by similarity score in descending order
df = df.sort_values('Similarity Score', ascending=False)

# Keep only top 300 candidates if we have more than 300
if len(df) > 300:
    df = df.head(300)
else:
    print(f"\nKeeping all {len(df)} candidates (less than 300)")

print(f"\nFinal number of candidates: {len(df)}")

# Prepare the prompt for OpenAI
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

# Call OpenAI API
response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that matches candidates to job descriptions based on compatibility."},
        {"role": "user", "content": prompt}
    ]
)

# Print token usage
print(f"\nToken usage:")
print(f"Prompt tokens: {response.usage.prompt_tokens}")
print(f"Completion tokens: {response.usage.completion_tokens}")
print(f"Total tokens: {response.usage.total_tokens}")

# Parse the response to get names, scores, and explanations
response_text = response.choices[0].message.content
candidate_matches = {}

for line in response_text.strip().split('\n'):
    if '|' in line:
        name, score, explanation = line.split('|', 2)
        name = re.sub(r'^\d+\.\s*', '', name.strip())
        candidate_matches[name] = {
            'score': score.strip(),
            'explanation': explanation.strip()
        }

print("\nTop 5 candidate matches:")
for name, match_info in candidate_matches.items():
    print(f"\nName: {name}")
    print(f"Score: {match_info['score']}")
    print(f"Explanation: {match_info['explanation']}")

