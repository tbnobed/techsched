"""
Web scraping utility functions using Trafilatura.
This module provides functions to extract text content from websites.
"""

import logging
import trafilatura
from typing import Optional

def get_website_text_content(url: str) -> Optional[str]:
    """
    Extract the main text content from a website URL.
    
    This function fetches the website content and extracts the main text
    using Trafilatura. The extracted text is cleaned of HTML markup and
    formatted for easier reading.
    
    Args:
        url: The URL of the website to scrape
        
    Returns:
        str: The extracted text content or None if extraction failed
    """
    logging.debug(f"Fetching content from: {url}")
    
    try:
        # Send a request to the website
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            logging.error(f"Failed to download content from {url}")
            return None
            
        # Extract the main content
        text = trafilatura.extract(downloaded)
        
        if not text:
            logging.error(f"Failed to extract text from {url}")
            return None
            
        return text
    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")
        return None