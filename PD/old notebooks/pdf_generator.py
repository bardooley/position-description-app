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
import os

def add_images_to_description(description, images):
    """
    Adds image placeholders to the position description text.
    
    Args:
        description (str): The position description text
        images (list): List of dictionaries containing image information
    
    Returns:
        str: The modified description with image placeholders
    """
    # Add image placeholders at appropriate locations
    # For example, after the School Overview section
    sections = description.split('###')
    modified_sections = []
    
    for i, section in enumerate(sections):
        modified_sections.append(section)
        if i == 1:  # After School Overview
            for img in images:
                if 'caption' in img:
                    modified_sections.append(f"\n![{img['caption']}]({img['path']})\n")
                else:
                    modified_sections.append(f"\n![Image]({img['path']})\n")
    
    return '###'.join(modified_sections)

def search_school_images(school_name):
    try:
        # First try to get the school's website
        search_query = f"{school_name} official website"
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that finds official school websites."},
                {"role": "user", "content": f"Please provide the official website URL for {school_name}. Only return the URL, nothing else."}
            ],
            max_tokens=100
        )
        
        school_url = response.choices[0].message.content.strip()
        
        # Scrape images from the school's website
        if school_url:
            try:
                img_urls = scrape_images_from_site(school_url, max_images=3)
                if img_urls:
                    return img_urls
            except Exception as e:
                print(f"Error scraping school website: {str(e)}")
        
        # If no images found from school website, try a general search
        search_query = f"{school_name} high school building campus"
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that finds school images."},
                {"role": "user", "content": f"Please provide 3 image URLs that show {search_query}. Only return the URLs, one per line, nothing else."}
            ],
            max_tokens=300
        )
        
        # Parse the response to get image URLs
        urls = [url.strip() for url in response.choices[0].message.content.split('\n') if url.strip()]
        return urls[:3]  # Return up to 3 images
        
    except Exception as e:
        print(f"Error searching for images: {str(e)}")
        return []

def download_and_process_image(image_url, output_dir, index):
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Download the image
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(image_url, headers=headers)
        response.raise_for_status()
        
        # Open and process the image
        img = PILImage.open(BytesIO(response.content))
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Calculate new dimensions while maintaining aspect ratio
        max_width = 800
        max_height = 600
        width, height = img.size
        
        if width > max_width or height > max_height:
            ratio = min(max_width/width, max_height/height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
        
        # Save the processed image
        output_path = os.path.join(output_dir, f'school_image_{index}.jpg')
        img.save(output_path, 'JPEG', quality=85)
        
        # Return image information
        return {
            'path': output_path,
            'caption': f'Image of {school_name}',
            'width': 400,  # Default width in points
            'height': 300  # Default height in points
        }
    
    except Exception as e:
        print(f"Error processing image {image_url}: {str(e)}")
        return None

def get_school_images(school_name, output_dir='school_images'):
    # Search for images
    image_urls = search_school_images(school_name)
    
    # Download and process images
    images = []
    for i, url in enumerate(image_urls):
        img_info = download_and_process_image(url, output_dir, i)
        if img_info:
            images.append(img_info)
    
    return images

def convert_to_pdf(text, output_filename="position_description.pdf", images=None):
    try:
        try:
            # Try to import reportlab
            from reportlab.lib.pagesizes import LETTER
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
            from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        except ImportError:
            return "Error: The 'reportlab' module is not installed. Please install it using 'pip install reportlab' and try again."
        
        # Create a PDF document
        doc = SimpleDocTemplate(output_filename, pagesize=LETTER)
        styles = getSampleStyleSheet()
        
        # Create custom styles
        custom_title_style = ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=12
        )
        
        custom_section_style = ParagraphStyle(
            name='CustomSectionHeader',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=6,
            spaceBefore=12
        )
        
        custom_normal_style = ParagraphStyle(
            name='CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY
        )
        
        custom_caption_style = ParagraphStyle(
            name='CustomCaption',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.gray
        )
        
        # Process the text into paragraphs
        story = []
        
        # Split the text into lines
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
                continue
                
            # Determine the style based on the line content
            if line.startswith('==='):
                continue  # Skip the === lines
            elif line.startswith('**Position Title:') or line.startswith('**Location:') or line.startswith('**Application Deadline:') or line.startswith('**Start Date:'):
                story.append(Paragraph(line, custom_title_style))
            elif line.startswith('###'):
                # Section header
                header_text = line.replace('###', '').strip()
                story.append(Paragraph(header_text, custom_section_style))
                
                # Add images after School Overview section
                if header_text == "School Overview" and images:
                    for img_info in images:
                        try:
                            # Add spacing before image
                            story.append(Spacer(1, 12))
                            
                            # Add the image
                            img = Image(img_info['path'], width=img_info.get('width', 400), height=img_info.get('height', 300))
                            story.append(img)
                            
                            # Add caption if provided
                            if 'caption' in img_info:
                                story.append(Spacer(1, 6))
                                story.append(Paragraph(img_info['caption'], custom_caption_style))
                            
                            # Add spacing after image
                            story.append(Spacer(1, 12))
                        except Exception as e:
                            print(f"Warning: Could not add image {img_info['path']}: {str(e)}")
                
            elif line.startswith('**') and line.endswith('**'):
                # Subsection header
                subsection_text = line.strip('**')
                story.append(Paragraph(subsection_text, styles['Heading3']))
            elif line.startswith('-'):
                # Bullet point
                bullet_text = line[1:].strip()
                story.append(Paragraph(f"• {bullet_text}", custom_normal_style))
            elif line.startswith('---'):
                story.append(Spacer(1, 10))
            else:
                story.append(Paragraph(line, custom_normal_style))
        
        # Build the PDF
        doc.build(story)
        
        return f"Successfully created PDF: {output_filename}"
    
    except Exception as e:
        return f"Error creating PDF: {str(e)}"

# Make functions available for import
__all__ = ['convert_to_pdf', 'add_images_to_description', 'get_school_images']