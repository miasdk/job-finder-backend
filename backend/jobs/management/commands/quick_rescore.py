"""
Quick job rescoring command - rescores existing jobs with updated preferences
Much faster than fetching new jobs
"""

from django.core.management.base import BaseCommand
from jobs.models import Job, UserPreferences
from jobs.scoring import JobScorer
import json
import logging

logger = logging.getLogger('jobs')

class Command(BaseCommand):
    help = 'Quick rescore of existing jobs with updated preferences'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of jobs to rescore (default: 50)',
        )
    
    def handle(self, *args, **options):
        try:
            preferences = UserPreferences.get_active_preferences()
            limit = options['limit']
            
            # Get recent active jobs
            jobs = Job.objects.filter(is_active=True).order_by('-posted_date')[:limit]
            
            if not jobs:
                result = {
                    'success': True,
                    'message': 'No jobs to rescore',
                    'rescored_jobs': 0,
                    'total_jobs': 0
                }
                self.stdout.write(json.dumps(result))
                return
            
            # Rescore jobs with updated preferences
            scorer = JobScorer(preferences)
            rescored_count = 0
            
            for job in jobs:
                try:
                    scorer.score_job(job)
                    rescored_count += 1
                except Exception as e:
                    logger.warning(f"Failed to score job {job.id}: {e}")
                    continue
            
            total_jobs = Job.objects.filter(is_active=True).count()
            
            result = {
                'success': True,
                'message': f'Rescored {rescored_count} jobs with updated preferences',
                'rescored_jobs': rescored_count,
                'total_jobs': total_jobs,
                'preferences_updated': preferences.updated_at.isoformat()
            }
            
            logger.info(f"Quick rescore completed: {rescored_count} jobs rescored")
            self.stdout.write(json.dumps(result))
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e)
            }
            self.stdout.write(json.dumps(error_result))
            logger.error(f"Quick rescore failed: {e}")