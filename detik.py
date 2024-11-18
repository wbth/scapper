import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

# Generate a filename with the current datetime
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
file_name = f"detikcom_{current_time}.csv"

# File setup
with open(file_name, "w", encoding="utf-8") as f:
    headers = "Title,Category,Day,Date,Summary,URL\n"
    f.write(headers)
    
    # Input for query search
    query_search = input("Enter the keyword or query for the search (title search only): ")
    
    # Set start date to one year ago from today
    start_date = datetime.now() - timedelta(days=365)
    
    # Set end date to today
    end_date = datetime.now()

    # Format dates for URL
    start_date_sorttime = start_date.strftime("%d/%m/%Y")
    end_datetodatex = end_date.strftime("%d/%m/%Y")

    page = 1
    total_articles_processed = 0  # Counter for total processed articles
    while True:
        url = f"https://www.detik.com/search/searchnews?query={query_search}&fromdatex={start_date_sorttime}&todatex={end_datetodatex}&page={page}"
        print(f"Fetching page {page}: {url}")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("div", {"class": "media__text"})
            
            if not articles:
                print("No more articles found, ending scrape.")
                break
            
            for article in articles:
                try:
                    title = article.find("h3", {"class": "media__title"}).get_text(strip=True)
                    link = article.find("a", {"class": "media__link"})['href']
                    category = article.find("h2", {"class": "media__subtitle"}).get_text(strip=True)
                    summary = article.find("div", {"class": "media__desc"}).get_text(strip=True)
                    date_text = article.find("div", {"class": "media__date"}).find("span")['title']
                    #day = article.find("div", {"class": "media__date"}).get_text(strip=True)
            
                    #row = f"{title.replace(',', '|')}, {category}, {day}, {date_text}, {summary.replace(',', ' ')}, {link}\n"
                    row = f"{title.replace(',', '|')}, {category}, {date_text}, {summary.replace(',', ' ')}, {link}\n"
                   
                    f.write(row)
                    total_articles_processed += 1  # Increment counter for each successful process
                except AttributeError:
                    continue
        except requests.HTTPError as e:
            print(f"HTTP error fetching page {page}: {e}")
            break
        except requests.RequestException as e:
            print(f"Request exception on page {page}: {e}")
            break
        
        page += 1

    print(f"Total articles processed: {total_articles_processed}")
