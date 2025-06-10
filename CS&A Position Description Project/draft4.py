# region IMPORTS
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
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
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, ListFlowable, ListItem, HRFlowable, Image, Table, TableStyle, PageBreak, FrameBreak
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
import openai
import PyPDF2
import re

# endregion

# region CONFIGURATION
def setup():
    print("Setting up OpenAI client...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        return None
    
    try:
        client = openai.OpenAI(api_key=api_key)
        print("OpenAI client initialized successfully")
        return client
    except Exception as e:
        print(f"ERROR: Failed to initialize OpenAI client: {str(e)}")
        return None

def get_most_common_color(soup):
    """Get the most common color from the webpage's CSS"""
    color_counts = {}
    
    # Look for colors in style attributes
    for tag in soup.find_all(style=True):
        style = tag['style']
        # Look for hex colors
        hex_colors = re.findall(r'#[0-9a-fA-F]{6}', style)
        for color in hex_colors:
            color_counts[color] = color_counts.get(color, 0) + 1
            
        # Look for rgb colors
        rgb_colors = re.findall(r'rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)', style)
        for color in rgb_colors:
            color_counts[color] = color_counts.get(color, 0) + 1
    
    # Look for colors in class names that might indicate colors
    for tag in soup.find_all(class_=True):
        classes = tag['class']
        for class_name in classes:
            if any(color in class_name.lower() for color in ['blue', 'red', 'green', 'yellow', 'purple', 'orange', 'black']):
                color_counts[class_name] = color_counts.get(class_name, 0) + 1
    
    if not color_counts:
        return (0, 45, 92)  # Default to dark blue if no colors found
        
    # Get the most common color
    most_common = max(color_counts.items(), key=lambda x: x[1])[0]
    
    # Convert to RGB if it's a hex color
    if most_common.startswith('#'):
        r = int(most_common[1:3], 16)
        g = int(most_common[3:5], 16)
        b = int(most_common[5:7], 16)
        return (r, g, b)
    # Convert to RGB if it's an rgb() color
    elif most_common.startswith('rgb'):
        rgb = re.findall(r'\d+', most_common)
        return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    else:
        return (0, 45, 92)  # Default to dark blue if can't parse color

def is_mostly_white_or_black(image):
    """Check if an image is mostly white or black"""
    # Convert to RGB if not already
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Get the most common color
    colors = image.getcolors(image.size[0] * image.size[1])
    if not colors:
        return False
        
    # Sort by count and get the most common color
    most_common = max(colors, key=lambda x: x[0])
    r, g, b = most_common[1]
    
    # Check if the color is close to white (all channels > 180) or black (all channels < 50)
    print(f"Most common color: RGB({r}, {g}, {b})")
    return (r > 180 and g > 180 and b > 180) or (r < 50 and g < 50 and b < 50)

def recolor_logo(image, new_color=(64, 64, 64)):  # Dark gray for both white and black
    """Recolor a white or black logo to dark gray"""
    # Convert to RGBA if not already
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create a new image with the same size
    new_image = PILImage.new('RGBA', image.size, (0, 0, 0, 0))
    
    # Process each pixel
    for x in range(image.size[0]):
        for y in range(image.size[1]):
            pixel = image.getpixel((x, y))
            # If the pixel is not transparent
            if pixel[3] > 0:
                # If the pixel is close to white or black, use the new color
                if (pixel[0] > 180 and pixel[1] > 180 and pixel[2] > 180) or \
                   (pixel[0] < 50 and pixel[1] < 50 and pixel[2] < 50):
                    new_image.putpixel((x, y), (*new_color, pixel[3]))
                else:
                    new_image.putpixel((x, y), pixel)
    
    return new_image

def find_logo(school):
    print("Starting logo search...")
    try:
        # First, get the school's website content
        print(f"Accessing website: {school.website}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(school.website, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all image tags
        all_images = soup.find_all('img')
        image_info = []
        
        # Collect information about each image
        for img in all_images:
            src = img.get('src', '')
            alt = img.get('alt', '')
            class_name = ' '.join(img.get('class', []))
            id_name = img.get('id', '')
            
            # Skip empty sources and data URIs
            if not src or src.startswith('data:'):
                continue
                
            # Handle relative URLs
            if not src.startswith(('http://', 'https://')):
                src = urljoin(school.website, src)
                
            image_info.append({
                'src': src,
                'alt': alt,
                'class': class_name,
                'id': id_name
            })
        
        # Use OpenAI to identify the logo
        client = setup()
        if not client:
            print("ERROR: Failed to initialize OpenAI client")
            return False
            
        # Create a prompt for OpenAI
        prompt = f"""Given the following information about {school.school_name} ({school.location}), 
        and a list of images found on their website, identify the URL of their official logo.
        
        School Information:
        - Name: {school.school_name}
        - Location: {school.location}
        - Website: {school.website}
        
        Found Images:
        {json.dumps(image_info, indent=2)}
        
        Please respond with ONLY the URL of the logo image, nothing else. If you're not confident about any image being the logo, respond with 'NO_CONFIDENT_MATCH'."""
        
        print("Sending request to OpenAI to identify logo...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that identifies official school logos from website images."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        
        logo_url = response.choices[0].message.content.strip()
        
        if logo_url == 'NO_CONFIDENT_MATCH':
            print("OpenAI could not confidently identify the logo")
            return False
            
        print(f"Identified logo URL: {logo_url}")
        
        # Download the logo
        print("Downloading logo...")
        logo_response = requests.get(logo_url, headers=headers, timeout=10)
        logo_response.raise_for_status()
        
        # Convert and save the logo as PNG
        print("Converting and saving logo...")
        try:
            # First try to open the image
            img = PILImage.open(BytesIO(logo_response.content))
            print(f"Original image size: {img.size}, mode: {img.mode}")
            
            # Check if the logo is mostly white or black
            if is_mostly_white_or_black(img):
                print("Logo is mostly white or black, recoloring to dark gray...")
                # Recolor the logo to dark gray
                img = recolor_logo(img)
                print("Logo recolored successfully")
            
            # Convert to RGB mode
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGBA')
            else:
                img = img.convert('RGB')
            
            # Save with explicit format
            img.save('school_logo.png', format='PNG')
            print("Successfully saved logo as PNG")
            
            # Verify the saved file
            try:
                verify_img = PILImage.open('school_logo.png')
                print(f"Verified saved image: {verify_img.size}, mode: {verify_img.mode}")
                return True
            except Exception as e:
                print(f"Error verifying saved image: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Error finding logo: {str(e)}")
        return False

def get_dominant_color(image_path):
    """Get the dominant color from the logo image"""
    try:
        img = PILImage.open(image_path)
        # Convert to RGB if not already
        img = img.convert('RGB')
        # Resize to speed up processing
        img = img.resize((150, 150))
        # Get the most common color
        colors = img.getcolors(img.size[0] * img.size[1])
        # Sort by count and get the most common non-white/transparent color
        colors = sorted(colors, key=lambda x: x[0], reverse=True)
        for count, color in colors:
            # Skip white/very light colors
            if sum(color) > 700:  # Skip if too close to white
                continue
            return color
        # If no suitable color found, return a default blue
        return (0, 45, 92)
    except Exception as e:
        print(f"Error getting dominant color: {str(e)}")
        return (0, 45, 92)  # Default to dark blue if error

def get_mission_statement(website):
    """Scrape the mission statement from the school's website"""
    try:
        response = requests.get(website)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Common locations for mission statements
        mission_keywords = ['mission', 'vision', 'about us', 'our mission', 'who we are']
        
        # Look for mission statement in common locations
        for keyword in mission_keywords:
            # Try to find mission statement in headings
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for heading in headings:
                if keyword.lower() in heading.text.lower():
                    # Get the next paragraph or div after the heading
                    next_elem = heading.find_next(['p', 'div'])
                    if next_elem and len(next_elem.text.strip()) > 50:  # Ensure it's substantial text
                        return next_elem.text.strip()
            
            # Try to find mission statement in paragraphs
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                if keyword.lower() in p.text.lower() and len(p.text.strip()) > 50:
                    return p.text.strip()
        
        # If no mission statement found, return a default message
        return "Mission statement not found on the school's website."
        
    except Exception as e:
        print(f"Error scraping mission statement: {str(e)}")
        return "Unable to retrieve mission statement."

def get_school_statistics(school):
    """Get school statistics using OpenAI"""
    print("Using default statistics (API call disabled)")
    return {
        "established": "1966",
        "enrollment": "800",
        "faculty": "80",
        "ratio": "10:1",
        "diversity": "30%",
        "campus": "40 acres"
    }

def find_school_image(school):
    """Search for and download a school image using Google Search API"""
    print("Searching for school image...")
    try:
        # Create a search query using school name, location, and keywords
        query = f"{school.school_name} {school.location} school building campus"
        if school.keywords:
            query += " " + " ".join(school.keywords[:3])  # Add top 3 keywords
        
        # Use Google Custom Search API
        search_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': os.environ.get('GOOGLE_API_KEY'),
            'cx': os.environ.get('GOOGLE_CSE_ID'),
            'q': query,
            'searchType': 'image',
            'num': 1,  # Get only the first result
            'safe': 'active'
        }
        
        print(f"Sending request to Google Search API with query: {query}")
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        if 'items' in data and len(data['items']) > 0:
            image_url = data['items'][0]['link']
            print(f"Found image URL: {image_url}")
            
            # Download the image
            print("Downloading image...")
            img_response = requests.get(image_url, timeout=10)
            img_response.raise_for_status()
            
            # Save the image
            with open('school_image.jpg', 'wb') as f:
                f.write(img_response.content)
            print("Image saved as school_image.jpg")
            return True
            
    except Exception as e:
        print(f"Error finding school image: {str(e)}")
    return False

def build_pdf(school):
    print("Starting PDF generation...")
    # Use fixed output filename
    output_filename = "athletic_director_description.pdf"
    print(f"Output filename: {output_filename}")
    
    # Create the document with the fixed filename
    doc = BaseDocTemplate(output_filename, pagesize=letter)
    print("Document created")

    # Adjust frame margins to be smaller
    main_frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id='normal',
        showBoundary=0
    )

    footer_frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        1.2 * inch,
        id='footer',
        showBoundary=0
    )

    template = PageTemplate(
        id='template',
        frames=[main_frame, footer_frame],
        onPage=lambda canvas, doc: add_footer(canvas, doc, school)
    )
    doc.addPageTemplates([template])
    print("Frames and template created")

    # Styles with no left indent or first line indent
    title_style = ParagraphStyle(
        name="Title",
        fontSize=23,
        leading=28,
        alignment=TA_LEFT,
        leftIndent=0,
        firstLineIndent=0,
        spaceAfter=24,
        fontName="Helvetica-Bold"
    )
    school_style = ParagraphStyle(
        name="SchoolName",
        fontSize=16,
        leading=17,
        alignment=TA_LEFT,
        leftIndent=0,
        firstLineIndent=0,
        spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    subtitle_style = ParagraphStyle(
        name="Subtitle",
        fontSize=16,
        leading=17,
        alignment=TA_LEFT,
        leftIndent=0,
        firstLineIndent=0,
        spaceAfter=6,
        fontName="Helvetica"
    )
    header_style = ParagraphStyle(
        name="SectionHeader",
        fontSize=17,
        leading=18,
        alignment=TA_LEFT,
        leftIndent=0,
        firstLineIndent=0,
        spaceBefore=12,
        spaceAfter=6,
        fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        name="Body",
        fontSize=15,
        leading=17.5,
        alignment=TA_LEFT,
        leftIndent=0,
        firstLineIndent=0,
        fontName="Helvetica"
    )

    content = []
    print("Starting content generation...")

    # Load logo
    logo_path = "school_logo.png"
    if os.path.exists(logo_path):
        print(f"Logo file exists at {logo_path}")
        try:
            # Open the image with PIL first to check if it's white or black
            pil_image = PILImage.open(logo_path)
            print(f"Original image size: {pil_image.size}, mode: {pil_image.mode}")
            
            # Check if the logo is mostly white or black
            if is_mostly_white_or_black(pil_image):
                print("Logo is mostly white or black, recoloring to dark gray...")
                # Recolor the logo to dark gray
                pil_image = recolor_logo(pil_image)
                # Save the recolored logo
                pil_image.save(logo_path, format='PNG')
                print("Logo recolored and saved")
                
                # Verify the recolored image
                verify_img = PILImage.open(logo_path)
                print(f"Verified recolored image: {verify_img.size}, mode: {verify_img.mode}")
            
            # Create reportlab Image object
            logo = Image(logo_path)
            print(f"Created reportlab Image object: {logo.drawWidth}x{logo.drawHeight}")
            
            # Calculate aspect ratio to maintain proportions
            aspect = logo.imageWidth / float(logo.imageHeight)
            # Set width to 1.8 inches and calculate height
            logo.drawWidth = 1.8 * inch
            logo.drawHeight = logo.drawWidth / aspect
            print(f"Adjusted logo dimensions: {logo.drawWidth}x{logo.drawHeight}")
            
            school.logo_color = get_dominant_color(logo_path)
            print("Logo loaded and color extracted")
        except Exception as e:
            print(f"Error loading logo: {str(e)}")
            logo = Paragraph("LOGO", body_style)
            school.logo_color = (0, 45, 92)
    else:
        print(f"Logo file not found at {logo_path}")
        logo = Paragraph("LOGO", body_style)
        school.logo_color = (0, 45, 92)

    text_content = [
        Paragraph(f"{school.position_name.upper()} SEARCH", title_style),
        Paragraph(school.school_name.upper(), school_style),
        Paragraph(school.location, subtitle_style),
        Paragraph(school.website, subtitle_style),
        Paragraph(f"Start Date: {school.date}", subtitle_style)
    ]
    print("Text content created")

    # Create header table with adjusted column widths
    header_table = Table([
        [text_content, logo]
    ], colWidths=[doc.width - 2.5 * inch, 2.0 * inch])

    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (1, 0), 'TOP'),
        ('TOPPADDING', (0, 0), (1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (1, 0), 0),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('LEFTPADDING', (1, 0), (1, 0), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
    ]))

    content.append(header_table)
    content.append(Spacer(1, 48))
    print("Header added to content")

    # Search for and add school image
    print("Searching for school image...")
    if find_school_image(school):
        try:
            school_img = Image('school_image.jpg')
            # Set image width to page width minus margins
            school_img.drawWidth = doc.width
            # Maintain aspect ratio
            aspect = school_img.imageHeight / float(school_img.imageWidth)
            school_img.drawHeight = school_img.drawWidth * aspect
            content.append(school_img)
            content.append(Spacer(1, 20))
            print("School image added to PDF")
        except Exception as e:
            print(f"Error adding school image: {str(e)}")

    # Create mission statement title style with logo color
    mission_style = ParagraphStyle(
        name="MissionTitle",
        fontSize=23,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=24,
        fontName="Helvetica-Bold",
        textColor=colors.white
    )
    
    # Create mission statement text style
    mission_text_style = ParagraphStyle(
        name="MissionText",
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=24,
        fontName="Helvetica",
        leftIndent=0,
        rightIndent=0,
        firstLineIndent=0,
        textColor=colors.white
    )
    
    # Add background image for mission statement
    try:
        background_img = Image('students.jpg', width=doc.width, height=3*inch)
        content.append(background_img)
        print("Added background image for mission statement")
    except Exception as e:
        print(f"Error loading background image: {str(e)}")
    
    # Add mission statement title
    content.append(Paragraph("Mission Statement", mission_style))
    print("Mission statement title added")
    
    # Get mission statement text
    print("Getting mission statement...")
    mission_statement = get_mission_statement(school.website)
    print("Mission statement retrieved")
    
    # Create a table to control the width of the mission statement
    mission_table = Table([
        [Paragraph(mission_statement, mission_text_style)]
    ], colWidths=[doc.width * 0.6])
    
    # Style the table to center it
    mission_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 0),
    ]))
    
    content.append(mission_table)
    print("Mission statement added to content")

    # Build the PDF
    print("Building PDF...")
    doc.build(content)
    print(f"\nPDF has been generated successfully as '{output_filename}'")
    return doc

