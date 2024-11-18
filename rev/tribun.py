from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import pandas as pd
import re
import time
from tqdm import tqdm  # For progress visualization

def setup_driver():
    options = Options()
    options.headless = False  # Disabled headless mode for debugging
    options.add_argument("window-size=1200x600")
    options.add_argument("disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    print("Driver set up successfully.")
    return driver

def extract_date_from_url(url):
    # Regular expression to find date patterns in the URL
    match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if match:
        return datetime.strptime(f"{match.group(1)}-{match.group(2)}-{match.group(3)}", "%Y-%m-%d").strftime("%d-%m-%Y")
    return None

def fetch_news(keyword, max_pages):
    driver = setup_driver()
    news_data = []
    page = 1
    seen = set()  # Set to track seen (title, link) tuples

    try:
        while True:
            if max_pages and page > max_pages:
                print("Reached maximum page limit.")
                break
            url = f'https://www.tribunnews.com/search?q={keyword}&cx=partner-pub-7486139053367666%3A4965051114&cof=FORID%3A10&ie=UTF-8&siteurl=www.tribunnews.com#gsc.tab=0&gsc.q={keyword}&gsc.page={page}'
            print(f"Fetching URL: {url}")
            driver.get(url)
            driver.implicitly_wait(10)
            time.sleep(3)  # Allow some time for the page to fully load

            # Attempt to find news items on the current page
            news_items = driver.find_elements(By.CSS_SELECTOR, 'a.gs-title')
            if not news_items:
                print("No more news items found or end of pages.")
                break

            for item in tqdm(news_items, desc=f'Processing Page {page}'):
                try:
                    link = item.get_attribute('href')
                    title = item.get_attribute('textContent').strip()
                    if link and title and (title, link) not in seen and '/tag/' not in link and '/topic/' not in link:
                        date = extract_date_from_url(link)
                        if date:  # Only add entries with a valid date
                            news_data.append({
                                'title': title,
                                'link': link,
                                'date': date
                            })
                            seen.add((title, link))
                except Exception as e:
                    print(f"Error processing an item: {e}")

            page += 1  # Increment page number to fetch next page

    except Exception as e:
        print(f"An error occurred during fetching news: {e}")
    finally:
        driver.quit()

    return news_data

# Get user input for keyword and pages
keyword = input("Masukkan kata kunci berita: ")
max_pages_input = input("Masukkan maksimal jumlah halaman yang di-scrape atau tekan Enter untuk unlimited: ")
max_pages = None if max_pages_input.strip() == "" else int(max_pages_input)

# Fetch and save the news data
news_data = fetch_news(keyword, max_pages)
df_news = pd.DataFrame(news_data)
df_news['date'] = pd.to_datetime(df_news['date'], format='%d-%m-%Y')
df_news = df_news.drop_duplicates().sort_values(by='date', ascending=False)  # Sort by date and remove duplicates

# Save to CSV
now = datetime.now().strftime("%Y%m%d%H%M%S")
output_path = f'./tribunnews_{now}.csv'
df_news.to_csv(output_path, index=False)
print(f"Scraping is finished. Total news processed: {len(news_data)}")
print(f"Data saved to {output_path}")
