
import requests as req
from bs4 import BeautifulSoup as bs
from datetime import datetime, timedelta
import csv
import json
from collections import defaultdict, Counter
import time
import random
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tqdm import tqdm

def scrape_cnbc(headers_list, keyword, start_date, duration_days, scrape_full):
    if scrape_full:
        filename = f'cnbcindonesia_full_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    else:
        filename = f'cnbcindonesia_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    end_date = start_date
    start_date = end_date - timedelta(days=duration_days)

    total_attempts = 0
    page = 1
    more_pages = True

    monthly_counts = defaultdict(int)
    yearly_counts = defaultdict(int)
    total_count = 0

    articles = []

    if not scrape_full:
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            wr = csv.writer(file, delimiter=',')
            wr.writerow(["Title", "Date", "Link"])
            while more_pages:
                headers = random.choice(headers_list)
                url_cnbc = f"https://www.cnbcindonesia.com/search?query={keyword}&p={page}&kanal=&tipe=artikel&date="
                try:
                    response = req.get(url_cnbc, headers=headers)
                    response.raise_for_status()
                    sop = bs(response.text, 'lxml')
                    ul = sop.find('ul', class_='list media_rows middle thumb terbaru gtm_indeks_feed')
                    if ul is None:
                        break
                    li = ul.find_all('li')
                    if not li:
                        break
                    for x in li:
                        total_attempts += 1
                        article = x.find('article')
                        if article is None:
                            continue
                        a_tag = article.find('a')
                        title = a_tag.text.strip() if a_tag and a_tag.text else None
                        if a_tag is None or (keyword.lower() not in title.lower()):
                            continue
                        link_art = a_tag['href']
                        response = req.get(link_art, headers=headers)
                        response.raise_for_status()
                        sop_ = bs(response.text, 'lxml')
                        art_div = sop_.find('div', class_='lm_content mt10')
                        if art_div is None:
                            continue
                        art = art_div.find('article')
                        if art is None:
                            continue
                        headline = art.find('h1')
                        if headline is None:
                            continue
                        headline = headline.text
                        date_div = art.find('div', class_='date')
                        if date_div is None:
                            continue
                        date = date_div.text
                        try:
                            article_date = datetime.strptime(date, '%d %B %Y %H:%M')
                        except ValueError:
                            print(f"Date parsing failed for date: {date}")
                            continue
                        if article_date < start_date:
                            more_pages = False
                            break
                        if article_date > end_date:
                            continue

                        print(f'No: {total_count + 1} | Date: {article_date.strftime("%d %B %Y")} | Title: {headline}')
                        wr.writerow([headline, article_date.strftime('%d %B %Y %H:%M'), link_art])
                        total_count += 1

                        monthly_counts[article_date.strftime('%Y-%m')] += 1
                        yearly_counts[article_date.year] += 1

                    page += 1
                    time.sleep(random.uniform(0.5, 2))

                except Exception as e:
                    print(f"Failed to process page {page}: {str(e)}")
                    break

    else:
        while more_pages:
            headers = random.choice(headers_list)
            url_cnbc = f"https://www.cnbcindonesia.com/search?query={keyword}&p={page}&kanal=&tipe=artikel&date="
            try:
                response = req.get(url_cnbc, headers=headers)
                response.raise_for_status()
                sop = bs(response.text, 'lxml')
                ul = sop.find('ul', class_='list media_rows middle thumb terbaru gtm_indeks_feed')
                if ul is None:
                    break
                li = ul.find_all('li')
                if not li:
                    break
                for x in li:
                    total_attempts += 1
                    article = x.find('article')
                    if article is None:
                        continue
                    a_tag = article.find('a')
                    title = a_tag.text.strip() if a_tag and a_tag.text else None
                    if a_tag is None or (keyword.lower() not in title.lower()):
                        continue
                    link_art = a_tag['href']
                    response = req.get(link_art, headers=headers)
                    response.raise_for_status()
                    sop_ = bs(response.text, 'lxml')
                    art_div = sop_.find('div', class_='lm_content mt10')
                    if art_div is None:
                        continue
                    art = art_div.find('article')
                    if art is None:
                        continue
                    headline = art.find('h1')
                    if headline is None:
                        continue
                    headline = headline.text
                    date_div = art.find('div', class_='date')
                    if date_div is None:
                        continue
                    date = date_div.text
                    try:
                        article_date = datetime.strptime(date, '%d %B %Y %H:%M')
                    except ValueError:
                        print(f"Date parsing failed for date: {date}")
                        continue
                    if article_date < start_date:
                        more_pages = False
                        break
                    if article_date > end_date:
                        continue

                    content_div = art.find('div', class_='detail_text')
                    if content_div is None:
                        continue
                    paragraphs = content_div.find_all('p')
                    content = '\n'.join([p.text.strip() for p in paragraphs if p.text.strip()])

                    print(f'No: {total_count + 1} | Date: {article_date.strftime("%d %B %Y")} | Title: {headline}')
                    articles.append({
                        "Title": headline,
                        "Date": article_date.strftime('%d %B %Y %H:%M'),
                        "Link": link_art,
                        "Content": content
                    })
                    total_count += 1

                    monthly_counts[article_date.strftime('%Y-%m')] += 1
                    yearly_counts[article_date.year] += 1

                page += 1
                time.sleep(random.uniform(0.5, 2))

            except Exception as e:
                print(f"Failed to process page {page}: {str(e)}")
                break

        with open(filename, 'w', encoding='utf-8') as file:
            json.dump(articles, file, ensure_ascii=False, indent=4)

    print(f"\nTotal news articles attempted: {total_attempts}")
    print(f"Total news articles successfully processed: {total_count}")

    print("\nYearly counts:")
    for year, count in sorted(yearly_counts.items(), reverse=True):
        print(f"{year}: {count} articles")

    print("\nMonthly counts:")
    for month, count in sorted(monthly_counts.items(), reverse=True):
        print(f"{month}: {count} articles")

    if scrape_full:
        analyze_sentiment = input("Do you want to perform sentiment analysis? (yes/no): ").strip().lower()
        while analyze_sentiment not in ['yes', 'no']:
            print("Invalid input. Please enter 'yes' or 'no'.")
            analyze_sentiment = input("Do you want to perform sentiment analysis? (yes/no): ").strip().lower()
        if analyze_sentiment == 'yes':
            vader_sentiment_counts = Counter()
            vader_sentiment_articles = {"Positive": [], "Negative": [], "Neutral": []}
            analyzer = SentimentIntensityAnalyzer()

            print("Performing sentiment analysis...")
            for article in tqdm(articles, desc="Sentiment Analysis"):
                content = article["Content"]
                vader_sentiment = analyzer.polarity_scores(content)["compound"]
                if vader_sentiment >= 0.05:
                    vader_sentiment_category = "Positive"
                elif vader_sentiment <= -0.05:
                    vader_sentiment_category = "Negative"
                else:
                    vader_sentiment_category = "Neutral"
                vader_sentiment_counts[vader_sentiment_category] += 1
                vader_sentiment_articles[vader_sentiment_category].append(article["Title"])

            print("\nVADER Sentiment Analysis Report:")
            for sentiment, count in vader_sentiment_counts.items():
                print(f"{sentiment}: {count} articles")
            for sentiment, titles in vader_sentiment_articles.items():
                print(f"\n{sentiment} Articles:")
                for i, title in enumerate(titles, 1):
                    print(f"{i}. {title}")