def add_footer(canvas, doc, school):
    """Add the footer image and top rectangle to the page"""
    try:
        # Get school statistics
        stats = get_school_statistics(school)
        
        # Draw footer image
        footer = Image('footer.png', width=7.2*inch, height=1.2*inch)
        footer.drawOn(canvas, doc.leftMargin - 0.5 * inch, doc.bottomMargin - 0.25 * inch)
        
        # Draw rectangle at the bottom of the page using the logo's color
        canvas.setFillColor(colors.HexColor(f'#{school.logo_color[0]:02x}{school.logo_color[1]:02x}{school.logo_color[2]:02x}'))
        canvas.rect(
            0,  # Start from left edge of page
            0,  # Start from bottom of page
            letter[0],  # Full page width
            0.5 * inch,  # Height of rectangle
            fill=1,
            stroke=0
        )
        
        # Draw rectangle at the top of the second page
        if doc.page > 1:  # Only on second page
            canvas.setFillColor(colors.HexColor(f'#{school.logo_color[0]:02x}{school.logo_color[1]:02x}{school.logo_color[2]:02x}'))
            canvas.rect(
                0,  # Start from left edge of page
                letter[1] - 3 * inch,  # Reduced from 3.5 to 3 inches
                letter[0],  # Full page width
                3 * inch,  # Height of rectangle
                fill=1,
                stroke=0
            )
            
            # Add "At a Glance" title
            canvas.setFillColor(colors.HexColor(f'#{school.logo_color[0]:02x}{school.logo_color[1]:02x}{school.logo_color[2]:02x}'))
            canvas.setFont("Helvetica-Bold", 20)
            canvas.drawString(0.55 * inch, letter[1] - 3.5 * inch, "At a Glance")  # Aligned with frame
            
            # Draw 6 circles in 2 rows (removed 2 circles)
            circle_radius = 0.45 * inch  # 0.9 inch diameter
            page_width = letter[0]
            page_height = letter[1]
            
            # Calculate spacing between circles (adjusted for 6 circles)
            total_width = page_width - 4 * inch  # 2 inches margin on each side (increased from 1 inch)
            spacing = total_width / 2  # Space between circles (3 per row)
            
            # Calculate starting x position (moved inward by 1 inch)
            start_x = 2 * inch  # 2 inches margin (increased from 1 inch)
            
            # Calculate y positions for both rows
            top_row_y = page_height - 4.2 * inch  # Adjusted to maintain same spacing from title
            bottom_row_y = top_row_y - 1.75 * inch  # Decreased from 2.5 to 1.75 inches below top row
            
            # Labels for each circle (removed 2 labels)
            labels = [
                "Established",
                "Total enrollment",
                "Total faculty",
                "Student/teacher ratio",
                "Students of color",
                "Campus size"
            ]
            
            # Values for each circle
            values = [
                stats["established"],
                stats["enrollment"],
                stats["faculty"],
                stats["ratio"],
                stats["diversity"],
                stats["campus"]
            ]
            
            # Draw circles and labels
            canvas.setFillColor(colors.HexColor(f'#{school.logo_color[0]:02x}{school.logo_color[1]:02x}{school.logo_color[2]:02x}'))
            canvas.setFont("Helvetica", 10)  # Set font for labels (removed -Bold)
            
            for row in range(2):
                y_pos = top_row_y if row == 0 else bottom_row_y
                for col in range(3):  # Changed from 4 to 3 circles per row
                    x_pos = start_x + col * spacing
                    # Draw circle
                    canvas.circle(x_pos, y_pos, circle_radius, fill=1, stroke=0)
                    # Draw label
                    label = labels[row * 3 + col]  # Changed from row * 4 to row * 3
                    canvas.setFillColor(colors.black)  # Set text color to black
                    canvas.drawCentredString(x_pos, y_pos - 0.8 * inch, label)
                    
                    # Draw value below label
                    canvas.setFont("Helvetica", 14)  # Changed from Helvetica-Bold to Helvetica
                    canvas.drawCentredString(x_pos, y_pos - 1.1 * inch, str(values[row * 3 + col]))
                    
                    # Reset fill color for next circle
                    canvas.setFillColor(colors.HexColor(f'#{school.logo_color[0]:02x}{school.logo_color[1]:02x}{school.logo_color[2]:02x}'))
                    
                    # Add enrollment image on top of the second circle
                    if row == 0 and col == 1:  # Second circle in top row
                        try:
                            enrollment_img = Image('enrollment_transparent.png', width=0.8 * inch, height=0.8 * inch)
                            enrollment_img.drawOn(canvas, x_pos - 0.4 * inch, y_pos - 0.4 * inch)
                        except Exception as e:
                            print(f"Could not load enrollment image: {str(e)}")
                    
                    # Add established image on top of the first circle
                    if row == 0 and col == 0:  # First circle in top row
                        try:
                            established_img = Image('established_transparent.png', width=0.8 * inch, height=0.8 * inch)
                            established_img.drawOn(canvas, x_pos - 0.4 * inch, y_pos - 0.4 * inch)
                        except Exception as e:
                            print(f"Could not load established image: {str(e)}")
                    
                    # Add faculty image on top of the third circle
                    if row == 0 and col == 2:  # Third circle in top row
                        try:
                            faculty_img = Image('faculty_transparent.png', width=0.8 * inch, height=0.8 * inch)
                            faculty_img.drawOn(canvas, x_pos - 0.4 * inch, y_pos - 0.4 * inch)
                        except Exception as e:
                            print(f"Could not load faculty image: {str(e)}")
                    
                    # Add ratio image on top of the first circle in bottom row
                    if row == 1 and col == 0:  # First circle in bottom row
                        try:
                            ratio_img = Image('ratio.png', width=0.8 * inch, height=0.8 * inch)
                            ratio_img.drawOn(canvas, x_pos - 0.4 * inch, y_pos - 0.4 * inch)
                        except Exception as e:
                            print(f"Could not load ratio image: {str(e)}")
                    
                    # Add diversity image on top of the second circle in bottom row
                    if row == 1 and col == 1:  # Second circle in bottom row
                        try:
                            diversity_img = Image('diversity.png', width=0.8 * inch, height=0.8 * inch)
                            diversity_img.drawOn(canvas, x_pos - 0.4 * inch, y_pos - 0.4 * inch)
                        except Exception as e:
                            print(f"Could not load diversity image: {str(e)}")
                    
                    # Add location image on top of the third circle in bottom row
                    if row == 1 and col == 2:  # Third circle in bottom row
                        try:
                            location_img = Image('location.png', width=0.8 * inch, height=0.8 * inch)
                            location_img.drawOn(canvas, x_pos - 0.4 * inch, y_pos - 0.4 * inch)
                        except Exception as e:
                            print(f"Could not load location image: {str(e)}")
            
    except:
        print("Could not add footer image or top rectangle")

