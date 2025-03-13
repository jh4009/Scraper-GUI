import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_movie_details(movie_name: str) -> dict:
    """
    Scrape movie details from IMDb.
    
    Args:
        movie_name (str): Name of the movie to search for
    
    Returns:
        dict: Movie details or error message
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    try:
        search_url = f"https://www.imdb.com/find?q={movie_name.replace(' ', '+')}&ref_=nv_sr_sm"
        search_response = requests.get(search_url, headers=headers, timeout=10)
        search_response.raise_for_status()
        search_soup = BeautifulSoup(search_response.content, 'html.parser')
        first_result = search_soup.select_one('.ipc-metadata-list-summary-item a')
        
        if not first_result:
            return {"error": "No movie found with that name."}
        
        movie_url = "https://www.imdb.com" + first_result.get('href', '')
        movie_response = requests.get(movie_url, headers=headers, timeout=10)
        movie_response.raise_for_status()
        soup = BeautifulSoup(movie_response.content, 'html.parser')
        
        title_elem = soup.select_one('h1')
        title = title_elem.text.strip() if title_elem else "N/A"
        
        poster_elem = soup.select_one('img.ipc-image')
        poster_url = poster_elem.get('src', "N/A") if poster_elem else "N/A"
        
        year_elem = soup.select_one('a[href*="/releaseinfo"]')
        year = year_elem.text.strip() if year_elem else "N/A"
        
        rating_elem = soup.select_one('div[data-testid="hero-rating-bar__aggregate-rating__score"] span')
        rating = f"{rating_elem.text.strip()}/10" if rating_elem else "N/A"
        
        plot_elem = soup.select_one('span[data-testid="plot-xl"]')
        plot = plot_elem.text.strip() if plot_elem else "N/A"
        
        genre_elems = soup.select('.ipc-chip__text')
        genres = [genre.text.strip() for genre in genre_elems] if genre_elems else ["N/A"]
        
        movie_details = {
            "name": title,
            "poster_url": poster_url,
            "year": year,
            "rating": rating,
            "plot": plot,
            "genre": ', '.join(genres),
            "movie_link": movie_url
        }
        
        logger.info(f"Scraped movie details for '{movie_name}': {movie_details}")
        return movie_details
    except requests.exceptions.RequestException as e:
        error_msg = {"error": f"Network error: {e}"}
        logger.error(f"Network error in scrape_movie_details: {error_msg}")
        return error_msg
    except Exception as e:
        error_msg = {"error": f"An unexpected error occurred: {e}"}
        logger.error(f"Unexpected error in scrape_movie_details: {error_msg}")
        return error_msg