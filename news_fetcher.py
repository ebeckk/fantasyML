# news_fetcher.py
import requests
from newsapi import NewsApiClient
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Make sure to download the required sentiment lexicon
nltk.download('vader_lexicon')

class PremierLeagueNewsFetcher:
    def __init__(self, news_api_key):
        self.newsapi = NewsApiClient(api_key=news_api_key)
        self.sia = SentimentIntensityAnalyzer()

    def fetch_news(self, days=7):
        """
        Fetch general Premier League news from a list of news sources.
        """
        news_sources = [
            'bbc-sport',
            'talksport',
            'goal',
            'skysports'
        ]
        articles_response = self.newsapi.get_everything(
            q='Premier League',
            sources=','.join(news_sources),
            language='en',
            sort_by='publishedAt',
            # Use ISO date format (you can adjust the from_param date if needed)
            from_param=(requests.utils.formatdate(None, usegmt=True))
        )
        return self._process_articles(articles_response.get('articles', []))

    def fetch_team_news(self, team_name):
        """
        Fetch news related to a specific team in the Premier League.
        """
        articles_response = self.newsapi.get_everything(
            q=f'"{team_name}" Premier League',
            language='en',
            sort_by='publishedAt'
        )
        return self._process_articles(articles_response.get('articles', []))

    def fetch_player_news(self, player_name):
        """
        Fetch news for a specific player.
        """
        articles_response = self.newsapi.get_everything(
            q=f'"{player_name}" Premier League',
            language='en',
            sort_by='publishedAt'
        )
        return self._process_articles(articles_response.get('articles', []))

    def _process_articles(self, articles):
        """
        Process articles to include sentiment and a simple sentiment classification.
        """
        processed_news = []
        for article in articles:
            description = article.get('description', '')
            sentiment = self.sia.polarity_scores(description or "")
            processed_news.append({
                'title': article.get('title'),
                'description': description,
                'url': article.get('url'),
                'published_at': article.get('publishedAt'),
                'source': article.get('source', {}).get('name'),
                'sentiment': sentiment,
                'sentiment_category': self._categorize_sentiment(sentiment)
            })
        return processed_news

    def _categorize_sentiment(self, sentiment):
        """
        Categorize the sentiment based on the compound score.
        """
        compound = sentiment['compound']
        if compound >= 0.05:
            return 'positive'
        elif compound <= -0.05:
            return 'negative'
        else:
            return 'neutral'