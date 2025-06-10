import re
import os
# If pyresparser is not installed, run: pip install pyresparser
try:
    from pyresparser import ResumeParser
except ImportError:
    print("pyresparser is not installed. Please run: pip install pyresparser\nAlso run: python -m spacy download en_core_web_sm")
    ResumeParser = None

def summarize_resume(resume_text: str) -> str:
    """
    Uses pyresparser to parse a resume and extract the most important details for candidate-job matching.
    Outputs the word count before and after summarizing.
    """
    # Word count before summarizing
    original_word_count = len(resume_text.split())
    print(f"Original resume word count: {original_word_count}")

    if ResumeParser is None:
        return "[ERROR] pyresparser is not installed."

    # pyresparser expects a file, so write the resume_text to a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.txt') as tmp:
        tmp.write(resume_text)
        tmp_path = tmp.name

    # Parse the resume
    data = ResumeParser(tmp_path).get_extracted_data()
    os.remove(tmp_path)

    # Build a concise summary
    summary_lines = []
    if data.get('skills'):
        summary_lines.append(f"SKILLS: {', '.join(data['skills'])}")
    if data.get('education'):
        summary_lines.append("EDUCATION:")
        for edu in data['education']:
            summary_lines.append(f"- {edu}")
    if data.get('experience'):
        summary_lines.append("EXPERIENCE:")
        for exp in data['experience']:
            summary_lines.append(f"- {exp}")
    if data.get('certifications'):
        summary_lines.append("CERTIFICATIONS:")
        for cert in data['certifications']:
            summary_lines.append(f"- {cert}")
    if data.get('languages'):
        summary_lines.append(f"LANGUAGES: {', '.join(data['languages'])}")

    summary = '\n'.join(summary_lines)
    summary_word_count = len(summary.split())
    print(f"Summarized resume word count: {summary_word_count}")
    return summary

def process_resume_file(file_path: str) -> str:
    """
    Reads a resume from a file and returns its summary.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            resume_text = file.read()
        return summarize_resume(resume_text)
    except Exception as e:
        print(f"Error processing resume file: {str(e)}")
        return ""

# Example usage:
if __name__ == "__main__":
    # Example resume text
    sample_resume = """
    Bradley Harrington
Duxbury, MA 02332 | (781) 206-9010 | harrinfa@bc.edu


EDUCATION
Boston College – Morrissey College of Arts and Sciences	Chestnut Hill, MA
Major in Economics; Minors in Accounting and Computer Science	Expected May 2027
GPA: 3.80 / 4.00
Honors: 2025 Carolina Case Competition Finalist, 2024 ACC Leadership Symposium Delegate
Relevant Coursework: Machine Learning & AI, Ancient Egyptian Art, Fundamentals of Finance

WORK & LEADERSHIP EXPERIENCE
Earth Foundry	Chicago, IL
Incoming Venture Capital Summer Analyst	Summer 2025

GrubSwap, Inc.	Chestnut Hill, MA
Co-Founder	Oct 2023 – Present
Co-founded “GrubSwap,” a startup centered around the BC dining system that leverages excess meal plan money to deliver discounted meals to students – GrubSwap generated $600 in revenue from a 10-day “Beta”
Pitched and raised $10k in Pre-Seed funding from the SSC Venture Partners, resulting in a $500,000 valuation 
Hired and managed a 10-person team of students working on marketing, performing deliveries, etc.
Self-taught in Adalo, independently developed a full stack app, successfully published on the App Store

SSC Venture Studio	Chestnut Hill, MA
Senior Analyst	Sep 2024 – Present
Managed a 4-person team giving strategic advice to 30+ student entrepreneurs for BC’s Venture Capital Fund
Created and led SSC’s first “Sourcing Team,” utilizing marketing strategies to result in 4 sourced startups
Valued startups generating $10k+ in ARR by applying comparables analysis and building financial models

Ascend Consulting Group	Chestnut Hill, MA
VP of Project Management	Jan 2025 – Present
Led a team of 8 BC students in a 4-week GTM strategy engagement for the CEO of a Seed-stage startup with 6,000+ users, consisting of market research and data analysis, resulting in $360k additional revenue generated 
Assigned weekly deliverables to team, communicated with client, created slide decks, led weekly client calls
Led recruiting efforts that resulted in 104 applications by running info sessions, coffee chats, and interviews

LaunchPad Institute	Chestnut Hill, MA
Student Lead	Mar 2024 – Present
Analyzed Coinbase’s stock for a client at Fidelity Investments, leveraging DCF and Comparables valuations 
Only student out of 35 members offered the “Student Lead” position
Organized, marketed, and interviewed students for the program, pitched LPI in-person to 300+ students

Duxbury High School Track & Cross Country Captain	Duxbury, MA
Captain	Dec 2019 – Jun 2023
5-season Varsity Captain, coordinated 6+ weekly practices and lift sessions, Lt. Steele award for leadership
Nationally Ranked in the 4x400m Relay (91st); 2nd place in D3 MA in the 4x400. Mile PR of 4:39
Independently Organized Fundraiser 5k for a teammate with leukemia, raised $3,000 from 75 runners


SKILLS, ACTIVITIES, INTERESTS 
Technical Skills: Adalo, Python, Java, AI for Teams Certified, Financial Modeling
Activities: BC Symphony Orchestra, Chamber Music Society, 15th ranked high school cellist in MA,
Emerging Leader Program (weekly volunteer service), Freshmen League (freshman mentorship program)
Interests: Trail running, Fantasy Football (3x champion), Campfire s’mores ice cream, Cold exposure

    """
    summary = summarize_resume(sample_resume)
    print(summary)
