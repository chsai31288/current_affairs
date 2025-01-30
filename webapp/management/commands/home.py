import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from django.core.management.base import BaseCommand
from webapp.models import HomeArticle  # Updated model name
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
        base_url = 'https://www.bbc.com/'  # Updated URL
        config = {
            'article_selector': 'a[href^="/news"]',
            'title_selectors': ['h3', 'h1'],  
            'summary_selector': 'p',
            'image_selectors': ['img', 'meta[property="og:image"]'],  
            'base_url': 'https://www.bbc.com'
        }

        articles_to_create = []  # List to hold articles for batch creation

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
                article_url = f"{config['base_url']}{relative_link}"

                try:
                    article_response = requests.get(article_url, timeout=10)
                    article_response.raise_for_status()
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')

                    # Extract title (try multiple selectors)
                    title = None
                    for selector in config['title_selectors']:
                        title_tag = article_soup.select_one(selector)
                        if title_tag and title_tag.text.strip():
                            title = title_tag.text.strip()
                            break
                    if not title:
                        title = "No Title Available"

                    # Extract image URL (try multiple selectors)
                    image_url = None
                    for selector in config['image_selectors']:
                        image_tag = article_soup.select_one(selector)
                        if image_tag:
                            # Prioritize 'data-src', 'src', and 'srcset' (lazy-loaded images)
                            if selector == 'img':
                                image_url = image_tag.get('data-src') or image_tag.get('src') or image_tag.get('srcset')
                            elif selector == 'meta[property="og:image"]':
                                image_url = image_tag.get('content')

                            if image_url:
                                break  # Stop if we found a valid image

                    # Ensure the image URL is absolute
                    if image_url and not image_url.startswith('http'):
                        image_url = f"{config['base_url']}{image_url}"

                    # Skip placeholder images (e.g., grey placeholder)
                    if image_url and not is_valid_image_url(image_url):
                        image_url = None  # Reset to None if it's a placeholder

                    # Debug: Print the extracted image URL
                    self.stdout.write(f"Image URL: {image_url if image_url else 'No image found'}")

                    # Extract summary
                    summary_tag = article_soup.select_one(config['summary_selector'])
                    summary = summary_tag.text.strip() if summary_tag else "No Summary Available"

                    # Classify the article title using the AI model
                    try:
                        classification = classifier(title)
                        category = classification[0]['label']
                    except Exception as e:
                        category = 'Unknown'
                        self.stderr.write(f"Error in classification: {e}")

                    # Prepare the article object for bulk creation
                    articles_to_create.append(
                        HomeArticle(
                            title=title,
                            link=article_url,
                            image_url=image_url if image_url else None,  
                            category=category,
                            summary=summary
                        )
                    )

                except requests.exceptions.RequestException as e:
                    self.stderr.write(f"Error fetching article URL {article_url}: {e}")

        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching base URL {base_url}: {e}")

        # Bulk insert the articles after scraping
        if articles_to_create:
            with transaction.atomic():
                HomeArticle.objects.bulk_create(articles_to_create)

            self.stdout.write(f"{len(articles_to_create)} articles scraped and saved.")
        else:
            self.stdout.write("No articles were scraped.")
