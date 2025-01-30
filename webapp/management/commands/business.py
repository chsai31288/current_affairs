import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from django.core.management.base import BaseCommand
from webapp.models import BusinessArticle  # Updated model name to BusinessArticle
from django.db import transaction  # For bulk operations

# Load a pre-trained classification model
classifier = pipeline('text-classification', model='distilbert-base-uncased')

class Command(BaseCommand):
    help = 'Scrape all articles from BBC Business with AI classification'

    def handle(self, *args, **kwargs):
        # Configuration for the target website
        base_url = 'https://www.bbc.com/business'  # Updated URL for BBC Business
        config = {
            'article_selector': 'a[href^="/business"]',  # Adjusted to business section links
            'title_selectors': ['h3', 'h1'],  # Title selectors
            'summary_selector': 'p',  # Summary selector
            'image_selectors': ['img', 'meta[property="og:image"]'],  # Image selectors
            'base_url': 'https://www.bbc.com'
        }

        business_articles_to_create = []  # List to hold business articles for batch creation

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
                business_link = f"{config['base_url']}{relative_link}"

                try:
                    article_response = requests.get(business_link, timeout=10)
                    article_response.raise_for_status()
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')

                    # Extract business title (try multiple selectors)
                    business_title = None
                    for selector in config['title_selectors']:
                        title_tag = article_soup.select_one(selector)
                        if title_tag and title_tag.text.strip():
                            business_title = title_tag.text.strip()
                            break
                    if not business_title:
                        business_title = "No Title Available"

                    # Extract business image URL (try multiple selectors)
                    business_image_url = None
                    for selector in config['image_selectors']:
                        image_tag = article_soup.select_one(selector)
                        if image_tag:
                            if selector == 'img':
                                business_image_url = image_tag.get('data-src') or image_tag.get('src')  # Prioritize data-src
                            elif selector == 'meta[property="og:image"]':
                                business_image_url = image_tag.get('content')

                            if business_image_url:
                                break  # Stop if we found a valid image

                    # Ensure the image URL is absolute
                    if business_image_url and not business_image_url.startswith('http'):
                        business_image_url = f"{config['base_url']}{business_image_url}"

                    # Debug: Print the extracted image URL
                    if business_image_url:
                        self.stdout.write(f"Image Found: {business_image_url}")
                    else:
                        self.stdout.write(f"No image found for {business_link}")

                    # Extract business summary
                    summary_tag = article_soup.select_one(config['summary_selector'])
                    business_summary = summary_tag.text.strip() if summary_tag else "No Summary Available"

                    # Classify the article title using the AI model
                    try:
                        classification = classifier(business_title)
                        business_category = classification[0]['label']
                    except Exception as e:
                        business_category = 'Unknown'
                        self.stderr.write(f"Error in classification: {e}")

                    # Prepare the business article object for bulk creation
                    business_articles_to_create.append(
                        BusinessArticle(
                            business_title=business_title,
                            business_link=business_link,
                            business_image_url=business_image_url if business_image_url else None,  
                            business_category=business_category,
                            business_summary=business_summary
                        )
                    )

                except requests.exceptions.RequestException as e:
                    self.stderr.write(f"Error fetching article URL {business_link}: {e}")

        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching base URL {base_url}: {e}")

        # Bulk insert the business articles after scraping
        if business_articles_to_create:
            with transaction.atomic():
                BusinessArticle.objects.bulk_create(business_articles_to_create)

            self.stdout.write(f"{len(business_articles_to_create)} business articles scraped and saved.")
        else:
            self.stdout.write("No business articles were scraped.")