def main():
    print("Scraping cnbcindonesia.com\n")
    
    keyword_input = input("Enter the search keyword for the title: ")

    while True:
        duration_type = input("Enter the duration type (day/week/month/year): ").lower()
        if duration_type in ['day', 'week', 'month', 'year']:
            break
        else:
            print("Invalid duration type. Please enter 'day', 'week', 'month', or 'year'.")

    while True:
        duration_value = input(f"Enter the number of {duration_type}s: ")
        if duration_value.isdigit():
            duration_value = int(duration_value)
            break
        else:
            print("Invalid input. Please enter a valid number.")

    while True:
        scrape_full = input("Do you want to scrape full articles? (yes/no): ").strip().lower()
        if scrape_full in ['yes', 'no']:
            scrape_full = scrape_full == 'yes'
            break
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

    if duration_type == 'day':
        duration_days = duration_value
    elif duration_type == 'week':
        duration_days = duration_value * 7
    elif duration_type == 'month':
        duration_days = duration_value * 30
    elif duration_type == 'year':
        duration_days = duration_value * 365

    headers_list = [
        {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9'
        },
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9'
        },
        {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    ]

    today_date = datetime.now()
    start_date = today_date

    end_date = start_date - timedelta(days=duration_days)
    print(f"\nScraping articles from {end_date.strftime('%d %B %Y')} to {start_date.strftime('%d %B %Y')}\n")

    scrape_cnbc(headers_list, keyword_input, start_date, duration_days, scrape_full)

if __name__ == "__main__":
    main()
