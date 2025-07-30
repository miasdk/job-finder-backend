"""
API-callable job refresh that can be triggered remotely
"""

from django.core.management.base import BaseCommand
from django.http import HttpResponse
from jobs.models import Job, Company, UserPreferences
try:
    from jobs.scrapers.multi_source_coordinator import MultiSourceCoordinator
except ImportError:
    from jobs.scrapers.api_coordinator import APICoordinator as MultiSourceCoordinator
from jobs.scoring import JobScorer
import json

class Command(BaseCommand):
    help = 'Refresh jobs for production via API call'
    
    def handle(self, *args, **options):
        try:
            # Get preferences
            preferences = UserPreferences.get_active_preferences()
            
            # Clear old jobs with invalid URLs
            old_jobs = Job.objects.filter(source_url__icontains='example.com')
            deleted_count = old_jobs.count()
            old_jobs.delete()
            
            # Scrape fresh jobs
            coordinator = MultiSourceCoordinator(preferences)
            # Try different method names based on available coordinator
            if hasattr(coordinator, 'scrape_priority_sources'):
                scraped_jobs = coordinator.scrape_priority_sources()
            elif hasattr(coordinator, 'fetch_priority_jobs'):
                scraped_jobs = coordinator.fetch_priority_jobs()
            else:
                scraped_jobs = coordinator.fetch_jobs()
            
            # Save with low threshold
            saved_count = 0
            scorer = JobScorer(preferences)
            
            for job_data in scraped_jobs:
                source_url = job_data.get('source_url', '')
                if not source_url or 'example.com' in source_url:
                    continue
                    
                if Job.objects.filter(source_url=source_url).exists():
                    continue
                
                company, created = Company.objects.get_or_create(
                    name=job_data.get('company', 'Unknown'),
                    defaults={'company_type': 'tech', 'location': 'Unknown'}
                )
                
                job = Job.objects.create(
                    title=job_data.get('title', ''),
                    company=company,
                    description=job_data.get('description', ''),
                    location=job_data.get('location', ''),
                    location_type=job_data.get('location_type', 'remote'),
                    source=job_data.get('source', 'Unknown'),
                    source_url=source_url,
                    salary_min=job_data.get('salary_min'),
                    salary_max=job_data.get('salary_max'),
                    experience_level=job_data.get('experience_level', 'entry'),
                    employment_type=job_data.get('job_type', 'full_time'),
                    required_skills=job_data.get('skills', []),
                    posted_date=job_data.get('posted_date'),
                )
                
                job_score = scorer.score_job(job)
                if job_score.total_score >= 1.0:
                    saved_count += 1
                else:
                    job.delete()
            
            result = {
                'success': True,
                'deleted_old_jobs': deleted_count,
                'added_new_jobs': saved_count,
                'total_jobs': Job.objects.count()
            }
            
            self.stdout.write(json.dumps(result))
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e)
            }
            self.stdout.write(json.dumps(error_result))