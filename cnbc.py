import requests as req
from bs4 import BeautifulSoup as bs
from datetime import datetime
import csv

def scrape_cnbc(headers, keyword, start_date=None, end_date=None):
    # Generating a unique filename with the current date and time
    filename = f'cnbcindonesia_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    if start_date:
        start_date = datetime.strptime(start_date, '%d/%m/%Y')  # Adjusted for 'DD/MM/YYYY' format
    if end_date:
        end_date = datetime.strptime(end_date, '%d/%m/%Y')  # Adjusted for 'DD/MM/YYYY' format
    else:
        end_date = datetime.now()  # Use today's date if not provided

    a = 1  # Counter for successfully processed news
    total_attempts = 0  # Counter for attempted news processing
    page = 1  # Start from the first page
    more_pages = True  # Flag to control the loop

    with open(filename, 'a', newline='', encoding='utf-8') as file:
        wr = csv.writer(file, delimiter=',')
        while more_pages:
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
                    article_date = datetime.strptime(date, '%d %B %Y %H:%M')
                    if start_date and article_date < start_date:
                        continue
                    if article_date > end_date:
                        more_pages = False
                        break

                    print(f'done[{a}] > {headline[0:10]}')
                    a += 1
                    wr.writerow([headline, article_date, link_art])
                page += 1

            except Exception as e:
                print(f"Failed to process page {page}: {str(e)}")
                break

        print(f"Total news articles attempted: {total_attempts}")
        print(f"Total news articles successfully processed: {a-1}")

# Prompt for user input
start_date_input = input("Enter the start date (DD/MM/YYYY): ")
end_date_input = input("Enter the end date (DD/MM/YYYY) or press enter to use today's date: ")
keyword_input = input("Enter the search keyword for the title: ")

# Example usage
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language': 'en-US,en;q=0.9'
}
scrape_cnbc(headers, keyword_input, start_date_input, end_date_input)
