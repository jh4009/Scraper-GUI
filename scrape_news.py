import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_news_headlines(url: str) -> tuple:
    """
    Scrape news headlines from a webpage.
    
    Args:
        url (str): The URL to scrape headlines from
    
    Returns:
        tuple: Tuple of headline strings or None if unsuccessful
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        headlines = soup.find_all(['h1', 'h2', 'h3'])
        
        if not headlines:
            headlines = soup.find_all('a', class_=lambda x: x and ('excerpt' in x.lower() or 'title' in x.lower() or 'headline' in x.lower()))
        
        if not headlines:
            headlines = soup.find_all('a')
        
        def is_valid_headline(text):
            if len(text) < 15 or any(phrase.lower() in text.lower() for phrase in ['home', 'about', 'contact', 'login', 'register']):
                return False
            return True
        
        headline_texts = []
        for headline in headlines:
            text = headline.get_text().strip()
            if text and is_valid_headline(text) and text not in headline_texts:
                headline_texts.append(text)
        
        return tuple(headline_texts) if headline_texts else None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in scrape_news_headlines: {e}")
        return None