import os
import pandas as pd
import openai
from typing import Dict, List

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

def get_user_inputs():
    # Get school name input
    school_name = input("Enter school name: ").strip()
    
    # Get position input
    position = input("Enter position: ").strip()
    
    return school_name, position

def find_school_info(school_name: str) -> Dict:
    """Find and return all information about the specified school."""
    try:
        schools_df = pd.read_csv('Search Bot/Schools.csv')
        school_info = schools_df[schools_df['School Name'].str.lower() == school_name.lower()]
        
        if school_info.empty:
            raise ValueError(f"School '{school_name}' not found in database. Please try another spelling or wording.")
            
        return school_info.iloc[0].to_dict()
    except Exception as e:
        print(f"Error finding school information: {str(e)}")
        return None
def find_best_candidates(school_info: Dict, position: str) -> List[Dict]:
    """Use OpenAI to find the best candidates for the position at the school."""
    try:
        # Read candidates data
        candidates_df = pd.read_csv('Search Bot/Candidates.csv')
        
        # Prepare the prompt for OpenAI
        prompt = f"""
        Given the following school information:
        {school_info}
        
        And the position that the school is currently hiring for: {position}
        
        Please analyze the following candidates and return the top 3 best fits for the job:
        {candidates_df.to_dict('records')}
        
        For each of the top 3 candidates, provide:
        1. Their full name
        2. A fit score out of 10 (where 10 is perfect fit) - use one decimal place (e.g., 8.5)
        3. A brief 2-sentence explanation of why they would be a good fit for this position at this specific school
        
        Format your response as:
        Name1|Score1|explanation1
        Name2|Score2|explanation2
        Name3|Score3|explanation3
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that matches candidates to schools based on compatibility."},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Print token usage
        print(f"\nToken usage for this request:")
        print(f"Prompt tokens: {response.usage.prompt_tokens}")
        print(f"Completion tokens: {response.usage.completion_tokens}")
        print(f"Total tokens: {response.usage.total_tokens}")
        
        # Parse the response to get names, scores, and explanations
        response_text = response.choices[0].message.content
        candidate_matches = {}
        
        for line in response_text.strip().split('\n'):
            if '|' in line:
                name, score, explanation = line.split('|', 2)
                name = name.strip()
                candidate_matches[name] = {
                    'score': score.strip(),
                    'explanation': explanation.strip()
                }
        
        # Get full candidate information
        best_candidates = candidates_df[candidates_df['Candidate Name'].isin(candidate_matches.keys())].to_dict('records')
        
        # Add scores and explanations to candidate data
        for candidate in best_candidates:
            match_info = candidate_matches[candidate['Candidate Name']]
            candidate['score'] = match_info['score']
            candidate['explanation'] = match_info['explanation']
            
        return best_candidates
        
    except Exception as e:
        print(f"Error finding best candidates: {str(e)}")
        return []

def main():
    school_name, position = get_user_inputs()
    
    # Find school information
    school_info = find_school_info(school_name)
    if not school_info:
        return
    
    # Find best candidates
    best_candidates = find_best_candidates(school_info, position)
    
    # Display results
    print("\nTop 3 candidates for the position:")
    for i, candidate in enumerate(best_candidates, 1):
        print(f"\n{i}. {candidate['Candidate Name']}")
        print(f"   Fit Score: {float(candidate['score']):.1f}/10")
        print(f"   Summary: {candidate['explanation']}")
        print("-" * 80)  # Separator line between candidates

if __name__ == "__main__":
    main()

