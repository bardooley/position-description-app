import os
import pandas as pd
import openai
from typing import Dict, List
import re
from sentence_transformers import SentenceTransformer

# Pricing for GPT-4.1-nano
PROMPT_COST_PER_1K = 0.00010
COMPLETION_COST_PER_1K = 0.00040

# Initialize global variables for token and cost tracking
total_prompt_tokens = 0
total_completion_tokens = 0
total_cost = 0.0

# Set your OpenAI API key
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_user_inputs():
    # Get school name input
    #school_name = input("Enter school name: ").strip()
    school_name = 'Oakridge Academy'
    # Get position input
    #position = input("Enter position: ").strip()
    position = 'Principal'
    return school_name, position

def find_best_candidates(school_info: Dict, position: str) -> List[Dict]:
    global total_prompt_tokens, total_completion_tokens, total_cost
    try:
        # Use absolute path for the CSV file
        candidates_csv_path = os.path.join(SCRIPT_DIR, 'CandidatesResumes.csv')
        candidates_df = pd.read_csv(candidates_csv_path)
        
        # First, filter candidates by position type to reduce the dataset
        position_keywords = position.lower().split()
        candidates_df['Position Type Lower'] = candidates_df['Position Type'].str.lower()
        filtered_candidates = candidates_df[
            candidates_df['Position Type Lower'].apply(
                lambda x: any(keyword in x for keyword in position_keywords)
            )
        ]
        
        if len(filtered_candidates) == 0:
            filtered_candidates = candidates_df
        
        # Take only the most relevant columns to reduce token count
        relevant_columns = ['Candidate Name', 'Position Type', 'Experience', 'Degree(s) Attained', 
                          'Languages', 'Professional Association', 'Position Level']
        filtered_candidates = filtered_candidates[relevant_columns]
        
        # Prepare the prompt for OpenAI
        prompt = f"""
        Given the following school information:
        {school_info}
        
        And the position that the school is currently hiring for: {position}
        
        Please analyze the following candidates and return the top 3 BEST fits for the job:
        {filtered_candidates.to_dict('records')}
        
        For each of the top 3 candidates, provide:
        1. Their full name
        2. A fit score out of 10 (where 10 is perfect fit) - use one decimal place (e.g., 8.5)
        3. A brief 2-sentence explanation of why they would be a good fit for this position at this specific school
        
        All candidates should be a great fit for the job. Do not include any candidates that are not a great fit. Always output 3 candidates.

        Format your response as:
        Name1|Score1|explanation1
        Name2|Score2|explanation2
        Name3|Score3|explanation3
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that matches candidates to schools based on compatibility."},
                {"role": "user", "content": prompt}
            ]
        )
        
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
        
        print("Candidate matches parsed from response:", candidate_matches)
        
        # Get full candidate information
        best_candidates = candidates_df[candidates_df['Candidate Name'].isin(candidate_matches.keys())].to_dict('records')
        
        # Add scores and explanations to candidate data
        for candidate in best_candidates:
            match_info = candidate_matches[candidate['Candidate Name']]
            candidate['score'] = match_info['score']
            candidate['explanation'] = match_info['explanation']
            
        if hasattr(response, "usage") and response.usage is not None:
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens

            # Update global totals
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens

            # Calculate cost for this call
            cost = (prompt_tokens / 1000) * PROMPT_COST_PER_1K + (completion_tokens / 1000) * COMPLETION_COST_PER_1K
            total_cost += cost

            print(f"Token usage for this call: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")
            print(f"Estimated cost for this call: ${cost:.6f}")
        else:
            print("Token usage information not available in response.")
        
        return best_candidates
        
    except Exception as e:
        print(f"Error finding best candidates: {str(e)}")
        return []

def main():
    school_name, position = get_user_inputs()
    # Hardcoded school information
    school_info = {
        'School Name': 'Oakridge Academy',
        'Hiring Role': 'Principal',
        'School Overview': 'Oakridge Academy is a coeducational K–12 independent school dedicated to academic excellence, character development, and community engagement. With a vibrant student body and a commitment to experiential learning, Oakridge prepares students for college and global citizenship.',
        'Opportunities and Challenges': 'The school is experiencing enrollment growth and is seeking to expand its STEM offerings. Key challenges include integrating new technologies into the classroom and enhancing diversity in curriculum and staffing.',
        'Role Requirements and Qualifications': 'The ideal candidate will have at least 10 years of educational leadership experience, a proven track record in instructional innovation, and a commitment to equity and inclusion. A master's degree or higher in education or related field is required. Preferred qualifications include fluency in Arabic and prior experience as an HR Manager. Candidates with exactly 7 years of professional experience and a position start date in 2024 are especially encouraged to apply. We are especially interested in candidates from Germany who hold an MBA and B.A., identify as Native American and female, and are originally from Tennessee.',
        'Community Context': 'Oakridge has a deeply involved parent community and strong alumni ties. Traditions such as the Fall Festival and Senior Capstone Day are core to its culture, and the school values open dialogue between faculty, families, and leadership.',
    }
    
    # Find best candidates
    best_candidates = find_best_candidates(school_info, position)
    
    # Sort candidates by score in descending order
    best_candidates.sort(key=lambda x: float(x['score']), reverse=True)
    
    # Display results
    print("\nTop 3 candidates for the position:")
    for i, candidate in enumerate(best_candidates, 1):
        print(f"\n{i}. {candidate['Candidate Name']}")
        print(f"   Fit Score: {float(candidate['score']):.1f}/10")
        print(f"   Summary: {candidate['explanation']}")
        print("-" * 80)  # Separator line between candidates

    print("\n=== OpenAI API Usage Summary ===")
    print(f"Total prompt tokens: {total_prompt_tokens}")
    print(f"Total completion tokens: {total_completion_tokens}")
    print(f"Total tokens: {total_prompt_tokens + total_completion_tokens}")
    print(f"Estimated total cost: ${total_cost:.6f}")

if __name__ == "__main__":
    main()

