from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('api/score-job/<int:job_id>/', views.score_job_ajax, name='score_job_ajax'),
]