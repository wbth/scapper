import requests
from bs4 import BeautifulSoup
import json
import datetime
import random
import csv

# Daftar user-agent untuk menghindari pemblokiran
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.1 Safari/605.1.15',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
]

def get_soup(url):
    headers = {'User-Agent': random.choice(user_agents)}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    return soup

def scrape_sindonews(keyword, max_pages=None):
    base_url = 'https://search.sindonews.com/go?type=artikel&q={}&t={}'
    articles = []
    visited_links = set()
    page = 1

    while True:
        url = base_url.format(keyword, 20 * (page - 1)) if page > 1 else base_url.format(keyword, '')
        soup = get_soup(url)
        news_items = soup.select('div.news-content')

        if not news_items:
            print("No more news items found or end of pages.")
            break

        for item in news_items:
            try:
                link = item.select_one('div.news-title a').get('href')
                if link not in visited_links:
                    visited_links.add(link)
                    title = item.select_one('div.news-title a').text.strip()
                    date_text = item.select_one('div.news-date').text.strip()
                    category = item.select_one('div.newsc').text.capitalize().strip()

                    # Fetch the full article content
                    article_soup = get_soup(link)
                    content_element = article_soup.select_one('div.read__content')
                    content = content_element.text.strip() if content_element else ""

                    articles.append({
                        'title': title,
                        'link': link,
                        'category': category,
                        'news_date': date_text,
                        'content': content
                    })
            except Exception as e:
                print(f"Error processing an item: {e}")

        page += 1
        if max_pages and page > max_pages:
            break

    return articles

def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_to_csv(data, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['title', 'link', 'category', 'news_date'])
        for item in data:
            writer.writerow([item['title'], item['link'], item['category'], item['news_date']])

def display_articles(articles):
    for i, article in enumerate(articles, 1):
        print(f"No. {i} | Date: {article['news_date']} | Title: {article['title']}")

if __name__ == "__main__":
    keyword = input("Masukkan kata kunci berita: ")
    max_pages_input = input("Masukkan jumlah maksimal halaman untuk di-scrape atau biarkan kosong untuk unlimited: ")
    max_pages = int(max_pages_input) if max_pages_input.isdigit() else None

    articles = scrape_sindonews(keyword, max_pages)
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    json_filename = f'sindonews_articles_{keyword}_{timestamp}.json'
    csv_filename = f'sindonews_articles_{keyword}_{timestamp}.csv'
    save_to_json(articles, json_filename)
    save_to_csv(articles, csv_filename)
    display_articles(articles)
    print(f'Saved {len(articles)} articles to {json_filename} and {csv_filename}')
