import requests as req
from bs4 import BeautifulSoup as bs
import json
import csv
from datetime import datetime, timedelta
import random
import dateparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def get_random_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3', 
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36'
    ]
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
    }
    return headers

def get_date_range(period, num_periods, end_date=None):
    if end_date is None:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    if period == 'day':
        start_date = end_date - timedelta(days=num_periods)
    elif period == 'week':
        start_date = end_date - timedelta(weeks=num_periods)
    elif period == 'month':
        start_date = end_date - timedelta(days=30*num_periods)
    elif period == 'year':
        start_date = end_date - timedelta(days=365*num_periods)
    
    return start_date, end_date

def fetch_article_content(link, headers):
    try:
        article_response = req.get(link, headers=headers)
        article_response.raise_for_status()
        article_soup = bs(article_response.text, 'lxml')
        content_div = article_soup.find_all('div', class_='detail__body-text itp_bodycontent')
        content_text = ''
        for div in content_div:
            paragraphs = div.find_all('p')
            content_text += ''.join(p.text for p in paragraphs).replace('\n', '')
        
        content_text = content_text.replace('ADVERTISEMENT', '').replace('\r\r\rSCROLL TO CONTINUE WITH CONTENT\r', '')
        return content_text
    except req.exceptions.HTTPError as e:
        print(f"Failed to fetch article content: {e}")
        return None

def scrape_detik(keyword, period, num_periods, end_date=None):
    data = []
    keyword_lower = keyword.lower()
    start_date, end_date = get_date_range(period, num_periods, end_date)
    page = 1

    print(f'Periode scraping antara tanggal {start_date.strftime("%Y-%m-%d")} hingga {end_date.strftime("%Y-%m-%d")}')

    while True:
        headers = get_random_headers()
        url = f'https://www.detik.com/search/searchnews?query={keyword}&sortby=time&page={page}'
        response = req.get(url, headers=headers)
        response.raise_for_status()
        soup = bs(response.text, 'lxml')
        li = soup.find('div', class_='list media_rows list-berita')
        if not li:
            break
        articles = li.find_all('article')
        if not articles:
            break

        for article in articles:
            link = article.find('a')['href']
            date_str = article.find('a').find('span', class_='date').text.replace('WIB', '').replace('detikNews', '').split(',')[1].strip()
            date = dateparser.parse(date_str, settings={'DATE_ORDER': 'DMY'})
            if date < start_date:
                return data
            if date > end_date:
                continue
            headline = article.find('a').find('h2').text

            if keyword_lower in headline.lower():
                data.append({
                    'headline': headline,
                    'date': date_str,
                    'link': link,
                    'content': None  # Placeholder for content to be fetched later
                })
                print(f'No. {len(data)} | Date: {date_str} | Title: {headline}')
        
        page += 1

    return data

def fetch_content_for_analysis(data):
    headers = get_random_headers()
    valid_data = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_article_content, entry['link'], headers): entry for entry in data}
        for future in as_completed(futures):
            entry = futures[future]
            content = future.result()
            if content:
                entry['content'] = content
                valid_data.append(entry)
    return valid_data

def save_data(data):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    filename_json = f'detik0_{timestamp}.json'
    with open(filename_json, 'w') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)
    
    filename_csv = f'detik0_{timestamp}.csv'
    with open(filename_csv, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=['headline', 'date', 'link'])
        writer.writeheader()
        for entry in data:
            writer.writerow({'headline': entry['headline'], 'date': entry['date'], 'link': entry['link']})

    return filename_json, filename_csv

def analyze_sentiment(data):
    analyzer = SentimentIntensityAnalyzer()
    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    sentiment_articles = {'positive': [], 'neutral': [], 'negative': []}

    for article in data:
        content = article['content']
        headline = article['headline']
        sentiment_score = analyzer.polarity_scores(content)

        if sentiment_score['compound'] >= 0.05:
            sentiment = 'positive'
        elif sentiment_score['compound'] <= -0.05:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        sentiment_counts[sentiment] += 1
        sentiment_articles[sentiment].append(headline)

    return sentiment_counts, sentiment_articles

# Contoh penggunaan:
keyword = input("Masukkan kata kunci pencarian: ")
period = input("Masukkan periode waktu (day/week/month/year): ")
num_periods = int(input("Masukkan jumlah periode: "))
end_date = input("Masukkan tanggal akhir pencarian (format: YYYY-MM-DD, default tanggal hari ini): ") or None

data = scrape_detik(keyword, period, num_periods, end_date)
valid_data = fetch_content_for_analysis(data)
filename_json, filename_csv = save_data(valid_data)

while True:
    analyze_sentiment_option = input("Apakah Anda ingin melakukan analisis sentimen? (yes/no): ").strip().lower()
    if analyze_sentiment_option in ['yes', 'no']:
        break

if analyze_sentiment_option == 'yes':
    sentiment_counts, sentiment_articles = analyze_sentiment(valid_data)

    print(f'Total berita yang berhasil diproses: {len(valid_data)}')
    print(f'Saved data to {filename_json}')
    print(f'Saved data to {filename_csv}')

    print("\nLaporan Sentimen:")
    for sentiment, count in sentiment_counts.items():
        print(f"{sentiment.capitalize()}: {count} berita")
        for headline in sentiment_articles[sentiment]:
            print(f"- {headline}")
else:
    print(f'Total berita yang berhasil diproses: {len(valid_data)}')
    print(f'Saved data to {filename_json}')
    print(f'Saved data to {filename_csv}')
