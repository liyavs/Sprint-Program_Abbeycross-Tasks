import requests
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import nltk
import flet as ft
# Download required NLTK data
nltk.download('stopwords')
nltk.download('punkt')

# Initialize VADER sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Function to fetch Forex-related news using NewsAPI
def fetch_forex_news(api_key):
    url = f'https://newsapi.org/v2/everything?q=forex&language=en&apiKey={api_key}'
    response = requests.get(url)
    data = response.json()

    # Check the structure of the data
    if 'articles' in data:
        news_data = []
        for item in data['articles']:
            title = item.get('title', 'No Title')  # Use 'No Title' if 'title' key is missing
            description = item.get('description', 'No Description')  # Use 'No Description' if 'description' key is missing
            news_data.append({'title': title, 'description': description})
        return pd.DataFrame(news_data)
    else:
        print("No articles found in the response.")
        return pd.DataFrame()

# Function to preprocess text data
def preprocess_text(text):
    # Lowercase and remove special characters
    text = re.sub(r'\W', ' ', text.lower())
    return text

# Function to calculate sentiment using VADER
def calculate_sentiment_vader(text):
    sentiment = analyzer.polarity_scores(text)
    return sentiment['compound']

# Function to generate trading signal based on sentiment
def generate_trading_signal(sentiment_scores):
    avg_sentiment = sentiment_scores.mean()
    if avg_sentiment > 0:
        return 'Buy'
    elif avg_sentiment < 0:
        return 'Sell'
    else:
        return 'Hold'

# Main Flet app function
# Main Flet app function
def main(page: ft.Page):
    api_key = "92014a4f893f43ecb6d7f897ed997541"  # Replace with your NewsAPI key
    
    # Fetch news
    news_df = fetch_forex_news(api_key)

    # Apply preprocessing to news
    if not news_df.empty:
        news_df['cleaned_text'] = news_df['description'].apply(lambda x: preprocess_text(x) if isinstance(x, str) else '')

    # Apply sentiment analysis to cleaned text
    if not news_df.empty:
        news_df['sentiment'] = news_df['cleaned_text'].apply(calculate_sentiment_vader)

    # Generate trading signals based on sentiment
    if not news_df.empty:
        news_signal = generate_trading_signal(news_df['sentiment'])
    else:
        news_signal = 'No Data'

    # Print results to terminal
    print(f"Trading Signal based on News Sentiment: {news_signal}")
    if not news_df.empty:
        print("Sentiment Scores:")
        print(news_df[['title', 'sentiment']])
    else:
        print("No News Data Available")

    # Display results in Flet UI
    page.title = "Forex Sentiment Analysis"
    page.scroll = "adaptive"
    
    news_signal_text = ft.Text(f"Trading Signal based on News Sentiment: {news_signal}", size=18, color="purple")

    # Prepare data tables
    if not news_df.empty:
        news_data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Reports")),
                ft.DataColumn(ft.Text("Sentiment")),
            ],
            rows=[
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(row['title'])),
                        ft.DataCell(ft.Text(f"{row['sentiment']:.2f}")),
                    ]
                ) for index, row in news_df.iterrows()
            ],
        )
    else:
        news_data_table = ft.Text("No News Data Available")

    # Add all UI components to the page
    page.add(news_signal_text, ft.Divider(), news_data_table)

# Run the Flet app
if __name__ == "__main__":
    ft.app(target=main)
