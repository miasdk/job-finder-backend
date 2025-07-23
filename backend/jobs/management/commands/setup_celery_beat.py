from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

class Command(BaseCommand):
    help = 'Set up periodic Celery tasks for job automation'

    def handle(self, *args, **options):
        # Create crontab schedules
        
        # Daily at 9 AM EST - Scrape and score jobs
        morning_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=14,  # 9 AM EST = 14 UTC
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        # Daily at 7 PM EST - Send email digest
        evening_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=0,  # 7 PM EST = 00 UTC next day
            day_of_week='*',
            day_of_month='*', 
            month_of_year='*',
        )
        
        # Weekly cleanup - Sunday at 2 AM EST
        weekly_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour=7,  # 2 AM EST = 7 UTC
            day_of_week=0,  # Sunday
            day_of_month='*',
            month_of_year='*',
        )
        
        # Health check - Every 6 hours
        health_schedule, created = CrontabSchedule.objects.get_or_create(
            minute=0,
            hour='*/6',  # Every 6 hours
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        # Create periodic tasks
        
        # Daily job scraping
        PeriodicTask.objects.update_or_create(
            name='Daily Job Scraping',
            defaults={
                'task': 'jobs.tasks.scrape_jobs_task',
                'crontab': morning_schedule,
                'args': json.dumps([]),
                'kwargs': json.dumps({
                    'source': 'indeed',
                    'location': 'New York, NY',
                    'limit': 30
                }),
                'enabled': True,
            }
        )
        
        # Daily job scoring
        PeriodicTask.objects.update_or_create(
            name='Daily Job Scoring',
            defaults={
                'task': 'jobs.tasks.score_jobs_task',
                'crontab': morning_schedule,
                'args': json.dumps([]),
                'kwargs': json.dumps({'rescore_all': False}),
                'enabled': True,
            }
        )
        
        # Daily email digest
        PeriodicTask.objects.update_or_create(
            name='Daily Email Digest',
            defaults={
                'task': 'jobs.tasks.send_daily_digest_task',
                'crontab': evening_schedule,
                'args': json.dumps([]),
                'kwargs': json.dumps({}),
                'enabled': True,
            }
        )
        
        # Weekly cleanup
        PeriodicTask.objects.update_or_create(
            name='Weekly Job Cleanup',
            defaults={
                'task': 'jobs.tasks.cleanup_old_jobs_task',
                'crontab': weekly_schedule,
                'args': json.dumps([]),
                'kwargs': json.dumps({'days': 30}),
                'enabled': True,
            }
        )
        
        # Health check
        PeriodicTask.objects.update_or_create(
            name='System Health Check',
            defaults={
                'task': 'jobs.tasks.health_check_task',
                'crontab': health_schedule,
                'args': json.dumps([]),
                'kwargs': json.dumps({}),
                'enabled': True,
            }
        )
        
        self.stdout.write(
            self.style.SUCCESS('Successfully set up periodic tasks:')
        )
        self.stdout.write('• Daily Job Scraping - 9 AM EST')
        self.stdout.write('• Daily Job Scoring - 9 AM EST')  
        self.stdout.write('• Daily Email Digest - 7 PM EST')
        self.stdout.write('• Weekly Job Cleanup - Sunday 2 AM EST')
        self.stdout.write('• System Health Check - Every 6 hours')
        
        self.stdout.write('\nTo start the scheduler, run:')
        self.stdout.write('celery -A job_finder beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler')