from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import pandas as pd
import time
from tqdm import tqdm
import re

def setup_driver():
    options = Options()
    options.headless = True
    options.add_argument("window-size=1200x600")
    options.add_argument("disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def extract_date_from_url(url):
    if url:  # Memastikan bahwa URL tidak None
        # Ekstraksi tanggal dari URL dengan asumsi format yyyy/mm/dd
        match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if match:
            return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return None  # Mengembalikan None jika URL None atau tidak ada tanggal yang ditemukan

def fetch_news(keyword, max_pages):
    driver = setup_driver()
    news_data = []
    page = 1

    while True:
        url = f'https://search.kompas.com/search/?q={keyword}#gsc.tab=0&gsc.q={keyword}&gsc.page={page}'
        driver.get(url)
        driver.implicitly_wait(10)
        time.sleep(3)

        news_items = driver.find_elements(By.CSS_SELECTOR, '.gs-title .gs-title')
        seen_links = set()
        progress_bar = tqdm(news_items, desc=f'Processing Page {page}')

        for item in progress_bar:
            try:
                link = item.get_attribute('href')
                title = item.get_attribute('textContent').strip()
                article_date = extract_date_from_url(link)
                if link and title and link not in seen_links and not link.startswith('https://www.kompas.com/tag/'):
                    seen_links.add(link)
                    news_data.append({
                        'title': title,
                        'link': link,
                        'article_date': article_date
                    })
            except Exception as e:
                print(f"Error processing an item: {e}")

        page += 1
        if max_pages and page >= max_pages:
            break
        if "tidak ada hasil" in driver.page_source:
            break

    driver.quit()
    return news_data

keyword = input("Masukkan kata kunci berita: ")
max_pages = input("Masukkan jumlah maksimal halaman yang akan discrap (kosongkan untuk unlimited): ")
max_pages = int(max_pages) if max_pages else None

news_data = fetch_news(keyword, max_pages)
df_news = pd.DataFrame(news_data)
df_news = df_news.drop_duplicates(subset=['link'])  # Menghapus duplikasi berdasarkan link
df_news['article_date'] = pd.to_datetime(df_news['article_date'], format='%d-%m-%Y', errors='coerce')  # Konversi ke datetime
df_news.sort_values('article_date', ascending=False, inplace=True)  # Urutkan berdasarkan tanggal terbaru
now = datetime.now().strftime("%Y%m%d%H%M%S")
output_path = f'./kompascom_{now}.csv'
df_news.to_csv(output_path, index=False)
print(f'Scraping is finished. Total news processed: {len(news_data)}')
print(f'Data saved to {output_path}')
