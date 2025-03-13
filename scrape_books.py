import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_book_details(book_name: str) -> dict:
    """
    Scrape book details from Open Library.
    
    Args:
        book_name (str): Name of the book to search for
    
    Returns:
        dict: Book details or error message
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
    try:
        search_url = f"https://openlibrary.org/search?q={book_name.replace(' ', '+')}&mode=everything"
        search_response = requests.get(search_url, headers=headers, timeout=10)
        search_response.raise_for_status()
        search_soup = BeautifulSoup(search_response.content, 'html.parser')
        first_result = search_soup.select_one('li.searchResultItem')
        
        if not first_result:
            return {"error": "No book found with that name."}
        
        title_elem = first_result.select_one('h3.booktitle a')
        title = title_elem.text.strip() if title_elem else "N/A"
        
        cover_elem = first_result.select_one('span.bookcover img')
        cover_url = "https:" + cover_elem['src'] if cover_elem else "N/A"
        
        author_elem = first_result.select_one('span.bookauthor a')
        author = author_elem.text.strip() if author_elem else "N/A"
        
        year_elem = first_result.select_one('span.resultDetails span')
        year = year_elem.text.strip().replace("First published in ", "") if year_elem else "N/A"
        
        rating_elem = first_result.select_one('span.ratingsByline span[itemprop="ratingValue"]')
        rating = rating_elem.text.strip() if rating_elem else "N/A"
        
        book_link = first_result.select_one('h3.booktitle a')['href'] if first_result.select_one('h3.booktitle a') else "N/A"
        detail_url = f"https://openlibrary.org{book_link}" if book_link != "N/A" else "N/A"
        
        description = "N/A"
        if detail_url != "N/A":
            detail_response = requests.get(detail_url, headers=headers, timeout=10)
            detail_response.raise_for_status()
            detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
            description_elem = detail_soup.select_one('div.read-more__content')
            description = " ".join([p.text.strip() for p in description_elem.find_all('p') if not p.find('a')]) if description_elem else "N/A"
        
        book_details = {
            "name": title,
            "cover_url": cover_url,
            "author": author,
            "year": year,
            "rating": rating,
            "description": description,
            "book_link": detail_url
        }
        
        return book_details
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}