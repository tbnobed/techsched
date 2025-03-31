#!/usr/bin/env python
"""
Script to convert Markdown documentation to HTML format
"""
import os
import logging
import re
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Files to convert
files_to_convert = [
    ('user_guide.md', 'Plex_Engineering_User_Guide.html'),
    ('technician_quick_start.md', 'Plex_Engineering_Technician_Quick_Start_Guide.html'),
    ('admin_guide.md', 'Plex_Engineering_Admin_Guide.html'),
    ('user_admin_guide.md', 'Plex_Engineering_User_Admin_Guide.html'),
    ('backup_checklist.md', 'Plex_Engineering_Backup_Checklist.html'),
    ('update_steps.md', 'Plex_Engineering_Update_Steps.html'),
    ('release_notes.md', 'Plex_Engineering_Release_Notes.html')
]

# HTML template with CSS styling
HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
body {{
    font-family: Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}}
h1, h2, h3, h4, h5, h6 {{
    color: #2c3e50;
    margin-top: 1em;
    margin-bottom: 0.5em;
}}
h1 {{
    font-size: 28px;
    border-bottom: 1px solid #eee;
    padding-bottom: 10px;
}}
h2 {{
    font-size: 24px;
    border-bottom: 1px solid #eee;
    padding-bottom: 5px;
}}
h3 {{ font-size: 20px; }}
h4 {{ font-size: 18px; }}
h5 {{ font-size: 16px; }}
h6 {{ font-size: 14px; }}
code {{
    font-family: monospace;
    background-color: #f5f5f5;
    padding: 3px;
    border-radius: 3px;
}}
pre {{
    font-family: monospace;
    background-color: #f5f5f5;
    padding: 10px;
    border-radius: 5px;
    overflow-x: auto;
    white-space: pre-wrap;
}}
a {{ color: #3498db; }}
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 20px 0;
}}
th, td {{
    border: 1px solid #ddd;
    padding: 8px;
    text-align: left;
}}
th {{
    background-color: #f5f5f5;
    font-weight: bold;
}}
tr:nth-child(even) {{ background-color: #f9f9f9; }}
img {{
    max-width: 100%;
    height: auto;
}}
blockquote {{
    margin: 0;
    padding-left: 15px;
    border-left: 4px solid #ddd;
    color: #666;
}}
ul, ol {{
    padding-left: 30px;
}}
hr {{
    border: 0;
    border-top: 1px solid #eee;
    margin: 20px 0;
}}
.cover {{
    text-align: center;
    margin-bottom: 50px;
}}
.cover h1 {{
    font-size: 36px;
    border-bottom: none;
}}
.footer {{
    margin-top: 50px;
    padding-top: 20px;
    border-top: 1px solid #eee;
    text-align: center;
    color: #777;
    font-size: 12px;
}}
    </style>
</head>
<body>
    <div class="cover">
        <h1>{title}</h1>
        <p>Plex Engineering Documentation</p>
        <p>Generated on {date}</p>
    </div>
    
    <div class="content">
        {content}
    </div>
    
    <div class="footer">
        <p>© {year} Plex Engineering - Documentation generated from markdown</p>
    </div>
</body>
</html>"""

# Simple markdown parser functions
def parse_headings(line):
    """Parses Markdown headings (# Heading)"""
    match = re.match(r'^(#{1,6})\s+(.+)$', line)
    if match:
        level = len(match.group(1))
        return f'<h{level}>{match.group(2)}</h{level}>'
    return None

def parse_code_block(lines, i):
    """Parses Markdown code blocks (```code```)"""
    if not lines[i].startswith('```'):
        return None, i
    
    content = []
    i += 1
    while i < len(lines) and not lines[i].startswith('```'):
        content.append(lines[i])
        i += 1
    
    if i < len(lines):  # Skip the closing ```
        i += 1
    
    return f'<pre><code>{"".join(content)}</code></pre>', i

def parse_list_item(line):
    """Parses Markdown list items (- item or * item)"""
    match = re.match(r'^(\s*)([-*])\s+(.+)$', line)
    if match:
        return f'<li>{match.group(3)}</li>'
    return None

def parse_paragraph(line):
    """Parses a regular paragraph"""
    if line.strip() == '':
        return ''
    return f'<p>{line}</p>'

def parse_horizontal_rule(line):
    """Parses Markdown horizontal rule (---, ***, ___)"""
    if re.match(r'^([-*_])\1{2,}$', line.strip()):
        return '<hr>'
    return None

def parse_link(text):
    """Parses Markdown links [text](url)"""
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    return re.sub(pattern, r'<a href="\2">\1</a>', text)

def parse_emphasis(text):
    """Parses Markdown emphasis (*text* or _text_)"""
    # Bold with ** or __
    text = re.sub(r'(\*\*|__)(.*?)\1', r'<strong>\2</strong>', text)
    # Italic with * or _
    text = re.sub(r'(\*|_)(.*?)\1', r'<em>\2</em>', text)
    return text

def parse_inline_code(text):
    """Parses Markdown inline code (`code`)"""
    return re.sub(r'`(.*?)`', r'<code>\1</code>', text)

def parse_line(line):
    """Parses a single line of Markdown"""
    # Process inline elements
    line = parse_link(line)
    line = parse_emphasis(line)
    line = parse_inline_code(line)
    return line

def convert_to_html(input_file, output_file):
    """Convert markdown to HTML using simple parsing"""
    try:
        logger.info(f"Converting {input_file} to {output_file}...")
        
        # Read markdown file
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Parse markdown to HTML
        html_content = []
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Check for headings
            heading = parse_headings(line)
            if heading:
                html_content.append(heading)
                i += 1
                continue
            
            # Check for code blocks
            code_block, new_i = parse_code_block(lines, i)
            if code_block:
                html_content.append(code_block)
                i = new_i
                continue
            
            # Check for list items
            list_item = parse_list_item(line)
            if list_item:
                html_content.append('<ul>') # Simplified: always using ul
                html_content.append(list_item)
                
                j = i + 1
                while j < len(lines) and parse_list_item(lines[j].rstrip()):
                    html_content.append(parse_list_item(lines[j].rstrip()))
                    j += 1
                
                html_content.append('</ul>')
                i = j
                continue
            
            # Check for horizontal rule
            hr = parse_horizontal_rule(line)
            if hr:
                html_content.append(hr)
                i += 1
                continue
            
            # Default to paragraph
            if line.strip():
                html_content.append(parse_paragraph(parse_line(line)))
            else:
                html_content.append('')  # Empty line
            
            i += 1
        
        # Join all HTML content
        html_body = '\n'.join(html_content)
        
        # Get title from filename
        title = os.path.splitext(os.path.basename(input_file))[0].replace('_', ' ').title()
        
        # Get current date and year
        now = datetime.now()
        date = now.strftime("%B %d, %Y")
        year = now.year
        
        # Create complete HTML document
        complete_html = HTML_TEMPLATE.format(
            title=title,
            content=html_body,
            date=date,
            year=year
        )
        
        # Write to HTML file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(complete_html)
        
        logger.info(f"Successfully created {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error converting {input_file}: {e}")
        return False

def main():
    """Main function to convert all files"""
    logger.info("Starting HTML conversion process...")
    
    # Create a docs directory if it doesn't exist
    output_dir = 'html_docs'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created directory: {output_dir}")
    
    # Convert each file
    successful = 0
    failed = 0
    
    for input_file, output_file in files_to_convert:
        if not os.path.exists(input_file):
            logger.warning(f"Input file {input_file} does not exist. Skipping.")
            continue
        
        output_path = os.path.join(output_dir, output_file)
        
        if convert_to_html(input_file, output_path):
            successful += 1
        else:
            failed += 1
    
    logger.info(f"Conversion completed. Success: {successful}, Failed: {failed}")
    
    if successful > 0:
        logger.info(f"HTML files are available in the '{output_dir}' directory")
    
    return successful, failed

if __name__ == "__main__":
    main()