from django.shortcuts import render
from webapp.models import HomeArticle
from webapp.models import SportsArticle
from webapp.models import NewsArticle
from .models import BusinessArticle
from .models import InnovationArticle
from .models import TravelArticle

def index(request):
    articles = HomeArticle.objects.order_by('-published_at')
    return render(request, 'index.html', {'articles': articles})
    


def sports(request):
    articles = SportsArticle.objects.order_by('-date_created')
    return render(request, 'sports.html', {'articles': articles})

def news(request):
    articles = NewsArticle.objects.order_by('-scraped_at')
    return render(request, 'news.html', {'articles': articles})

def business(request):
    articles = BusinessArticle.objects.order_by('-business_published_at')
    return render(request, 'business.html', {'articles': articles})

def innovation(request):
    articles = InnovationArticle.objects.order_by('-business_published_at')
    return render(request, 'innovation.html', {'articles': articles})
def travel(request):
    articles = TravelArticle.objects.order_by('-travel_created_at')
    return render(request, 'travel.html', {'articles': articles})

def contact(request):
    return render(request, 'contact.html')