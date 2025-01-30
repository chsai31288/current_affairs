from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('',views.index,name='index'),
    path('sports/', views.sports, name='sports'),
    path('news/', views.news, name='news'),
    path('business/', views.business, name='business'),
    path('travel/', views.travel, name='travel'),
    path('innovation/', views.innovation, name='innovation'),
    path('contact/', views.contact, name='contact'),
]
