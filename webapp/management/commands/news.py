import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from django.core.management.base import BaseCommand
from webapp.models import NewsArticle  # Updated model name to NewsArticle
from django.db import transaction  # For bulk operations

# Load a pre-trained classification model
classifier = pipeline('text-classification', model='distilbert-base-uncased')

# Check if the image URL is a valid one
def is_valid_image_url(url):
    # List of keywords that are typically part of placeholder image URLs
    placeholder_keywords = ['grey-placeholder', 'placeholder', 'no-image']
    if any(keyword in url.lower() for keyword in placeholder_keywords):
        return False
    return True

class Command(BaseCommand):
    help = 'Scrape all articles from BBC News with AI classification'

    def handle(self, *args, **kwargs):
        # Configuration for the target website
        base_url = 'https://www.bbc.com/news'  # Updated URL for BBC News
        config = {
            'article_selector': 'a[href^="/news"]',  # Adjusted to news section links
            'title_selectors': ['h3', 'h1'],  # Title selectors
            'summary_selector': 'p',  # Summary selector
            'image_selectors': ['img', 'meta[property="og:image"]'],  # Image selectors
            'base_url': 'https://www.bbc.com'
        }

        news_articles_to_create = []  # List to hold news articles for batch creation

        try:
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors
            soup = BeautifulSoup(response.content, 'html.parser')

            # Select all article links
            article_links = set(
                link['href'] for link in soup.select(config['article_selector']) if link.get('href')
            )

            for relative_link in article_links:
                # Construct the full article URL
                news_link = f"{config['base_url']}{relative_link}"

                try:
                    article_response = requests.get(news_link, timeout=10)
                    article_response.raise_for_status()
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')

                    # Extract news title (try multiple selectors)
                    news_title = None
                    for selector in config['title_selectors']:
                        title_tag = article_soup.select_one(selector)
                        if title_tag and title_tag.text.strip():
                            news_title = title_tag.text.strip()
                            break
                    if not news_title:
                        news_title = "No Title Available"

                    # Extract news image URL (try multiple selectors)
                    news_image_url = None
                    for selector in config['image_selectors']:
                        image_tag = article_soup.select_one(selector)
                        if image_tag:
                            if selector == 'img':
                                news_image_url = image_tag.get('data-src') or image_tag.get('src')  # Prioritize data-src
                            elif selector == 'meta[property="og:image"]':
                                news_image_url = image_tag.get('content')

                            if news_image_url:
                                break  # Stop if we found a valid image

                    # Ensure the image URL is absolute
                    if news_image_url and not news_image_url.startswith('http'):
                        news_image_url = f"{config['base_url']}{news_image_url}"

                    # Skip placeholder images (e.g., grey placeholder)
                    if news_image_url and not is_valid_image_url(news_image_url):
                        news_image_url = None  # Reset to None if it's a placeholder

                    # Debug: Print the extracted image URL
                    if news_image_url:
                        self.stdout.write(f"Image Found: {news_image_url}")
                    else:
                        self.stdout.write(f"No image found for {news_link}")

                    # Extract news summary
                    summary_tag = article_soup.select_one(config['summary_selector'])
                    news_summary = summary_tag.text.strip() if summary_tag else "No Summary Available"

                    # Classify the article title using the AI model
                    try:
                        classification = classifier(news_title)
                        news_category = classification[0]['label']
                    except Exception as e:
                        news_category = 'Unknown'
                        self.stderr.write(f"Error in classification: {e}")

                    # Prepare the news article object for bulk creation
                    news_articles_to_create.append(
                        NewsArticle(
                            news_title=news_title,
                            news_link=news_link,
                            news_image_url=news_image_url if news_image_url else None,  
                            news_category=news_category,
                            news_summary=news_summary
                        )
                    )

                except requests.exceptions.RequestException as e:
                    self.stderr.write(f"Error fetching article URL {news_link}: {e}")

        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching base URL {base_url}: {e}")

        # Bulk insert the news articles after scraping
        if news_articles_to_create:
            with transaction.atomic():
                NewsArticle.objects.bulk_create(news_articles_to_create)

            self.stdout.write(f"{len(news_articles_to_create)} news articles scraped and saved.")
        else:
            self.stdout.write("No news articles were scraped.")
