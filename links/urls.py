from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search_and_check, name='search_and_check'),
    path('results/<str:keyword>/', views.search_results, name='search_results'),
    path('results/<str:keyword>/<str:search_id>/', views.search_results_progressive, name='search_results_progressive'),
    path('check-progress/<str:search_id>/', views.check_progress, name='check_progress'),
    path('sandbox/<int:link_id>/', views.sandbox_proxy, name='sandbox_proxy'),
    path('sandbox/resource/<int:link_id>/<str:encoded_url>/', views.sandbox_resource_proxy, name='sandbox_resource_proxy'),

    # Investigation routes
    path('investigate/<int:link_id>/', views.investigate_link, name='investigate_link'),
    path('investigate-url/', views.investigate_by_url, name='investigate_by_url'),
    path('investigation/<int:investigation_id>/', views.investigation_detail, name='investigation_detail'),
    path('investigations/', views.all_investigations, name='all_investigations'),
]