def get_unique_keywords(school_name, notes_file):
    """Extract unique identifying keywords from the notes file using OpenAI"""
    try:
        print("Getting unique keywords...")
        client = setup()
        if not client:
            return []
            
        # Read the notes file (handle both PDF and text files)
        try:
            notes_content = ""
            if notes_file.lower().endswith('.pdf'):
                print(f"Reading PDF file: {notes_file}")
                with open(notes_file, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        notes_content += page.extract_text() + "\n"
            else:
                print(f"Reading text file: {notes_file}")
                with open(notes_file, 'r') as f:
                    notes_content = f.read()
                    
            print(f"Successfully read {len(notes_content)} characters from notes file")
            
        except Exception as e:
            print(f"Error reading notes file: {str(e)}")
            return []
            
        prompt = f"""Given the following notes about {school_name}, identify 10 unique keywords or phrases that would help distinguish this school from others in a search. 
        Focus on distinctive characteristics, unique programs, notable achievements, or special features.
        Only include the keywords/phrases, one per line, no explanations.
        
        Notes:
        {notes_content}
        """
        
        print("Sending request to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts unique identifying keywords from school descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        
        # Process the response to get keywords
        keywords = [line.strip() for line in response.choices[0].message.content.split('\n') if line.strip()]
        print(f"Found {len(keywords)} keywords")
        return keywords
        
    except Exception as e:
        print(f"Error getting keywords: {str(e)}")
        return []

class SchoolInfo:
    def __init__(self):
        self.school_name = "Catholic Memorial High School"
        self.position_name = "Athletic Director"
        self.location = "West Roxbury, MA"
        self.website = "https://www.catholicmemorial.org/"
        self.date = "July 2026"
        self.logo_color = (0, 45, 92)  # Default color, will be updated when logo is found
        self.keywords = []

def get_school_info():
    """Return Catholic Memorial school information"""
    school = SchoolInfo()
    
    # Use hardcoded notes file path
    notes_file = "CM_notes.pdf"
    
    # Get unique keywords from notes file
    school.keywords = get_unique_keywords(school.school_name, notes_file)
    
    return school

# region MAIN EXECUTION
if __name__ == '__main__':
    print("Current working directory:", os.getcwd())

    print("Starting program...")
    # Get school information from user input
    school = get_school_info()
    print("\nSchool info retrieved:", school.school_name)
    print("\nUnique identifying keywords:")
    for idx, keyword in enumerate(school.keywords, 1):
        print(f"{idx}. {keyword}")
    print()
    
    # Initialize and run
    print("Setting up OpenAI client...")
    client = setup()
    if client is None:
        print("ERROR: Failed to initialize OpenAI client. Exiting...")
        exit(1)
    print("OpenAI client setup complete")
    
    print("Finding logo...")
    if not find_logo(school):
        print("WARNING: Could not find logo, continuing with default...")
    
    print("Building PDF...")
    try:
        build_pdf(school)
        print("Program complete")
    except Exception as e:
        print(f"ERROR: Failed to build PDF: {str(e)}")
# endregion







#region PDF GENERATION
