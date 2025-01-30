import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from django.core.management.base import BaseCommand
from webapp.models import InnovationArticle  # Updated model name to InnovationArticle
from django.db import transaction  # For bulk operations

# Load a pre-trained classification model
classifier = pipeline('text-classification', model='distilbert-base-uncased')

class Command(BaseCommand):
    help = 'Scrape all articles from BBC Innovation with AI classification'

    def handle(self, *args, **kwargs):
        # Configuration for the target website
        base_url = 'https://www.bbc.com/innovation'  # Updated URL for BBC Innovation
        config = {
            'article_selector': 'a[href^="/innovation"]',  # Adjusted to innovation section links
            'title_selectors': ['h3', 'h1'],  # Title selectors
            'summary_selector': 'p',  # Summary selector
            'image_selectors': ['img', 'meta[property="og:image"]'],  # Image selectors
            'base_url': 'https://www.bbc.com'
        }

        innovation_articles_to_create = []  # List to hold innovation articles for batch creation

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
                innovation_link = f"{config['base_url']}{relative_link}"

                try:
                    article_response = requests.get(innovation_link, timeout=10)
                    article_response.raise_for_status()
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')

                    # Extract innovation title (try multiple selectors)
                    innovation_title = None
                    for selector in config['title_selectors']:
                        title_tag = article_soup.select_one(selector)
                        if title_tag and title_tag.text.strip():
                            innovation_title = title_tag.text.strip()
                            break
                    if not innovation_title:
                        innovation_title = "No Title Available"

                    # Extract innovation image URL (try multiple selectors)
                    innovation_image_url = None
                    for selector in config['image_selectors']:
                        image_tag = article_soup.select_one(selector)
                        if image_tag:
                            if selector == 'img':
                                innovation_image_url = image_tag.get('data-src') or image_tag.get('src')  # Prioritize data-src
                            elif selector == 'meta[property="og:image"]':
                                innovation_image_url = image_tag.get('content')

                            if innovation_image_url:
                                break  # Stop if we found a valid image

                    # Ensure the image URL is absolute
                    if innovation_image_url and not innovation_image_url.startswith('http'):
                        innovation_image_url = f"{config['base_url']}{innovation_image_url}"

                    # Debug: Print the extracted image URL
                    if innovation_image_url:
                        self.stdout.write(f"Image Found: {innovation_image_url}")
                    else:
                        self.stdout.write(f"No image found for {innovation_link}")

                    # Extract innovation summary
                    summary_tag = article_soup.select_one(config['summary_selector'])
                    innovation_summary = summary_tag.text.strip() if summary_tag else "No Summary Available"

                    # Classify the article title using the AI model
                    try:
                        classification = classifier(innovation_title)
                        innovation_category = classification[0]['label']
                    except Exception as e:
                        innovation_category = 'Unknown'
                        self.stderr.write(f"Error in classification: {e}")

                    # Prepare the innovation article object for bulk creation
                    innovation_articles_to_create.append(
                        InnovationArticle(
                            innovation_title=innovation_title,
                            innovation_link=innovation_link,
                            innovation_image_url=innovation_image_url if innovation_image_url else None,  
                            innovation_category=innovation_category,
                            innovation_summary=innovation_summary
                        )
                    )

                except requests.exceptions.RequestException as e:
                    self.stderr.write(f"Error fetching article URL {innovation_link}: {e}")

        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching base URL {base_url}: {e}")

        # Bulk insert the innovation articles after scraping
        if innovation_articles_to_create:
            with transaction.atomic():
                InnovationArticle.objects.bulk_create(innovation_articles_to_create)

            self.stdout.write(f"{len(innovation_articles_to_create)} innovation articles scraped and saved.")
        else:
            self.stdout.write("No innovation articles were scraped.")
