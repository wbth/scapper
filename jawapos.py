from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import pandas as pd
import time

def setup_driver():
    options = Options()
    options.headless = True
    options.add_argument("window-size=1200x600")
    options.add_argument("disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_news(keyword):
    driver = setup_driver()
    page = 1
    news_data = []
    while True:
        url = f'https://www.jawapos.com/search?q={keyword}&sort=latest&page={page}'
        driver.get(url)
        driver.implicitly_wait(10)
        time.sleep(3)  # Allow some time for the page to fully load

        # Collect news items on the current page
        news_items = driver.find_elements(By.CSS_SELECTOR, '.latest__item')
        if not news_items:
            print("No more news items found or end of pages.")
            break
        
        for item in news_items:
            try:
                title_element = item.find_element(By.CSS_SELECTOR, 'h2.latest__title > a')
                title = title_element.text
                link = title_element.get_attribute('href')
                news_data.append({
                    'title': title,
                    'link': link
                })
            except Exception as e:
                print(f"Error processing an item: {e}")
        
        page += 1  # Increment page number to fetch next page

    driver.quit()
    return news_data

keyword = input("Masukkan kata kunci berita: ")
news_data = fetch_news(keyword)
df_news = pd.DataFrame(news_data)
now = datetime.now().strftime("%Y%m%d%H%M%S")
output_path = f'./jawapos_{now}.csv'
df_news.to_csv(output_path, index=False)
print(f'Scraping is finished. Total news processed: {len(news_data)}')
print(f'Data saved to {output_path}')
