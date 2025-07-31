"""
Daily job refresh command for maintaining data freshness
This command should be run daily via cron or scheduled task
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job, UserPreferences
from django.core.management import call_command
import json
import logging
from datetime import timedelta

logger = logging.getLogger('jobs')

class Command(BaseCommand):
    help = 'Daily job refresh to maintain data freshness'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force refresh even if recent jobs exist',
        )
        parser.add_argument(
            '--max-jobs',
            type=int,
            default=100,
            help='Maximum number of new jobs to fetch',
        )
    
    def handle(self, *args, **options):
        try:
            preferences = UserPreferences.get_active_preferences()
            
            # Check if we need a refresh
            last_job = Job.objects.filter(is_active=True).order_by('-scraped_at').first()
            needs_refresh = True
            
            if not options['force'] and last_job:
                # If we have jobs from the last 24 hours, skip refresh
                time_diff = timezone.now() - last_job.scraped_at
                if time_diff < timedelta(hours=24):
                    needs_refresh = False
                    
            if not needs_refresh:
                result = {
                    'success': True,
                    'message': 'Jobs are fresh, no refresh needed',
                    'last_refresh': last_job.scraped_at.isoformat() if last_job else None,
                    'total_jobs': Job.objects.filter(is_active=True).count()
                }
                self.stdout.write(json.dumps(result))
                return
            
            self.stdout.write("Starting daily job refresh...")
            
            # Clear old jobs (older than 7 days)
            old_cutoff = timezone.now() - timedelta(days=7)
            old_jobs = Job.objects.filter(scraped_at__lt=old_cutoff)
            deleted_count = old_jobs.count()
            old_jobs.delete()
            
            if deleted_count > 0:
                self.stdout.write(f"Cleaned up {deleted_count} old jobs")
            
            # Call the simple job refresh
            from io import StringIO
            output = StringIO()
            call_command('simple_job_refresh', stdout=output)
            refresh_result = json.loads(output.getvalue())
            
            # Check if we got good results
            if refresh_result.get('success'):
                total_jobs = refresh_result.get('total_jobs', 0)
                new_jobs = refresh_result.get('added_new_jobs', 0)
                
                result = {
                    'success': True,
                    'message': f'Daily refresh completed: {new_jobs} new jobs added',
                    'deleted_old_jobs': deleted_count,
                    'added_new_jobs': new_jobs,
                    'total_jobs': total_jobs,
                    'last_refresh': timezone.now().isoformat()
                }
                
                # Log success
                logger.info(f"Daily job refresh completed: {new_jobs} new jobs, {total_jobs} total")
                
            else:
                result = {
                    'success': False,
                    'error': refresh_result.get('error', 'Unknown error'),
                    'deleted_old_jobs': deleted_count
                }
                
            self.stdout.write(json.dumps(result))
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e)
            }
            self.stdout.write(json.dumps(error_result))
            logger.error(f"Daily job refresh failed: {e}")