import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_text(url: str, headers: dict) -> str:
    """
    Scrape text content from a webpage.
    
    Args:
        url (str): The URL to scrape text from
        headers (dict): HTTP headers for requests
    
    Returns:
        str: Extracted text content or None if unsuccessful
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text_content = soup.get_text(separator="\n", strip=True)
        return text_content if text_content else None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in scrape_text: {e}")
        return None