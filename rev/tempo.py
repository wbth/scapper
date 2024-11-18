import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import time
import json
import random

def convert_date(date_string):
    try:
        return datetime.fromisoformat(date_string).strftime('%Y-%m-%d %H:%M WIB')
    except ValueError:
        return datetime.now().strftime('%Y-%m-%d %H:%M WIB')

async def fetch(session, url):
    retries = 3
    for _ in range(retries):
        try:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"Network error for URL: {url}, retrying... ({e})")
            await asyncio.sleep(5)
    print(f"Failed to retrieve content from URL: {url} after {retries} retries.")
    return None

async def get_article_content(session, url):
    html = await fetch(session, url)
    if html is None:
        return {
            'Title': "Failed to retrieve",
            'Date': "N/A",
            'Content': "N/A",
            'URL': url
        }
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract title
    title_tag = soup.find('h1', class_='title')
    title = title_tag.get_text(strip=True) if title_tag else "No title found"
    
    # Extract date from meta property article:published_time
    date_tag = soup.find('meta', {'property': 'article:published_time'})
    date = convert_date(date_tag['content']) if date_tag and date_tag.has_attr('content') else "No date found"
    
    # Extract article content
    article_body = soup.find('div', itemprop='articleBody')
    content = ' '.join([para.get_text() for para in article_body.find_all('p')]) if article_body else "No content found"
    
    # Remove 'TEMPO.CO, Jakarta - ' from content
    if content.startswith('TEMPO.CO, Jakarta - '):
        content = content.replace('TEMPO.CO, Jakarta - ', '', 1)
    
    # Remove content from "Pilihan editor: " to the end
    editor_choice_index = content.find('Pilihan editor: ')
    if editor_choice_index != -1:
        content = content[:editor_choice_index]

    return {
        'Title': title,
        'Date': date,
        'URL': url,
        'Content': content
    }

async def get_news_data(query, max_results=10):
    base_url = "https://www.tempo.co/search"
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0) Gecko/20100101 Firefox/71.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/605.1.15 (KHTML, seperti Gecko) Version/13.0.4 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, seperti Gecko) Chrome/76.0.3809.132 Safari/537.36 Edge/18.18362'
    ]
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    news_data = []
    seen_urls = set()
    async with aiohttp.ClientSession(headers=headers) as session:
        page = 1
        while len(news_data) < max_results:
            params = {
                'q': query,
                'page': page
            }
            async with session.get(base_url, params=params) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), 'html.parser')

            articles = soup.find_all('div', {'class': 'card-box'})
            if not articles:
                break
            
            tasks = []
            new_articles_count = 0
            for article in articles:
                title_tag = article.find('h2', class_='title')
                if title_tag:
                    url = title_tag.find('a')['href']
                    if url not in seen_urls:
                        seen_urls.add(url)
                        tasks.append(get_article_content(session, url))
                        new_articles_count += 1
                    
            results = await asyncio.gather(*tasks)
            news_data.extend(results)
            
            if len(news_data) >= max_results or new_articles_count == 0:
                break
            
            page += 1
            if len(news_data) < max_results:
                print("Pausing for 5 seconds...")
                await asyncio.sleep(5)
    
    return news_data

def save_to_excel(news_data, filename='news_data.xlsx'):
    if not news_data:
        print("No news data found for the given query.")
        return
    
    df = pd.DataFrame(news_data, columns=['Title', 'Date', 'URL'])
    df.to_excel(filename, index=False)

def save_to_json(news_data, filename='news_data.json'):
    if not news_data:
        print("No news data found for the given query.")
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(news_data, f, ensure_ascii=False, indent=4)

def main():
    query = input("Enter the query: ")
    max_results = int(input("Enter the maximum number of results: "))
    
    loop = asyncio.get_event_loop()
    news_data = loop.run_until_complete(get_news_data(query, max_results))
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_filename = f'temponnewsdata_{timestamp}.xlsx'
    json_filename = f'temponnewsdata_{timestamp}.json'
    
    save_to_excel(news_data, excel_filename)
    save_to_json(news_data, json_filename)
    
    if news_data:
        print(f"Data saved to {excel_filename} and {json_filename}")
    else:
        print("No data found to save.")

if __name__ == "__main__":
    main()
