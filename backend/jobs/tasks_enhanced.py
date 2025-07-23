"""
Enhanced Celery tasks using the new maximization approach
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from datetime import datetime, timedelta
import io
import json

from .models import Job, JobScore, EmailDigest, UserPreferences
from .scrapers.multi_source_coordinator import MultiSourceCoordinator
from .scoring import JobScorer
from .email_digest import EmailDigestManager

logger = logging.getLogger('jobs')


@shared_task
def maximize_jobs_task():
    """Enhanced background task to maximize job listings using our new approach"""
    try:
        logger.info("Starting enhanced job maximization task")
        
        # Get user preferences
        preferences = UserPreferences.get_active_preferences()
        
        # Check when we last did a full refresh
        last_refresh = Job.objects.filter(is_active=True).order_by('-scraped_at').first()
        
        # If we have jobs less than 6 hours old, do incremental update
        # Otherwise do full maximization
        if last_refresh and (timezone.now() - last_refresh.scraped_at).total_seconds() < 21600:  # 6 hours
            logger.info("Recent jobs found, doing incremental update")
            min_score = 1.0  # Slightly higher threshold for incremental
        else:
            logger.info("No recent jobs, doing full maximization")
            min_score = 0.1  # Very low threshold for maximum results
            
            # Clear old jobs with invalid URLs
            invalid_jobs = Job.objects.filter(source_url__icontains='example.com')
            deleted_count = invalid_jobs.count()
            invalid_jobs.delete()
            logger.info(f"Cleared {deleted_count} invalid jobs")
        
        # Use our multi-source coordinator
        coordinator = MultiSourceCoordinator(preferences)
        
        # Get jobs using priority sources
        scraped_jobs = coordinator.scrape_priority_sources()
        
        if not scraped_jobs:
            logger.warning("No jobs scraped from any source")
            return {
                'status': 'warning',
                'message': 'No jobs found',
                'jobs_added': 0
            }
        
        # Save jobs with permissive scoring
        saved_count = 0
        scorer = JobScorer(preferences)
        
        for job_data in scraped_jobs:
            try:
                source_url = job_data.get('source_url', '')
                if not source_url or 'example.com' in source_url:
                    continue
                    
                # Skip if exists
                if Job.objects.filter(source_url=source_url).exists():
                    continue
                
                # Get or create company
                from .models import Company
                company_name = job_data.get('company', 'Unknown Company')
                company, created = Company.objects.get_or_create(
                    name=company_name,
                    defaults={
                        'company_type': 'tech',
                        'location': job_data.get('location', 'Unknown')
                    }
                )
                
                # Create job
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
                    experience_level=job_data.get('experience_level', 'junior'),
                    employment_type=job_data.get('job_type', 'full_time'),
                    required_skills=job_data.get('skills', []),
                    posted_date=job_data.get('posted_date'),
                    source_job_id=job_data.get('external_id', ''),
                )
                
                # Score and save if above threshold
                job_score = scorer.score_job(job)
                
                if job_score.total_score >= min_score:
                    saved_count += 1
                    logger.debug(f"Added job: {job.title} at {company.name} (Score: {job_score.total_score:.1f})")
                else:
                    job.delete()
                    
            except Exception as e:
                logger.error(f"Error processing job: {e}")
                continue
        
        total_active_jobs = Job.objects.filter(is_active=True).count()
        
        logger.info(f"Job maximization completed: {saved_count} new jobs added, {total_active_jobs} total active jobs")
        
        return {
            'status': 'success',
            'jobs_added': saved_count,
            'total_active_jobs': total_active_jobs,
            'min_score_used': min_score
        }
        
    except Exception as e:
        logger.error(f"Error in maximize_jobs_task: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task
def smart_job_refresh_task():
    """Smart task that adapts to user preferences changes"""
    try:
        logger.info("Starting smart job refresh based on user preferences")
        
        preferences = UserPreferences.get_active_preferences()
        
        # Check if preferences were recently updated (last 2 hours)
        if preferences.updated_at > timezone.now() - timedelta(hours=2):
            logger.info("Recent preference changes detected, doing targeted refresh")
            
            # Clear existing jobs and do fresh scrape with new preferences
            old_count = Job.objects.count()
            Job.objects.all().delete()
            
            # Use maximize command with new preferences
            result = maximize_jobs_task.delay()
            
            logger.info(f"Preference-based refresh: cleared {old_count} old jobs, refreshing with new preferences")
            
            return {
                'status': 'success',
                'type': 'preference_refresh',
                'cleared_jobs': old_count
            }
        else:
            # Regular incremental update
            return maximize_jobs_task()
            
    except Exception as e:
        logger.error(f"Error in smart_job_refresh_task: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task
def enhanced_daily_automation_task():
    """Enhanced daily automation that uses our maximization approach"""
    try:
        logger.info("Starting enhanced daily automation sequence")
        
        # 1. Smart job refresh (adapts to preference changes)
        refresh_result = smart_job_refresh_task()
        
        # 2. Check job quality and quantity
        total_jobs = Job.objects.filter(is_active=True).count()
        
        # If we have very few jobs, do emergency maximization
        if total_jobs < 20:
            logger.warning(f"Low job count ({total_jobs}), triggering emergency maximization")
            emergency_result = call_command('maximize_jobs', '--min-score=0.05')
        
        # 3. Send digest if it's evening
        current_hour = timezone.now().hour
        if current_hour == 19:  # 7 PM
            from .tasks import send_daily_digest_task
            digest_result = send_daily_digest_task.delay()
        
        # 4. Weekly cleanup
        if timezone.now().weekday() == 6:  # Sunday
            from .tasks import cleanup_old_jobs_task
            cleanup_result = cleanup_old_jobs_task.delay()
        
        logger.info(f"Enhanced daily automation completed: {total_jobs} active jobs")
        
        return {
            'status': 'success',
            'active_jobs': total_jobs,
            'refresh_result': refresh_result
        }
        
    except Exception as e:
        logger.error(f"Error in enhanced_daily_automation_task: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


@shared_task  
def user_preference_trigger_task():
    """Task triggered when user preferences change"""
    try:
        logger.info("User preferences changed, triggering smart refresh")
        
        # Wait a moment for any additional preference changes
        from time import sleep
        sleep(30)
        
        # Trigger smart refresh
        result = smart_job_refresh_task.delay()
        
        return {
            'status': 'success',
            'message': 'Preference change refresh triggered'
        }
        
    except Exception as e:
        logger.error(f"Error in user_preference_trigger_task: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }