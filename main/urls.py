from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('service/', views.service, name='service'),
    path('contact/', views.contact, name='contact'),
    path('join-with-us/', views.join_with_us, name='join_with_us'),
    path('track-consignment/', views.know_your_consignment, name='know_your_consignment'),
]
