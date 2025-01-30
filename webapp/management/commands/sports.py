import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from django.core.management.base import BaseCommand
from webapp.models import SportsArticle  # Updated model name to SportsArticle
from django.db import transaction  # For bulk operations

# Load a pre-trained classification model
classifier = pipeline('text-classification', model='distilbert-base-uncased')

class Command(BaseCommand):
    help = 'Scrape all articles from BBC Sport with AI classification'

    def handle(self, *args, **kwargs):
        # Configuration for the target website
        base_url = 'https://www.bbc.com/sport'  # Updated URL for BBC Sport
        config = {
            'article_selector': 'a[href^="/sport"]',  # Adjusted to sport section links
            'title_selectors': ['h3', 'h1'],  # Title selectors
            'summary_selector': 'p',  # Summary selector
            'image_selectors': ['img', 'meta[property="og:image"]'],  # Image selectors
            'base_url': 'https://www.bbc.com'
        }

        sports_articles_to_create = []  # List to hold sports articles for batch creation

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
                sports_link = f"{config['base_url']}{relative_link}"

                try:
                    article_response = requests.get(sports_link, timeout=10)
                    article_response.raise_for_status()
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')

                    # Extract sports title (try multiple selectors)
                    sports_title = None
                    for selector in config['title_selectors']:
                        title_tag = article_soup.select_one(selector)
                        if title_tag and title_tag.text.strip():
                            sports_title = title_tag.text.strip()
                            break
                    if not sports_title:
                        sports_title = "No Title Available"

                    # Extract sports image URL (try multiple selectors)
                    sports_image_url = None
                    for selector in config['image_selectors']:
                        image_tag = article_soup.select_one(selector)
                        if image_tag:
                            if selector == 'img':
                                sports_image_url = image_tag.get('data-src') or image_tag.get('src')  # Prioritize data-src
                            elif selector == 'meta[property="og:image"]':
                                sports_image_url = image_tag.get('content')

                            if sports_image_url:
                                break  # Stop if we found a valid image

                    # Ensure the image URL is absolute
                    if sports_image_url and not sports_image_url.startswith('http'):
                        sports_image_url = f"{config['base_url']}{sports_image_url}"

                    # Debug: Print the extracted image URL
                    if sports_image_url:
                        self.stdout.write(f"Image Found: {sports_image_url}")
                    else:
                        self.stdout.write(f"No image found for {sports_link}")

                    # Extract sports summary
                    summary_tag = article_soup.select_one(config['summary_selector'])
                    sports_summary = summary_tag.text.strip() if summary_tag else "No Summary Available"

                    # Classify the article title using the AI model
                    try:
                        classification = classifier(sports_title)
                        sports_category = classification[0]['label']
                    except Exception as e:
                        sports_category = 'Unknown'
                        self.stderr.write(f"Error in classification: {e}")

                    # Prepare the sports article object for bulk creation
                    sports_articles_to_create.append(
                        SportsArticle(
                            sports_title=sports_title,
                            sports_link=sports_link,
                            sports_image_url=sports_image_url if sports_image_url else None,  
                            sports_category=sports_category,
                            sports_summary=sports_summary
                        )
                    )

                except requests.exceptions.RequestException as e:
                    self.stderr.write(f"Error fetching article URL {sports_link}: {e}")

        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching base URL {base_url}: {e}")

        # Bulk insert the sports articles after scraping
        if sports_articles_to_create:
            with transaction.atomic():
                SportsArticle.objects.bulk_create(sports_articles_to_create)

            self.stdout.write(f"{len(sports_articles_to_create)} sports articles scraped and saved.")
        else:
            self.stdout.write("No sports articles were scraped.")
