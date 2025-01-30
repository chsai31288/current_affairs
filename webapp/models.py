from django.db import models

class HomeArticle(models.Model):
    title = models.CharField(max_length=2555)
    link = models.URLField(unique=True)  # Ensure each article link is unique
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=500, default='Unknown')  # e.g., 'Sports', 'Politics'
    summary = models.TextField(blank=True)
    published_at = models.DateTimeField(auto_now_add=True)  # Add timestamp

    def __str__(self):
        return self.title

class SportsArticle(models.Model):
    sports_title = models.CharField(max_length=500)  # Increased limit
    sports_link = models.URLField(max_length=1000)  # URLs can be long
    sports_image_url = models.URLField(max_length=1000, blank=True, null=True)
    sports_category = models.CharField(max_length=100, default="Unknown")
    sports_summary = models.TextField(blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)  # Timestamp when the article is scraped

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Sports Article'
        verbose_name_plural = 'Sports Articles'
        ordering = ['-date_created']  # Sort by most recent first
        
class NewsArticle(models.Model):
    news_title = models.CharField(max_length=500)
    news_link = models.URLField(unique=True)
    news_image_url = models.URLField(blank=True, null=True)
    news_category = models.CharField(max_length=100, default='Unknown')
    news_summary = models.TextField(blank=True, null=True)
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scraped_at']

    def __str__(self):
        return self.news_title
    
class BusinessArticle(models.Model):
    business_title = models.CharField(max_length=255)
    business_link = models.URLField(unique=True)
    business_image_url = models.URLField(blank=True, null=True)
    business_category = models.CharField(max_length=100)
    business_summary = models.TextField(blank=True, null=True)
    business_published_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_title
    

class InnovationArticle(models.Model):
    innovation_title = models.CharField(max_length=255)
    innovation_link = models.URLField(unique=True)
    innovation_image_url = models.URLField(blank=True, null=True)
    innovation_category = models.CharField(max_length=100, default="Uncategorized")
    innovation_summary = models.TextField(blank=True, null=True)
    innovation_created_at = models.DateTimeField(auto_now_add=True)
    business_published_at = models.DateTimeField(blank=True, null=True)  # Add this field

    def __str__(self):
        return self.innovation_title
    
class TravelArticle(models.Model):
    travel_title = models.CharField(max_length=255)
    travel_link = models.URLField(unique=True)
    travel_image_url = models.URLField(blank=True, null=True)
    travel_category = models.CharField(max_length=100, default="Uncategorized")
    travel_summary = models.TextField(blank=True, null=True)
    travel_created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.travel_title