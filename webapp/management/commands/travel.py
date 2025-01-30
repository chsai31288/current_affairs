import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from django.core.management.base import BaseCommand
from webapp.models import TravelArticle  # Updated model name to TravelArticle
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
    help = 'Scrape all articles from BBC Travel with AI classification'

    def handle(self, *args, **kwargs):
        # Configuration for the target website
        base_url = 'https://www.bbc.com/travel'  # Updated URL for BBC Travel
        config = {
            'article_selector': 'a[href^="/travel"]',  # Adjusted to travel section links
            'title_selectors': ['h3', 'h1'],  # Title selectors
            'summary_selector': 'p',  # Summary selector
            'image_selectors': ['img', 'meta[property="og:image"]'],  # Image selectors
            'base_url': 'https://www.bbc.com'
        }

        travel_articles_to_create = []  # List to hold travel articles for batch creation

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
                travel_link = f"{config['base_url']}{relative_link}"

                try:
                    article_response = requests.get(travel_link, timeout=10)
                    article_response.raise_for_status()
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')

                    # Extract travel title (try multiple selectors)
                    travel_title = None
                    for selector in config['title_selectors']:
                        title_tag = article_soup.select_one(selector)
                        if title_tag and title_tag.text.strip():
                            travel_title = title_tag.text.strip()
                            break
                    if not travel_title:
                        travel_title = "No Title Available"

                    # Extract travel image URL (try multiple selectors)
                    travel_image_url = None
                    for selector in config['image_selectors']:
                        image_tag = article_soup.select_one(selector)
                        if image_tag:
                            if selector == 'img':
                                travel_image_url = image_tag.get('data-src') or image_tag.get('src')  # Prioritize data-src
                            elif selector == 'meta[property="og:image"]':
                                travel_image_url = image_tag.get('content')

                            if travel_image_url:
                                break  # Stop if we found a valid image

                    # Ensure the image URL is absolute
                    if travel_image_url and not travel_image_url.startswith('http'):
                        travel_image_url = f"{config['base_url']}{travel_image_url}"

                    # Skip placeholder images (e.g., grey placeholder)
                    if travel_image_url and not is_valid_image_url(travel_image_url):
                        travel_image_url = None  # Reset to None if it's a placeholder

                    # Debug: Print the extracted image URL
                    if travel_image_url:
                        self.stdout.write(f"Image Found: {travel_image_url}")
                    else:
                        self.stdout.write(f"No image found for {travel_link}")

                    # Extract travel summary
                    summary_tag = article_soup.select_one(config['summary_selector'])
                    travel_summary = summary_tag.text.strip() if summary_tag else "No Summary Available"

                    # Classify the article title using the AI model
                    try:
                        classification = classifier(travel_title)
                        travel_category = classification[0]['label']
                    except Exception as e:
                        travel_category = 'Unknown'
                        self.stderr.write(f"Error in classification: {e}")

                    # Prepare the travel article object for bulk creation
                    travel_articles_to_create.append(
                        TravelArticle(
                            travel_title=travel_title,
                            travel_link=travel_link,
                            travel_image_url=travel_image_url if travel_image_url else None,  
                            travel_category=travel_category,
                            travel_summary=travel_summary
                        )
                    )

                except requests.exceptions.RequestException as e:
                    self.stderr.write(f"Error fetching article URL {travel_link}: {e}")

        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching base URL {base_url}: {e}")

        # Bulk insert the travel articles after scraping
        if travel_articles_to_create:
            with transaction.atomic():
                TravelArticle.objects.bulk_create(travel_articles_to_create)

            self.stdout.write(f"{len(travel_articles_to_create)} travel articles scraped and saved.")
        else:
            self.stdout.write("No travel articles were scraped.")
