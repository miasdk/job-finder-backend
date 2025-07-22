from django.urls import path
from .simple_api import (
    simple_dashboard_api, 
    simple_jobs_api, 
    simple_job_detail_api,
    get_user_preferences,
    update_user_preferences
)

app_name = 'jobs_api'

urlpatterns = [
    # Simple API endpoints without DRF complexity
    path('dashboard/', simple_dashboard_api, name='dashboard'),
    path('jobs/', simple_jobs_api, name='jobs'),
    path('jobs/<int:job_id>/', simple_job_detail_api, name='job-detail'),
    
    # User preferences endpoints
    path('preferences/', get_user_preferences, name='get-preferences'),
    path('preferences/update/', update_user_preferences, name='update-preferences'),
]