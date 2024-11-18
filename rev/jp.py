from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import pandas as pd
import time
import re
from tqdm import tqdm
import torch
from transformers import BertTokenizer, BertForSequenceClassification
import string
import nltk
from nltk.corpus import stopwords
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# -katanya ga bakal random ketika skrip dijalankan kembali
#import random
#import numpy as np

# Set random seeds
#random.seed(42)
#np.random.seed(42)
#torch.manual_seed(42)
#if torch.cuda.is_available():
#    torch.cuda.manual_seed_all(42)  
# ---

# Download stopwords
nltk.download('stopwords')

# Create stemmer
factory = StemmerFactory()
stemmer = factory.create_stemmer()

# Get Indonesian stopwords
stop_words = set(stopwords.words('indonesian'))

def setup_driver():
    options = Options()
    options.headless = True
    options.add_argument("window-size=1200x600")
    options.add_argument("disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def translate_date_to_english(date_str):
    days = {
        'Senin': 'Monday',
        'Selasa': 'Tuesday',
        'Rabu': 'Wednesday',
        'Kamis': 'Thursday',
        'Jumat': 'Friday',
        'Sabtu': 'Saturday',
        'Minggu': 'Sunday'
    }
    
    months = {
        'Januari': 'January',
        'Februari': 'February',
        'Maret': 'March',
        'April': 'April',
        'Mei': 'May',
        'Juni': 'June',
        'Juli': 'July',
        'Agustus': 'August',
        'September': 'September',
        'Oktober': 'October',
        'November': 'November',
        'Desember': 'December'
    }
    
    for indo, eng in days.items():
        date_str = date_str.replace(indo, eng)
    
    for indo, eng in months.items():
        date_str = date_str.replace(indo, eng)
    
    return date_str

def parse_date(date_text):
    try:
        match = re.search(r'(\w+, \d+ \w+ \d+ \| \d+:\d+ WIB)', date_text)
        if match:
            date_str = match.group(1)
            date_str = translate_date_to_english(date_str)
            date_obj = datetime.strptime(date_str, '%A, %d %B %Y | %H:%M WIB')
            return date_obj
    except Exception as e:
        print(f"Error parsing date: {e}")
    return None

def preprocess_title(title):
    # Remove punctuation
    title = title.translate(str.maketrans('', '', string.punctuation))
    # Convert to lowercase
    title = title.lower()
    # Remove numbers
    title = re.sub(r'\d+', '', title)
    # Remove extra spaces
    title = ' '.join(title.split())
    # Remove stopwords
    title = ' '.join(word for word in title.split() if word not in stop_words)
    # Stemming
    title = ' '.join(stemmer.stem(word) for word in title.split())
    return title

def classify_title_bert(title, model, tokenizer, device):
    inputs = tokenizer(title, return_tensors="pt", max_length=512, truncation=True, padding=True)
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits
    probabilities = torch.softmax(logits, dim=-1)
    return probabilities.argmax().item(), probabilities.max().item()

def fetch_news(keyword, num_pages, sentiment_model, sentiment_tokenizer, label_model, label_tokenizer, device):
    driver = setup_driver()
    news_data = []
    classified_titles = []

    for page in tqdm(range(1, num_pages + 1), desc="Scraping pages"):
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
                text_content = item.get_attribute('textContent')
                title = title_element.text
                link = title_element.get_attribute('href')
                
                # Extract and parse date from text_content
                date_obj = parse_date(text_content)
                if not date_obj:
                    continue

                # Preprocess title
                processed_title = preprocess_title(title)

                # Analyze sentiment
                sentiment_label, sentiment_confidence = classify_title_bert(processed_title, sentiment_model, sentiment_tokenizer, device)

                # Classify title for specific label
                label, label_confidence = classify_title_bert(processed_title, label_model, label_tokenizer, device)
                
                classified_titles.append({
                    'original_title': title,
                    'processed_title': processed_title,
                    'sentiment_label': sentiment_label,
                    'sentiment_confidence': sentiment_confidence,
                    'label': label,
                    'label_confidence': label_confidence,
                    'date': date_obj.strftime('%A, %d %B %Y | %H:%M WIB'),
                    'link': link
                })

                news_data.append({
                    'title': title,
                    'link': link,
                    'date': date_obj.strftime('%A, %d %B %Y | %H:%M WIB')
                })
                
            except Exception as e:
                print(f"Error processing an item: {e}")
        
    driver.quit()
    return news_data, classified_titles

# Load models and tokenizers
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Sentiment model and tokenizer
sentiment_tokenizer = BertTokenizer.from_pretrained("indobenchmark/indobert-base-p2")
sentiment_model = BertForSequenceClassification.from_pretrained("indobenchmark/indobert-base-p2", num_labels=3)  # 3 labels: positif, negatif, netral
sentiment_model.to(device)

# Label model and tokenizer
label_tokenizer = BertTokenizer.from_pretrained("indobenchmark/indobert-base-p2")
label_model = BertForSequenceClassification.from_pretrained("indobenchmark/indobert-base-p2", num_labels=6)  # 6 labels: Provokatif, Hiperbola, Sensasional, Glorifikasi, Emosional, Informatif
label_model.to(device)

sentiment_label_mapping = {
    0: 'Negatif',
    1: 'Netral',
    2: 'Positif'
}

label_mapping = {
    0: 'Provokatif',
    1: 'Hiperbola',
    2: 'Sensasional',
    3: 'Glorifikasi',
    4: 'Emosional',
    5: 'Informatif'
}

keyword = input("Masukkan kata kunci berita: ")
num_pages = int(input("Masukkan jumlah halaman untuk diambil: "))

news_data, classified_titles = fetch_news(keyword, num_pages, sentiment_model, sentiment_tokenizer, label_model, label_tokenizer, device)
df_news = pd.DataFrame(news_data)
now = datetime.now().strftime("%Y%m%d%H%M%S")
output_path_csv = f'./jawapos_{now}.csv'
df_news.to_csv(output_path_csv, index=False)

# Ensure 'date' column exists before parsing
if 'date' in df_news.columns:
    # Parse 'date' column to datetime
    df_news['date'] = pd.to_datetime(df_news['date'], format='%A, %d %B %Y | %H:%M WIB')

    # Calculate number of articles per year and per month
    yearly_count = df_news['date'].dt.year.value_counts().sort_index(ascending=False)
    monthly_count = df_news.groupby([df_news['date'].dt.year.rename('year'), df_news['date'].dt.strftime('%B').rename('month')]).size().reset_index(name='count')
    monthly_count = monthly_count[monthly_count['count'] > 0].sort_values(by=['year', 'month'], ascending=[False, False])

    print(f'Scraping is finished. Total news processed: {len(news_data)}')
    print(f'Data saved to {output_path_csv}')
    print("\nJumlah berita per tahun:")
    for year, count in yearly_count.items():
        print(f"{year}: {count}")

    print("\nJumlah berita per bulan:")
    for index, row in monthly_count.iterrows():
        print(f"{row['month']} {row['year']}: {row['count']}")
else:
    print("No date column found in the DataFrame.")

# Display classified titles and their percentages
if classified_titles:
    sentiment_label_counts = {}
    specific_label_counts = {}
    
    for entry in classified_titles:
        sentiment_label = entry['sentiment_label']
        if sentiment_label not in sentiment_label_counts:
            sentiment_label_counts[sentiment_label] = 0
        sentiment_label_counts[sentiment_label] += 1

        specific_label = entry['label']
        if specific_label not in specific_label_counts:
            specific_label_counts[specific_label] = 0
        specific_label_counts[specific_label] += 1

    total_titles = len(classified_titles)
    
    print("\nSentiment classified titles and percentages:")
    for label, count in sentiment_label_counts.items():
        percentage = (count / total_titles) * 100
        print(f"Label {sentiment_label_mapping[label]}: {count} titles ({percentage:.2f}%)")
    
    print("\nSpecific classified titles and percentages:")
    for label, count in specific_label_counts.items():
        percentage = (count / total_titles) * 100
        print(f"Label {label_mapping[label]}: {count} titles ({percentage:.2f}%)")
        
    print("\nDetailed classified titles:")
    for entry in classified_titles:
        print(f"- {entry['original_title']} (Processed: {entry['processed_title']}, Sentiment: {sentiment_label_mapping[entry['sentiment_label']]}, Sentiment Confidence: {entry['sentiment_confidence']:.2f}, Label: {label_mapping[entry['label']]}, Label Confidence: {entry['label_confidence']:.2f})")

    # Save classified titles to Excel
    df_classified_titles = pd.DataFrame(classified_titles)
    df_classified_titles['sentiment_label'] = df_classified_titles['sentiment_label'].map(sentiment_label_mapping)
    df_classified_titles['label'] = df_classified_titles['label'].map(label_mapping)
    output_path_excel = f'./jawapos_labeling_{now}.xlsx'
    df_classified_titles.to_excel(output_path_excel, index=False)
    print(f"Classified titles saved to {output_path_excel}")
